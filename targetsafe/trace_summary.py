from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from targetsafe.models import AgentEvent, CandidateRecord, ToolCallLog


FLOW_BLUEPRINT = [
    ("plan", "Plan", "Planner Agent"),
    ("evidence", "Evidence search", "Evidence Agent"),
    ("library", "Library build", "Molecular Proposer"),
    ("molecular_eval", "Molecular evaluation", "RDKit/QSAR Evaluator"),
    ("qsar_ad", "QSAR / AD", "RDKit/QSAR Evaluator"),
    ("critic", "Critic review", "Critic Agent"),
    ("redesign", "Replan / Redesign", "Redesign Agent"),
    ("decision", "Decision", "Decision Agent"),
    ("report", "Report", "Report Agent"),
]

PHASE_ALIASES = {
    "plan": {"plan"},
    "evidence": {"act"},
    "library": {"act"},
    "molecular_eval": {"observe"},
    "qsar_ad": {"observe"},
    "critic": {"critique"},
    "redesign": {"replan", "re-evaluate"},
    "decision": {"decide"},
    "report": {"report"},
}


def build_agent_trace_summary(
    *,
    agent_events: list[AgentEvent],
    tool_logs: list[ToolCallLog],
    candidates: list[CandidateRecord],
    evidence_mode: dict[str, Any],
    redesign_report: dict[str, Any],
    validation_report: dict[str, Any],
    performance_summary: dict[str, Any],
) -> dict[str, Any]:
    status_counts = Counter(c.decision.final_status if c.decision else "Unscored" for c in candidates)
    fallback_logs = [log for log in tool_logs if log.fallback_used or "fallback" in log.status.lower() or log.error_category]
    critic_findings_count = sum(len(c.decision.critic_findings) for c in candidates if c.decision)
    review_candidate_count = status_counts.get("Hold", 0) + status_counts.get("No-Go", 0)
    events_by_node = _events_by_node(agent_events)
    nodes: list[dict[str, Any]] = []

    for node_id, label, agent in FLOW_BLUEPRINT:
        node_events = events_by_node.get(node_id, [])
        status = _node_status(
            node_id=node_id,
            node_events=node_events,
            fallback_logs=fallback_logs,
            critic_findings_count=critic_findings_count,
            review_candidate_count=review_candidate_count,
            redesign_report=redesign_report,
            validation_report=validation_report,
        )
        nodes.append(
            {
                "id": node_id,
                "label": label,
                "agent": agent,
                "status": status,
                "event_count": len(node_events),
                "summary": _node_summary(
                    node_id=node_id,
                    candidates=candidates,
                    status_counts=status_counts,
                    fallback_count=len(fallback_logs),
                    critic_findings_count=critic_findings_count,
                    redesign_report=redesign_report,
                    validation_report=validation_report,
                    performance_summary=performance_summary,
                    evidence_mode=evidence_mode,
                ),
                "event_steps": [event.step for event in node_events],
            }
        )

    edges = [
        {"source": FLOW_BLUEPRINT[index][0], "target": FLOW_BLUEPRINT[index + 1][0], "type": "then"}
        for index in range(len(FLOW_BLUEPRINT) - 1)
    ]
    if int(redesign_report.get("created_children", 0) or 0) > 0:
        edges.append({"source": "redesign", "target": "molecular_eval", "type": "re-evaluate"})

    phase_summaries = {
        node["id"]: {
            "label": node["label"],
            "status": node["status"],
            "summary": node["summary"],
            "event_count": node["event_count"],
        }
        for node in nodes
    }
    decision_impact = _decision_impact(status_counts, critic_findings_count, redesign_report, validation_report)
    plain_summary = [
        (
            f"The agent planned the run, screened {len(candidates)} candidates, and produced "
            f"{status_counts.get('Go', 0)} Go, {status_counts.get('Hold', 0)} Hold, "
            f"and {status_counts.get('No-Go', 0)} No-Go decisions."
        ),
        (
            "Critic review changed the interpretation from a simple score into a gated decision: "
            f"{critic_findings_count} critic finding(s) were recorded."
        ),
        (
            f"Evidence mode was {evidence_mode.get('label', evidence_mode.get('mode', 'unknown'))}; "
            f"{len(fallback_logs)} fallback or tool-warning event(s) were logged."
        ),
        decision_impact,
    ]
    return {
        "schema": "targetsafe.agent_trace_summary.v1",
        "plain_summary": plain_summary,
        "flow_nodes": nodes,
        "flow_edges": edges,
        "phase_summaries": phase_summaries,
        "fallback_events_count": len(fallback_logs),
        "critic_findings_count": critic_findings_count,
        "decision_impact": decision_impact,
    }


