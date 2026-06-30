from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

from targetsafe.data_sources import PublicDataSources
from targetsafe.decision import decide_candidate
from targetsafe.models import CandidateRecord, DecisionResult, EvidenceBundle
from targetsafe.thresholds import ThresholdRegistry


class LLMClient:
    def __init__(
        self,
        enabled: bool = False,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self.requested = enabled
        self.api_key = (api_key or os.getenv("OPENAI_API_KEY") or "").strip()
        self.enabled = enabled and bool(self.api_key)
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    def chat(self, system: str, user: str) -> str | None:
        if not self.enabled:
            return None
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0.2,
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                data = json.loads(response.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
        except Exception:
            return None


class PlannerAgent:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient(False)

    def plan(self, disease: str, target: str, optimization_goal: str) -> list[str]:
        fallback = [
            "Validate disease, target, seed SMILES, and optimization goal.",
            "Collect EGFR activity and class-level clinical/regulatory evidence.",
            "Generate seed-derived analog candidates and remove duplicates.",
            "Calculate descriptors, drug-likeness, structural alerts, and SA score.",
            "Estimate conservative activity interval, evidence confidence, nearest analogs, and applicability domain.",
            "Apply sourced hard gates before Go/Hold/No-Go triage.",
            "Run critic review for invalid structures, alerts, weak evidence, and overclaiming.",
            "Produce molecular twin view, evidence graph, trace log, and HTML report.",
        ]
        prompt = (
            f"Disease: {disease}\nTarget: {target}\nGoal: {optimization_goal}\n"
            "Return a concise 8-step execution plan for a drug-discovery triage agent."
        )
        text = self.llm.chat("You are a cautious drug-discovery workflow planner.", prompt)
        if not text:
            return fallback
        steps = [line.strip("- 0123456789.").strip() for line in text.splitlines() if line.strip()]
        return steps[:10] or fallback


class EvidenceAgent:
    def __init__(self, sources: PublicDataSources) -> None:
        self.sources = sources

    def collect(self, disease: str, target: str) -> EvidenceBundle:
        return self.sources.collect_evidence(disease, target)


class CriticAgent:
    def __init__(self, enabled: bool = True, thresholds: ThresholdRegistry | None = None) -> None:
        self.enabled = enabled
        self.thresholds = thresholds or ThresholdRegistry()

    def review(self, candidate: CandidateRecord) -> DecisionResult:
        if candidate.decision is None:
            candidate.decision = decide_candidate(candidate, self.thresholds)
        decision = candidate.decision
        if not self.enabled:
            return decision

        findings: list[str] = []
        desc = candidate.descriptors
        evidence_threshold = self.thresholds.get("evidence_confidence_min_for_go").value
        if not desc or not desc.valid:
            findings.append("Critic: invalid structure cannot be triaged as a lead candidate.")
        else:
            if decision.final_status == "Go" and candidate.evidence_confidence < evidence_threshold:
                findings.append("Critic: downgraded Go to Hold because evidence confidence is weak.")
                decision.final_status = "Hold"
            if decision.final_status == "Go" and not candidate.in_applicability_domain:
                findings.append("Critic: downgraded Go to Hold because candidate is outside applicability domain.")
                decision.final_status = "Hold"
            if decision.final_status == "Go" and desc.alerts:
                findings.append("Critic: downgraded Go to Hold because structural alerts require review.")
                decision.final_status = "Hold"
            if desc.method == "heuristic":
                findings.append("Critic: RDKit unavailable; descriptor values are heuristic and require confirmation.")
                if decision.final_status == "Go":
                    findings.append("Critic: downgraded Go to Hold until RDKit descriptors confirm the profile.")
                    decision.final_status = "Hold"
            if candidate.predicted_activity is not None and (candidate.prediction_interval or {}).get("lower", 0.0) < candidate.predicted_activity:
                findings.append("Critic: high predicted activity is a ranking aid, not an experimentally verified claim.")

        decision.critic_findings.extend(findings)
        if findings and "additional evidence" not in " ".join(decision.follow_up).lower():
            decision.follow_up.append("Confirm critic findings with RDKit, assay data, and expert review.")
        return decision


class ReportAgent:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient(False)

    def executive_summary(self, result_payload: dict[str, Any]) -> str:
        prompt = json.dumps(result_payload, default=str)[:12000]
        text = self.llm.chat(
            "You summarize cautious, evidence-grounded drug-discovery triage reports.",
            "Summarize the following Target-SAFE run without overclaiming:\n" + prompt,
        )
        if text:
            return text
        counts: dict[str, int] = {}
        for c in result_payload.get("candidates", []):
            status = (c.get("decision") or {}).get("final_status", "Unscored")
            counts[status] = counts.get(status, 0) + 1
        return (
            "Target-SAFE narrowed seed-derived candidates using hard gates, evidence confidence, "
            f"and critic review. Status distribution: {counts}. All outputs are decision-support "
            "signals and require experimental confirmation."
        )
