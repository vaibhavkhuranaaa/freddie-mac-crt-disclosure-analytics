from __future__ import annotations

import csv
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def row(period: str, pool: str, status: str, upb: str) -> str:
    fields = [""] * 40
    fields[0], fields[1], fields[2], fields[36], fields[39] = period, pool, "never-emitted-loan-id", status, upb
    return "|".join(fields)


class RealIntakeTests(unittest.TestCase):
    def test_adapter_derives_aggregate_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "aggregate-only-output"
            source = Path(tmpdir) / "approved_lld.txt"
            source.write_text("\n".join([row("202507", "123456", "00", "100.00"), row("202507", "123456", "02", "40.00"), row("202507", "123456", "RA", "10.00")]) + "\n", encoding="utf-8")
            subprocess.run(["python3", "scripts/intake_real_clarity.py", str(source), "--deal-id", "APPROVED-DEAL", "--program", "STACR", "--output-dir", str(output_dir)], cwd=ROOT, check=True)
            output = output_dir / "real_aggregate.csv"
            with output.open(newline="", encoding="utf-8") as handle:
                result = next(csv.DictReader(handle))
            self.assertEqual(result["current_upb"], "150.0")
            self.assertEqual(result["d30_plus_upb"], "40.0")
            self.assertEqual(result["d60_plus_upb"], "40.0")
            self.assertNotIn("never-emitted-loan-id", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