def attach_candidate_decision_flows(candidates: list[CandidateRecord]) -> None:
    for candidate in candidates:
        candidate.candidate_decision_flow = build_candidate_decision_flow(candidate)


def build_candidate_decision_flow(candidate: CandidateRecord) -> list[dict[str, Any]]:
    decision = candidate.decision
    descriptors = candidate.descriptors
    nodes: list[dict[str, Any]] = []

    valid = bool(descriptors and descriptors.valid)
    nodes.append(
        {
            "id": "valid_smiles",
            "label": "Valid SMILES",
            "status": "done" if valid else "blocked",
            "summary": "Structure parsed successfully." if valid else "Invalid or unparseable SMILES blocked the candidate.",
        }
    )
    if not valid:
        nodes.append(
            {
                "id": "final_decision",
                "label": "Final decision",
                "status": "blocked",
                "summary": f"{decision.final_status if decision else 'No-Go'}: input correction is required before scientific review.",
            }
        )
        return nodes

    alert_count = len(descriptors.alerts if descriptors else [])
    severe_count = len(descriptors.severe_alerts if descriptors else [])
    nodes.append(
        {
            "id": "structural_alerts",
            "label": "Structural alerts",
            "status": "blocked" if severe_count else ("review" if alert_count else "done"),
            "summary": f"{alert_count} alert(s), {severe_count} severe blocker(s).",
        }
    )

    criteria = decision.criteria if decision else {}
    gate_lookup = {gate.criterion_id: gate for gate in (decision.gate_audit if decision else [])}
    for criterion_id, label in [
        ("molecular_weight", "Descriptor gates"),
        ("conservative_activity", "Conservative activity"),
        ("applicability_domain", "Applicability domain"),
        ("prediction_uncertainty", "Prediction uncertainty"),
        ("evidence_support", "Evidence support"),
    ]:
        status = _criteria_status(criteria.get(criterion_id) or getattr(gate_lookup.get(criterion_id), "status", "review"))
        gate = gate_lookup.get(criterion_id)
        summary = gate.message if gate else _fallback_candidate_summary(candidate, criterion_id)
        nodes.append({"id": criterion_id, "label": label, "status": status, "summary": summary})

    critic_findings = decision.critic_findings if decision else []
    nodes.append(
        {
            "id": "critic_review",
            "label": "Critic review",
            "status": "review" if critic_findings else "done",
            "summary": "; ".join(critic_findings[:2]) if critic_findings else "No critic blocker was recorded.",
        }
    )

    if candidate.parent_candidate_id or candidate.redesign_reason or candidate.redesign_action:
        nodes.append(
            {
                "id": "redesign_context",
                "label": "Redesign context",
                "status": "review" if decision and decision.final_status == "Hold" else "done",
                "summary": candidate.redesign_action or candidate.redesign_reason or f"Child of {candidate.parent_candidate_id}.",
            }
        )

    final_status = decision.final_status if decision else "Unscored"
    nodes.append(
        {
            "id": "final_decision",
            "label": "Final decision",
            "status": _final_status_to_flow_status(final_status),
            "summary": f"{final_status}: {'; '.join((decision.reasons if decision else [])[:2])}",
        }
    )
    return nodes


def _events_by_node(agent_events: list[AgentEvent]) -> dict[str, list[AgentEvent]]:
    grouped: dict[str, list[AgentEvent]] = defaultdict(list)
    for event in agent_events:
        text = f"{event.phase} {event.agent} {event.action}".lower()
        if "planner" in text or "create_run_plan" in text:
            grouped["plan"].append(event)
        if "evidence" in text or "public" in text:
            grouped["evidence"].append(event)
        if "library" in text or "proposer" in text or "candidate" in text:
            grouped["library"].append(event)
        if "descriptor" in text or "rdkit" in text or "molecular" in text:
            grouped["molecular_eval"].append(event)
        if "qsar" in text or "applicability" in text or "validation" in text:
            grouped["qsar_ad"].append(event)
        if "critic" in text or "critique" in text:
            grouped["critic"].append(event)
        if "redesign" in text or "replan" in text or "re-evaluate" in text:
            grouped["redesign"].append(event)
        if "decision" in text or "decide" in text or "compare_parent_child" in text:
            grouped["decision"].append(event)
    return grouped


