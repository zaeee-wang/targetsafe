from __future__ import annotations

from typing import Any

from targetsafe.models import CandidateRecord, EvidenceBundle
from targetsafe.thresholds import ThresholdRegistry


def build_evidence_graph(
    run_id: str,
    candidates: list[CandidateRecord],
    evidence: EvidenceBundle,
    thresholds: ThresholdRegistry,
) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = [
        {
            "id": "target_EGFR",
            "type": "target",
            "label": evidence.target,
            "detail": "Pilot target for EGFR mutation-positive NSCLC.",
        },
        {
            "id": "disease_context",
            "type": "disease",
            "label": evidence.disease,
            "detail": "Disease context selected by the user.",
        },
    ]
    edges: list[dict[str, Any]] = [
        {"source": "target_EGFR", "target": "disease_context", "type": "context_for", "weight": 1.0}
    ]

    for rule_id, rule in thresholds.to_dict()["rules"].items():
        nodes.append(
            {
                "id": f"threshold_{rule_id}",
                "type": "threshold",
                "label": rule["label"],
                "value": rule["value"],
                "units": rule["units"],
                "source": rule["source"],
                "rationale": rule["rationale"],
            }
        )

    for idx, item in enumerate(evidence.chembl_activities[:10], 1):
        node_id = f"chembl_activity_{idx}"
        nodes.append(
            {
                "id": node_id,
                "type": "assay",
                "label": item.get("molecule_chembl_id", f"ChEMBL activity {idx}"),
                "detail": item,
            }
        )
        edges.append({"source": node_id, "target": "target_EGFR", "type": "supports", "weight": 0.6})

    for idx, item in enumerate(evidence.regulatory_risks[:8], 1):
        node_id = f"risk_{idx}"
        nodes.append(
            {
                "id": node_id,
                "type": "class_risk",
                "label": item.get("risk", f"Class risk {idx}"),
                "detail": item.get("interpretation", ""),
            }
        )
        edges.append({"source": node_id, "target": "target_EGFR", "type": "requires_review", "weight": 0.4})

    for candidate in candidates:
        _add_candidate_subgraph(candidate, nodes, edges)

    return {
        "run_id": run_id,
        "schema": "targetsafe.evidence_graph.v1",
        "summary": _graph_summary(nodes, edges),
        "nodes": nodes,
        "edges": edges,
    }


