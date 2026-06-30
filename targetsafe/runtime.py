from __future__ import annotations

import os
from typing import Any

from targetsafe.embeddings import gpu_diagnostics, gpu_status


OPENAI_MODELS = ["gpt-4.1-mini", "gpt-4.1", "o4-mini", "custom"]
ANTHROPIC_MODELS = ["claude-3-5-sonnet-latest", "claude-3-5-haiku-latest", "custom"]


def llm_provider_options() -> list[dict[str, Any]]:
    return [
        {
            "id": "deterministic",
            "label": "Deterministic fallback",
            "requires_key": False,
            "default_model": "none",
            "models": ["none"],
            "base_url": "",
            "description": "No external LLM call; planner/report text uses deterministic templates.",
        },
        {
            "id": "openai",
            "label": "OpenAI",
            "requires_key": True,
            "default_model": OPENAI_MODELS[0],
            "models": OPENAI_MODELS,
            "base_url": "https://api.openai.com/v1",
            "description": "Uses an OpenAI chat-completions compatible endpoint for optional summaries.",
        },
        {
            "id": "anthropic",
            "label": "Anthropic",
            "requires_key": True,
            "default_model": ANTHROPIC_MODELS[0],
            "models": ANTHROPIC_MODELS,
            "base_url": "https://api.anthropic.com/v1",
            "description": "Uses Anthropic Messages API for optional summaries.",
        },
        {
            "id": "openai-compatible",
            "label": "OpenAI-compatible custom",
            "requires_key": True,
            "default_model": "custom",
            "models": ["custom"],
            "base_url": "",
            "description": "Use a custom /chat/completions compatible base URL.",
        },
    ]


def runtime_status(
    requested_gpu: bool = True,
    requested_llm: bool = True,
    llm_api_key: str | None = None,
    llm_base_url: str | None = None,
    llm_model: str | None = None,
    llm_provider: str | None = None,
) -> dict[str, Any]:
    provider = normalize_llm_provider(llm_provider)
    env_key = _env_key_for_provider(provider)
    llm_configured = bool((llm_api_key or "").strip() or env_key)
    if provider == "deterministic":
        llm_configured = False
    default_model = default_model_for_provider(provider)
    return {
        "schema": "targetsafe.runtime_status.v1",
        "gpu": gpu_status(requested=requested_gpu),
        "gpu_diagnostics": gpu_diagnostics(),
        "llm": {
            "requested": requested_llm,
            "configured": llm_configured,
            "used": bool(requested_llm and llm_configured),
            "provider": provider,
            "base_url_configured": bool(llm_base_url or _env_base_url_for_provider(provider)),
            "model": llm_model or _env_model_for_provider(provider) or default_model,
            "message": (
                "Deterministic fallback selected; no external LLM call will be made."
                if provider == "deterministic"
                else "An API key is configured or was provided for this run; LLM planner/report summarization can be used."
                if requested_llm and llm_configured
                else f"{provider} API key is not configured; deterministic planner/report fallback is used."
                if requested_llm
                else "LLM lane was not requested for this profile."
            ),
        },
        "public_evidence_apis": {
            "requested": True,
            "requires_user_api_key": False,
            "sources": ["ChEMBL", "PubChem", "ClinicalTrials.gov", "openFDA"],
            "message": "Public evidence APIs are called without a user-provided key; calls may still be rate-limited or fall back to cache.",
        },
    }


def normalize_llm_provider(provider: str | None) -> str:
    value = (provider or "openai").strip().lower()
    if value in {"none", "off", "fallback", "deterministic"}:
        return "deterministic"
    if value in {"openai", "anthropic", "openai-compatible"}:
        return value
    return "openai-compatible"


def default_model_for_provider(provider: str) -> str:
    if provider == "anthropic":
        return ANTHROPIC_MODELS[0]
    if provider == "deterministic":
        return "none"
    return OPENAI_MODELS[0]


def _env_key_for_provider(provider: str) -> str:
    if provider == "anthropic":
        return os.getenv("ANTHROPIC_API_KEY", "")
    if provider == "deterministic":
        return ""
    return os.getenv("OPENAI_API_KEY", "")


def _env_base_url_for_provider(provider: str) -> str:
    if provider == "anthropic":
        return os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1")
    if provider == "openai-compatible":
        return os.getenv("OPENAI_BASE_URL", "")
    if provider == "openai":
        return os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    return ""


def _env_model_for_provider(provider: str) -> str:
    if provider == "anthropic":
        return os.getenv("ANTHROPIC_MODEL", "")
    if provider == "deterministic":
        return "none"
    return os.getenv("OPENAI_MODEL", "")
