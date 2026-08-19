from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "data/restricted/metrics/metrics.duckdb"
PROJECTION = ROOT / "data/public/crt_public_projection.json"


def nested_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {key for child in value.values() for key in nested_keys(child)}
    if isinstance(value, list):
        return {key for child in value for key in nested_keys(child)}
    return set()


@unittest.skipUnless(DATABASE.exists(), "restricted M8 database is not available")
class PublicProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from scripts.build_public_projection import build_projection

        cls.projection = build_projection()

    def test_projection_uses_full_metric_scope(self) -> None:
        self.assertEqual(self.projection["source_scope"]["records"], 20_439_666)
        self.assertEqual(self.projection["source_scope"]["deal_period_groups"], 292)
        self.assertEqual(len(self.projection["portfolio_periods"]), 37)
        self.assertEqual(len(self.projection["deal_periods"]), 292)
        self.assertEqual(len(self.projection["pool_periods"]), 292)
        self.assertEqual(self.projection["metric_version"], "m8.1.0")

    def test_projection_matches_private_metric_engine(self) -> None:
        latest = next(row for row in self.projection["portfolio_periods"] if row["reporting_period"] == "202607")
        selected = next(row for row in self.projection["deal_periods"] if row["reporting_period"] == "202607" and row["deal_id"] == "2022-HQA1")
        with duckdb.connect(str(DATABASE), read_only=True) as connection:
            private_latest = connection.execute(
                "SELECT d60_plus_rate, d60_change_1m_bps FROM portfolio_period_metrics WHERE reporting_period='202607'"
            ).fetchone()
            private_selected = connection.execute(
                "SELECT d60_plus_rate, d60_change_1m_bps FROM deal_period_metrics WHERE reporting_period='202607' AND deal_id='2022-HQA1'"
            ).fetchone()
        self.assertAlmostEqual(latest["d60_plus_rate"], private_latest[0], places=12)
        self.assertAlmostEqual(latest["d60_change_1m_bps"], private_latest[1], places=12)
        self.assertAlmostEqual(selected["d60_plus_rate"], private_selected[0], places=12)
        self.assertAlmostEqual(selected["d60_change_1m_bps"], private_selected[1], places=12)
        contributions = [row for row in self.projection["deal_periods"] if row["reporting_period"] == "202607"]
        self.assertAlmostEqual(
            sum(row["total_contribution_bps"] for row in contributions),
            latest["d60_change_1m_bps"],
            places=10,
        )

    def test_projection_has_exact_public_boundary(self) -> None:
        self.assertTrue(self.projection["public_release_allowed"])
        self.assertEqual(self.projection["classification"], "approved-aggregate-projection")
        forbidden = {
            "loan_identifier", "payment_history", "servicer_name", "seller_name",
            "property_state", "classic_fico_value", "original_ltv_value", "original_dti_value",
        }
        self.assertFalse(nested_keys(self.projection) & forbidden)
        from scripts.build_public_projection import json_value

        serialized = json.dumps(self.projection, default=json_value).lower()
        for term in ("data/restricted", "metrics.duckdb", "loan_period_typed", "private_app"):
            self.assertNotIn(term, serialized)

    def test_projection_stays_in_static_single_file_envelope(self) -> None:
        from scripts.build_public_projection import json_value

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "projection.json"
            output.write_text(json.dumps(self.projection, default=json_value, separators=(",", ":")), encoding="utf-8")
            self.assertLess(output.stat().st_size, 2_000_000)
        self.assertTrue(PROJECTION.exists())


if __name__ == "__main__":
    unittest.main()
