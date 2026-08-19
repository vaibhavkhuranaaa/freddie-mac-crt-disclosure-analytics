#!/usr/bin/env python3
"""Build the reviewed aggregate-only M10 projection from the full metric engine."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "data/restricted/metrics/metrics.duckdb"
EVALUATION = ROOT / "data/derived/m8_metric_evaluation.json"
OUTPUT = ROOT / "data/public/crt_public_projection.json"
METRIC_IDS = (
    "d60_plus_rate",
    "d60_change_bps",
    "d60_rate_effect_bps",
    "d60_mix_effect_bps",
    "current_to_d30_roll_rate",
    "d30_to_d60_roll_rate",
    "cure_rate",
    "voluntary_payoff_rate",
    "loan_match_rate",
    "eligible_current_upb",
)


def json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(type(value).__name__)


def query(connection: duckdb.DuckDBPyConnection, sql: str) -> list[dict[str, Any]]:
    relation = connection.execute(sql)
    columns = [column[0] for column in relation.description]
    return [dict(zip(columns, row, strict=True)) for row in relation.fetchall()]


def build_projection(database: Path = DATABASE, evaluation_path: Path = EVALUATION) -> dict[str, Any]:
    evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
    with duckdb.connect(str(database), read_only=True) as connection:
        portfolio = query(
            connection,
            """
            SELECT reporting_period, eligible_active_loans, eligible_current_upb,
                   excluded_ra_records, excluded_ra_upb, excluded_xx_records, excluded_xx_upb,
                   d30_plus_upb, d60_plus_upb, d90_plus_upb,
                   d30_plus_rate, d60_plus_rate, d90_plus_rate,
                   d60_change_1m_bps, d60_change_3m_bps, metric_version
            FROM portfolio_period_metrics ORDER BY reporting_period
            """,
        )
        deals = query(
            connection,
            """
            SELECT d.deal_id, d.reporting_period, d.eligible_active_loans,
                   d.eligible_current_upb, d.d60_plus_upb, d.d30_plus_rate,
                   d.d60_plus_rate, d.d90_plus_rate, d.d60_change_1m_bps,
                   d.d60_change_3m_bps, f.loan_match_rate,
                   f.current_to_d30_rate_upb, f.d30_to_d60_rate_upb,
                   f.cure_rate_upb, f.voluntary_payoff_rate_upb,
                   x.rate_effect_bps, x.mix_effect_bps, x.total_contribution_bps,
                   d.metric_version
            FROM deal_period_metrics d
            LEFT JOIN deal_period_flow_metrics f USING (deal_id, reporting_period)
            LEFT JOIN portfolio_d60_decomposition x USING (deal_id, reporting_period)
            ORDER BY d.reporting_period, d.deal_id
            """,
        )
        pools = query(
            connection,
            """
            SELECT deal_id, reference_pool_number, reporting_period,
                   eligible_active_loans, eligible_current_upb, d60_plus_upb,
                   d60_plus_rate, d60_change_1m_bps, metric_version
            FROM pool_period_metrics ORDER BY reporting_period, deal_id, reference_pool_number
            """,
        )
        relation = connection.execute(
            f"""
            SELECT metric_id, metric_version, definition, method, desired_direction,
                   baseline, supported_decision, limitation
            FROM metric_catalog
            WHERE metric_id IN ({','.join('?' for _ in METRIC_IDS)})
            ORDER BY metric_id
            """,
            list(METRIC_IDS),
        )
        columns = [column[0] for column in relation.description]
        metric_catalog = [dict(zip(columns, row, strict=True)) for row in relation.fetchall()]
        metric_catalog.append(
            {
                "metric_id": "d60_total_contribution_bps",
                "metric_version": evaluation["metric_version"],
                "definition": "Signed deal contribution to the portfolio monthly D60+ rate change, in basis points.",
                "method": "Current deal weight times current D60+ rate minus prior deal weight times prior D60+ rate; exactly equals rate effect plus mix effect.",
                "desired_direction": "Lower or negative contribution is favorable.",
                "baseline": "Eligible-current-UPB-weighted portfolio monthly D60+ change.",
                "supported_decision": "Choose which deal contribution to investigate first.",
                "limitation": "Contribution depends on both performance and portfolio weight and does not establish causality.",
            }
        )

    periods = [row["reporting_period"] for row in portfolio]
    deal_ids = sorted({row["deal_id"] for row in deals})
    return {
        "schema_version": 1,
        "classification": "approved-aggregate-projection",
        "public_release_allowed": True,
        "metric_version": evaluation["metric_version"],
        "source_scope": {
            "records": evaluation["source_records"],
            "deal_period_groups": evaluation["release_reconciliation"]["groups"],
            "deals": len(deal_ids),
            "periods": len(periods),
            "latest_period": periods[-1],
        },
        "controls": {
            "typed_input_gate": evaluation["typed_input_gate"]["status"],
            "release_reconciliation": evaluation["release_reconciliation"]["status"],
            "transition_integrity": evaluation["transition_integrity"]["status"],
            "decomposition_integrity": evaluation["decomposition_integrity"]["status"],
            "maximum_decomposition_variance_bps": evaluation["decomposition_integrity"]["maximum_variance_bps"],
        },
        "boundary": {
            "grain": "aggregate deal-period and reference-pool-period metrics",
            "restricted_drill_through": False,
            "excluded": [
                "loan rows",
                "loan identifiers",
                "payment histories",
                "borrower attributes",
                "seller, servicer, and geographic dimensions",
                "local file and database paths",
            ],
        },
        "portfolio_periods": portfolio,
        "deal_periods": deals,
        "pool_periods": pools,
        "metric_catalog": metric_catalog,
    }


def main() -> None:
    projection = build_projection()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(projection, default=json_value, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(f"Public projection: {OUTPUT} ({OUTPUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
