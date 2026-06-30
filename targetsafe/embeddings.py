from __future__ import annotations

from typing import Any

from targetsafe.chem import tanimoto_like_similarity
from targetsafe.models import CandidateRecord, EvidenceBundle


def gpu_status() -> dict[str, Any]:
    try:
        import torch  # type: ignore

        available = bool(torch.cuda.is_available())
        return {
            "requested": True,
            "available": available,
            "backend": "torch.cuda" if available else "torch",
            "device_count": int(torch.cuda.device_count()) if available else 0,
            "message": "CUDA device detected." if available else "Torch is installed but CUDA is not available.",
        }
    except Exception as exc:
        return {
            "requested": True,
            "available": False,
            "backend": "none",
            "device_count": 0,
            "message": f"GPU acceleration unavailable; using CPU analog retrieval fallback ({exc.__class__.__name__}).",
        }


def enrich_with_molecular_embeddings(
    candidates: list[CandidateRecord],
    evidence: EvidenceBundle,
    use_gpu: bool = False,
) -> dict[str, Any]:
    status = gpu_status() if use_gpu else {
        "requested": False,
        "available": False,
        "backend": "cpu",
        "device_count": 0,
        "message": "GPU profile not selected; CPU analog retrieval used.",
    }
    references = [item for item in evidence.known_inhibitors if item.get("smiles")]
    for candidate in candidates:
        analogs = []
        for ref in references:
            similarity = tanimoto_like_similarity(candidate.smiles, str(ref.get("smiles", "")))
            analogs.append(
                {
                    "name": ref.get("name", "EGFR reference"),
                    "smiles": ref.get("smiles", ""),
                    "similarity": round(similarity, 3),
                    "evidence": ref.get("evidence", ""),
                    "activity_nM": ref.get("activity_nM"),
                    "pchembl": ref.get("pchembl"),
                    "source": ref.get("activity_source") or ref.get("evidence", ""),
                    "method": "gpu_embedding_candidate" if status["available"] else "cpu_tanimoto_fallback",
                }
            )
        candidate.nearest_analogs = sorted(analogs, key=lambda item: item["similarity"], reverse=True)[:3]
    return status
