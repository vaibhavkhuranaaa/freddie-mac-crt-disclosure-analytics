from __future__ import annotations

import csv
import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def row(period: str, pool: str, status: str, upb: str) -> str:
    fields = [""] * 40
    fields[0], fields[1], fields[2], fields[36], fields[39] = period, pool, "never-emitted-loan-id", status, upb
    return "|".join(fields)


class ClarityArchiveIntakeTests(unittest.TestCase):
    def test_streams_only_requested_deals_to_aggregate_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            archive = root / "approved.zip"
            with zipfile.ZipFile(archive, "w") as package:
                package.writestr("22HQA1_20230701_lld.txt", row("202307", "111", "00", "100") + "\n" + row("202307", "111", "02", "25") + "\n")
                package.writestr("24HQA1_20230701_lld.txt", row("202307", "999", "02", "500") + "\n")
                package.writestr("22HQA1_20230701_agg_zipcode.txt", "not-used\n")
            output_dir = root / "aggregate-only-output"
            subprocess.run(["python3", "scripts/intake_clarity_archive.py", str(archive), "--deal", "2022-HQA1", "--output-dir", str(output_dir)], cwd=ROOT, check=True)
            with (output_dir / "real_aggregate.csv").open(newline="", encoding="utf-8") as handle:
                result = next(csv.DictReader(handle))
            self.assertEqual(result["deal_id"], "2022-HQA1")
            self.assertEqual(result["current_upb"], "125.0")
            self.assertEqual(result["d60_plus_upb"], "25.0")
            self.assertNotIn("never-emitted-loan-id", (output_dir / "real_aggregate.csv").read_text(encoding="utf-8"))

    def test_processes_all_standard_lld_files_when_no_filter_is_given(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            archive = root / "approved.zip"
            with zipfile.ZipFile(archive, "w") as package:
                package.writestr("22HQA1_20230701_lld.txt", row("202307", "111", "00", "100") + "\n")
                package.writestr("24HQA1_20230701_lld.txt", row("202307", "999", "02", "500") + "\n")
                package.writestr("24HQA1_20230701_lld_eu.txt", "intentionally-not-standard-lld\n")
            output_dir = root / "aggregate-only-output"
            subprocess.run(["python3", "scripts/intake_clarity_archive.py", str(archive), "--output-dir", str(output_dir)], cwd=ROOT, check=True)
            with (output_dir / "real_intake_manifest.json").open(encoding="utf-8") as handle:
                manifest = __import__("json").load(handle)
            self.assertEqual(manifest["intake_scope"], "full-standard-lld-archive")
            self.assertEqual(manifest["loan_level_files_processed"], 2)

    def test_file_quality_report_detects_revisions_and_tests_fallback_controls(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            archive = root / "approved.zip"
            with zipfile.ZipFile(archive, "w") as package:
                package.writestr("22HQA1_20230701_lld.txt", row("202307", "111", "RA", "0") + "\n")
                package.writestr("22HQA1_20230715_lld.txt", row("202307", "111", "XX", "10") + "\n")
                package.writestr("notes.txt", "not a standard disclosure")
                package.writestr("24HQA1_20230801_lld.txt", row("202308", "999", "02", "50") + "\n")
            output_dir = root / "aggregate-only-output"
            subprocess.run(["python3", "scripts/intake_clarity_archive.py", str(archive), "--output-dir", str(output_dir)], cwd=ROOT, check=True)
            report = json.loads((output_dir / "real_intake_quality_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["accepted_files"], 1)
            self.assertEqual(report["rejected_files"], 3)
            self.assertTrue(report["official_total_reconciliation"]["fallback_checks_passed"])
            self.assertTrue(report["reporting_period_continuity"]["continuous"])
            rejected_reasons = {item["reason"] for item in report["files"] if item["status"] == "rejected"}
            self.assertIn("duplicate-or-revised-disclosure", rejected_reasons)
            self.assertIn("not-standard-monthly-lld", rejected_reasons)

    def test_official_totals_reconciliation_rejects_a_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            archive = root / "approved.zip"
            with zipfile.ZipFile(archive, "w") as package:
                package.writestr("22HQA1_20230701_lld.txt", row("202307", "111", "00", "100") + "\n")
            totals = root / "official.json"
            totals.write_text(json.dumps([{"file_name": "22HQA1_20230701_lld.txt", "records": 99, "current_upb": 100}]), encoding="utf-8")
            result = subprocess.run(["python3", "scripts/intake_clarity_archive.py", str(archive), "--official-totals", str(totals), "--output-dir", str(root / "out")], cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("no standard *_lld.txt files passed intake validation", result.stderr)


if __name__ == "__main__":
    unittest.main()
