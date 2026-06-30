from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Iterable

from targetsafe.chem import canonicalize_smiles, generate_seed_analogs
from targetsafe.models import CandidateRecord, EvidenceBundle


DEFAULT_LIBRARY_SOURCES = ("seed_analog", "chembl_target", "pubchem_reference")


@dataclass
class LibraryBuildResult:
    candidates: list[CandidateRecord]
    report: dict[str, Any]
    screening_stages: list[dict[str, Any]] = field(default_factory=list)


def build_candidate_library(
    seed_smiles: str,
    evidence: EvidenceBundle,
    library_sources: Iterable[str] | None = None,
    library_limit: int = 2000,
    seed_count: int = 300,
    uploaded_smiles: Iterable[str] | None = None,
) -> LibraryBuildResult:
    sources = _normalize_sources(library_sources)
    raw_entries: list[dict[str, str]] = []
    source_counts: dict[str, int] = {}

    if "seed_analog" in sources:
        seed_candidates = generate_seed_analogs(seed_smiles, count=max(seed_count, 60))
        for candidate in seed_candidates:
            raw_entries.append(
                {
                    "smiles": candidate.smiles,
                    "library_source": "seed_analog",
                    "source": candidate.source,
                    "source_compound_id": candidate.source_compound_id,
                    "source_name": candidate.source_name or candidate.candidate_id,
                }
            )
        source_counts["seed_analog"] = len(seed_candidates)

    if "chembl_target" in sources:
        count = 0
        for row in evidence.chembl_activities:
            smiles = _first_text(
                row,
                "canonical_smiles",
                "canonical_smiles__canonical_smiles",
                "molecule_structures.canonical_smiles",
                "smiles",
            )
            if not smiles:
                continue
            count += 1
            raw_entries.append(
                {
                    "smiles": smiles,
                    "library_source": "chembl_target",
                    "source": "chembl_target_activity",
                    "source_compound_id": _first_text(row, "molecule_chembl_id", "parent_molecule_chembl_id") or f"chembl_{count}",
                    "source_name": _first_text(row, "molecule_pref_name", "compound_name") or "ChEMBL target compound",
                }
            )
        source_counts["chembl_target"] = count

    if "pubchem_reference" in sources:
        count = 0
        for row in evidence.pubchem_records:
            smiles = _first_text(row, "canonical_smiles", "isomeric_smiles", "smiles")
            if not smiles:
                continue
            count += 1
            raw_entries.append(
                {
                    "smiles": smiles,
                    "library_source": "pubchem_reference",
                    "source": "pubchem_reference_record",
                    "source_compound_id": _first_text(row, "pubchem_cid", "drug_id") or f"pubchem_{count}",
                    "source_name": _first_text(row, "name", "drug_id") or "PubChem reference",
                }
            )
        source_counts["pubchem_reference"] = count

    if "uploaded" in sources:
        count = 0
        for index, smiles in enumerate(uploaded_smiles or [], start=1):
            normalized = str(smiles).strip()
            if not normalized:
                continue
            count += 1
            raw_entries.append(
                {
                    "smiles": _extract_smiles(normalized),
                    "library_source": "uploaded",
                    "source": "uploaded_library",
                    "source_compound_id": f"uploaded_{index:05d}",
                    "source_name": _extract_name(normalized, default=f"Uploaded {index:05d}"),
                }
            )
        source_counts["uploaded"] = count

    candidates: list[CandidateRecord] = []
    seen: set[str] = set()
    invalid_rows = 0
    duplicate_rows = 0
    for entry in raw_entries[: max(library_limit * 2, library_limit)]:
        canonical = canonicalize_smiles(entry["smiles"])
        if not canonical:
            invalid_rows += 1
            continue
        if canonical in seen:
            duplicate_rows += 1
            continue
        seen.add(canonical)
        cluster = diversity_cluster_id(canonical)
        candidates.append(
            CandidateRecord(
                candidate_id=f"C{len(candidates) + 1:05d}",
                smiles=canonical,
                source=entry["source"],
                library_source=entry["library_source"],
                source_compound_id=entry["source_compound_id"],
                source_name=entry["source_name"],
                diversity_cluster=cluster,
                screening_stage="stage1_deduplicated",
            )
        )
        if len(candidates) >= library_limit:
            break

    report = {
        "schema": "targetsafe.library_report.v1",
        "library_sources": sorted(sources),
        "source_input_counts": source_counts,
        "raw_input_count": len(raw_entries),
        "valid_unique_count": len(candidates),
        "invalid_or_unparseable_count": invalid_rows,
        "duplicate_count": duplicate_rows,
        "library_limit": library_limit,
        "interpretation": (
            "Large-library mode stages molecules before detailed scoring. Go/Hold/No-Go remains target-specific and "
            "requires descriptor, QSAR/applicability, evidence graph, and critic review."
        ),
    }
    stages = [
        {"stage": "stage0_library_assembly", "count": len(raw_entries), "description": "Seed, ChEMBL, PubChem/reference, and uploaded rows are collected."},
        {"stage": "stage1_deduplicated", "count": len(candidates), "description": "Valid canonical SMILES are deduplicated and assigned diversity clusters."},
    ]
    return LibraryBuildResult(candidates=candidates, report=report, screening_stages=stages)


