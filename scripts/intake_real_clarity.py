#!/usr/bin/env python3
"""Aggregate an approved Freddie Mac CRT Clarity loan-level disclosure without emitting row-level data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"
MIN_FIELDS = 40
PERIOD_INDEX = 0
POOL_INDEX = 1
DELINQUENCY_INDEX = 36
CURRENT_UPB_INDEX = 39


def numeric(value: str) -> float:
    value = value.strip().replace(",", "")
    return float(value) if value else 0.0


def status_bucket(status: str) -> int | None:
    value = status.strip().upper()
    if value in {"RA", "XX", ""}:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"unexpected Current Loan Delinquency Status: {status!r}") from exc


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Approved local Clarity loan-level disclosure file")
    parser.add_argument("--deal-id", required=True)
    parser.add_argument("--program", required=True, choices=("STACR", "ACIS"))
    parser.add_argument("--terms-version", default="CRT Disclosure File Terms, reviewed by project owner")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DERIVED,
        help="Local directory for aggregate-only outputs (default: data/derived)",
    )
    args = parser.parse_args()
    source = args.source.resolve()
    if not source.is_file():
        raise SystemExit(f"source file not found: {source}")

    aggregates: dict[tuple[str, str], dict[str, float | int]] = defaultdict(
        lambda: {"current_upb": 0.0, "d30_plus_upb": 0.0, "d60_plus_upb": 0.0, "ra_count": 0, "xx_count": 0, "records": 0}
    )
    with source.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter="|")
        for line_number, row in enumerate(reader, start=1):
            if len(row) < MIN_FIELDS:
                raise ValueError(f"line {line_number} has {len(row)} fields; expected at least {MIN_FIELDS}")
            period, pool = row[PERIOD_INDEX].strip(), row[POOL_INDEX].strip()
            if len(period) != 6 or not period.isdigit() or not pool:
                raise ValueError(f"line {line_number} has invalid period or reference-pool number")
            current_upb = numeric(row[CURRENT_UPB_INDEX])
            if current_upb < 0:
                raise ValueError(f"line {line_number} has negative Current Actual UPB")
            bucket = status_bucket(row[DELINQUENCY_INDEX])
            target = aggregates[(period, pool)]
            target["records"] += 1
            target["current_upb"] += current_upb
            if bucket is None:
                if row[DELINQUENCY_INDEX].strip().upper() == "RA":
                    target["ra_count"] += 1
                else:
                    target["xx_count"] += 1
            elif bucket >= 1:
                target["d30_plus_upb"] += current_upb
                if bucket >= 2:
                    target["d60_plus_upb"] += current_upb

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "real_aggregate.csv"
    with output.open("w", encoding="utf-8", newline="") as handle:
        fields = ["reporting_period", "deal_id", "program", "reference_pool_number", "current_upb", "d30_plus_upb", "d60_plus_upb", "d30_plus_rate", "d60_plus_rate", "records_aggregated", "ra_records", "xx_records", "source_classification"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for (period, pool), value in sorted(aggregates.items()):
            current_upb = float(value["current_upb"])
            writer.writerow({
                "reporting_period": period,
                "deal_id": args.deal_id,
                "program": args.program,
                "reference_pool_number": pool,
                "current_upb": round(current_upb, 2),
                "d30_plus_upb": round(float(value["d30_plus_upb"]), 2),
                "d60_plus_upb": round(float(value["d60_plus_upb"]), 2),
                "d30_plus_rate": round(float(value["d30_plus_upb"]) / current_upb, 8) if current_upb else 0.0,
                "d60_plus_rate": round(float(value["d60_plus_upb"]) / current_upb, 8) if current_upb else 0.0,
                "records_aggregated": value["records"],
                "ra_records": value["ra_count"],
                "xx_records": value["xx_count"],
                "source_classification": "approved-real-disclosure",
            })
    manifest = {
        "intake_date": date.today().isoformat(),
        "source_file_name": source.name,
        "source_sha256": sha256(source),
        "terms_version": args.terms_version,
        "layout": "Freddie Mac CRT Reference Pool Disclosure File Layouts v4.2, effective July 2026",
        "fields_read": ["Period", "Reference Pool Number", "Current Loan Delinquency Status", "Current Actual UPB"],
        "fields_retained": [],
        "derived_output": str(output.relative_to(ROOT)) if output.is_relative_to(ROOT) else str(output),
        "aggregate_groups": len(aggregates),
    }
    (output_dir / "real_intake_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Derived {len(aggregates)} aggregate group(s) to {output}")


if __name__ == "__main__":
    main()
