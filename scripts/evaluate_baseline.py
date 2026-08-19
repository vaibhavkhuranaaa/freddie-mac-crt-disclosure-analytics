#!/usr/bin/env python3
"""Validate the synthetic aggregate CRT baseline and write reproducible evidence."""

from __future__ import annotations

import csv
import json
import time
from collections import defaultdict
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "crt_aggregate_fixture.csv"
RESULT = ROOT / "evaluation" / "baseline.json"
REPORT = ROOT / "evaluation" / "report.md"

REQUIRED_FIELDS = {
    "reporting_period",
    "deal_id",
    "program",
    "reference_pool_upb",
    "delinquent_upb",
    "prepayment_upb",
    "credit_event_upb",
    "tranche",
    "attachment_pct",
    "detachment_pct",
    "tranche_notional",
    "source_classification",
}
PROHIBITED_FIELD_TOKENS = {"borrower", "household", "property", "address", "loan_id", "fico"}
EXPECTED_TOTAL_TRANCHE_NOTIONAL = 9_842_250.0


def fail(message: str) -> None:
    raise ValueError(message)


def main() -> None:
    started = time.perf_counter()
    with FIXTURE.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            fail("fixture has no header")
        fields = set(reader.fieldnames)
        if fields != REQUIRED_FIELDS:
            fail(f"fixture fields differ from the approved baseline: {sorted(fields)}")
        unsafe_fields = sorted(
            field for field in fields if any(token in field.lower() for token in PROHIBITED_FIELD_TOKENS)
        )
        if unsafe_fields:
            fail(f"fixture contains prohibited fields: {unsafe_fields}")
        rows = list(reader)

    if not rows:
        fail("fixture is empty")

    pools: dict[tuple[str, str], dict[str, object]] = {}
    total_tranche_notional = 0.0
    for index, row in enumerate(rows, start=2):
        if row["source_classification"] != "synthetic-fixture":
            fail(f"row {index} is not labeled synthetic-fixture")
        try:
            date.fromisoformat(f"{row['reporting_period']}-01")
        except ValueError as exc:
            raise ValueError(f"row {index} has invalid reporting_period") from exc
        numeric = {
            key: float(row[key])
            for key in (
                "reference_pool_upb",
                "delinquent_upb",
                "prepayment_upb",
                "credit_event_upb",
                "attachment_pct",
                "detachment_pct",
                "tranche_notional",
            )
        }
        if any(value < 0 for value in numeric.values()):
            fail(f"row {index} contains a negative numeric value")
        if any(numeric[key] > numeric["reference_pool_upb"] for key in ("delinquent_upb", "prepayment_upb", "credit_event_upb")):
            fail(f"row {index} contains a pool metric above reference_pool_upb")
        if numeric["attachment_pct"] >= numeric["detachment_pct"]:
            fail(f"row {index} has invalid tranche attachment/detachment")

        pool_key = (row["reporting_period"], row["deal_id"])
        pool_values = tuple(
            numeric[key]
            for key in ("reference_pool_upb", "delinquent_upb", "prepayment_upb", "credit_event_upb")
        )
        if pool_key in pools and pools[pool_key]["values"] != pool_values:
            fail(f"row {index} conflicts with aggregate pool values for {pool_key}")
        pools[pool_key] = {"values": pool_values, "program": row["program"]}
        total_tranche_notional += numeric["tranche_notional"]

    if total_tranche_notional != EXPECTED_TOTAL_TRANCHE_NOTIONAL:
        fail("synthetic tranche-notional reconciliation failed")

    rates = []
    for (period, deal_id), pool in sorted(pools.items()):
        upb, delinquent, prepayment, credit_event = pool["values"]
        rates.append(
            {
                "reporting_period": period,
                "deal_id": deal_id,
                "delinquency_rate": round(delinquent / upb, 8),
                "prepayment_rate": round(prepayment / upb, 8),
                "credit_event_rate": round(credit_event / upb, 8),
            }
        )

    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
    result = {
        "evaluation_id": "E-M1-BASELINE-001",
        "fixture": str(FIXTURE.relative_to(ROOT)),
        "source_classification": "synthetic-fixture",
        "rows_validated": len(rows),
        "pool_periods_covered": len(pools),
        "schema_validity_rate": 1.0,
        "control_check_pass_rate": 1.0,
        "tranche_notional_total": total_tranche_notional,
        "expected_tranche_notional_total": EXPECTED_TOTAL_TRANCHE_NOTIONAL,
        "absolute_reconciliation_variance": 0.0,
        "runtime_ms": elapsed_ms,
        "rates": rates,
        "limitations": [
            "This result validates synthetic aggregate fixture behavior only.",
            "It is not evidence of performance on Freddie Mac disclosure files.",
            "No borrower-level or record-level decisioning is included.",
        ],
    }
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    REPORT.write_text(
        "# M1 baseline evaluation\n\n"
        "- Evaluation ID: `E-M1-BASELINE-001`\n"
        "- Input: synthetic aggregate fixture only\n"
        f"- Rows validated: {result['rows_validated']}\n"
        f"- Deal/reporting-period groups: {result['pool_periods_covered']}\n"
        "- Schema validity: 100%\n"
        "- Control checks: 100%\n"
        "- Reconciliation variance: 0.00\n"
        f"- Runtime: {elapsed_ms} ms\n\n"
        "## Limitation\n\n"
        "This evaluation proves only the synthetic aggregate baseline and its controls. "
        "It does not validate production or Freddie Mac source-data performance.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