def select_detailed_candidates(
    candidates: list[CandidateRecord],
    detailed_eval_limit: int,
) -> tuple[list[CandidateRecord], dict[str, Any], list[dict[str, Any]]]:
    if detailed_eval_limit <= 0:
        detailed_eval_limit = len(candidates)
    selected: list[CandidateRecord] = []
    by_cluster: dict[str, list[CandidateRecord]] = {}
    for candidate in candidates:
        by_cluster.setdefault(candidate.diversity_cluster, []).append(candidate)
    cluster_ids = sorted(by_cluster)
    cursor = 0
    while len(selected) < min(detailed_eval_limit, len(candidates)) and cluster_ids:
        cluster_id = cluster_ids[cursor % len(cluster_ids)]
        bucket = by_cluster[cluster_id]
        if bucket:
            selected.append(bucket.pop(0))
        if not bucket:
            cluster_ids.remove(cluster_id)
            cursor = 0
        else:
            cursor += 1
    selected_ids = {candidate.candidate_id for candidate in selected}
    for candidate in candidates:
        if candidate.candidate_id in selected_ids:
            candidate.screening_stage = "stage2_detailed_evaluation"
        else:
            candidate.screening_stage = "stage1_prefilter_pass_not_detailed"
            candidate.prefilter_reason = "Not evaluated in detail because detailed_eval_limit was reached."
    summary = {
        "detailed_eval_limit": detailed_eval_limit,
        "detailed_evaluation_count": len(selected),
        "prefilter_pass_not_detailed_count": max(0, len(candidates) - len(selected)),
        "diversity_cluster_count": len({candidate.diversity_cluster for candidate in candidates}),
    }
    stages = [
        {
            "stage": "stage2_detailed_evaluation",
            "count": len(selected),
            "description": "A diversity-aware subset receives descriptors, QSAR/applicability scoring, decisions, and graph evidence.",
        }
    ]
    return selected, summary, stages


def diversity_cluster_id(smiles: str, bucket_count: int = 32) -> str:
    digest = hashlib.sha1(smiles.encode("utf-8")).hexdigest()
    return f"cluster_{int(digest[:8], 16) % bucket_count:02d}"


def parse_uploaded_smiles_text(text: str) -> list[str]:
    rows: list[str] = []
    for raw in text.replace("\r", "\n").split("\n"):
        line = raw.strip()
        if not line or line.lower().startswith(("smiles", "#")):
            continue
        rows.append(line)
    return rows


def _normalize_sources(library_sources: Iterable[str] | None) -> set[str]:
    values = {str(item).strip().lower().replace("-", "_") for item in (library_sources or DEFAULT_LIBRARY_SOURCES)}
    allowed = {"seed_analog", "chembl_target", "pubchem_reference", "uploaded"}
    normalized = values & allowed
    return normalized or set(DEFAULT_LIBRARY_SOURCES)


def _first_text(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value: Any = row
        for part in key.split("."):
            if not isinstance(value, dict):
                value = None
                break
            value = value.get(part)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _extract_smiles(line: str) -> str:
    if "," in line:
        return line.split(",", 1)[0].strip()
    if "\t" in line:
        return line.split("\t", 1)[0].strip()
    return line.split()[0].strip()


def _extract_name(line: str, default: str) -> str:
    if "," in line:
        name = line.split(",", 1)[1].strip()
        return name or default
    if "\t" in line:
        name = line.split("\t", 1)[1].strip()
        return name or default
    parts = line.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else default
