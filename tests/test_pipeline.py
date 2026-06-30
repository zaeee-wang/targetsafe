from __future__ import annotations

import unittest
import uuid
from pathlib import Path

from targetsafe.chem import evaluate_smiles
from targetsafe.decision import decide_candidate
from targetsafe.models import CandidateRecord
from targetsafe.pipeline import PipelineConfig, run_pipeline


class TargetSafePipelineTests(unittest.TestCase):
    def test_pipeline_runs_offline_and_scores_candidates(self) -> None:
        root = Path("work") / "test_runs" / uuid.uuid4().hex
        result = run_pipeline(
            PipelineConfig(
                candidate_count=55,
                allow_network=False,
                output_dir=root,
                cache_path=root / "cache.sqlite",
            )
        )
        candidate_rows = [c for c in result.candidates if c.candidate_id.startswith("C")]
        self.assertGreaterEqual(len(candidate_rows), 50)
        self.assertTrue(result.report_path)
        self.assertIn("candidate_count_at_least_50", result.evaluation_report["acceptance_checks"])
        statuses = {c.decision.final_status for c in result.candidates if c.decision}
        self.assertTrue({"Go", "Hold", "No-Go"} & statuses)

    def test_invalid_smiles_is_no_go(self) -> None:
        candidate = CandidateRecord(candidate_id="X", smiles="not-a-smiles", source="test")
        candidate.descriptors = evaluate_smiles(candidate.smiles)
        decision = decide_candidate(candidate)
        self.assertEqual(decision.final_status, "No-Go")
        self.assertIn("invalid_smiles", decision.hard_gate_failures)

    def test_alert_control_is_flagged(self) -> None:
        candidate = CandidateRecord(candidate_id="X", smiles="O=N(=O)c1ccc(N=Nc2ccccc2)cc1", source="test")
        candidate.descriptors = evaluate_smiles(candidate.smiles)
        decision = decide_candidate(candidate)
        self.assertIn(decision.final_status, {"Hold", "No-Go"})
        self.assertTrue(candidate.descriptors.alerts)


if __name__ == "__main__":
    unittest.main()
