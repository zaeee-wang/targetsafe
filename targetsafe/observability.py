from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


SECRET_KEYS = ("api_key", "authorization", "token", "secret", "password")


@dataclass
class TargetSafeError:
    error_code: str
    category: str
    severity: str
    source: str
    user_message: str
    debug_message: str = ""
    retryable: bool = False
    fallback_used: bool = False
    run_id: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RunLogger:
    def __init__(self, run_id: str, log_dir: str | Path = "work/logs") -> None:
        self.run_id = run_id
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.log_dir / f"{run_id}.jsonl"
        self.events: list[dict[str, Any]] = []

    def log(self, event_type: str, **payload: Any) -> None:
        event = {
            "timestamp": time.time(),
            "run_id": self.run_id,
            "event_type": event_type,
            **_mask_secrets(payload),
        }
        self.events.append(event)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")

    def log_error(self, error: TargetSafeError) -> None:
        self.log("error", **error.to_dict())


class APIGate:
    def __init__(
        self,
        provider: str,
        enabled: bool,
        requires_key: bool = False,
        api_key: str = "",
        timeout_seconds: int = 8,
        retry_budget: int = 0,
        cache_fallback: bool = True,
        logger: RunLogger | None = None,
    ) -> None:
        self.provider = provider
        self.enabled = enabled
        self.requires_key = requires_key
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.retry_budget = retry_budget
        self.cache_fallback = cache_fallback
        self.logger = logger

    def check(self, endpoint: str, source: str = "") -> dict[str, Any]:
        allowed = bool(self.enabled and (not self.requires_key or self.api_key.strip()))
        reason = ""
        if not self.enabled:
            reason = "network_disabled"
        elif self.requires_key and not self.api_key.strip():
            reason = "api_key_missing"
        payload = {
            "provider": self.provider,
            "source": source or self.provider,
            "endpoint": endpoint,
            "allowed": allowed,
            "reason": reason,
            "requires_key": self.requires_key,
            "api_key_configured": bool(self.api_key.strip()),
            "timeout_seconds": self.timeout_seconds,
            "retry_budget": self.retry_budget,
            "cache_fallback": self.cache_fallback,
        }
        if self.logger:
            self.logger.log("api_gate_check", **payload)
        return payload


def classify_error(category: str, source: str, message: str, run_id: str = "", fallback_used: bool = True) -> TargetSafeError:
    retryable = category in {"network_refused", "timeout", "rate_limited", "http_error", "unknown_error"}
    severity = "warning" if fallback_used else "error"
    user_message = _user_message_for(category, source, fallback_used)
    return TargetSafeError(
        error_code=category,
        category=_error_group(category),
        severity=severity,
        source=source,
        user_message=user_message,
        debug_message=message,
        retryable=retryable,
        fallback_used=fallback_used,
        run_id=run_id,
    )


def summarize_errors(errors: list[dict[str, Any]], tool_logs: list[Any] | None = None) -> dict[str, Any]:
    categories: dict[str, int] = {}
    severities: dict[str, int] = {}
    sources: dict[str, int] = {}
    for item in errors:
        category = str(item.get("error_code") or item.get("category") or "unknown")
        severity = str(item.get("severity") or "warning")
        source = str(item.get("source") or "unknown")
        categories[category] = categories.get(category, 0) + 1
        severities[severity] = severities.get(severity, 0) + 1
        sources[source] = sources.get(source, 0) + 1
    if tool_logs:
        for log in tool_logs:
            code = getattr(log, "error_code", "") or getattr(log, "error_category", "")
            if code and code not in {"cached", "ok"}:
                categories[code] = categories.get(code, 0) + 1
                sources[getattr(log, "source", "tool")] = sources.get(getattr(log, "source", "tool"), 0) + 1
    return {
        "schema": "targetsafe.error_summary.v1",
        "total_errors": len(errors),
        "categories": categories,
        "severities": severities,
        "sources": sources,
        "has_blocking_error": bool(severities.get("error") or severities.get("critical")),
        "interpretation": (
            "Errors were isolated to individual tools or candidates; fallback/cached evidence was used where possible."
            if errors or categories
            else "No explicit Target-SAFE error events were recorded."
        ),
    }


def read_jsonl(path: str | Path, level: str = "", category: str = "") -> list[dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if level and str(item.get("severity", item.get("status", ""))).lower() != level.lower():
            continue
        if category and str(item.get("category", item.get("error_code", ""))).lower() != category.lower():
            continue
        rows.append(item)
    return rows


def _error_group(code: str) -> str:
    if code in {"network_refused", "timeout", "rate_limited", "http_error", "http_empty", "parse_error", "network_disabled"}:
        return "api_network"
    if code in {"invalid_smiles", "rdkit_unavailable", "depiction_failed", "conformer_failed"}:
        return "chemistry"
    if code in {"gpu_unavailable", "torch_cuda_unusable", "cuda_oom", "llm_key_missing", "llm_provider_error", "llm_timeout"}:
        return "compute"
    return "runtime"


def _user_message_for(category: str, source: str, fallback_used: bool) -> str:
    suffix = " Target-SAFE used a fallback path." if fallback_used else ""
    messages = {
        "network_refused": f"{source} connection was refused by the local/network environment.",
        "timeout": f"{source} did not respond before the configured timeout.",
        "rate_limited": f"{source} rate limit was reached.",
        "http_empty": f"{source} returned no usable rows.",
        "parse_error": f"{source} returned a response that could not be parsed.",
        "network_disabled": f"{source} live access is disabled for this run.",
        "invalid_smiles": "A molecule could not be parsed as valid SMILES.",
        "llm_key_missing": "LLM was requested, but no provider API key was configured.",
        "gpu_unavailable": "GPU was requested, but no usable compute backend was available.",
    }
    return messages.get(category, f"{source} produced a recoverable error.") + suffix


def _mask_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        masked: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(secret in lowered for secret in SECRET_KEYS):
                masked[key] = "***" if item else ""
            else:
                masked[key] = _mask_secrets(item)
        return masked
    if isinstance(value, list):
        return [_mask_secrets(item) for item in value]
    return value
