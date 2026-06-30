from __future__ import annotations

import hashlib
import time
from typing import Any

from targetsafe.chem import tanimoto_like_similarity
from targetsafe.models import CandidateRecord, EvidenceBundle


def gpu_status(requested: bool = True) -> dict[str, Any]:
    if not requested:
        return {
            "requested": False,
            "available": False,
            "used": False,
            "backend": "cpu",
            "device_count": 0,
            "message": "GPU lane was not requested.",
        }
    try:
        import torch  # type: ignore

        available = bool(torch.cuda.is_available())
        device_name = torch.cuda.get_device_name(0) if available else ""
        return {
            "requested": True,
            "available": available,
            "used": False,
            "backend": "torch.cuda" if available else "torch",
            "torch_version": str(getattr(torch, "__version__", "")),
            "cuda_version": str(getattr(torch.version, "cuda", "") or ""),
            "device_count": int(torch.cuda.device_count()) if available else 0,
            "device_name": device_name,
            "message": "CUDA device detected." if available else "Torch is installed but CUDA is not available.",
        }
    except Exception as exc:
        return {
            "requested": True,
            "available": False,
            "used": False,
            "backend": "none",
            "device_count": 0,
            "message": f"GPU acceleration unavailable; using CPU analog retrieval fallback ({exc.__class__.__name__}).",
        }


def enrich_with_molecular_embeddings(
    candidates: list[CandidateRecord],
    evidence: EvidenceBundle,
    use_gpu: bool = False,
) -> dict[str, Any]:
    status = gpu_status(requested=use_gpu)
    references = [item for item in evidence.known_inhibitors if item.get("smiles")]
    gpu_matrix: list[list[float]] | None = None
    if use_gpu and status.get("available") and references:
        started = time.perf_counter()
        try:
            gpu_matrix = _cuda_similarity_matrix(
                [candidate.smiles for candidate in candidates],
                [str(ref.get("smiles", "")) for ref in references],
            )
            status = {
                **status,
                "used": True,
                "method": "cuda_hashed_smiles_tanimoto_matrix",
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                "matrix_shape": [len(candidates), len(references)],
            }
        except Exception as exc:
            gpu_matrix = None
            status = {
                **status,
                "used": False,
                "available": False,
                "fallback_reason": f"CUDA similarity lane failed with {exc.__class__.__name__}; CPU fallback used.",
            }
    for candidate in candidates:
        analogs = []
        candidate_index = candidates.index(candidate)
        for ref_index, ref in enumerate(references):
            similarity = (
                float(gpu_matrix[candidate_index][ref_index])
                if gpu_matrix is not None
                else tanimoto_like_similarity(candidate.smiles, str(ref.get("smiles", "")))
            )
            analogs.append(
                {
                    "name": ref.get("name", "EGFR reference"),
                    "smiles": ref.get("smiles", ""),
                    "similarity": round(similarity, 3),
                    "evidence": ref.get("evidence", ""),
                    "activity_nM": ref.get("activity_nM"),
                    "pchembl": ref.get("pchembl"),
                    "source": ref.get("activity_source") or ref.get("evidence", ""),
                    "method": "cuda_hashed_smiles_tanimoto_matrix"
                    if gpu_matrix is not None
                    else "cpu_tanimoto_fallback",
                }
            )
        candidate.nearest_analogs = sorted(analogs, key=lambda item: item["similarity"], reverse=True)[:3]
    return status


def _cuda_similarity_matrix(candidate_smiles: list[str], reference_smiles: list[str]) -> list[list[float]]:
    import torch  # type: ignore

    device = torch.device("cuda")
    candidate_fp = torch.tensor([_hashed_smiles_fingerprint(smiles) for smiles in candidate_smiles], device=device)
    reference_fp = torch.tensor([_hashed_smiles_fingerprint(smiles) for smiles in reference_smiles], device=device)
    intersection = candidate_fp @ reference_fp.T
    candidate_sum = candidate_fp.sum(dim=1, keepdim=True)
    reference_sum = reference_fp.sum(dim=1, keepdim=True).T
    union = candidate_sum + reference_sum - intersection
    similarity = torch.where(union > 0, intersection / union, torch.zeros_like(intersection))
    return similarity.detach().cpu().tolist()


def _hashed_smiles_fingerprint(smiles: str, n_bits: int = 512) -> list[float]:
    bits = [0.0] * n_bits
    tokens = [smiles[index : index + size] for size in (1, 2, 3) for index in range(max(0, len(smiles) - size + 1))]
    for token in tokens:
        digest = hashlib.sha1(token.encode("utf-8")).hexdigest()
        bits[int(digest[:8], 16) % n_bits] = 1.0
    return bits
