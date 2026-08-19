from __future__ import annotations

import csv
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
COLUMNS = [
    "deal_id",
    "source_member",
    "source_field_count",
    "period",
    "reference_pool_number",
    "loan_identifier",
    "current_actual_upb",
    "upb_at_issuance",
    "upb_at_removal",
    "current_loan_delinquency_status",
    "zero_balance_code",
    "modification_flag",
    "borrower_assistance_plan",
    "payment_deferral_flag",
    "delinquency_due_to_disaster",
    "distressed_principal_balance_flag",
    "actual_loss",
    "cumulative_modification_costs",
    "classic_fico",
    "original_ltv",
    "original_cltv",
    "original_dti",
    "current_interest_rate",
    "loan_age",
    "first_payment_date",
    "loan_purpose",
    "channel",
    "occupancy_status",
    "property_type",
    "property_state",
    "seller_name",
    "servicer_name",
]


def loan(
    deal: str,
    pool: str,
    period: str,
    loan_id: str,
    upb: str,
    status: str,
    *,
    zero_balance: str | None = None,
    removal_upb: str | None = None,
    modification: str | None = None,
    deferral: str | None = None,
    assistance: str | None = None,
    actual_loss: str | None = None,
    fico: str = "700",
    ltv: str = "95",
    dti: str = "50",
    occupancy: str = "P",
) -> dict[str, object]:
    return {
        "deal_id": deal,
        "source_member": f"{pool}_{period}01_lld.txt",
        "source_field_count": 93,
        "period": period,
        "reference_pool_number": pool,
        "loan_identifier": loan_id,
        "current_actual_upb": upb,
        "upb_at_issuance": "100",
        "upb_at_removal": removal_upb,
        "current_loan_delinquency_status": status,
        "zero_balance_code": zero_balance,
        "modification_flag": modification,
        "borrower_assistance_plan": assistance,
        "payment_deferral_flag": deferral,
        "delinquency_due_to_disaster": None,
        "distressed_principal_balance_flag": "N",
        "actual_loss": actual_loss,
        "cumulative_modification_costs": None,
        "classic_fico": fico,
        "original_ltv": ltv,
        "original_cltv": ltv,
        "original_dti": dti,
        "current_interest_rate": "6.0",
        "loan_age": "24",
        "first_payment_date": "202406",
        "loan_purpose": "P",
        "channel": "R",
        "occupancy_status": occupancy,
        "property_type": "SF",
        "property_state": "IL",
        "seller_name": "Seller",
        "servicer_name": "Servicer",
    }


def fixture_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    states = {
        "202606": [
            loan("2026-HQA1", "26HQA1", "202606", "A1", "100", "00"),
            loan("2026-HQA1", "26HQA1", "202606", "A2", "50", "01", fico="650", ltv="85", dti="40", occupancy="S"),
            loan("2026-HQA1", "26HQA1", "202606", "A3", "50", "00"),
            loan("2026-HQA1", "26HQA1", "202606", "A4", "20", "RA"),
            loan("2026-HQA1", "26HQA1", "202606", "A5", "40", "02"),
        ],
        "202607": [
            loan("2026-HQA1", "26HQA1", "202607", "A1", "100", "01", modification="Y", deferral="C", assistance="F"),
            loan("2026-HQA1", "26HQA1", "202607", "A2", "50", "00", fico="650", ltv="85", dti="40", occupancy="S"),
            loan("2026-HQA1", "26HQA1", "202607", "A3", "0", "00", zero_balance="01", removal_upb="50"),
            loan("2026-HQA1", "26HQA1", "202607", "A4", "20", "RA"),
            loan("2026-HQA1", "26HQA1", "202607", "A5", "0", "02", zero_balance="02", removal_upb="40", actual_loss="10"),
        ],
        "202608": [
            loan("2026-HQA1", "26HQA1", "202608", "A1", "100", "02", modification="P", deferral="P"),
            loan("2026-HQA1", "26HQA1", "202608", "A2", "50", "00", fico="650", ltv="85", dti="40", occupancy="S"),
            loan("2026-HQA1", "26HQA1", "202608", "A3", "0", "00", zero_balance="01", removal_upb="50"),
            loan("2026-HQA1", "26HQA1", "202608", "A4", "20", "RA"),
            loan("2026-HQA1", "26HQA1", "202608", "A5", "0", "02", zero_balance="02", removal_upb="40", actual_loss="15"),
        ],
    }
    for period, period_rows in states.items():
        rows.extend(period_rows)
        rows.append(loan("2026-HQA2", "26HQA2", period, "B1", "100", "02", fico="780", ltv="85", dti="30"))
    return rows


