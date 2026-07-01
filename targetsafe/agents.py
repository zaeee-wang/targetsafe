from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

from targetsafe.data_sources import PublicDataSources
from targetsafe.decision import decide_candidate
from targetsafe.models import CandidateRecord, DecisionResult, EvidenceBundle, GateAudit
from targetsafe.observability import APIGate, RunLogger, classify_error
from targetsafe.runtime import default_model_for_provider, normalize_llm_provider
from targetsafe.thresholds import ThresholdRegistry


class LLMClient:
    def __init__(
        self,
        enabled: bool = False,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        provider: str | None = None,
        logger: RunLogger | None = None,
    ) -> None:
        self.requested = enabled
        self.provider = normalize_llm_provider(provider)
        env_key = "ANTHROPIC_API_KEY" if self.provider == "anthropic" else "OPENAI_API_KEY"
        self.api_key = (api_key or os.getenv(env_key) or "").strip()
        self.enabled = enabled and self.provider != "deterministic" and bool(self.api_key)
        self.base_url = (base_url or self._default_base_url()).rstrip("/")
        self.model = model or self._default_model()
        self.last_error = ""
        self.logger = logger

    def chat(self, system: str, user: str) -> str | None:
        if not self.enabled:
            return None
        if self.provider == "anthropic":
            return self._chat_anthropic(system, user)
        return self._chat_openai_compatible(system, user)

    def test_connection(self) -> dict[str, Any]:
        if not self.requested or self.provider == "deterministic":
            return {
                "ok": True,
                "provider": self.provider,
                "used": False,
                "message": "Deterministic fallback selected; no external LLM call required.",
            }
        if not self.api_key:
            return {
                "ok": False,
                "provider": self.provider,
                "used": False,
                "message": "API key is not configured.",
            }
        text = self.chat(
            "You are a terse health-check responder.",
            "Return the word ok if this connection works.",
        )
        return {
            "ok": bool(text),
            "provider": self.provider,
            "used": bool(text),
            "model": self.model,
            "base_url_configured": bool(self.base_url),
            "message": "LLM connection test succeeded." if text else self.last_error or "LLM connection test failed.",
        }

    def _chat_openai_compatible(self, system: str, user: str) -> str | None:
        endpoint = f"{self.base_url}/chat/completions"
        gate = APIGate(
            provider=self.provider,
            enabled=self.enabled,
            requires_key=True,
            api_key=self.api_key,
            timeout_seconds=12,
            cache_fallback=False,
            logger=self.logger,
        )
        gate_payload = gate.check(endpoint=endpoint, source="LLM")
        if not gate_payload["allowed"]:
            self.last_error = "LLM API gate denied the request."
            return None
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0.2,
        }
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            if self.logger:
                self.logger.log("tool_call_started", source="LLM", provider=self.provider, endpoint=endpoint, model=self.model)
            with urllib.request.urlopen(request, timeout=12) as response:
                data = json.loads(response.read().decode("utf-8"))
            if self.logger:
                self.logger.log("tool_call_finished", source="LLM", provider=self.provider, endpoint=endpoint, status="ok")
            return data["choices"][0]["message"]["content"]
        except Exception as exc:
            self.last_error = f"{self.provider} request failed with {exc.__class__.__name__}."
            if self.logger:
                error = classify_error("llm_provider_error", "LLM", str(exc), run_id=self.logger.run_id, fallback_used=True)
                self.logger.log("tool_call_failed", source="LLM", provider=self.provider, endpoint=endpoint, error=error.to_dict())
                self.logger.log_error(error)
            return None

    def _chat_anthropic(self, system: str, user: str) -> str | None:
        endpoint = f"{self.base_url}/messages"
        gate = APIGate(
            provider=self.provider,
            enabled=self.enabled,
            requires_key=True,
            api_key=self.api_key,
            timeout_seconds=12,
            cache_fallback=False,
            logger=self.logger,
        )
        gate_payload = gate.check(endpoint=endpoint, source="LLM")
        if not gate_payload["allowed"]:
            self.last_error = "LLM API gate denied the request."
            return None
        payload = {
            "model": self.model,
            "system": system,
            "max_tokens": 1000,
            "temperature": 0.2,
            "messages": [{"role": "user", "content": user}],
        }
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            if self.logger:
                self.logger.log("tool_call_started", source="LLM", provider=self.provider, endpoint=endpoint, model=self.model)
            with urllib.request.urlopen(request, timeout=12) as response:
                data = json.loads(response.read().decode("utf-8"))
            if self.logger:
                self.logger.log("tool_call_finished", source="LLM", provider=self.provider, endpoint=endpoint, status="ok")
            content = data.get("content") or []
            text_parts = [part.get("text", "") for part in content if isinstance(part, dict)]
            return "\n".join(part for part in text_parts if part).strip() or None
        except Exception as exc:
            self.last_error = f"{self.provider} request failed with {exc.__class__.__name__}."
            if self.logger:
                error = classify_error("llm_provider_error", "LLM", str(exc), run_id=self.logger.run_id, fallback_used=True)
                self.logger.log("tool_call_failed", source="LLM", provider=self.provider, endpoint=endpoint, error=error.to_dict())
                self.logger.log_error(error)
            return None

    def _default_base_url(self) -> str:
        if self.provider == "anthropic":
            return os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1")
        if self.provider == "openai":
            return os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        if self.provider == "openai-compatible":
            return os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        return ""

    def _default_model(self) -> str:
        if self.provider == "anthropic":
            return os.getenv("ANTHROPIC_MODEL", default_model_for_provider(self.provider))
        if self.provider == "deterministic":
            return "none"
        return os.getenv("OPENAI_MODEL", default_model_for_provider(self.provider))


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
        for finding in findings:
            blocks_go = any(token in finding.lower() for token in ["downgraded", "invalid", "unavailable", "alerts"])
            decision.gate_audit.append(
                GateAudit(
                    gate_id="critic_review",
                    criterion_id="critic_review",
                    label="Critic overclaim review",
                    observed_value=finding,
                    status="review" if blocks_go and decision.final_status != "No-Go" else "block" if decision.final_status == "No-Go" else "pass",
                    decision_effect="review_required" if blocks_go else "info",
                    message=finding,
                    source="Target-SAFE Critic Agent",
                    rationale="The critic prevents confident advancement when evidence, applicability, alerts, or descriptor provenance are weak.",
                )
            )
            if blocks_go:
                decision.criteria.setdefault("critic_review", "review")
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
