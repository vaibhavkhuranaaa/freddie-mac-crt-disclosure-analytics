from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.serve_private_workbench import (  # noqa: E402
    APP_DIR,
    DEFAULT_DATABASE,
    HOST,
    RequestError,
    WorkbenchRepository,
    local_request_allowed,
)


class PrivateWorkbenchTests(unittest.TestCase):
    def test_surface_is_accessible_and_separate_from_public_release(self) -> None:
        html = (APP_DIR / "index.html").read_text(encoding="utf-8")
        css = (APP_DIR / "styles.css").read_text(encoding="utf-8")
        javascript = (APP_DIR / "app.js").read_text(encoding="utf-8")

        self.assertIn('class="skip-link"', html)
        self.assertIn('aria-live="polite"', html)
        self.assertIn("View comparison data table", html)
        self.assertGreaterEqual(html.count("<caption>"), 5)
        self.assertIn("prefers-reduced-motion", css)
        self.assertIn("@media (max-width: 680px)", css)
        self.assertIn("window.history.replaceState", javascript)
        self.assertIn("Load 50 restricted rows", html)
        self.assertIn("Portfolio D60+ contribution", html)
        self.assertIn("selected-measure-heading", html)
        self.assertIn("periodLabel", javascript)
        self.assertIn("100% prior-loan match", javascript)
        self.assertIn('tabindex="0" aria-label="Scrollable restricted loan rows"', html)
        self.assertIn('<title id="trend-chart-title">', javascript)
        self.assertNotIn("loadDealAndLoans", javascript)
        self.assertIn("Identifiers are masked by default", html)
        self.assertNotIn("<script>", html)
        self.assertNotIn("<style>", html)
        self.assertNotIn("—", html + javascript)
        self.assertNotIn("–", html + javascript)

        self.assertEqual(HOST, "127.0.0.1")
        self.assertFalse((ROOT / "dist/private_app").exists())
        manifest = json.loads((ROOT / "dist/manifest.json").read_text(encoding="utf-8"))
        manifest_text = json.dumps(manifest).lower()
        for forbidden in ("private_app", "metrics.duckdb", "loan_identifier", "data/restricted"):
            self.assertNotIn(forbidden, manifest_text)

    def test_request_validators_and_nonrestricted_database_refusal(self) -> None:
        self.assertEqual(WorkbenchRepository.validate_period("202607"), "202607")
        self.assertEqual(WorkbenchRepository.validate_deal("2026-HQA1"), "2026-HQA1")
        for value in ("2026-07", "latest", "", "20260701"):
            with self.assertRaises(RequestError):
                WorkbenchRepository.validate_period(value)
        for value in ("../metrics", "deal id", "", "x" * 33):
            with self.assertRaises(RequestError):
                WorkbenchRepository.validate_deal(value)

        with tempfile.TemporaryDirectory() as directory:
            outside = Path(directory) / "metrics.duckdb"
            outside.touch()
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/serve_private_workbench.py",
                    "--database",
                    str(outside),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("outside data/restricted", result.stderr)

    def test_private_service_rejects_non_loopback_host_and_origin(self) -> None:
        self.assertTrue(local_request_allowed("127.0.0.1:8011", None, 8011))
        self.assertTrue(
            local_request_allowed(
                "localhost:8011", "http://localhost:8011", 8011
            )
        )
        self.assertFalse(local_request_allowed("example.com", None, 8011))
        self.assertFalse(
            local_request_allowed(
                "127.0.0.1:8011", "https://example.com", 8011
            )
        )

    @unittest.skipUnless(DEFAULT_DATABASE.exists(), "restricted M8 database is not available")
    def test_complete_full_data_workflow_and_performance(self) -> None:
        repository = WorkbenchRepository(DEFAULT_DATABASE)
        bootstrap = repository.bootstrap()
        self.assertTrue(bootstrap["local_only"])
        self.assertEqual(bootstrap["data_classification"], "restricted-derived-analytics")
        self.assertEqual(bootstrap["latest_period"], "202607")
        self.assertEqual(len(bootstrap["periods"]), 37)
        self.assertEqual(len(bootstrap["deals"]), 10)
        self.assertEqual(len(bootstrap["metric_catalog"]), 20)

        overview = repository.overview("202607")
        self.assertEqual(len(overview["watchlist"]), 10)
        expected_top = max(overview["watchlist"], key=lambda row: float(row["total_contribution_bps"]))
        self.assertEqual(overview["watchlist"][0]["deal_id"], expected_top["deal_id"])
        self.assertAlmostEqual(
            overview["decomposition_totals"]["total_contribution_bps"],
            float(overview["portfolio"]["d60_change_1m_bps"]),
            places=10,
        )

        detail = repository.deal("202607", "2022-HQA1")
        self.assertEqual(detail["current"]["metric_version"], "m8.1.0")
        self.assertEqual(float(detail["flow"]["loan_match_rate"]), 1.0)
        self.assertTrue(detail["series"])
        self.assertTrue(detail["pools"])
        self.assertTrue(detail["risk_layers"])

        masked = repository.loans("202607", "2022-HQA1", status="d90", limit=5)
        revealed = repository.loans(
            "202607",
            "2022-HQA1",
            status="d90",
            limit=1,
            include_identifiers=True,
        )
        self.assertTrue(masked["rows"])
        self.assertTrue(masked["rows"][0]["loan_identifier"].startswith("restricted-"))
        self.assertFalse(revealed["rows"][0]["loan_identifier"].startswith("restricted-"))

        package = repository.evidence_package("202607", "2022-HQA1")
        self.assertFalse(package["public_release_allowed"])
        self.assertNotIn("loan", package)
        self.assertNotIn("rows", package)
        self.assertEqual(package["metric_version"], "m8.1.0")

        for result in (bootstrap, overview, detail, masked, revealed):
            self.assertLess(result["query_ms"], 5_000)


if __name__ == "__main__":
    unittest.main()