def _node_status(
    *,
    node_id: str,
    node_events: list[AgentEvent],
    fallback_logs: list[ToolCallLog],
    critic_findings_count: int,
    review_candidate_count: int,
    redesign_report: dict[str, Any],
    validation_report: dict[str, Any],
) -> str:
    if node_id == "evidence" and fallback_logs:
        return "fallback"
    if node_id == "critic" and critic_findings_count:
        return "review"
    if node_id == "redesign" and int(redesign_report.get("created_children", 0) or 0):
        return "review"
    if node_id == "qsar_ad" and validation_report.get("status") == "insufficient_data":
        return "review"
    if node_id == "decision" and review_candidate_count:
        return "review"
    if node_events or node_id == "report":
        return "done"
    return "review"


def _node_summary(
    *,
    node_id: str,
    candidates: list[CandidateRecord],
    status_counts: Counter,
    fallback_count: int,
    critic_findings_count: int,
    redesign_report: dict[str, Any],
    validation_report: dict[str, Any],
    performance_summary: dict[str, Any],
    evidence_mode: dict[str, Any],
) -> str:
    if node_id == "plan":
        return "Planner created a tool-grounded run plan from disease, target, seed, compute profile, and optimization intent."
    if node_id == "evidence":
        return f"Evidence mode: {evidence_mode.get('label', evidence_mode.get('mode', 'unknown'))}; fallback/tool-warning events: {fallback_count}."
    if node_id == "library":
        return f"Library staged {len(candidates)} evaluated candidates after validity, deduplication, controls, and source labeling."
    if node_id == "molecular_eval":
        valid = len([c for c in candidates if c.descriptors and c.descriptors.valid])
        return f"RDKit descriptor and structure checks completed for {valid}/{len(candidates)} parseable structures."
    if node_id == "qsar_ad":
        return f"QSAR/applicability validation status: {validation_report.get('status', 'unknown')}."
    if node_id == "critic":
        return f"Critic findings recorded: {critic_findings_count}; findings can downgrade overconfident Go calls to Hold."
    if node_id == "redesign":
        return f"Constrained redesign children created: {redesign_report.get('created_children', 0)}."
    if node_id == "decision":
        return f"Decision distribution: Go {status_counts.get('Go', 0)}, Hold {status_counts.get('Hold', 0)}, No-Go {status_counts.get('No-Go', 0)}."
    return f"Report and JSON outputs generated after {performance_summary.get('duration_ms', '-')} ms."


def _decision_impact(
    status_counts: Counter,
    critic_findings_count: int,
    redesign_report: dict[str, Any],
    validation_report: dict[str, Any],
) -> str:
    parts = []
    if critic_findings_count:
        parts.append(f"Critic review introduced {critic_findings_count} review signal(s), preventing unsupported confident decisions.")
    if int(redesign_report.get("created_children", 0) or 0):
        parts.append(f"Redesign created {redesign_report.get('created_children')} child candidate(s) for re-evaluation.")
    if validation_report.get("status") == "insufficient_data":
        parts.append("QSAR validation remained insufficient-data, so decisions should be interpreted as demo-grade triage.")
    if not parts:
        parts.append("No critic or redesign event materially changed the decision path in this run.")
    parts.append(f"Final triage left {status_counts.get('Hold', 0)} Hold and {status_counts.get('No-Go', 0)} No-Go candidate(s) for review or correction.")
    return " ".join(parts)


def _criteria_status(value: str) -> str:
    lowered = str(value or "").lower()
    if lowered in {"pass", "done", "go"}:
        return "done"
    if lowered in {"block", "blocked", "fail", "no-go"}:
        return "blocked"
    return "review"


def _final_status_to_flow_status(value: str) -> str:
    if value == "Go":
        return "done"
    if value == "No-Go":
        return "blocked"
    return "review"


def _fallback_candidate_summary(candidate: CandidateRecord, criterion_id: str) -> str:
    if criterion_id == "conservative_activity":
        lower = (candidate.prediction_interval or {}).get("lower")
        return f"Lower-bound pChEMBL estimate: {lower if lower is not None else 'not available'}."
    if criterion_id == "applicability_domain":
        return f"Nearest-analog applicability score: {candidate.applicability_score:.3f}."
    if criterion_id == "prediction_uncertainty":
        width = (candidate.prediction_interval or {}).get("width")
        return f"Prediction interval width: {width if width is not None else 'not available'}."
    if criterion_id == "evidence_support":
        return f"Evidence confidence: {candidate.evidence_confidence:.3f}."
    return "Descriptor and rule-based gate reviewed."
