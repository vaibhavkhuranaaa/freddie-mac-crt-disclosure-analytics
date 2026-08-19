#!/usr/bin/env python3
"""Stream an approved Clarity CRT ZIP into aggregate-only reference-pool metrics.

The generated report deliberately contains file-level operational evidence only:
names, counts, status totals, and aggregate balances.  It never emits loan rows
or identifiers from those rows.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import time
import zipfile
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from intake_real_clarity import (
    CURRENT_UPB_INDEX, DELINQUENCY_INDEX, MIN_FIELDS, PERIOD_INDEX, POOL_INDEX,
    numeric, sha256, status_bucket,
)


ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"
LLD_FILE = re.compile(r"^(?P<short_deal>\d{2}[A-Z]+\d+)_(?P<as_of>\d{8})_lld\.txt$")


def normalized_deal_id(short_deal: str) -> str:
    return f"20{short_deal[:2]}-{short_deal[2:]}"


def expected_period(as_of: str) -> str:
    return as_of[:6]


def continuity(periods: set[str]) -> dict[str, object]:
    if not periods:
        return {"first_period": None, "last_period": None, "missing_periods": [], "continuous": False}
    first, last = min(periods), max(periods)
    year, month = int(first[:4]), int(first[4:])
    expected: list[str] = []
    while f"{year:04d}{month:02d}" <= last:
        expected.append(f"{year:04d}{month:02d}")
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    missing = [period for period in expected if period not in periods]
    return {"first_period": first, "last_period": last, "missing_periods": missing, "continuous": not missing}


def load_official_totals(path: Path | None) -> dict[str, dict[str, float]] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("files", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("official totals JSON must be a list or an object with a files list")
    result: dict[str, dict[str, float]] = {}
    for row in rows:
        if not isinstance(row, dict) or "file_name" not in row:
            raise ValueError("each official totals entry needs file_name")
        result[str(row["file_name"])] = {key: float(row[key]) for key in ("records", "current_upb") if key in row}
    return result


def validate_official_total(file_report: dict[str, object], official: dict[str, dict[str, float]] | None) -> dict[str, object]:
    if official is None:
        return {"status": "unavailable", "reason": "No official file-level totals were supplied with the authorized archive.", "fallback_checks": ["file record counts reconcile to aggregate records", "D60+ UPB <= D30+ UPB <= current UPB"]}
    expected = official.get(str(file_report["file_name"]))
    if expected is None:
        return {"status": "unavailable", "reason": "Official totals did not include this accepted file."}
    mismatches = {key: {"expected": value, "actual": file_report[key]} for key, value in expected.items() if float(file_report[key]) != value}
    return {"status": "pass" if not mismatches else "fail", "mismatches": mismatches}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="Approved local Clarity CRT ZIP package")
    parser.add_argument("--deal", action="append", help="Optional portal deal ID filter; omit to process every standard *_lld.txt file in the archive")
    parser.add_argument("--official-totals", type=Path, help="Optional official file-level JSON totals (file_name, records, current_upb)")
    parser.add_argument("--terms-version", default="CRT Disclosure File Terms, reviewed by project owner")
    parser.add_argument("--output-dir", type=Path, default=DERIVED)
    args = parser.parse_args()
    started = time.perf_counter()
    archive = args.archive.resolve()
    approved_deals = set(args.deal or [])
    if not archive.is_file() or archive.suffix.lower() != ".zip":
        raise SystemExit(f"ZIP source archive not found: {archive}")
    official_totals = load_official_totals(args.official_totals)

    aggregates: dict[tuple[str, str, str], dict[str, float | int]] = defaultdict(lambda: {"current_upb": 0.0, "d30_plus_upb": 0.0, "d60_plus_upb": 0.0, "ra_count": 0, "xx_count": 0, "records": 0})
    file_reports: list[dict[str, object]] = []
    accepted_periods: set[str] = set()
    with zipfile.ZipFile(archive) as package:
        infos = [info for info in package.infolist() if not info.is_dir()]
        candidates: dict[tuple[str, str], list[zipfile.ZipInfo]] = defaultdict(list)
        parsed: dict[str, re.Match[str]] = {}
        for info in infos:
            match = LLD_FILE.fullmatch(Path(info.filename).name)
            if match is not None:
                parsed[info.filename] = match
                candidates[(normalized_deal_id(match.group("short_deal")), expected_period(match.group("as_of")))].append(info)
        for info in infos:
            match = parsed.get(info.filename)
            report: dict[str, object] = {"file_name": info.filename, "archive_bytes": info.file_size}
            if match is None:
                report.update({"status": "rejected", "reason": "not-standard-monthly-lld"})
                file_reports.append(report)
                continue
            deal_id, period = normalized_deal_id(match.group("short_deal")), expected_period(match.group("as_of"))
            report.update({"deal_id": deal_id, "file_period": period})
            if approved_deals and deal_id not in approved_deals:
                report.update({"status": "rejected", "reason": "outside-requested-deal-scope"})
                file_reports.append(report)
                continue
            if len(candidates[(deal_id, period)]) > 1:
                report.update({"status": "rejected", "reason": "duplicate-or-revised-disclosure", "revision_candidates": [item.filename for item in candidates[(deal_id, period)]]})
                file_reports.append(report)
                continue
            local_aggregates: dict[tuple[str, str, str], dict[str, float | int]] = defaultdict(lambda: {"current_upb": 0.0, "d30_plus_upb": 0.0, "d60_plus_upb": 0.0, "ra_count": 0, "xx_count": 0, "records": 0})
            statuses: Counter[str] = Counter()
            zero_upb_records = 0
            try:
                with package.open(info) as raw, io.TextIOWrapper(raw, encoding="utf-8", newline="") as handle:
                    for line_number, row in enumerate(csv.reader(handle, delimiter="|"), start=1):
                        if len(row) < MIN_FIELDS:
                            raise ValueError(f"{info.filename}:{line_number} has {len(row)} fields; expected at least {MIN_FIELDS}")
                        row_period, pool = row[PERIOD_INDEX].strip(), row[POOL_INDEX].strip()
                        if len(row_period) != 6 or not row_period.isdigit() or not pool:
                            raise ValueError(f"{info.filename}:{line_number} has invalid period or reference-pool number")
                        if row_period != period:
                            raise ValueError(f"{info.filename}:{line_number} period {row_period} conflicts with filename period {period}")
                        current_upb = numeric(row[CURRENT_UPB_INDEX])
                        if current_upb < 0:
                            raise ValueError(f"{info.filename}:{line_number} has negative Current Actual UPB")
                        status = row[DELINQUENCY_INDEX].strip().upper() or "XX"
                        bucket = status_bucket(status)
                        statuses[status] += 1
                        if current_upb == 0:
                            zero_upb_records += 1
                        target = local_aggregates[(row_period, deal_id, pool)]
                        target["records"] += 1
                        target["current_upb"] += current_upb
                        if bucket is None:
                            target["ra_count" if status == "RA" else "xx_count"] += 1
                        elif bucket >= 1:
                            target["d30_plus_upb"] += current_upb
                            if bucket >= 2:
                                target["d60_plus_upb"] += current_upb
            except (UnicodeDecodeError, ValueError) as error:
                report.update({"status": "rejected", "reason": "content-validation-failed", "detail": str(error)})
                file_reports.append(report)
                continue
            totals = {key: sum(float(value[key]) for value in local_aggregates.values()) for key in ("current_upb", "d30_plus_upb", "d60_plus_upb", "records", "ra_count", "xx_count")}
            report.update({"status": "accepted", "aggregate_groups": len(local_aggregates), "zero_upb_records": zero_upb_records, "status_counts": dict(sorted(statuses.items())), **totals})
            report["official_reconciliation"] = validate_official_total(report, official_totals)
            if report["official_reconciliation"]["status"] == "fail":
                report.update({"status": "rejected", "reason": "official-total-reconciliation-failed"})
                file_reports.append(report)
                continue
            for key, value in local_aggregates.items():
                for measure, amount in value.items():
                    aggregates[key][measure] += amount
            accepted_periods.add(period)
            file_reports.append(report)
    accepted = [report for report in file_reports if report["status"] == "accepted"]
    if not accepted:
        raise SystemExit("no standard *_lld.txt files passed intake validation")
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "real_aggregate.csv"
    fields = ["reporting_period", "deal_id", "reference_pool_number", "current_upb", "d30_plus_upb", "d60_plus_upb", "d30_plus_rate", "d60_plus_rate", "records_aggregated", "ra_records", "xx_records", "source_classification"]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for (period, deal_id, pool), value in sorted(aggregates.items()):
            current_upb = float(value["current_upb"])
            writer.writerow({"reporting_period": period, "deal_id": deal_id, "reference_pool_number": pool, "current_upb": round(current_upb, 2), "d30_plus_upb": round(float(value["d30_plus_upb"]), 2), "d60_plus_upb": round(float(value["d60_plus_upb"]), 2), "d30_plus_rate": round(float(value["d30_plus_upb"]) / current_upb, 8) if current_upb else 0.0, "d60_plus_rate": round(float(value["d60_plus_upb"]) / current_upb, 8) if current_upb else 0.0, "records_aggregated": value["records"], "ra_records": value["ra_count"], "xx_records": value["xx_count"], "source_classification": "approved-real-disclosure"})
    aggregate_totals = {key: sum(float(value[key]) for value in aggregates.values()) for key in ("current_upb", "d30_plus_upb", "d60_plus_upb", "records", "ra_count", "xx_count")}
    fallback_passed = all(float(report["records"]) >= 0 and float(report["d60_plus_upb"]) <= float(report["d30_plus_upb"]) <= float(report["current_upb"]) for report in accepted) and sum(float(report["records"]) for report in accepted) == aggregate_totals["records"]
    quality_report = {"report_version": 1, "reporting_period_continuity": continuity(accepted_periods), "revision_policy": "Reject every same deal/file-period candidate unless an approved source identifies a canonical revision; do not silently select one.", "official_total_reconciliation": {"status": "tested-unavailable" if official_totals is None else "performed", "fallback_checks_passed": fallback_passed}, "accepted_files": len(accepted), "rejected_files": len(file_reports) - len(accepted), "aggregate_totals": aggregate_totals, "runtime_ms": round((time.perf_counter() - started) * 1000, 3), "files": file_reports}
    report_path = output_dir / "real_intake_quality_report.json"
    report_path.write_text(json.dumps(quality_report, indent=2) + "\n", encoding="utf-8")
    manifest = {"intake_date": date.today().isoformat(), "source_archive_name": archive.name, "source_archive_sha256": sha256(archive), "terms_version": args.terms_version, "layout": "Freddie Mac CRT Reference Pool Disclosure File Layouts v4.2, effective July 2026", "intake_scope": "full-standard-lld-archive" if not approved_deals else "selected-standard-lld-files", "approved_deals": sorted(approved_deals) if approved_deals else "all standard LLD deals in archive", "loan_level_files_processed": len(accepted), "fields_read": ["Period", "Reference Pool Number", "Current Loan Delinquency Status", "Current Actual UPB"], "fields_retained": [], "derived_output": str(output.relative_to(ROOT)) if output.is_relative_to(ROOT) else str(output), "aggregate_groups": len(aggregates), "quality_report": str(report_path.relative_to(ROOT)) if report_path.is_relative_to(ROOT) else str(report_path), "quality_report_sha256": sha256(report_path), "official_total_reconciliation_status": quality_report["official_total_reconciliation"]["status"], "runtime_ms": quality_report["runtime_ms"]}
    (output_dir / "real_intake_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Derived {len(aggregates)} aggregate group(s) from {len(accepted)} accepted file(s) to {output}")


if __name__ == "__main__":
    main()
