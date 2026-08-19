#!/usr/bin/env python3
"""Build the restricted full-field CRT loan-period foundation as Parquet."""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import shutil
import tempfile
import time
import zipfile
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import duckdb

from intake_clarity_archive import LLD_FILE, expected_period, normalized_deal_id
from intake_real_clarity import sha256


ROOT = Path(__file__).resolve().parents[1]
RESTRICTED = ROOT / "data" / "restricted"
DEFAULT_OUTPUT = RESTRICTED / "full-data"
DEFAULT_QUALITY_REPORT = ROOT / "data" / "derived" / "full_data_quality_report.json"
ALLOWED_WIDTHS = {89, 90, 93}
LAYOUT = "Freddie Mac CRT Reference Pool Disclosure File Layouts v4.2, effective July 2026"

FIELD_NAMES = (
    "period",
    "reference_pool_number",
    "loan_identifier",
    "amortization_type",
    "seller_name",
    "property_state",
    "postal_code_3_digit",
    "metropolitan_statistical_area_or_division",
    "first_payment_date",
    "maturity_date",
    "original_loan_term",
    "original_interest_rate",
    "original_upb",
    "upb_at_issuance",
    "loan_purpose",
    "channel",
    "property_type",
    "number_of_units",
    "occupancy_status",
    "number_of_borrowers",
    "first_time_homebuyer_indicator",
    "prepayment_penalty_indicator",
    "classic_fico",
    "original_ltv",
    "original_cltv",
    "original_dti",
    "mortgage_insurance_percent",
    "updated_credit_score_at_issuance",
    "special_eligibility_program",
    "mortgage_insurance_type",
    "filler_31",
    "disaster_grace_period",
    "servicer_name",
    "loan_age",
    "remaining_months_to_legal_maturity",
    "adjusted_remaining_months_to_maturity",
    "current_loan_delinquency_status",
    "payment_history",
    "current_interest_rate",
    "current_actual_upb",
    "current_interest_bearing_upb",
    "upb_at_removal",
    "zero_balance_code",
    "zero_balance_effective_date",
    "defect_settlement_date",
    "modification_flag",
    "delinquency_due_to_disaster",
    "ddlpi",
    "bankruptcy_flag",
    "foreclosure_referral_date",
    "net_sales_proceeds",
    "mi_credit",
    "taxes_and_insurance",
    "legal_costs",
    "maintenance_and_preservation_costs",
    "bankruptcy_cramdown_costs",
    "miscellaneous_expenses",
    "miscellaneous_credits",
    "mi_cancellation_indicator",
    "estimated_ltv",
    "filler_61",
    "updated_credit_score_1",
    "updated_credit_score_2",
    "number_of_modifications",
    "modification_program",
    "modification_type",
    "modification_first_payment_date",
    "modification_dti",
    "total_capitalized_amount",
    "interest_rate_step_indicator",
    "first_step_rate_adjustment_date",
    "first_step_rate",
    "second_step_rate_adjustment_date",
    "second_step_rate",
    "third_step_rate_adjustment_date",
    "third_step_rate",
    "fourth_step_rate_adjustment_date",
    "fourth_step_rate",
    "fifth_step_rate_adjustment_date",
    "fifth_step_rate",
    "delinquent_accrued_interest",
    "current_period_modification_costs",
    "updated_credit_score_3",
    "property_valuation_method",
    "group_number",
    "enhanced_relief_refi_indicator",
    "borrower_assistance_plan",
    "payment_deferral_flag",
    "distressed_principal_balance_flag",
    "temporary_subsidy_buydown_plan_type",
    "vantagescore_4",
    "actual_loss",
    "cumulative_modification_costs",
)