def _add_candidate_subgraph(
    candidate: CandidateRecord,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> None:
    desc = candidate.descriptors
    decision = candidate.decision
    candidate_id = f"candidate_{candidate.candidate_id}"
    descriptor_id = f"descriptor_{candidate.candidate_id}"
    prediction_id = f"prediction_{candidate.candidate_id}"
    decision_id = f"decision_{candidate.candidate_id}"
    alert_id = f"alert_{candidate.candidate_id}"
    redesign_node_ids: list[str] = []

    nodes.append(
        {
            "id": candidate_id,
            "type": "candidate",
            "label": candidate.candidate_id,
            "smiles": candidate.smiles,
            "status": decision.final_status if decision else "Unscored",
            "generation": candidate.generation,
            "parent_candidate_id": candidate.parent_candidate_id,
            "redesign_reason": candidate.redesign_reason,
            "redesign_action": candidate.redesign_action,
        }
    )
    nodes.append(
        {
            "id": descriptor_id,
            "type": "descriptor",
            "label": "Molecular descriptors",
            "detail": desc.to_dict() if desc else {},
        }
    )
    nodes.append(
        {
            "id": prediction_id,
            "type": "model_prediction",
            "label": "EGFR activity estimate",
            "activity": candidate.predicted_activity,
            "interval": candidate.prediction_interval,
            "applicability": candidate.applicability_score,
            "in_domain": candidate.in_applicability_domain,
            "nearest_analogs": candidate.nearest_analogs,
        }
    )
    nodes.append(
        {
            "id": decision_id,
            "type": "decision",
            "label": decision.final_status if decision else "Unscored",
            "detail": decision.to_dict() if decision else {},
        }
    )
    edges.extend(
        [
            {"source": candidate_id, "target": descriptor_id, "type": "derived_from", "weight": 1.0},
            {"source": descriptor_id, "target": prediction_id, "type": "derived_from", "weight": 0.8},
            {"source": prediction_id, "target": decision_id, "type": "supports", "weight": 0.8},
            {"source": decision_id, "target": candidate_id, "type": "classifies", "weight": 1.0},
        ]
    )

    if candidate.parent_candidate_id:
        parent_id = f"candidate_{candidate.parent_candidate_id}"
        redesign_id = f"redesign_{candidate.candidate_id}"
        redesign_node_ids = [parent_id, redesign_id]
        nodes.append(
            {
                "id": redesign_id,
                "type": "redesign_action",
                "label": candidate.redesign_reason or "critic redesign",
                "action": candidate.redesign_action,
                "parent_candidate_id": candidate.parent_candidate_id,
                "child_candidate_id": candidate.candidate_id,
            }
        )
        edges.extend(
            [
                {"source": parent_id, "target": redesign_id, "type": "critic_triggers", "weight": 0.95},
                {"source": redesign_id, "target": candidate_id, "type": "redesigns", "weight": 0.95},
            ]
        )

    if desc and (desc.alerts or desc.severe_alerts):
        nodes.append(
            {
                "id": alert_id,
                "type": "structural_alert",
                "label": "Structural alert",
                "alerts": desc.alerts,
                "severe_alerts": desc.severe_alerts,
            }
        )
        edges.append(
            {
                "source": alert_id,
                "target": decision_id,
                "type": "blocks" if desc.severe_alerts else "requires_review",
                "weight": 1.0 if desc.severe_alerts else 0.55,
            }
        )

    if decision:
        for threshold_id in decision.threshold_ids:
            edges.append(
                {
                    "source": f"threshold_{threshold_id}",
                    "target": decision_id,
                    "type": "derived_from",
                    "weight": 0.65,
                }
            )
        for analog in candidate.nearest_analogs[:3]:
            analog_id = f"analog_{candidate.candidate_id}_{_safe_id(analog.get('name', 'ref'))}"
            nodes.append(
                {
                    "id": analog_id,
                    "type": "known_analog",
                    "label": analog.get("name", "EGFR reference"),
                    "smiles": analog.get("smiles"),
                    "similarity": analog.get("similarity"),
                    "pchembl": analog.get("pchembl"),
                    "source": analog.get("source"),
                }
            )
            edges.append(
                {
                    "source": analog_id,
                    "target": prediction_id,
                    "type": "supports" if (analog.get("similarity") or 0) >= 0.18 else "weakens",
                    "weight": float(analog.get("similarity") or 0.0),
                }
            )
        candidate.evidence_node_ids = [candidate_id, descriptor_id, prediction_id, decision_id] + redesign_node_ids
        decision.evidence_node_ids = candidate.evidence_node_ids
        _attach_molecular_twin(candidate, candidate_id, descriptor_id, prediction_id, decision_id)


def _attach_molecular_twin(
    candidate: CandidateRecord,
    candidate_id: str,
    descriptor_id: str,
    prediction_id: str,
    decision_id: str,
) -> None:
    desc = candidate.descriptors
    decision = candidate.decision
    criteria = decision.criteria if decision else {}
    pass_count = sum(1 for value in criteria.values() if value == "pass")
    total_count = max(1, len(criteria))
    candidate.molecular_twin = {
        "title": f"{candidate.candidate_id} molecular evidence twin",
        "definition": "Computed research twin: structure, descriptors, model uncertainty, evidence, and next validation state.",
        "evidence_completeness": round(pass_count / total_count, 3),
        "sections": {
            "Molecular Identity": {
                "node_id": candidate_id,
                "canonical_smiles": desc.canonical_smiles if desc else candidate.smiles,
                "molecular_weight": round(desc.molecular_weight, 2) if desc else None,
                "method": desc.method if desc else "unknown",
            },
            "Predicted Target Fit": {
                "node_id": prediction_id,
                "predicted_pchembl": round(candidate.predicted_activity, 3) if candidate.predicted_activity else None,
                "prediction_interval": candidate.prediction_interval,
                "applicability_score": round(candidate.applicability_score, 3),
                "in_applicability_domain": candidate.in_applicability_domain,
                "nearest_analogs": candidate.nearest_analogs,
            },
            "ADMET/Risk": {
                "node_id": descriptor_id,
                "qed": round(desc.qed, 3) if desc else None,
                "logp": round(desc.logp, 3) if desc else None,
                "tpsa": round(desc.tpsa, 2) if desc else None,
                "sa_score": round(desc.sa_score, 2) if desc else None,
                "alerts": desc.alerts if desc else [],
                "severe_alerts": desc.severe_alerts if desc else [],
            },
            "Evidence": {
                "evidence_confidence": candidate.evidence_confidence,
                "node_ids": candidate.evidence_node_ids,
            },
            "Redesign": {
                "parent_candidate_id": candidate.parent_candidate_id,
                "generation": candidate.generation,
                "reason": candidate.redesign_reason,
                "action": candidate.redesign_action,
            },
            "Decision": {
                "node_id": decision_id,
                "status": decision.final_status if decision else "Unscored",
                "criteria": criteria,
                "reasons": decision.reasons if decision else [],
                "uncertainty": decision.uncertainty if decision else [],
            },
            "Next Validation": {
                "follow_up": decision.follow_up if decision else ["Run candidate through the Target-SAFE pipeline."],
            },
        },
    }


def _graph_summary(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, Any]:
    edge_counts: dict[str, int] = {}
    for edge in edges:
        edge_type = str(edge.get("type", "unknown"))
        edge_counts[edge_type] = edge_counts.get(edge_type, 0) + 1
    return {"node_count": len(nodes), "edge_count": len(edges), "edge_counts": edge_counts}


def _safe_id(value: object) -> str:
    text = "".join(ch if ch.isalnum() else "_" for ch in str(value).lower())
    return text.strip("_") or "ref"
