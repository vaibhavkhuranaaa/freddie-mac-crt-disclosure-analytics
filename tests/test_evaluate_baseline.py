from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BaselineEvaluationTests(unittest.TestCase):
    def test_synthetic_baseline_is_reproducible(self) -> None:
        subprocess.run([sys.executable, "scripts/evaluate_baseline.py"], cwd=ROOT, check=True)
        result = json.loads((ROOT / "evaluation" / "baseline.json").read_text(encoding="utf-8"))
        self.assertEqual(result["source_classification"], "synthetic-fixture")
        self.assertEqual(result["schema_validity_rate"], 1.0)
        self.assertEqual(result["control_check_pass_rate"], 1.0)
        self.assertEqual(result["absolute_reconciliation_variance"], 0.0)
        self.assertEqual(result["rows_validated"], 10)


if __name__ == "__main__":
    unittest.main()
