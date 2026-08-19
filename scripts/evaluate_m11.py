#!/usr/bin/env python3
"""Evaluate M11 analytical quality, controls, performance, and evidence gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
import time
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

import duckdb

try:
    from .build_public_projection import DATABASE, OUTPUT as PROJECTION, build_projection, json_value
    from .build_release import DIST, validate_public_inputs
    from .serve_private_workbench import WorkbenchRepository
except ImportError:
    from build_public_projection import DATABASE, OUTPUT as PROJECTION, build_projection, json_value
    from build_release import DIST, validate_public_inputs
    from serve_private_workbench import WorkbenchRepository


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/derived/m11_evaluation.json"
BROWSER_EVIDENCE = ROOT / "data/derived/m11_browser_evaluation.json"
REVIEWER_EVIDENCE = ROOT / "data/restricted/m11_representative_review.json"
LATEST_PERIOD = "202607"
WALKTHROUGH_DEAL = "2022-HQA1"
EXPECTED_PUBLIC_FILES = {
    "DEPLOYMENT.md",
    "app.js",
    "data/public/crt_public_projection.json",
    "index.html",
    "styles.css",
    "vercel.json",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def benchmark(function: Callable[[], Any], repetitions: int = 5) -> tuple[Any, dict[str, float]]:
    values: list[float] = []
    result: Any = None
    for _ in range(repetitions):
        started = time.perf_counter()
        result = function()
        values.append((time.perf_counter() - started) * 1000)
    return result, {
        "first_ms": round(values[0], 3),
        "warm_median_ms": round(statistics.median(values[1:]), 3),
        "warm_max_ms": round(max(values[1:]), 3),
    }


def source_revision_attestation() -> dict[str, Any]:
    def git(*arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *arguments],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    revision = git("rev-parse", "HEAD")
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    status = git("status", "--porcelain")
    if any(result.returncode for result in (revision, branch, status)):
        return {
            "status": "unavailable",
            "reason": "Git metadata could not be read; no source revision claim is made.",
        }
    clean = not status.stdout.strip()
    return {
        "status": "verified" if clean else "working_tree_dirty",
        "revision": revision.stdout.strip(),
        "branch": branch.stdout.strip(),
        "working_tree_clean": clean,
        "scope": "Local source state only; final release attestation remains an M13 gate.",
    }


def serializable(value: Any) -> Any:
    return json.loads(json.dumps(value, default=json_value))


def reconcile_projection() -> dict[str, Any]:
    published = json.loads(PROJECTION.read_text(encoding="utf-8"))
    generated = serializable(build_projection())
    sections = ("portfolio_periods", "deal_periods", "pool_periods", "metric_catalog")
    section_matches = {section: published[section] == generated[section] for section in sections}
    with duckdb.connect(str(DATABASE), read_only=True) as connection:
        counts = connection.execute(
            """
            SELECT
                (SELECT count(*) FROM portfolio_period_metrics),
                (SELECT count(*) FROM deal_period_metrics),
                (SELECT count(*) FROM pool_period_metrics),
                (SELECT count(*) FROM portfolio_d60_decomposition),
                (SELECT max(abs(current_upb_variance)) FROM release_reconciliation),
                (SELECT max(abs(d30_plus_rate_variance)) FROM release_reconciliation),
                (SELECT max(abs(d60_plus_rate_variance)) FROM release_reconciliation)
            """
        ).fetchone()
        identity_variance = connection.execute(
            """
            WITH totals AS (
                SELECT reporting_period, sum(total_contribution_bps) contribution
                FROM portfolio_d60_decomposition GROUP BY reporting_period
            )
            SELECT max(abs(t.contribution - p.d60_change_1m_bps))
            FROM totals t JOIN portfolio_period_metrics p USING (reporting_period)
            """
        ).fetchone()[0]
    checks = {
        "published_projection_equals_fresh_private_engine_projection": published == generated,
        "portfolio_rows_exact": len(published["portfolio_periods"]) == counts[0] == 37,
        "deal_rows_exact": len(published["deal_periods"]) == counts[1] == 292,
        "pool_rows_exact": len(published["pool_periods"]) == counts[2] == 292,
        "source_scope_exact": published["source_scope"]["records"] == 20_439_666,
        "release_current_upb_variance_zero": float(counts[4] or 0) == 0,
        "release_d30_rate_variance_zero": float(counts[5] or 0) == 0,
        "release_d60_rate_variance_zero": float(counts[6] or 0) == 0,
        "decomposition_identity_within_0_01_bp": float(identity_variance) <= 0.01,
        **{f"{section}_exact": matches for section, matches in section_matches.items()},
    }
    return {
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "private_rows": {
            "portfolio_periods": counts[0],
            "deal_periods": counts[1],
            "pool_periods": counts[2],
            "decomposition_rows": counts[3],
        },
        "maximum_decomposition_identity_variance_bps": float(identity_variance),
        "maximum_release_variance": {
            "current_upb": float(counts[4] or 0),
            "d30_plus_rate": float(counts[5] or 0),
            "d60_plus_rate": float(counts[6] or 0),
        },
    }


def evaluate_boundary_and_attestation() -> dict[str, Any]:
    projection = validate_public_inputs()
    manifest_path = DIST / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    paths = {item["path"] for item in manifest["files"]}
    config = json.loads((DIST / "vercel.json").read_text(encoding="utf-8"))
    header_items = config["headers"][0]["headers"]
    headers = {item["key"].lower(): item["value"] for item in header_items}
    required_headers = {
        "content-security-policy",
        "x-content-type-options",
        "x-frame-options",
        "referrer-policy",
        "permissions-policy",
        "cross-origin-opener-policy",
        "cross-origin-resource-policy",
        "strict-transport-security",
    }
    bundle_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore").lower()
        for path in DIST.rglob("*")
        if path.is_file()
    )
    forbidden = ("data/restricted/metrics", "metrics.duckdb", "loan_identifier", "private_app")
    file_records = manifest["files"]
    expected_artifact_sha = hashlib.sha256(
        json.dumps(file_records, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    checks = {
        "approved_aggregate_classification": projection["classification"] == "approved-aggregate-projection",
        "no_restricted_drill_through": projection["boundary"]["restricted_drill_through"] is False,
        "exact_static_asset_set": paths == EXPECTED_PUBLIC_FILES,
        "all_manifest_hashes_match": all(
            sha256(DIST / item["path"]) == item["sha256"] for item in file_records
        ),
        "artifact_fingerprint_matches": manifest.get("artifact_sha256") == expected_artifact_sha,
        "required_candidate_headers_declared": required_headers <= set(headers),
        "csp_blocks_frames_and_objects": "frame-ancestors 'none'" in headers.get("content-security-policy", "")
        and "object-src 'none'" in headers.get("content-security-policy", ""),
        "restricted_terms_absent": not any(term in bundle_text for term in forbidden),
        "runtime_api_or_database_absent": paths.isdisjoint({"api", "metrics.duckdb"}),
    }
    return {
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "projection_bytes": PROJECTION.stat().st_size,
        "artifact_sha256": manifest.get("artifact_sha256"),
        "source_revision_attestation": source_revision_attestation(),
    }


def evaluate_private_performance() -> dict[str, Any]:
    repository = WorkbenchRepository(DATABASE)
    bootstrap, bootstrap_timing = benchmark(repository.bootstrap)
    overview, overview_timing = benchmark(lambda: repository.overview(LATEST_PERIOD))
    deal, deal_timing = benchmark(lambda: repository.deal(LATEST_PERIOD, WALKTHROUGH_DEAL))
    loans, loan_timing = benchmark(
        lambda: repository.loans(LATEST_PERIOD, WALKTHROUGH_DEAL, limit=50)
    )
    initial = (bootstrap_timing, overview_timing, deal_timing)
    checks = {
        "bootstrap_under_5000_ms": bootstrap_timing["first_ms"] <= 5_000,
        "overview_under_5000_ms": overview_timing["first_ms"] <= 5_000,
        "deal_under_5000_ms": deal_timing["first_ms"] <= 5_000,
        "initial_warm_queries_under_2000_ms": max(item["warm_max_ms"] for item in initial) <= 2_000,
        "on_demand_rows_under_2000_ms": loan_timing["warm_max_ms"] <= 2_000,
        "restricted_rows_masked": bool(loans["rows"])
        and all(row["loan_identifier"].startswith("restricted-") for row in loans["rows"]),
        "restricted_rows_not_in_initial_payloads": all("rows" not in item for item in (bootstrap, overview, deal)),
    }
    return {
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "budget_ms": {"first_interaction": 5_000, "warm_interaction": 2_000},
        "results": {
            "bootstrap": bootstrap_timing,
            "overview": overview_timing,
            "deal": deal_timing,
            "explicit_50_row_query": loan_timing,
        },
    }


def analytical_findings() -> list[dict[str, Any]]:
    with duckdb.connect(str(DATABASE), read_only=True) as connection:
        portfolio = connection.execute(
            """
            SELECT eligible_current_upb, d60_plus_rate, d60_change_1m_bps, d60_change_3m_bps
            FROM portfolio_period_metrics WHERE reporting_period = ?
            """,
            [LATEST_PERIOD],
        ).fetchone()
        totals = connection.execute(
            """
            SELECT sum(rate_effect_bps), sum(mix_effect_bps), sum(total_contribution_bps)
            FROM portfolio_d60_decomposition WHERE reporting_period = ?
            """,
            [LATEST_PERIOD],
        ).fetchone()
        contributors = connection.execute(
            """
            SELECT d.deal_id, d.eligible_current_upb, d.d60_change_1m_bps,
                   x.rate_effect_bps, x.mix_effect_bps, x.total_contribution_bps
            FROM deal_period_metrics d
            JOIN portfolio_d60_decomposition x USING (deal_id, reporting_period)
            WHERE d.reporting_period = ?
            ORDER BY x.total_contribution_bps DESC
            """,
            [LATEST_PERIOD],
        ).fetchall()
        fastest_rate = max(contributors, key=lambda row: float(row[2]))
        highest_flow = connection.execute(
            """
            SELECT d.deal_id, d.d60_plus_rate, f.prior_d30_matched_loans,
                   f.d30_to_d60_loans, f.d30_to_d60_rate_upb,
                   f.prior_d30_plus_matched_loans, f.cured_loans, f.cure_rate_upb
            FROM deal_period_metrics d
            JOIN deal_period_flow_metrics f USING (deal_id, reporting_period)
            WHERE d.reporting_period = ?
            ORDER BY f.d30_to_d60_rate_upb DESC LIMIT 1
            """,
            [LATEST_PERIOD],
        ).fetchone()
    top = contributors[0]
    return [
        {
            "id": "F-M11-001",
            "finding": "July 2026 portfolio D60+ deterioration was performance-led, not mix-led.",
            "calculation": {
                "eligible_current_upb": str(portfolio[0]),
                "d60_plus_rate": float(portfolio[1]),
                "monthly_change_bps": float(portfolio[2]),
                "three_month_change_bps": float(portfolio[3]),
                "rate_effect_bps": float(totals[0]),
                "mix_effect_bps": float(totals[1]),
                "reconciled_total_bps": float(totals[2]),
            },
            "business_meaning": "Within-deal delinquency-rate movement explains the increase while portfolio composition slightly offset it.",
            "supported_decision": "Prioritize deal-level performance investigation before treating composition change as the driver.",
            "limitation": "The midpoint attribution is descriptive and does not establish causality or forecast loss.",
        },
        {
            "id": "F-M11-002",
            "finding": f"{top[0]} contributed most to portfolio deterioration even though {fastest_rate[0]} had the largest deal rate increase.",
            "calculation": {
                "largest_contributor": {
                    "deal_id": top[0],
                    "eligible_current_upb": str(top[1]),
                    "deal_change_bps": float(top[2]),
                    "rate_effect_bps": float(top[3]),
                    "mix_effect_bps": float(top[4]),
                    "total_contribution_bps": float(top[5]),
                },
                "largest_deal_rate_increase": {
                    "deal_id": fastest_rate[0],
                    "eligible_current_upb": str(fastest_rate[1]),
                    "deal_change_bps": float(fastest_rate[2]),
                    "total_contribution_bps": float(fastest_rate[5]),
                },
            },
            "business_meaning": "Exposure weight changes portfolio impact, so the largest rate move is not automatically the largest portfolio driver.",
            "supported_decision": "Use portfolio contribution for first triage, then use deal rate change to assess severity within the selected deal.",
            "limitation": "Contribution is sensitive to the current portfolio composition and is not a deal risk score.",
        },
        {
            "id": "F-M11-003",
            "finding": f"{highest_flow[0]} had the highest July 2026 D30-to-D60 UPB roll rate while its D60+ stock remained low.",
            "calculation": {
                "deal_id": highest_flow[0],
                "d60_plus_rate": float(highest_flow[1]),
                "prior_d30_matched_loans": highest_flow[2],
                "d30_to_d60_loans": highest_flow[3],
                "d30_to_d60_rate_upb": float(highest_flow[4]),
                "prior_d30_plus_matched_loans": highest_flow[5],
                "cured_loans": highest_flow[6],
                "cure_rate_upb": float(highest_flow[7]),
            },
            "business_meaning": "A low severe-delinquency stock can coexist with elevated one-month escalation and cure flows.",
            "supported_decision": "Monitor both inflow and cure behavior rather than relying on the D60+ level alone.",
            "limitation": "The flow denominator is the matched prior-state population, the cohort is small, and a cure may be temporary.",
        },
    ]


def load_browser_evidence(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "status": "unavailable",
            "reason": "Run scripts/evaluate_m11_browser.py against both loopback surfaces.",
        }
    evidence = json.loads(path.read_text(encoding="utf-8"))
    return evidence


def load_reviewer_evidence(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "status": "unavailable",
            "representative_reviewers": 0,
            "completed_without_facilitator": 0,
            "gate_passed": False,
            "reason": "No independent-review study was supplied. Current result remains 0 of 5 and no representative-usability claim is made.",
        }
    study = json.loads(path.read_text(encoding="utf-8"))
    reviewers = int(study.get("representative_reviewers", 0))
    completions = int(study.get("completed_without_facilitator", 0))
    critical_defects = int(study.get("critical_defects", 0))
    attested = bool(study.get("attested_by") and study.get("attested_on"))
    passed = reviewers >= 5 and completions >= 4 and critical_defects == 0 and attested
    return {
        "status": "pass" if passed else "fail",
        "representative_reviewers": reviewers,
        "completed_without_facilitator": completions,
        "critical_defects": critical_defects,
        "owner_attested": attested,
        "gate_passed": passed,
        "source_classification": "restricted study evidence; aggregate counts only copied here",
    }


def m11_milestone_complete(automated_pass: bool) -> bool:
    """Apply owner-approved technical-only M11 completion scope."""
    return automated_pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate revised technical M11 scope without inventing independent-review evidence.")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--browser-evidence", type=Path, default=BROWSER_EVIDENCE)
    parser.add_argument("--reviewer-evidence", type=Path, default=REVIEWER_EVIDENCE)
    args = parser.parse_args()

    reconciliation = reconcile_projection()
    boundary = evaluate_boundary_and_attestation()
    private_performance = evaluate_private_performance()
    browser = load_browser_evidence(args.browser_evidence)
    reviewers = load_reviewer_evidence(args.reviewer_evidence)
    automated_pass = all(
        item.get("status") == "pass"
        for item in (reconciliation, boundary, private_performance, browser)
    )
    milestone_complete = m11_milestone_complete(automated_pass)
    report = {
        "report_version": 2,
        "evaluation_date": date.today().isoformat(),
        "milestone": "M11",
        "status": "pass" if milestone_complete else "incomplete",
        "milestone_complete": milestone_complete,
        "metric_version": "m8.1.0",
        "source_records": 20_439_666,
        "scope_revision": {
            "approved_on": "2026-08-12",
            "representative_review_required": False,
            "independent_review_result": "0/5",
            "claim_boundary": "Technical usability is verified. Independent or representative usability is not claimed.",
        },
        "automated_and_technical_gates_passed": automated_pass,
        "metric_reconciliation": reconciliation,
        "public_boundary_security_and_attestation": boundary,
        "private_performance_and_row_boundary": private_performance,
        "browser_accessibility_responsive_keyboard_and_performance": browser,
        "independent_reviewer_evidence": reviewers,
        "analytical_findings": analytical_findings(),
        "limitations": [
            "No independent user study was performed; observed result remains 0 of 5.",
            "Technical browser automation does not establish target-user understanding.",
        ],
        "remaining_blockers": [
            message
            for condition, message in (
                (browser.get("status") != "pass", "The reproducible M11 browser evidence is absent or failing."),
                (boundary["source_revision_attestation"]["status"] != "verified", "Git/source-revision attestation is unavailable in this workspace; this remains a release blocker, not an M11 analytical claim."),
            )
            if condition
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
