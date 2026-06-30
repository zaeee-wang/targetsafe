from __future__ import annotations

import hashlib
import subprocess
import time
from typing import Any

from targetsafe.chem import tanimoto_like_similarity
from targetsafe.models import CandidateRecord, EvidenceBundle


def gpu_status(requested: bool = True) -> dict[str, Any]:
    diagnostics = gpu_diagnostics()
    if not requested:
        return {
            "requested": False,
            "available": False,
            "used": False,
            "backend": "cpu",
            "device_count": 0,
            "message": "GPU lane was not requested.",
            "diagnostics": diagnostics,
        }
    torch_cuda = diagnostics.get("torch_cuda", {})
    directml = diagnostics.get("directml", {})
    cuda_usable = bool(torch_cuda.get("usable"))
    directml_usable = bool(directml.get("usable"))
    available = cuda_usable or directml_usable
    backend = "torch.cuda" if cuda_usable else "torch_directml" if directml_usable else "cpu_fallback"
    system_gpu_detected = bool(diagnostics.get("system_gpu", {}).get("detected"))
    message = (
        "CUDA device detected and available to PyTorch."
        if cuda_usable
        else "DirectML device detected and available for tensor acceleration."
        if directml_usable
        else "A system GPU was detected, but the current Python compute backend cannot use it."
        if system_gpu_detected
        else "No usable GPU compute backend detected; CPU fallback will be used."
    )
    return {
        "requested": True,
        "available": available,
        "used": False,
        "backend": backend,
        "torch_version": str(torch_cuda.get("torch_version", "")),
        "cuda_version": str(torch_cuda.get("cuda_version", "")),
        "device_count": int(torch_cuda.get("device_count") or directml.get("device_count") or 0),
        "device_name": str(torch_cuda.get("device_name") or directml.get("device_name") or ""),
        "system_gpu_detected": system_gpu_detected,
        "torch_cuda_usable": cuda_usable,
        "directml_usable": directml_usable,
        "message": message,
        "action_hint": diagnostics.get("action_hint", ""),
        "diagnostics": diagnostics,
    }


def gpu_diagnostics() -> dict[str, Any]:
    nvidia = _nvidia_smi_status()
    windows_gpu = _windows_video_controller_status()
    system_gpu = {
        "detected": bool(nvidia.get("detected") or windows_gpu.get("detected")),
        "nvidia_smi": nvidia,
        "windows_video_controller": windows_gpu,
        "message": (
            str(nvidia.get("message", ""))
            if nvidia.get("detected")
            else str(windows_gpu.get("message", ""))
            if windows_gpu.get("detected")
            else "No system GPU was detected by nvidia-smi or Windows video-controller diagnostics."
        ),
    }
    torch_cuda = _torch_cuda_status()
    directml = _directml_status()
    usable = bool(torch_cuda.get("usable") or directml.get("usable"))
    system_detected = bool(system_gpu.get("detected"))
    if usable:
        action_hint = "GPU acceleration is usable for Target-SAFE similarity/retrieval lanes."
    elif system_detected:
        action_hint = (
            "A GPU is visible to the operating system, but PyTorch CUDA/DirectML is not usable in this Python "
            "environment. Install a CUDA-enabled PyTorch build for NVIDIA GPUs or torch-directml for Windows DirectML."
        )
    else:
        action_hint = "No GPU compute backend was detected. Target-SAFE will continue with CPU fallback."
    return {
        "schema": "targetsafe.gpu_diagnostics.v1",
        "system_gpu": system_gpu,
        "torch_cuda": torch_cuda,
        "directml": directml,
        "usable": usable,
        "action_hint": action_hint,
    }


def enrich_with_molecular_embeddings(
    candidates: list[CandidateRecord],
    evidence: EvidenceBundle,
    use_gpu: bool = False,
) -> dict[str, Any]:
    status = gpu_status(requested=use_gpu)
    references = [item for item in evidence.known_inhibitors if item.get("smiles")]
    gpu_matrix: list[list[float]] | None = None
    backend = str(status.get("backend") or "")
    if use_gpu and status.get("available") and references:
        started = time.perf_counter()
        try:
            gpu_matrix = _accelerated_similarity_matrix(
                [candidate.smiles for candidate in candidates],
                [str(ref.get("smiles", "")) for ref in references],
                backend=backend,
            )
            status = {
                **status,
                "used": True,
                "method": f"{backend}_hashed_smiles_tanimoto_matrix",
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
                    "method": f"{backend}_hashed_smiles_tanimoto_matrix"
                    if gpu_matrix is not None
                    else "cpu_tanimoto_fallback",
                }
            )
        candidate.nearest_analogs = sorted(analogs, key=lambda item: item["similarity"], reverse=True)[:3]
    return status


