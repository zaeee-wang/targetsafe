from __future__ import annotations

import unittest
import uuid
from pathlib import Path

from targetsafe.chem import evaluate_smiles
from targetsafe.decision import decide_candidate
from targetsafe.models import CandidateRecord
from targetsafe.pipeline import PipelineConfig, run_pipeline
from targetsafe.reference_drugs import known_context_for_smiles, reference_drugs


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
        self.assertTrue(result.evaluation_report["acceptance_checks"]["all_decisions_have_threshold_sources"])
        self.assertTrue(result.evaluation_report["acceptance_checks"]["all_decisions_have_evidence_nodes"])
        self.assertIn("rules", result.threshold_registry)
        self.assertIn("nodes", result.evidence_graph)
        self.assertIn("model_id", result.model_card)
        statuses = {c.decision.final_status for c in result.candidates if c.decision}
        self.assertTrue({"Go", "Hold", "No-Go"} & statuses)

    def test_invalid_smiles_is_no_go(self) -> None:
        candidate = CandidateRecord(candidate_id="X", smiles="not-a-smiles", source="test")
        candidate.descriptors = evaluate_smiles(candidate.smiles)
        decision = decide_candidate(candidate)
        self.assertEqual(decision.final_status, "No-Go")
        self.assertIn("invalid_smiles", decision.hard_gate_failures)
        self.assertTrue(decision.threshold_ids)

    def test_alert_control_is_flagged(self) -> None:
        candidate = CandidateRecord(candidate_id="X", smiles="O=N(=O)c1ccc(N=Nc2ccccc2)cc1", source="test")
        candidate.descriptors = evaluate_smiles(candidate.smiles)
        decision = decide_candidate(candidate)
        self.assertIn(decision.final_status, {"Hold", "No-Go"})
        self.assertTrue(candidate.descriptors.alerts)

    def test_gpu_profile_falls_back_without_crashing(self) -> None:
        root = Path("work") / "test_runs" / uuid.uuid4().hex
        result = run_pipeline(
            PipelineConfig(
                candidate_count=20,
                compute_profile="gpu-accelerated",
                output_dir=root,
                cache_path=root / "cache.sqlite",
            )
        )
        self.assertEqual(result.compute_profile["id"], "gpu-accelerated")
        self.assertIn("gpu_status", result.compute_profile)
        self.assertTrue(result.candidates)

    def test_reference_drug_library_has_structures_and_risk_context(self) -> None:
        drugs = reference_drugs(include_structures=True)
        self.assertGreaterEqual(len(drugs), 5)
        for drug in drugs:
            self.assertTrue(drug["smiles"])
            self.assertTrue(drug["source_status"])
            self.assertTrue(drug["label_risk_context"])
            self.assertIn("structure_svg", drug)

    def test_known_context_returns_similarity_without_decision_blocking(self) -> None:
        context = known_context_for_smiles(
            "COc1cc2ncnc(Nc3ccc(F)c(Cl)c3)c2cc1OCCCN1CCOCC1"
        )
        self.assertIn("nearest_known_drugs", context)
        self.assertGreaterEqual(len(context["nearest_known_drugs"]), 3)
        self.assertIn("not candidate-specific toxicity", context["interpretation"])


if __name__ == "__main__":
    unittest.main()
