from __future__ import annotations

import json
import re
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRET_LIKE = re.compile(r"\b[0-9a-f]{40}\b|\b[0-9a-f]{64}\b|sha256:", re.IGNORECASE)


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as source:
        source.read(16)
        return struct.unpack(">II", source.read(8))


class M13ShowcaseTests(unittest.TestCase):
    def test_showcase_contract(self) -> None:
        required = (
            ROOT / "CASE-STUDY.md",
            ROOT / "docs/showcase-walkthrough.md",
            ROOT / "evaluation/m13-showcase-readiness.md",
            ROOT / "evaluation/m11-browser/public-desktop.png",
            ROOT / "evaluation/m11-browser/public-mobile.png",
            ROOT / "evaluation/p7-hosted-candidate-verification.md",
            ROOT / "evaluation/p7-browser/public-production.png",
            ROOT / "evaluation/p9-redesign/public-desktop.png",
            ROOT / "evaluation/p9-redesign/public-mobile.png",
            ROOT / "evaluation/p9-redesign/public-production.png",
            ROOT / "evaluation/p9-dashboard-redesign.md",
        )
        self.assertTrue(all(path.is_file() for path in required))
        self.assertEqual(
            png_dimensions(ROOT / "evaluation/m11-browser/public-desktop.png"),
            (1280, 577),
        )
        self.assertEqual(
            png_dimensions(ROOT / "evaluation/m11-browser/public-mobile.png"),
            (390, 844),
        )
        self.assertEqual(
            png_dimensions(ROOT / "evaluation/p7-browser/public-production.png"),
            (1280, 2716),
        )
        self.assertEqual(
            png_dimensions(ROOT / "evaluation/p9-redesign/public-desktop.png"),
            (1440, 900),
        )
        self.assertEqual(
            png_dimensions(ROOT / "evaluation/p9-redesign/public-mobile.png"),
            (390, 844),
        )
        self.assertEqual(
            png_dimensions(ROOT / "evaluation/p9-redesign/public-production.png"),
            (1440, 900),
        )
        markdown = list(ROOT.glob("*.md")) + list((ROOT / "docs").rglob("*.md"))
        self.assertFalse(
            [
                path
                for path in markdown
                if SECRET_LIKE.search(path.read_text(encoding="utf-8"))
            ]
        )
        self.assertFalse(
            [path for path in markdown if "—" in path.read_text(encoding="utf-8")]
        )
        package = json.loads(
            (ROOT / "portfolio/project.json").read_text(encoding="utf-8")
        )
        self.assertEqual(package["version"], 2)
        self.assertEqual(package["deployment"]["status"], "live")
        self.assertIn("Cloudflare R2", package["stack"])
        self.assertIn("20,439,666", package["outcome"])

    def test_p9_review_docket_contract(self) -> None:
        html = (ROOT / "app/index.html").read_text(encoding="utf-8")
        css = (ROOT / "app/styles.css").read_text(encoding="utf-8")
        script = (ROOT / "app/app.js").read_text(encoding="utf-8")
        self.assertIn("risk docket", html)
        self.assertIn('id="folio-period"', html)
        self.assertIn("Tap a deal to open", html)
        self.assertIn("deal-select", script)
        self.assertIn('aria-pressed="${selected}"', script)
        self.assertIn(
            'const mobile = window.matchMedia("(max-width: 700px)").matches', script
        )
        self.assertNotIn("Locate portfolio deterioration and test the driver.", html)
        self.assertNotIn("--aqua", css)


if __name__ == "__main__":
    unittest.main()
