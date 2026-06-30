from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ComputeProfile:
    id: str
    label: str
    allow_network: bool
    use_llm: bool
    use_gpu: bool
    train_qsar: bool
    use_cached_demo: bool
    description: str
    expected_runtime: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


PROFILES: dict[str, ComputeProfile] = {
    "cpu-demo": ComputeProfile(
        id="cpu-demo",
        label="CPU demo",
        allow_network=False,
        use_llm=False,
        use_gpu=False,
        train_qsar=False,
        use_cached_demo=True,
        description="Stable offline demo with fallback evidence and deterministic scoring.",
        expected_runtime="Fastest; designed for presentation reliability.",
    ),
    "cpu-evidence": ComputeProfile(
        id="cpu-evidence",
        label="CPU evidence-grade",
        allow_network=True,
        use_llm=False,
        use_gpu=False,
        train_qsar=True,
        use_cached_demo=False,
        description="Live public evidence refresh with CPU RDKit and scikit-learn QSAR.",
        expected_runtime="Moderate; depends on public API latency.",
    ),
    "gpu-accelerated": ComputeProfile(
        id="gpu-accelerated",
        label="GPU accelerated",
        allow_network=True,
        use_llm=False,
        use_gpu=True,
        train_qsar=True,
        use_cached_demo=False,
        description="Adds optional GPU embeddings, analog retrieval, and ensemble uncertainty.",
        expected_runtime="Moderate to slow; falls back gracefully when GPU libraries are absent.",
    ),
    "api-assisted": ComputeProfile(
        id="api-assisted",
        label="API assisted",
        allow_network=True,
        use_llm=True,
        use_gpu=False,
        train_qsar=True,
        use_cached_demo=False,
        description="Uses public evidence APIs and optional LLM graph-grounded summaries.",
        expected_runtime="Moderate; depends on API availability and configured credentials.",
    ),
    "full-research": ComputeProfile(
        id="full-research",
        label="Full research mode",
        allow_network=True,
        use_llm=True,
        use_gpu=True,
        train_qsar=True,
        use_cached_demo=False,
        description="Live evidence, optional GPU acceleration, ensemble uncertainty, and LLM report support.",
        expected_runtime="Slowest; best for final-quality runs when resources are available.",
    ),
}


def resolve_profile(profile_id: str | None) -> ComputeProfile:
    if not profile_id:
        return PROFILES["cpu-demo"]
    normalized = profile_id.strip().lower().replace("_", "-")
    return PROFILES.get(normalized, PROFILES["cpu-demo"])


def profile_options() -> list[dict[str, Any]]:
    return [profile.to_dict() for profile in PROFILES.values()]
