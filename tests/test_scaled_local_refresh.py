from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]


def disclosure_row(period: str, status: str = "00") -> str:
    fields = [""] * 93
    values = {
        0: period,
        1: "26HQA1",
        2: "L1",
        4: "Seller",
        5: "IL",
        8: "202401",
        13: "100",
        14: "P",
        15: "R",
        16: "SF",
        17: "P",
        22: "700",
        23: "80",
        24: "80",
        25: "35",
        32: "Servicer",
        33: "24",
        36: status,
        38: "6.0",
        39: "100",
        88: "Y",
    }
    for index, value in values.items():
        fields[index] = value
    return "|".join(fields)


def write_archive(path: Path, periods: dict[str, str]) -> None:
    with zipfile.ZipFile(path, "w") as package:
        for period, status in periods.items():
            package.writestr(
                f"26HQA1_{period}01_lld.txt",
                disclosure_row(period, status) + "\n",
            )


def run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *arguments],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


class ScaledLocalRefreshTests(unittest.TestCase):
    def test_append_refresh_preserves_history_and_recovers_orphan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base_archive = root / "base.zip"
            updated_archive = root / "updated.zip"
            write_archive(base_archive, {"202606": "00", "202607": "01"})
            write_archive(updated_archive, {"202606": "00", "202607": "01", "202608": "02"})
            foundation = root / "foundation"
            quality = root / "quality.json"
            operations = root / "operations"
            aggregate_dir = root / "aggregate"
            release = aggregate_dir / "real_aggregate.csv"
            database = root / "metrics.duckdb"
            metric_evaluation = root / "metric-evaluation.json"
            evaluation = root / "m12-evaluation.json"

            result = run(
                "scripts/build_full_data_layer.py",
                str(base_archive),
                "--output-dir",
                str(foundation),
                "--quality-report",
                str(quality),
                "--allow-nonrestricted-output",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            result = run(
                "scripts/intake_clarity_archive.py",
                str(base_archive),
                "--output-dir",
                str(aggregate_dir),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            result = run(
                "scripts/build_metric_engine.py",
                "--foundation",
                str(foundation),
                "--output",
                str(database),
                "--evaluation",
                str(metric_evaluation),
                "--release-aggregate",
                str(release),
                "--allow-nonrestricted-output",
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            command = [
                "scripts/run_scaled_local_refresh.py",
                str(base_archive),
                "--foundation",
                str(foundation),
                "--database",
                str(database),
                "--release-aggregate",
                str(release),
                "--operations-dir",
                str(operations),
                "--evaluation",
                str(evaluation),
                "--retain-runs",
                "2",
                "--allow-nonrestricted-output",
            ]
            result = run(*command)
            self.assertEqual(result.returncode, 0, result.stderr)
            broken_database = root / "broken.duckdb"
            broken_database.write_text("not a database", encoding="utf-8")
            interrupted_command = [
                str(broken_database) if value == str(database) else
                str(updated_archive) if value == str(base_archive) else value
                for value in command
            ]
            result = run(*interrupted_command)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(
                json.loads((foundation / "manifest.json").read_text(encoding="utf-8"))["records"],
                3,
            )
            result = run(*[str(updated_archive) if value == str(base_archive) else value for value in command])
            self.assertEqual(result.returncode, 0, result.stderr)

            manifest = json.loads((foundation / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["records"], 3)
            self.assertEqual(manifest["accepted_files"], 3)
            with duckdb.connect(str(database), read_only=True) as connection:
                self.assertEqual(
                    connection.execute("SELECT reporting_period, d60_plus_rate FROM portfolio_period_metrics ORDER BY reporting_period").fetchall(),
                    [("202606", 0.0), ("202607", 0.0), ("202608", 1.0)],
                )
            runs = sorted((operations / "runs").glob("*.json"))
            latest = next(
                record
                for record in (json.loads(path.read_text(encoding="utf-8")) for path in runs)
                if record.get("metric_refresh", {}).get("mode") == "rolling-window-incremental"
            )
            self.assertTrue(latest["metric_refresh"]["historical_row_hashes_preserved"])

            orphan_relative = "loan_period/deal_id=2026-HQA1/reporting_period=202609/data.parquet"
            orphan = foundation / orphan_relative
            orphan.parent.mkdir(parents=True)
            orphan.write_bytes(b"interrupted")
            interrupted = operations / "runs" / "interrupted.json"
            interrupted.write_text(
                json.dumps({"status": "running", "planned_partition_paths": [orphan_relative]}),
                encoding="utf-8",
            )
            result = run(*[str(updated_archive) if value == str(base_archive) else value for value in command])
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(orphan.exists())
            self.assertLessEqual(len(list((operations / "runs").glob("*.json"))), 2)

    def test_rejects_revision_of_existing_partition(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "base.zip"
            revised = root / "revised.zip"
            write_archive(archive, {"202606": "00", "202607": "01"})
            write_archive(revised, {"202606": "00", "202607": "02"})
            foundation = root / "foundation"
            aggregate = root / "aggregate"
            database = root / "metrics.duckdb"
            commands = (
                ["scripts/build_full_data_layer.py", str(archive), "--output-dir", str(foundation), "--quality-report", str(root / "quality.json"), "--allow-nonrestricted-output"],
                ["scripts/intake_clarity_archive.py", str(archive), "--output-dir", str(aggregate)],
                ["scripts/build_metric_engine.py", "--foundation", str(foundation), "--output", str(database), "--evaluation", str(root / "metric.json"), "--release-aggregate", str(aggregate / "real_aggregate.csv"), "--allow-nonrestricted-output"],
            )
            for command in commands:
                result = run(*command)
                self.assertEqual(result.returncode, 0, result.stderr)
            common = [
                "--foundation", str(foundation), "--database", str(database),
                "--release-aggregate", str(aggregate / "real_aggregate.csv"),
                "--operations-dir", str(root / "operations"), "--evaluation", str(root / "m12.json"),
                "--allow-nonrestricted-output",
            ]
            result = run("scripts/run_scaled_local_refresh.py", str(archive), *common)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = run("scripts/run_scaled_local_refresh.py", str(revised), *common)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("revises existing partition", result.stderr)


if __name__ == "__main__":
    unittest.main()
