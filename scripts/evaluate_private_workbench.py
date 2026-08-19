#!/usr/bin/env python3
"""Evaluate the M9 private workbench against the complete metric database."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from datetime import date
from pathlib import Path
from typing import Any, Callable

from serve_private_workbench import DEFAULT_DATABASE, ROOT, WorkbenchRepository


DEFAULT_OUTPUT = ROOT / "data/derived/m9_workbench_evaluation.json"
LATEST_PERIOD = "202607"
WALKTHROUGH_DEAL = "2022-HQA1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def benchmark(function: Callable[[], Any], repetitions: int = 6) -> tuple[Any, dict[str, float]]:
    durations: list[float] = []
    result: Any = None
    for _ in range(repetitions):
        started = time.perf_counter()
        result = function()
        durations.append((time.perf_counter() - started) * 1000)
    return result, {
        "first_ms": round(durations[0], 3),
        "warm_median_ms": round(statistics.median(durations[1:]), 3),
        "warm_max_ms": round(max(durations[1:]), 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the M9 private workbench.")
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    database = args.database.resolve()
    if not database.is_file():
        raise SystemExit(f"Metric database not found: {database}")

    repository = WorkbenchRepository(database)
    bootstrap, bootstrap_timing = benchmark(repository.bootstrap)
    overview, overview_timing = benchmark(lambda: repository.overview(LATEST_PERIOD))
    deal, deal_timing = benchmark(lambda: repository.deal(LATEST_PERIOD, WALKTHROUGH_DEAL))
    loans, loan_timing = benchmark(
        lambda: repository.loans(LATEST_PERIOD, WALKTHROUGH_DEAL, limit=50)
    )
    evidence, evidence_timing = benchmark(
        lambda: repository.evidence_package(LATEST_PERIOD, WALKTHROUGH_DEAL)
    )

    identity_variance = abs(
        overview["decomposition_totals"]["total_contribution_bps"]
        - float(overview["portfolio"]["d60_change_1m_bps"])
    )
    masked_identifiers = all(
        item["loan_identifier"].startswith("restricted-") for item in loans["rows"]
    )
    public_manifest = json.loads((ROOT / "dist/manifest.json").read_text(encoding="utf-8"))
    public_text = json.dumps(public_manifest).lower()
    forbidden_public_values = (
        "private_app",
        "metrics.duckdb",
        "loan_identifier",
        "data/restricted/metrics",
    )
    restricted_export_keys = {"loan", "loans", "rows", "loan_identifier"}

    timings = {
        "bootstrap": bootstrap_timing,
        "overview": overview_timing,
        "deal": deal_timing,
        "loan_detail": loan_timing,
        "evidence_export": evidence_timing,
    }
    first_max = max(item["first_ms"] for item in timings.values())
    warm_max = max(item["warm_max_ms"] for item in timings.values())
    checks = {
        "full_metric_database_present": True,
        "period_count": len(bootstrap["periods"]) == 37,
        "deal_count": len(bootstrap["deals"]) == 10,
        "metric_catalog_count": len(bootstrap["metric_catalog"]) == 19,
        "watchlist_complete": len(overview["watchlist"]) == 10,
        "decomposition_identity_within_0_01_bp": identity_variance <= 0.01,
        "selected_deal_history_present": bool(deal["series"]),
        "flow_view_present": deal["flow"] is not None,
        "risk_layer_view_present": bool(deal["risk_layers"]),
        "pool_view_present": bool(deal["pools"]),
        "loan_detail_present": bool(loans["rows"]),
        "loan_identifiers_masked_by_default": masked_identifiers,
        "evidence_export_excludes_rows": not (restricted_export_keys & evidence.keys()),
        "evidence_export_marked_nonpublic": evidence["public_release_allowed"] is False,
        "public_manifest_excludes_private_values": all(
            value not in public_text for value in forbidden_public_values
        ),
        "cold_budget_under_5000_ms": first_max <= 5_000,
        "warm_budget_under_2000_ms": warm_max <= 2_000,
    }
    if not all(checks.values()):
        failed = [name for name, passed in checks.items() if not passed]
        raise SystemExit(f"M9 evaluation failed: {', '.join(failed)}")

    report = {
        "report_version": 1,
        "evaluation_date": date.today().isoformat(),
        "milestone": "M9",
        "metric_version": deal["current"]["metric_version"],
        "database_sha256": sha256(database),
        "data_classification": "restricted-derived-analytics",
        "public_release_allowed": False,
        "scope": {
            "reporting_period": LATEST_PERIOD,
            "walkthrough_deal": WALKTHROUGH_DEAL,
            "periods": len(bootstrap["periods"]),
            "deals": len(bootstrap["deals"]),
            "metric_catalog_records": len(bootstrap["metric_catalog"]),
            "loan_detail_population": loans["total"],
        },
        "checks": checks,
        "decomposition_identity_variance_bps": identity_variance,
        "performance": {
            "budget": {"cold_ms": 5_000, "warm_ms": 2_000},
            "results": timings,
            "maximum_first_ms": first_max,
            "maximum_warm_ms": warm_max,
        },
        "boundary": {
            "server_host": "127.0.0.1",
            "database_read_only": True,
            "identifiers_masked_by_default": True,
            "public_bundle_unchanged": True,
            "evidence_export_contains_loan_rows": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
