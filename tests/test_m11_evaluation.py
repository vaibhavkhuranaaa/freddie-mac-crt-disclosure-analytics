from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class M11EvaluationTests(unittest.TestCase):
    def test_revised_m11_scope_closes_on_technical_gates(self) -> None:
        from scripts.evaluate_m11 import m11_milestone_complete

        self.assertTrue(m11_milestone_complete(True))
        self.assertFalse(m11_milestone_complete(False))

    def test_source_revision_attestation_reads_git_metadata(self) -> None:
        from scripts.evaluate_m11 import source_revision_attestation

        attestation = source_revision_attestation()
        self.assertIn(attestation["status"], {"verified", "working_tree_dirty"})
        self.assertEqual(len(attestation["revision"]), 40)
        self.assertTrue(attestation["branch"])

    def test_missing_independent_review_remains_explicit(self) -> None:
        from scripts.evaluate_m11 import load_reviewer_evidence

        with tempfile.TemporaryDirectory() as directory:
            evidence = load_reviewer_evidence(Path(directory) / "missing.json")
        self.assertEqual(evidence["status"], "unavailable")
        self.assertFalse(evidence["gate_passed"])
        self.assertEqual(evidence["representative_reviewers"], 0)

    def test_optional_independent_review_requires_four_of_five_and_attestation(self) -> None:
        from scripts.evaluate_m11 import load_reviewer_evidence

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "study.json"
            path.write_text(
                json.dumps(
                    {
                        "representative_reviewers": 5,
                        "completed_without_facilitator": 4,
                        "critical_defects": 0,
                        "attested_by": "project-owner",
                        "attested_on": "2026-08-10",
                    }
                ),
                encoding="utf-8",
            )
            evidence = load_reviewer_evidence(path)
        self.assertTrue(evidence["gate_passed"])
        self.assertEqual(evidence["status"], "pass")

    @unittest.skipUnless(
        (ROOT / "data/restricted/metrics/metrics.duckdb").exists(),
        "restricted M8 database is not available",
    )
    def test_all_shared_projection_rows_reconcile(self) -> None:
        from scripts.evaluate_m11 import reconcile_projection

        result = reconcile_projection()
        self.assertEqual(result["status"], "pass")
        self.assertTrue(all(result["checks"].values()))

    @unittest.skipUnless(
        (ROOT / "data/restricted/metrics/metrics.duckdb").exists(),
        "restricted M8 database is not available",
    )
    def test_three_findings_have_complete_decision_contracts(self) -> None:
        from scripts.evaluate_m11 import analytical_findings

        findings = analytical_findings()
        self.assertEqual(len(findings), 3)
        for finding in findings:
            for key in (
                "finding",
                "calculation",
                "business_meaning",
                "supported_decision",
                "limitation",
            ):
                self.assertTrue(finding[key])


if __name__ == "__main__":
    unittest.main()
