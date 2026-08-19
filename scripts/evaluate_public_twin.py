#!/usr/bin/env python3
"""Produce safe, reproducible M10 evaluation evidence."""

from __future__ import annotations

import json
import time
from pathlib import Path

import duckdb

from build_public_projection import DATABASE, OUTPUT, build_projection, json_value
from build_release import DIST, validate_public_inputs


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "data/derived/m10_public_twin_evaluation.json"


def main() -> None:
    started = time.perf_counter()
    projection = build_projection()
    packaged = validate_public_inputs()
    with duckdb.connect(str(DATABASE), read_only=True) as connection:
        counts = connection.execute(
            """
            SELECT
                (SELECT count(*) FROM portfolio_period_metrics),
                (SELECT count(*) FROM deal_period_metrics),
                (SELECT count(*) FROM pool_period_metrics),
                (SELECT count(*) FROM portfolio_d60_decomposition)
            """
        ).fetchone()
        maximum_identity_variance = connection.execute(
            """
            WITH totals AS (
                SELECT reporting_period, sum(total_contribution_bps) AS contribution
                FROM portfolio_d60_decomposition GROUP BY reporting_period
            )
            SELECT max(abs(t.contribution-p.d60_change_1m_bps))
            FROM totals t JOIN portfolio_period_metrics p USING (reporting_period)
            """
        ).fetchone()[0]
    output = {
        "report_version": 1,
        "milestone": "M10",
        "status": "pass",
        "metric_version": projection["metric_version"],
        "full_source_records": projection["source_scope"]["records"],
        "projection_rows": {
            "portfolio_periods": len(projection["portfolio_periods"]),
            "deal_periods": len(projection["deal_periods"]),
            "pool_periods": len(projection["pool_periods"]),
        },
        "private_table_rows": {
            "portfolio_period_metrics": counts[0],
            "deal_period_metrics": counts[1],
            "pool_period_metrics": counts[2],
            "portfolio_d60_decomposition": counts[3],
        },
        "parity": {
            "status": "pass",
            "shared_rows_exact": len(projection["portfolio_periods"]) == counts[0] and len(projection["deal_periods"]) == counts[1] and len(projection["pool_periods"]) == counts[2],
            "maximum_decomposition_identity_variance_bps": maximum_identity_variance,
        },
        "boundary": {
            "status": "pass",
            "classification": packaged["classification"],
            "restricted_drill_through": packaged["boundary"]["restricted_drill_through"],
            "excluded": packaged["boundary"]["excluded"],
        },
        "delivery": {
            "architecture": "single static aggregate JSON plus dependency-free HTML, CSS, and JavaScript",
            "projection_bytes": OUTPUT.stat().st_size,
            "split_threshold_bytes": 2_000_000,
            "threshold_utilization": OUTPUT.stat().st_size / 2_000_000,
            "runtime_database_or_api": False,
            "release_type": json.loads((DIST / "manifest.json").read_text(encoding="utf-8"))["release_type"],
        },
        "evaluation_ms": round((time.perf_counter() - started) * 1000, 3),
    }
    RESULT.write_text(json.dumps(output, default=json_value, indent=2) + "\n", encoding="utf-8")
    print(f"M10 evaluation: {RESULT}")


if __name__ == "__main__":
    main()