def sql_literal(value: str | Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def standard_members(package: zipfile.ZipFile) -> tuple[list[zipfile.ZipInfo], list[dict[str, object]]]:
    infos = [info for info in package.infolist() if not info.is_dir()]
    candidates: dict[tuple[str, str], list[zipfile.ZipInfo]] = defaultdict(list)
    parsed: dict[str, object] = {}
    rejected: list[dict[str, object]] = []
    for info in infos:
        match = LLD_FILE.fullmatch(Path(info.filename).name)
        if match is None:
            rejected.append({"source_member": info.filename, "reason": "not-standard-monthly-lld"})
            continue
        parsed[info.filename] = match
        key = (normalized_deal_id(match.group("short_deal")), expected_period(match.group("as_of")))
        candidates[key].append(info)
    accepted: list[zipfile.ZipInfo] = []
    for info in infos:
        match = parsed.get(info.filename)
        if match is None:
            continue
        key = (normalized_deal_id(match.group("short_deal")), expected_period(match.group("as_of")))
        if len(candidates[key]) > 1:
            rejected.append(
                {
                    "source_member": info.filename,
                    "reason": "duplicate-or-revised-disclosure",
                    "revision_candidates": [candidate.filename for candidate in candidates[key]],
                }
            )
        else:
            accepted.append(info)
    return accepted, rejected


def stage_member(
    package: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    staged_path: Path,
    expected_file_period: str,
) -> tuple[int, int]:
    widths: Counter[int] = Counter()
    loan_ids: set[str] = set()
    records = 0
    with (
        package.open(info) as raw,
        io.TextIOWrapper(raw, encoding="utf-8", newline="") as source,
        staged_path.open("w", encoding="utf-8", newline="") as target,
    ):
        writer = csv.writer(target, delimiter="|", lineterminator="\n")
        for line_number, row in enumerate(csv.reader(source, delimiter="|"), start=1):
            width = len(row)
            if width not in ALLOWED_WIDTHS:
                raise ValueError(f"{info.filename}:{line_number} has {width} fields; expected one of {sorted(ALLOWED_WIDTHS)}")
            if row[0].strip() != expected_file_period:
                raise ValueError(
                    f"{info.filename}:{line_number} period {row[0]!r} conflicts with filename period {expected_file_period}"
                )
            if not row[1].strip() or not row[2].strip():
                raise ValueError(f"{info.filename}:{line_number} is missing reference-pool number or loan identifier")
            loan_key = f"{row[1].strip()}|{row[2].strip()}"
            if loan_key in loan_ids:
                raise ValueError(f"{info.filename}:{line_number} duplicates loan identifier within the reference pool")
            loan_ids.add(loan_key)
            widths[width] += 1
            records += 1
            writer.writerow(row + [""] * (len(FIELD_NAMES) - width))
    if len(widths) != 1:
        raise ValueError(f"{info.filename} mixes schema widths: {dict(widths)}")
    return records, next(iter(widths))


def write_partition(
    connection: duckdb.DuckDBPyConnection,
    staged_path: Path,
    parquet_path: Path,
    deal_id: str,
    source_member: str,
    source_field_count: int,
) -> None:
    columns = "{" + ",".join(f"{sql_literal(name)}:'VARCHAR'" for name in FIELD_NAMES) + "}"
    query = f"""
        COPY (
            SELECT
                {sql_literal(deal_id)}::VARCHAR AS deal_id,
                {sql_literal(source_member)}::VARCHAR AS source_member,
                {source_field_count}::UTINYINT AS source_field_count,
                *
            FROM read_csv(
                {sql_literal(staged_path)},
                delim='|',
                header=false,
                columns={columns},
                strict_mode=true
            )
        ) TO {sql_literal(parquet_path)} (
            FORMAT PARQUET,
            COMPRESSION ZSTD,
            ROW_GROUP_SIZE 100000
        )
    """
    connection.execute(query)


def field_profile(connection: duckdb.DuckDBPyConnection, parquet_glob: str, records: int) -> list[dict[str, object]]:
    expressions = ",".join(f'count("{name}") AS "{name}"' for name in FIELD_NAMES)
    values = connection.execute(
        f"SELECT {expressions} FROM read_parquet({sql_literal(parquet_glob)}, hive_partitioning=false)"
    ).fetchone()
    assert values is not None
    return [
        {
            "position": position,
            "field": name,
            "non_null_records": int(non_null),
            "non_null_rate": round(int(non_null) / records, 8) if records else 0.0,
        }
        for position, (name, non_null) in enumerate(zip(FIELD_NAMES, values, strict=True), start=1)
    ]


def reference_reconciliation(archive_sha256: str, accepted_files: int, records: int) -> dict[str, object]:
    manifest_path = ROOT / "data" / "derived" / "real_intake_manifest.json"
    quality_path = ROOT / "data" / "derived" / "real_intake_quality_report.json"
    if not manifest_path.exists() or not quality_path.exists():
        return {"status": "unavailable", "reason": "existing aggregate intake evidence is missing"}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("source_archive_sha256") != archive_sha256:
        return {"status": "not-applicable", "reason": "source hash differs from the verified aggregate archive"}
    quality = json.loads(quality_path.read_text(encoding="utf-8"))
    expected_files = int(quality["accepted_files"])
    expected_records = int(quality["aggregate_totals"]["records"])
    return {
        "status": "pass" if (accepted_files, records) == (expected_files, expected_records) else "fail",
        "expected_files": expected_files,
        "actual_files": accepted_files,
        "expected_records": expected_records,
        "actual_records": records,
    }


def build(archive: Path, output_dir: Path, quality_report_path: Path) -> dict[str, object]:
    started = time.perf_counter()
    archive_sha256 = sha256(archive)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    quality_report_path.parent.mkdir(parents=True, exist_ok=True)
    build_dir = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}-building-", dir=output_dir.parent))
    staging_dir = build_dir / "staging"
    loan_period_dir = build_dir / "loan_period"
    staging_dir.mkdir()
    loan_period_dir.mkdir()
    connection = duckdb.connect()
    partitions: list[dict[str, object]] = []
    width_counts: Counter[int] = Counter()
    total_records = 0
    try:
        with zipfile.ZipFile(archive) as package:
            accepted, rejected = standard_members(package)
            if not accepted:
                raise ValueError("archive has no unambiguous standard monthly loan-level members")
            for index, info in enumerate(accepted, start=1):
                match = LLD_FILE.fullmatch(Path(info.filename).name)
                assert match is not None
                deal_id = normalized_deal_id(match.group("short_deal"))
                period = expected_period(match.group("as_of"))
                staged_path = staging_dir / f"{index:03d}.txt"
                records, source_field_count = stage_member(package, info, staged_path, period)
                partition_dir = loan_period_dir / f"deal_id={deal_id}" / f"reporting_period={period}"
                partition_dir.mkdir(parents=True, exist_ok=True)
                parquet_path = partition_dir / "data.parquet"
                write_partition(connection, staged_path, parquet_path, deal_id, info.filename, source_field_count)
                staged_path.unlink()
                actual_records = int(
                    connection.execute(
                        f"SELECT count(*) FROM read_parquet({sql_literal(parquet_path)}, hive_partitioning=false)"
                    ).fetchone()[0]
                )
                if actual_records != records:
                    raise ValueError(f"{info.filename} staged {records} rows but Parquet contains {actual_records}")
                total_records += records
                width_counts[source_field_count] += records
                partitions.append(
                    {
                        "source_member": info.filename,
                        "deal_id": deal_id,
                        "reporting_period": period,
                        "source_field_count": source_field_count,
                        "records": records,
                        "parquet_path": str(parquet_path.relative_to(build_dir)),
                        "parquet_bytes": parquet_path.stat().st_size,
                        "parquet_sha256": sha256(parquet_path),
                    }
                )
                if index == 1 or index % 25 == 0 or index == len(accepted):
                    print(f"[{index}/{len(accepted)}] {total_records:,} rows normalized", flush=True)
        parquet_glob = str(loan_period_dir / "**" / "*.parquet")
        profile = field_profile(connection, parquet_glob, total_records)
        reconciliation = reference_reconciliation(archive_sha256, len(partitions), total_records)
        if reconciliation["status"] == "fail":
            raise ValueError(f"full-data reconciliation failed: {reconciliation}")
        manifest = {
            "manifest_version": 1,
            "build_date": date.today().isoformat(),
            "source_archive_name": archive.name,
            "source_archive_sha256": archive_sha256,
            "layout": LAYOUT,
            "allowed_source_field_counts": sorted(ALLOWED_WIDTHS),
            "fields_retained": len(FIELD_NAMES),
            "storage": "partitioned-parquet-zstd",
            "data_classification": "restricted-loan-level",
            "public_release_allowed": False,
            "accepted_files": len(partitions),
            "rejected_members": rejected,
            "records": total_records,
            "source_field_count_records": {str(width): count for width, count in sorted(width_counts.items())},
            "partitions": partitions,
        }
        (build_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        quality = {
            "report_version": 1,
            "source_archive_sha256": archive_sha256,
            "layout": LAYOUT,
            "accepted_files": len(partitions),
            "records": total_records,
            "deals": len({partition["deal_id"] for partition in partitions}),
            "reporting_periods": len({partition["reporting_period"] for partition in partitions}),
            "first_reporting_period": min(str(partition["reporting_period"]) for partition in partitions),
            "last_reporting_period": max(str(partition["reporting_period"]) for partition in partitions),
            "source_field_count_records": manifest["source_field_count_records"],
            "duplicate_loan_keys_within_file": 0,
            "reference_reconciliation": reconciliation,
            "field_profile": profile,
            "public_exclusion_check": {
                "status": "pass",
                "restricted_output_root": str(output_dir.relative_to(ROOT)) if output_dir.is_relative_to(ROOT) else str(output_dir),
                "public_release_allowed": False,
            },
            "runtime_ms": round((time.perf_counter() - started) * 1000, 3),
        }
        quality_report_path.write_text(json.dumps(quality, indent=2) + "\n", encoding="utf-8")
        (build_dir / "quality_report.json").write_text(json.dumps(quality, indent=2) + "\n", encoding="utf-8")
        staging_dir.rmdir()
        build_dir.replace(output_dir)
        return quality
    except Exception:
        shutil.rmtree(build_dir, ignore_errors=True)
        raise
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="Approved local Clarity CRT ZIP package")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--quality-report", type=Path, default=DEFAULT_QUALITY_REPORT)
    parser.add_argument("--allow-nonrestricted-output", action="store_true", help="Tests only: allow output outside data/restricted")
    args = parser.parse_args()
    archive = args.archive.resolve()
    output_dir = args.output_dir.resolve()
    quality_report = args.quality_report.resolve()
    if not archive.is_file() or archive.suffix.lower() != ".zip":
        raise SystemExit(f"ZIP source archive not found: {archive}")
    if not args.allow_nonrestricted_output and not output_dir.is_relative_to(RESTRICTED.resolve()):
        raise SystemExit(f"full-data output must remain under {RESTRICTED}")
    if output_dir.exists():
        raise SystemExit(f"output already exists; M7 builder will not overwrite it: {output_dir}")
    quality = build(archive, output_dir, quality_report)
    print(
        f"Built {quality['accepted_files']} partitions and {quality['records']:,} restricted rows in {output_dir}",
        flush=True,
    )


if __name__ == "__main__":
    main()
