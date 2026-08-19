from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DemoSurfaceTests(unittest.TestCase):
    def test_public_twin_declares_usable_states_and_boundary(self) -> None:
        page = (ROOT / "app/index.html").read_text(encoding="utf-8")
        javascript = (ROOT / "app/app.js").read_text(encoding="utf-8")
        stylesheet = (ROOT / "app/styles.css").read_text(encoding="utf-8")
        for expected in (
            "Public full data",
            "Public masking boundary",
            "Unable to load disclosure data",
            "No disclosure records match these filters",
            "All loan-period rows and disclosed fields are queryable",
            "Portfolio D60+ contribution",
            "Largest portfolio contributor",
        ):
            self.assertIn(expected, page)
        self.assertIn("data/public/crt_public_projection.json", javascript)
        self.assertIn("window.history.replaceState", javascript)
        self.assertIn("prefers-reduced-motion", stylesheet)
        self.assertNotIn("../data/derived/real_aggregate.csv", page + javascript)
        self.assertIn("/api/records", javascript)

    def test_public_filters_have_visible_values_and_period_valid_deals(self) -> None:
        page = (ROOT / "app/index.html").read_text(encoding="utf-8")
        javascript = (ROOT / "app/app.js").read_text(encoding="utf-8")
        self.assertEqual(page.count("<option value="), 12)
        self.assertIn('id="selected-measure-heading"', page)
        self.assertIn("currentRows()", javascript)
        self.assertIn("Only deals reported in this month", page)
        self.assertIn("100% prior-loan match", javascript)

    def test_local_runbook_is_present(self) -> None:
        runbook = (ROOT / "docs/local-demo-runbook.md").read_text(encoding="utf-8")
        self.assertIn("scripts/serve_demo.py", runbook)
        self.assertIn("python3 -m unittest", runbook)

    def test_release_contains_only_public_workbench_assets(self) -> None:
        subprocess.run(["python3", "scripts/build_release.py"], cwd=ROOT, check=True)
        manifest = json.loads((ROOT / "dist/manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["release_type"], "public-full-record-crt-workbench")
        paths = {item["path"] for item in manifest["files"]}
        self.assertEqual(
            paths,
            {
                "DEPLOYMENT.md",
                "api/records.py",
                "api/release.py",
                "app.js",
                "data/public/crt_public_projection.json",
                "index.html",
                "requirements.txt",
                "styles.css",
                "vercel.json",
            },
        )
        self.assertRegex(manifest["artifact_sha256"], r"^[0-9a-f]{64}$")
        serialized = json.dumps(manifest).lower()
        for forbidden in (
            "data/restricted",
            "metrics.duckdb",
            "private_app",
            "real_aggregate.csv",
        ):
            self.assertNotIn(forbidden, serialized)
        deploy_ignore = (
            (ROOT / "dist/.vercelignore").read_text(encoding="utf-8").splitlines()
        )
        self.assertIn("manifest.json", deploy_ignore)
        self.assertIn(".env*", deploy_ignore)

    def test_public_candidate_declares_release_security_headers(self) -> None:
        config = json.loads((ROOT / "app/vercel.json").read_text(encoding="utf-8"))
        headers = {
            item["key"]: item["value"] for item in config["headers"][0]["headers"]
        }
        self.assertEqual(config["headers"][0]["source"], "/(.*)")
        for required in (
            "Content-Security-Policy",
            "X-Content-Type-Options",
            "X-Frame-Options",
            "Referrer-Policy",
            "Permissions-Policy",
            "Cross-Origin-Opener-Policy",
            "Cross-Origin-Resource-Policy",
            "Strict-Transport-Security",
        ):
            self.assertIn(required, headers)
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])

    def test_public_copy_declares_masked_full_record_capability(self) -> None:
        page = (ROOT / "app/index.html").read_text(encoding="utf-8")
        self.assertIn("All loan-period rows and disclosed fields are queryable", page)
        self.assertIn("Other disclosed field combinations may remain linkable", page)
        self.assertNotIn("Authorized loan detail", page)
        self.assertNotIn("Reveal restricted identifiers", page)


if __name__ == "__main__":
    unittest.main()
