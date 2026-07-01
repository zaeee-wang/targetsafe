from __future__ import annotations

from typing import Any


TARGET_PROFILES: dict[str, dict[str, Any]] = {
    "EGFR": {
        "target": "EGFR",
        "disease": "EGFR mutation-positive NSCLC",
        "scoring_mode": "scored_pilot",
        "badge": "Scored pilot",
        "seed_smiles": "COc1cc2ncnc(Nc3ccc(F)c(Cl)c3)c2cc1OCCCN1CCOCC1",
        "optimization_goal": "Maintain drug-likeness, reduce toxicity alerts, preserve EGFR evidence confidence",
        "interpretation_limit": "Full Go/Hold/No-Go scoring is enabled for the EGFR pilot, with applicability-domain and validation reporting.",
        "default_library_sources": ["seed_analog", "chembl_target", "pubchem_reference"],
    },
    "ALK": {
        "target": "ALK",
        "disease": "ALK-positive NSCLC",
        "scoring_mode": "evidence_only",
        "badge": "Evidence-only",
        "seed_smiles": "COc1cc(N2CCN(C)CC2)c(OC)c2c1C(=O)N(C)c1ccccc12",
        "optimization_goal": "Explore ALK inhibitor-like compounds while avoiding overclaiming before target-specific validation",
        "interpretation_limit": "Descriptor triage and evidence readiness are available; confident ALK Go scoring requires an ALK-specific assay/QSAR refresh.",
        "default_library_sources": ["seed_analog", "chembl_target", "pubchem_reference"],
    },
    "BRAF": {
        "target": "BRAF",
        "disease": "BRAF V600E melanoma",
        "scoring_mode": "evidence_only",
        "badge": "Evidence-only",
        "seed_smiles": "CCCS(=O)(=O)Nc1ccc(F)c(c1)C(=O)c1c[nH]c2ncc(Cl)cc12",
        "optimization_goal": "Explore BRAF inhibitor-like compounds and mark readiness gaps before target-specific scoring",
        "interpretation_limit": "Descriptor and public evidence context are available; BRAF Go/Hold/No-Go needs target-specific validation data.",
        "default_library_sources": ["seed_analog", "chembl_target", "pubchem_reference"],
    },
    "KRAS": {
        "target": "KRAS",
        "disease": "KRAS G12C solid tumor",
        "scoring_mode": "evidence_only",
        "badge": "Evidence-only",
        "seed_smiles": "CC(C)Oc1ccccc1C(=O)N1CCC(CC1)N1CCN(CC1)c1ncc(Cl)cc1F",
        "optimization_goal": "Explore KRAS-like candidate context while preserving covalent-chemistry caution",
        "interpretation_limit": "KRAS covalent chemistry needs target- and mechanism-specific rules before confident prioritization.",
        "default_library_sources": ["seed_analog", "chembl_target", "pubchem_reference"],
    },
    "HER2": {
        "target": "HER2",
        "disease": "HER2-positive breast cancer",
        "scoring_mode": "evidence_only",
        "badge": "Evidence-only",
        "seed_smiles": "CS(=O)(=O)CCNCC1=CC=C(O1)C1=CC2=C(NC3=CC=CC=C3N=C2N)C=C1",
        "optimization_goal": "Explore HER2 inhibitor-like compounds and mark evidence gaps before scoring",
        "interpretation_limit": "HER2 evidence can be browsed, but full scoring requires HER2-specific assay rows and validation metrics.",
        "default_library_sources": ["seed_analog", "chembl_target", "pubchem_reference"],
    },
}


def target_profiles() -> list[dict[str, Any]]:
    return list(TARGET_PROFILES.values())


def resolve_target_profile(target: str) -> dict[str, Any]:
    key = (target or "EGFR").strip().upper()
    if key in TARGET_PROFILES:
        return dict(TARGET_PROFILES[key])
    return {
        "target": target or "Unknown",
        "disease": "",
        "scoring_mode": "evidence_only",
        "badge": "Evidence-only",
        "seed_smiles": "",
        "optimization_goal": "Explore target evidence readiness before target-specific scoring",
        "interpretation_limit": "This target is not configured as a validated scoring pilot. Target-SAFE will provide descriptor/evidence readiness context and avoid confident Go claims.",
        "default_library_sources": ["seed_analog", "pubchem_reference"],
    }


def target_scenario_examples(base_request: dict[str, Any]) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for profile in target_profiles():
        request = {
            **base_request,
            "disease": profile["disease"],
            "target": profile["target"],
            "seed_smiles": profile["seed_smiles"],
            "optimization_goal": profile["optimization_goal"],
            "library_sources": profile["default_library_sources"],
        }
        examples.append(
            {
                "id": f"{profile['target'].lower()}_{profile['scoring_mode']}",
                "label": f"{profile['target']} {profile['badge']}",
                "description": profile["interpretation_limit"],
                "expected_behavior": (
                    "Can produce Go/Hold/No-Go under the validated EGFR pilot."
                    if profile["scoring_mode"] == "scored_pilot"
                    else "Should remain evidence-readiness oriented; confident Go is downgraded until target-specific validation exists."
                ),
                "scoring_mode": profile["scoring_mode"],
                "interpretation_limit": profile["interpretation_limit"],
                "default_library_sources": profile["default_library_sources"],
                "request": request,
            }
        )
    return examples