def write_fixture(root: Path, *, release_variance: float = 0) -> tuple[Path, Path]:
    foundation = root / "foundation"
    parquet_dir = foundation / "loan_period" / "deal_id=test" / "reporting_period=test"
    parquet_dir.mkdir(parents=True)
    rows = fixture_rows()
    connection = duckdb.connect()
    definitions = ",".join(f'"{column}" VARCHAR' for column in COLUMNS)
    connection.execute(f"CREATE TABLE fixture ({definitions})")
    connection.executemany(
        f"INSERT INTO fixture VALUES ({','.join('?' for _ in COLUMNS)})",
        [[row.get(column) for column in COLUMNS] for row in rows],
    )
    connection.execute(f"COPY fixture TO '{parquet_dir / 'data.parquet'}' (FORMAT PARQUET)")
    connection.close()
    (foundation / "manifest.json").write_text(
        json.dumps(
            {
                "data_classification": "restricted-loan-level",
                "public_release_allowed": False,
                "records": len(rows),
                "accepted_files": 6,
                "source_archive_sha256": "fixture",
            }
        ),
        encoding="utf-8",
    )
    release = root / "release.csv"
    fields = [
        "reporting_period",
        "deal_id",
        "reference_pool_number",
        "current_upb",
        "d30_plus_upb",
        "d60_plus_upb",
        "d30_plus_rate",
        "d60_plus_rate",
        "records_aggregated",
        "ra_records",
        "xx_records",
        "source_classification",
    ]
    groups: dict[tuple[str, str, str], list[dict[str, object]]] = {}
    for row in rows:
        groups.setdefault((str(row["period"]), str(row["deal_id"]), str(row["reference_pool_number"])), []).append(row)
    with release.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        for (period, deal, pool), group in sorted(groups.items()):
            current = sum(float(row["current_actual_upb"] or 0) for row in group) + release_variance
            d30 = sum(
                float(row["current_actual_upb"] or 0)
                for row in group
                if str(row["current_loan_delinquency_status"]).isdigit() and int(str(row["current_loan_delinquency_status"])) >= 1
            )
            d60 = sum(
                float(row["current_actual_upb"] or 0)
                for row in group
                if str(row["current_loan_delinquency_status"]).isdigit() and int(str(row["current_loan_delinquency_status"])) >= 2
            )
            writer.writerow(
                {
                    "reporting_period": period,
                    "deal_id": deal,
                    "reference_pool_number": pool,
                    "current_upb": f"{current:.2f}",
                    "d30_plus_upb": f"{d30:.2f}",
                    "d60_plus_upb": f"{d60:.2f}",
                    "d30_plus_rate": f"{d30/current:.8f}" if current else "0",
                    "d60_plus_rate": f"{d60/current:.8f}" if current else "0",
                    "records_aggregated": len(group),
                    "ra_records": sum(row["current_loan_delinquency_status"] == "RA" for row in group),
                    "xx_records": 0,
                    "source_classification": "fixture",
                }
            )
    return foundation, release


class MetricEngineTests(unittest.TestCase):
    def run_builder(self, root: Path, foundation: Path, release: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "uv",
                "run",
                "python",
                "scripts/build_metric_engine.py",
                "--foundation",
                str(foundation),
                "--output",
                str(root / "metrics.duckdb"),
                "--evaluation",
                str(root / "evaluation.json"),
                "--release-aggregate",
                str(release),
                "--allow-nonrestricted-output",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

    def test_full_metric_spine_and_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            foundation, release = write_fixture(root)
            result = self.run_builder(root, foundation, release)
            self.assertEqual(result.returncode, 0, result.stderr)
            connection = duckdb.connect(str(root / "metrics.duckdb"), read_only=True)
            latest = connection.execute(
                "SELECT reported_current_upb, eligible_current_upb, excluded_ra_upb, d60_plus_upb, d60_plus_rate "
                "FROM portfolio_period_metrics WHERE reporting_period='202608'"
            ).fetchone()
            self.assertEqual(tuple(map(float, latest)), (270.0, 250.0, 20.0, 200.0, 0.8))
            july = connection.execute(
                "SELECT current_to_d30_loans, cured_loans, voluntary_payoff_loans, credit_event_exit_loans, "
                "new_modification_loans FROM deal_period_flow_metrics "
                "WHERE deal_id='2026-HQA1' AND reporting_period='202607'"
            ).fetchone()
            self.assertEqual(july, (1, 1, 1, 1, 1))
            self.assertAlmostEqual(
                connection.execute(
                    "SELECT assistance_exposure_share FROM deal_period_metrics "
                    "WHERE deal_id='2026-HQA1' AND reporting_period='202607'"
                ).fetchone()[0],
                2 / 3,
            )
            august = connection.execute(
                "SELECT d30_to_d60_loans, actual_loss_increment_observations, actual_loss_increment "
                "FROM deal_period_flow_metrics WHERE deal_id='2026-HQA1' AND reporting_period='202608'"
            ).fetchone()
            self.assertEqual(august[:2], (1, 1))
            self.assertEqual(float(august[2]), 5.0)
            max_decomposition_variance = connection.execute(
                "WITH x AS (SELECT reporting_period,sum(rate_effect_bps+mix_effect_bps) v "
                "FROM portfolio_d60_decomposition GROUP BY 1) "
                "SELECT max(abs(x.v-p.d60_change_1m_bps)) FROM x JOIN portfolio_period_metrics p USING(reporting_period)"
            ).fetchone()[0]
            self.assertLess(float(max_decomposition_variance), 0.01)
            self.assertEqual(connection.execute("SELECT max(abs(current_upb_variance)) FROM release_reconciliation").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT count(*) FROM metric_catalog").fetchone()[0], len(METRIC_IDS))
            connection.close()
            evaluation = json.loads((root / "evaluation.json").read_text(encoding="utf-8"))
            self.assertFalse(evaluation["restricted_output"]["public_release_allowed"])

    def test_reconciliation_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            foundation, release = write_fixture(root, release_variance=1)
            result = self.run_builder(root, foundation, release)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("release reconciliation failed", result.stderr)
            self.assertFalse((root / "metrics.duckdb").exists())


METRIC_IDS = {
    "eligible_current_upb",
    "d30_plus_rate",
    "d60_plus_rate",
    "d90_plus_rate",
    "d60_change_bps",
    "d60_rate_effect_bps",
    "d60_mix_effect_bps",
    "current_to_d30_roll_rate",
    "d30_to_d60_roll_rate",
    "cure_rate",
    "voluntary_payoff_rate",
    "credit_event_exit_rate",
    "actual_loss_rate",
    "new_modification_rate",
    "assistance_share",
    "pool_factor",
    "weighted_average_risk_attributes",
    "risk_layer_share",
    "loan_match_rate",
}


if __name__ == "__main__":
    unittest.main()
