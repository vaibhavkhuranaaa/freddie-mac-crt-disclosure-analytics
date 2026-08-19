from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]


def row(width: int, period: str, pool: str, loan_id: str, final_value: str = "") -> str:
    fields = [""] * width
    fields[0], fields[1], fields[2] = period, pool, loan_id
    fields[-1] = final_value
    return "|".join(fields)


class FullDataLayerTests(unittest.TestCase):
    def test_preserves_and_null_pads_all_approved_layout_widths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            archive = root / "approved.zip"
            with zipfile.ZipFile(archive, "w") as package:
                package.writestr("22HQA1_20230701_lld.txt", row(89, "202307", "22HQA1", "L1", "Y") + "\n")
                package.writestr("22HQA1_20230801_lld.txt", row(90, "202308", "22HQA1", "L1", "1") + "\n")
                package.writestr("22HQA1_20260701_lld.txt", row(93, "202607", "22HQA1", "L1", "12.34") + "\n")
                package.writestr("notes.txt", "not a standard monthly file")
            output = root / "full-data"
            quality = root / "quality.json"
            subprocess.run(
                [
                    "uv",
                    "run",
                    "python",
                    "scripts/build_full_data_layer.py",
                    str(archive),
                    "--output-dir",
                    str(output),
                    "--quality-report",
                    str(quality),
                    "--allow-nonrestricted-output",
                ],
                cwd=ROOT,
                check=True,
            )
            report = json.loads(quality.read_text(encoding="utf-8"))
            self.assertEqual(report["records"], 3)
            self.assertEqual(report["accepted_files"], 3)
            self.assertEqual(report["source_field_count_records"], {"89": 1, "90": 1, "93": 1})
            rows = duckdb.connect().execute(
                "SELECT source_field_count, distressed_principal_balance_flag, "
                "temporary_subsidy_buydown_plan_type, actual_loss, cumulative_modification_costs "
                "FROM read_parquet(?, hive_partitioning=false) ORDER BY period",
                [str(output / "loan_period" / "**" / "*.parquet")],
            ).fetchall()
            self.assertEqual(rows[0], (89, "Y", None, None, None))
            self.assertEqual(rows[1], (90, None, "1", None, None))
            self.assertEqual(rows[2], (93, None, None, None, "12.34"))
            self.assertFalse(json.loads((output / "manifest.json").read_text(encoding="utf-8"))["public_release_allowed"])

    def test_rejects_unapproved_width_without_leaving_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            archive = root / "approved.zip"
            with zipfile.ZipFile(archive, "w") as package:
                package.writestr("22HQA1_20230701_lld.txt", row(88, "202307", "22HQA1", "L1") + "\n")
            output = root / "full-data"
            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "python",
                    "scripts/build_full_data_layer.py",
                    str(archive),
                    "--output-dir",
                    str(output),
                    "--quality-report",
                    str(root / "quality.json"),
                    "--allow-nonrestricted-output",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("has 88 fields", result.stderr)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
