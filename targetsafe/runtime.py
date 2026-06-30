from __future__ import annotations

import os
from typing import Any

from targetsafe.embeddings import gpu_status


def runtime_status(
    requested_gpu: bool = True,
    requested_llm: bool = True,
    llm_api_key: str | None = None,
    llm_base_url: str | None = None,
    llm_model: str | None = None,
) -> dict[str, Any]:
    llm_configured = bool((llm_api_key or "").strip() or os.getenv("OPENAI_API_KEY"))
    return {
        "schema": "targetsafe.runtime_status.v1",
        "gpu": gpu_status(requested=requested_gpu),
        "llm": {
            "requested": requested_llm,
            "configured": llm_configured,
            "used": bool(requested_llm and llm_configured),
            "provider": "openai-compatible",
            "base_url_configured": bool(llm_base_url or os.getenv("OPENAI_BASE_URL")),
            "model": llm_model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            "message": (
                "An API key is configured or was provided for this run; LLM planner/report summarization can be used."
                if requested_llm and llm_configured
                else "OPENAI_API_KEY is not configured; deterministic planner/report fallback is used."
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
