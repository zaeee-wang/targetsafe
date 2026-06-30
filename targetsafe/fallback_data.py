from __future__ import annotations


KNOWN_EGFR_INHIBITORS = [
    {
        "name": "Gefitinib-like seed",
        "smiles": "COc1cc2ncnc(Nc3ccc(F)c(Cl)c3)c2cc1OCCCN1CCOCC1",
        "evidence": "EGFR TKI reference scaffold for offline demo",
    },
    {
        "name": "Erlotinib-like control",
        "smiles": "C#Cc1cccc(Nc2ncnc3cc(OCCOC)c(OCCOC)cc23)c1",
        "evidence": "EGFR TKI reference scaffold for offline demo",
    },
    {
        "name": "Osimertinib-like control",
        "smiles": "COc1cc(N(C)CCN(C)C)c(Nc2nccc(Nc3ccccc3)c2)c(OC)c1",
        "evidence": "EGFR TKI reference scaffold for offline demo",
    },
]


FALLBACK_CHEMBL_ACTIVITIES = [
    {"molecule_chembl_id": "CHEMBL939", "standard_type": "IC50", "standard_value": "33", "standard_units": "nM"},
    {"molecule_chembl_id": "CHEMBL553", "standard_type": "IC50", "standard_value": "2", "standard_units": "nM"},
    {"molecule_chembl_id": "CHEMBL3353410", "standard_type": "IC50", "standard_value": "12", "standard_units": "nM"},
    {"molecule_chembl_id": "CHEMBL203", "standard_type": "target", "standard_value": None, "standard_units": None},
]


FALLBACK_TRIALS = [
    {
        "nctId": "NCT-EGFR-DEMO-001",
        "briefTitle": "EGFR inhibitor therapy in mutation-positive NSCLC",
        "overallStatus": "COMPLETED",
        "phase": "PHASE3",
    },
    {
        "nctId": "NCT-EGFR-DEMO-002",
        "briefTitle": "Combination therapy after EGFR TKI resistance",
        "overallStatus": "RECRUITING",
        "phase": "PHASE2",
    },
]


FALLBACK_REGULATORY_RISKS = [
    {
        "risk": "Interstitial lung disease / pneumonitis",
        "scope": "EGFR TKI class-level label risk",
        "interpretation": "Use as a checklist item, not as a candidate-specific safety conclusion.",
    },
    {
        "risk": "QT prolongation and cardiotoxicity monitoring",
        "scope": "EGFR TKI class-level label risk",
        "interpretation": "Requires follow-up assay or label review for specific products.",
    },
    {
        "risk": "Dermatologic and gastrointestinal adverse reactions",
        "scope": "EGFR pathway inhibition class effect",
        "interpretation": "Useful for clinical-risk context, not for structural toxicity prediction.",
    },
]


ANILINES = [
    "Nc3ccc(F)c(Cl)c3",
    "Nc3ccc(F)cc3",
    "Nc3ccc(Cl)cc3",
    "Nc3cccc(F)c3",
    "Nc3ccccc3",
    "Nc3ccc(C#N)cc3",
    "Nc3ccc(OC)cc3",
    "Nc3ccc(C)cc3",
    "Nc3ccc(N(C)C)cc3",
    "Nc3cc(F)ccc3Cl",
]

TAILS = [
    "OCCCN1CCOCC1",
    "OCCN1CCOCC1",
    "OCCN(C)C",
    "OCCOC",
    "OCCN(CC)CC",
    "OC",
]

CORES = [
    "COc1cc2ncnc({aniline})c2cc1{tail}",
    "COc1cc2ncnc({aniline})c2cc(OC)c1{tail}",
    "COc1cc2ncnc({aniline})c2ccc1{tail}",
]

