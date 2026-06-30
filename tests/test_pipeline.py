from __future__ import annotations

import unittest
import uuid
from pathlib import Path

from targetsafe.chem import evaluate_smiles, generate_seed_analogs
from targetsafe.data_sources import _categorize_fetch_error
from targetsafe.decision import decide_candidate
from targetsafe.embeddings import gpu_diagnostics
from targetsafe.models import CandidateRecord, EvidenceBundle
from targetsafe.pipeline import PipelineConfig, run_pipeline
from targetsafe.qsar import EvidenceWeightedQSAR
from targetsafe.reference_drugs import known_context_for_smiles, reference_drugs
from targetsafe.runtime import llm_provider_options, runtime_status
from targetsafe.validation import build_qsar_validation_report


class TargetSafePipelineTests(unittest.TestCase):
    def test_pipeline_runs_offline_and_scores_candidates(self) -> None:
        root = Path("work") / "test_runs" / uuid.uuid4().hex
        result = run_pipeline(
            PipelineConfig(
                candidate_count=55,
                compute_profile="cpu-demo",
                allow_network=False,
                library_sources=["seed_analog"],
                library_limit=120,
                detailed_eval_limit=55,
                display_limit=24,
                conformer_limit=6,
                output_dir=root,
                cache_path=root / "cache.sqlite",
            )
        )
        candidate_rows = [c for c in result.candidates if c.candidate_id.startswith("C")]
        self.assertGreaterEqual(len(candidate_rows), 50)
        self.assertTrue(result.report_path)
        self.assertIn("candidate_count_at_least_50", result.evaluation_report["acceptance_checks"])
        self.assertTrue(result.evaluation_report["acceptance_checks"]["all_decisions_have_threshold_sources"])
        self.assertTrue(result.evaluation_report["acceptance_checks"]["all_decisions_have_gate_audit"])
        self.assertTrue(result.evaluation_report["acceptance_checks"]["all_decisions_have_evidence_nodes"])
        self.assertIn("rules", result.threshold_registry)
        self.assertIn("nodes", result.evidence_graph)
        self.assertIn("model_id", result.model_card)
        self.assertEqual(result.evidence_mode["mode"], "offline_fallback")
        self.assertIn("library_report", result.to_public_dict())
        self.assertIn("tool_error_summary", result.to_public_dict())
        self.assertIn("gpu_diagnostics", result.to_public_dict())
        self.assertGreaterEqual(result.library_report["valid_unique_count"], 50)
        self.assertEqual(result.runtime_status["llm"]["used"], False)
        self.assertGreaterEqual(result.redesign_report["created_children"], 1)
        self.assertEqual(result.validation_report["status"], "insufficient_data")
        self.assertTrue(result.agent_events)
        phases = {event.phase for event in result.agent_events}
        self.assertTrue({"Critique", "Replan", "Re-evaluate"} <= phases)
        self.assertTrue(result.evaluation_report["acceptance_checks"]["redesign_children_have_parent"])
        statuses = {c.decision.final_status for c in result.candidates if c.decision}
        self.assertTrue({"Go", "Hold", "No-Go"} & statuses)
        self.assertFalse(any(c.parent_candidate_id == "CTRL_NEG_INVALID" for c in result.candidates))

    def test_invalid_smiles_is_no_go(self) -> None:
        candidate = CandidateRecord(candidate_id="X", smiles="not-a-smiles", source="test")
        candidate.descriptors = evaluate_smiles(candidate.smiles)
        decision = decide_candidate(candidate)
        self.assertEqual(decision.final_status, "No-Go")
        self.assertIn("invalid_smiles", decision.hard_gate_failures)
        self.assertTrue(decision.threshold_ids)
        self.assertTrue(decision.gate_audit)
        self.assertEqual(decision.gate_audit[0].status, "block")

    def test_caffeine_control_is_not_confident_go(self) -> None:
        candidate = CandidateRecord(candidate_id="CAF", smiles="Cn1cnc2c1c(=O)n(C)c(=O)n2C", source="test")
        candidate.descriptors = evaluate_smiles(candidate.smiles)
        candidate.predicted_activity = 5.0
        candidate.prediction_interval = {"lower": 4.0, "mean": 5.0, "upper": 6.6, "width": 2.6}
        candidate.applicability_score = 0.02
        candidate.in_applicability_domain = False
        candidate.evidence_confidence = 0.1
        decision = decide_candidate(candidate)
        self.assertEqual(decision.final_status, "Hold")
        self.assertEqual(decision.criteria["applicability_domain"], "review")
        self.assertTrue(any(gate.status == "review" for gate in decision.gate_audit))

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
                compute_profile="cpu-demo",
                use_gpu=True,
                library_sources=["seed_analog"],
                library_limit=60,
                detailed_eval_limit=20,
                display_limit=10,
                conformer_limit=0,
                output_dir=root,
                cache_path=root / "cache.sqlite",
            )
        )
        self.assertEqual(result.compute_profile["id"], "cpu-demo")
        self.assertTrue(result.compute_profile["effective_use_gpu"])
        self.assertIn("gpu_status", result.compute_profile)
        self.assertTrue(result.candidates)
        self.assertIn("used", result.compute_profile["gpu_status"])

    def test_runtime_status_reports_llm_key_absence_without_secret(self) -> None:
        status = runtime_status(requested_gpu=True, requested_llm=True)
        self.assertIn("gpu", status)
        self.assertIn("gpu_diagnostics", status)
        self.assertIn("llm", status)
        self.assertIn("public_evidence_apis", status)
        self.assertNotIn("api_key", status["llm"])
        self.assertIn("configured", status["llm"])

    def test_llm_provider_options_and_runtime_secret_safety(self) -> None:
        providers = {item["id"] for item in llm_provider_options()}
        self.assertTrue({"openai", "anthropic", "deterministic", "openai-compatible"} <= providers)
        status = runtime_status(requested_gpu=False, requested_llm=True, llm_provider="anthropic", llm_api_key="secret")
        self.assertEqual(status["llm"]["provider"], "anthropic")
        self.assertTrue(status["llm"]["configured"])
        self.assertNotIn("secret", str(status))

    def test_gpu_diagnostics_schema_reports_compute_backend(self) -> None:
        diagnostics = gpu_diagnostics()
        self.assertEqual(diagnostics["schema"], "targetsafe.gpu_diagnostics.v1")
        self.assertIn("system_gpu", diagnostics)
        self.assertIn("torch_cuda", diagnostics)
        self.assertIn("action_hint", diagnostics)

    def test_tool_error_categories(self) -> None:
        refused = OSError("[WinError 10061] connection refused")
        self.assertEqual(_categorize_fetch_error(refused), "network_refused")
        self.assertEqual(_categorize_fetch_error(TimeoutError("timed out")), "timeout")

    def test_uploaded_library_rows_are_staged_and_reported(self) -> None:
        root = Path("work") / "test_runs" / uuid.uuid4().hex
        uploaded = ["CCO ethanol", "CC(=O)O acetic_acid", "not-a-smiles bad_row"]
        result = run_pipeline(
            PipelineConfig(
                compute_profile="cpu-demo",
                library_sources=["uploaded"],
                uploaded_smiles=uploaded,
                library_limit=40,
                detailed_eval_limit=20,
                display_limit=10,
                conformer_limit=0,
                output_dir=root,
                cache_path=root / "cache.sqlite",
            )
        )
        self.assertIn("uploaded", result.library_report["library_sources"])
        self.assertGreaterEqual(result.library_report["raw_input_count"], 3)
        self.assertGreaterEqual(result.library_report["invalid_or_unparseable_count"], 1)
        self.assertTrue(result.screening_stages)

    def test_reference_drug_library_has_structures_and_risk_context(self) -> None:
        drugs = reference_drugs(include_structures=True)
        self.assertGreaterEqual(len(drugs), 5)
        scoring_refs = [drug for drug in drugs if drug.get("smiles")]
        self.assertGreaterEqual(len(scoring_refs), 5)
        self.assertGreaterEqual(len(drugs), 40)
        for drug in drugs:
            self.assertTrue(drug["source_status"])
            self.assertTrue(drug["label_risk_context"])
            self.assertTrue(drug.get("structure_svg") or drug.get("structure_image_url"))

    def test_known_context_returns_similarity_without_decision_blocking(self) -> None:
        context = known_context_for_smiles(
            "COc1cc2ncnc(Nc3ccc(F)c(Cl)c3)c2cc1OCCCN1CCOCC1"
        )
        self.assertIn("nearest_known_drugs", context)
        self.assertGreaterEqual(len(context["nearest_known_drugs"]), 3)
        self.assertIn("not candidate-specific toxicity", context["interpretation"])

    def test_validation_metrics_are_only_created_with_enough_rows(self) -> None:
        sparse_evidence = EvidenceBundle(target="EGFR", disease="test")
        sparse_qsar = EvidenceWeightedQSAR(sparse_evidence)
        sparse_report = build_qsar_validation_report(sparse_evidence, sparse_qsar)
        self.assertEqual(sparse_report["status"], "insufficient_data")
        self.assertEqual(sparse_report["metrics"], {})

        analogs = generate_seed_analogs(
            "COc1cc2ncnc(Nc3ccc(F)c(Cl)c3)c2cc1OCCCN1CCOCC1",
            count=28,
        )
        activities = []
        for index, candidate in enumerate(analogs):
            activities.append(
                {
                    "molecule_chembl_id": f"SYN{index:03d}",
                    "canonical_smiles": candidate.smiles,
                    "pchembl_value": 6.1 + (index % 9) * 0.22,
                    "source_status": "synthetic_live_like_test",
                }
            )
        evidence = EvidenceBundle(target="EGFR", disease="synthetic validation", chembl_activities=activities)
        qsar = EvidenceWeightedQSAR(evidence)
        report = build_qsar_validation_report(evidence, qsar)
        self.assertEqual(report["status"], "validated")
        self.assertGreaterEqual(report["split_summary"]["train_count"], 4)
        self.assertGreaterEqual(report["split_summary"]["test_count"], 3)
        self.assertIn("rmse", report["metrics"])
        self.assertIn("mae", report["metrics"])
        self.assertIn("spearman", report["metrics"])


if __name__ == "__main__":
    unittest.main()