def _accelerated_similarity_matrix(
    candidate_smiles: list[str],
    reference_smiles: list[str],
    backend: str = "torch.cuda",
) -> list[list[float]]:
    import torch  # type: ignore

    if backend == "torch_directml":
        import torch_directml  # type: ignore

        device = torch_directml.device()
    else:
        device = torch.device("cuda")
    candidate_fp = torch.tensor([_hashed_smiles_fingerprint(smiles) for smiles in candidate_smiles], device=device)
    reference_fp = torch.tensor([_hashed_smiles_fingerprint(smiles) for smiles in reference_smiles], device=device)
    intersection = candidate_fp @ reference_fp.T
    candidate_sum = candidate_fp.sum(dim=1, keepdim=True)
    reference_sum = reference_fp.sum(dim=1, keepdim=True).T
    union = candidate_sum + reference_sum - intersection
    similarity = torch.where(union > 0, intersection / union, torch.zeros_like(intersection))
    return similarity.detach().cpu().tolist()


def _nvidia_smi_status() -> dict[str, Any]:
    try:
        completed = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=4,
            check=False,
        )
    except Exception as exc:
        return {"detected": False, "method": "nvidia-smi", "message": f"nvidia-smi unavailable ({exc.__class__.__name__})."}
    if completed.returncode != 0:
        return {
            "detected": False,
            "method": "nvidia-smi",
            "message": (completed.stderr or completed.stdout or "nvidia-smi returned a nonzero status.").strip(),
        }
    devices = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    return {
        "detected": bool(devices),
        "method": "nvidia-smi",
        "devices": devices,
        "message": "NVIDIA GPU detected by nvidia-smi." if devices else "nvidia-smi returned no GPU rows.",
    }


def _windows_video_controller_status() -> dict[str, Any]:
    try:
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=4,
            check=False,
        )
    except Exception as exc:
        return {
            "detected": False,
            "method": "Win32_VideoController",
            "message": f"Windows video-controller check unavailable ({exc.__class__.__name__}).",
        }
    if completed.returncode != 0:
        return {
            "detected": False,
            "method": "Win32_VideoController",
            "message": (completed.stderr or "Windows video-controller check returned nonzero status.").strip(),
        }
    names = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    gpu_names = [name for name in names if "basic display" not in name.lower()]
    return {
        "detected": bool(gpu_names),
        "method": "Win32_VideoController",
        "devices": gpu_names,
        "message": f"Windows reports GPU/display adapter(s): {', '.join(gpu_names[:3])}" if gpu_names else "No non-basic Windows video controller found.",
    }


def _torch_cuda_status() -> dict[str, Any]:
    try:
        import torch  # type: ignore

        usable = bool(torch.cuda.is_available())
        return {
            "installed": True,
            "usable": usable,
            "torch_version": str(getattr(torch, "__version__", "")),
            "cuda_version": str(getattr(torch.version, "cuda", "") or ""),
            "device_count": int(torch.cuda.device_count()) if usable else 0,
            "device_name": torch.cuda.get_device_name(0) if usable else "",
            "message": "torch.cuda is usable." if usable else "Torch is installed, but torch.cuda.is_available() is false.",
        }
    except Exception as exc:
        return {
            "installed": False,
            "usable": False,
            "message": f"PyTorch CUDA check failed ({exc.__class__.__name__}).",
        }


def _directml_status() -> dict[str, Any]:
    try:
        import torch_directml  # type: ignore

        device = torch_directml.device()
        return {
            "installed": True,
            "usable": True,
            "device_count": 1,
            "device_name": str(device),
            "message": "torch-directml is installed and returned a DirectML device.",
        }
    except Exception as exc:
        return {
            "installed": False,
            "usable": False,
            "message": f"DirectML unavailable ({exc.__class__.__name__}).",
        }


def _hashed_smiles_fingerprint(smiles: str, n_bits: int = 512) -> list[float]:
    bits = [0.0] * n_bits
    tokens = [smiles[index : index + size] for size in (1, 2, 3) for index in range(max(0, len(smiles) - size + 1))]
    for token in tokens:
        digest = hashlib.sha1(token.encode("utf-8")).hexdigest()
        bits[int(digest[:8], 16) % n_bits] = 1.0
    return bits
