from __future__ import annotations

import base64
import html
import math
import re
from io import BytesIO
from typing import Iterable

from targetsafe.fallback_data import ANILINES, CORES, KNOWN_EGFR_INHIBITORS, TAILS
from targetsafe.models import CandidateRecord, DescriptorResult

try:
    from rdkit import Chem
    from rdkit.Chem import Crippen, Descriptors, Draw, Lipinski, QED, rdMolDescriptors
    from rdkit.Chem.FilterCatalog import FilterCatalog, FilterCatalogParams

    RDKIT_AVAILABLE = True
except Exception:
    Chem = None
    Crippen = None
    Descriptors = None
    Draw = None
    Lipinski = None
    QED = None
    rdMolDescriptors = None
    FilterCatalog = None
    FilterCatalogParams = None
    RDKIT_AVAILABLE = False


def generate_seed_analogs(seed_smiles: str, count: int = 60) -> list[CandidateRecord]:
    smiles: list[str] = [seed_smiles]
    smiles.extend(item["smiles"] for item in KNOWN_EGFR_INHIBITORS)
    for core in CORES:
        for aniline in ANILINES:
            for tail in TAILS:
                smiles.append(core.format(aniline=aniline, tail=tail))

    unique: list[str] = []
    seen: set[str] = set()
    for smi in smiles:
        canonical = canonicalize_smiles(smi) or smi
        if canonical not in seen:
            seen.add(canonical)
            unique.append(canonical)
        if len(unique) >= count:
            break

    return [
        CandidateRecord(candidate_id=f"C{i + 1:03d}", smiles=smi, source="seed_analog_library")
        for i, smi in enumerate(unique)
    ]


def canonicalize_smiles(smiles: str) -> str | None:
    if RDKIT_AVAILABLE:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        return Chem.MolToSmiles(mol)
    if _heuristic_valid_smiles(smiles):
        return re.sub(r"\s+", "", smiles)
    return None


def evaluate_smiles(smiles: str) -> DescriptorResult:
    if RDKIT_AVAILABLE:
        return _evaluate_smiles_rdkit(smiles)
    return _evaluate_smiles_heuristic(smiles)


def mol_svg_data_uri(smiles: str) -> str | None:
    if not RDKIT_AVAILABLE:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    try:
        svg = Draw.MolsToGridImage([mol], molsPerRow=1, subImgSize=(300, 180), useSVG=True)
        encoded = base64.b64encode(str(svg).encode("utf-8")).decode("ascii")
        return f"data:image/svg+xml;base64,{encoded}"
    except Exception:
        return None


def tanimoto_like_similarity(a: str, b: str) -> float:
    if RDKIT_AVAILABLE:
        mol_a = Chem.MolFromSmiles(a)
        mol_b = Chem.MolFromSmiles(b)
        if mol_a is not None and mol_b is not None:
            from rdkit import DataStructs

            fp_a = rdMolDescriptors.GetMorganFingerprintAsBitVect(mol_a, 2, nBits=2048)
            fp_b = rdMolDescriptors.GetMorganFingerprintAsBitVect(mol_b, 2, nBits=2048)
            return float(DataStructs.TanimotoSimilarity(fp_a, fp_b))
    grams_a = _char_ngrams(a)
    grams_b = _char_ngrams(b)
    if not grams_a or not grams_b:
        return 0.0
    return len(grams_a & grams_b) / len(grams_a | grams_b)


def _evaluate_smiles_rdkit(smiles: str) -> DescriptorResult:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return DescriptorResult(valid=False, canonical_smiles="", method="rdkit")

    canonical = Chem.MolToSmiles(mol)
    mw = float(Descriptors.MolWt(mol))
    logp = float(Crippen.MolLogP(mol))
    tpsa = float(rdMolDescriptors.CalcTPSA(mol))
    hbd = int(Lipinski.NumHDonors(mol))
    hba = int(Lipinski.NumHAcceptors(mol))
    rot = int(Lipinski.NumRotatableBonds(mol))
    qed = float(QED.qed(mol))
    lipinski = int(mw > 500) + int(logp > 5) + int(hbd > 5) + int(hba > 10)
    alerts, severe = _rdkit_alerts(mol)
    sa = _heuristic_sa_score(canonical, mw, rot, len(alerts))
    return DescriptorResult(
        valid=True,
        canonical_smiles=canonical,
        molecular_weight=mw,
        logp=logp,
        tpsa=tpsa,
        hbd=hbd,
        hba=hba,
        rotatable_bonds=rot,
        qed=qed,
        lipinski_violations=lipinski,
        alerts=alerts,
        severe_alerts=severe,
        sa_score=sa,
        method="rdkit",
    )


def _rdkit_alerts(mol: object) -> tuple[list[str], list[str]]:
    alerts: list[str] = []
    severe: list[str] = []
    try:
        params = FilterCatalogParams()
        params.AddCatalog(FilterCatalogParams.FilterCatalogs.PAINS_A)
        params.AddCatalog(FilterCatalogParams.FilterCatalogs.PAINS_B)
        params.AddCatalog(FilterCatalogParams.FilterCatalogs.PAINS_C)
        params.AddCatalog(FilterCatalogParams.FilterCatalogs.BRENK)
        catalog = FilterCatalog(params)
        for match in catalog.GetMatches(mol):
            description = match.GetDescription()
            alerts.append(description)
            if "nitro" in description.lower() or "tox" in description.lower():
                severe.append(description)
    except Exception:
        pass
    return alerts, severe


def _evaluate_smiles_heuristic(smiles: str) -> DescriptorResult:
    cleaned = re.sub(r"\s+", "", smiles)
    if not _heuristic_valid_smiles(cleaned):
        return DescriptorResult(valid=False, canonical_smiles="", method="heuristic")

    counts = _atom_counts(cleaned)
    mw = (
        counts["C"] * 12.01
        + counts["N"] * 14.01
        + counts["O"] * 16.00
        + counts["S"] * 32.06
        + counts["F"] * 19.00
        + counts["Cl"] * 35.45
        + counts["Br"] * 79.90
        + counts["I"] * 126.90
        + max(12, len(cleaned) * 0.65)
    )
    hetero = counts["N"] + counts["O"] + counts["S"]
    halogens = counts["F"] + counts["Cl"] + counts["Br"] + counts["I"]
    logp = 0.8 + 0.035 * counts["C"] + 0.25 * halogens - 0.12 * hetero
    tpsa = 11.5 * counts["N"] + 13.0 * counts["O"] + 20.0 * counts["S"]
    hbd = min(5, cleaned.count("N") + cleaned.count("O"))
    hba = min(12, hetero + cleaned.count("n") + cleaned.count("o"))
    rot = max(0, cleaned.count("C") // 6 + cleaned.count("OCC"))
    lipinski = int(mw > 500) + int(logp > 5) + int(hbd > 5) + int(hba > 10)
    alerts, severe = _heuristic_alerts(cleaned)
    qed = _heuristic_qed(mw, logp, tpsa, hbd, hba, rot, len(alerts))
    sa = _heuristic_sa_score(cleaned, mw, rot, len(alerts))
    return DescriptorResult(
        valid=True,
        canonical_smiles=cleaned,
        molecular_weight=mw,
        logp=logp,
        tpsa=tpsa,
        hbd=hbd,
        hba=hba,
        rotatable_bonds=rot,
        qed=qed,
        lipinski_violations=lipinski,
        alerts=alerts,
        severe_alerts=severe,
        sa_score=sa,
        method="heuristic",
    )


def _heuristic_valid_smiles(smiles: str) -> bool:
    if not smiles or len(smiles) < 3:
        return False
    if smiles.lower() in {"invalid", "not-a-smiles", "nan"}:
        return False
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789@+-[]()=#/%\\. ")
    if any(ch not in allowed for ch in smiles):
        return False
    if smiles.count("(") != smiles.count(")"):
        return False
    if not any(ch in smiles for ch in ["C", "c", "N", "n", "O", "o", "S", "s"]):
        return False
    return True


def _atom_counts(smiles: str) -> dict[str, int]:
    protected = smiles.replace("Cl", "L").replace("Br", "R")
    return {
        "C": protected.count("C") + protected.count("c"),
        "N": protected.count("N") + protected.count("n"),
        "O": protected.count("O") + protected.count("o"),
        "S": protected.count("S") + protected.count("s"),
        "F": protected.count("F"),
        "Cl": smiles.count("Cl"),
        "Br": smiles.count("Br"),
        "I": protected.count("I"),
    }


def _heuristic_alerts(smiles: str) -> tuple[list[str], list[str]]:
    alerts: list[str] = []
    severe: list[str] = []
    patterns = {
        "nitro_or_n_oxide": ["N(=O)=O", "[N+](=O)[O-]", "NO2"],
        "azo_or_diazo": ["N=N", "N#N"],
        "acid_chloride_or_reactive_halide": ["C(=O)Cl", "CCl3"],
        "hydrazine_like": ["NN", "NNC"],
        "aldehyde": ["C=O"],
    }
    for label, needles in patterns.items():
        if any(needle in smiles for needle in needles):
            alerts.append(label)
            if label != "aldehyde":
                severe.append(label)
    return alerts, severe


def _heuristic_qed(mw: float, logp: float, tpsa: float, hbd: int, hba: int, rot: int, alert_count: int) -> float:
    components = [
        _bell(mw, center=380, width=240),
        _bell(logp, center=2.8, width=3.0),
        _bell(tpsa, center=75, width=85),
        _bell(hbd, center=1.5, width=4),
        _bell(hba, center=6, width=7),
        _bell(rot, center=5, width=8),
    ]
    score = sum(components) / len(components) - 0.08 * alert_count
    return max(0.02, min(0.95, score))


def _heuristic_sa_score(smiles: str, mw: float, rot: int, alert_count: int) -> float:
    ring_digits = len(re.findall(r"\d", smiles))
    branches = smiles.count("(")
    complexity = 2.0 + 0.004 * max(0, mw - 250) + 0.12 * rot + 0.16 * branches + 0.08 * ring_digits
    complexity += 0.45 * alert_count
    return max(1.0, min(10.0, complexity))


def _bell(value: float, center: float, width: float) -> float:
    return math.exp(-((value - center) / max(width, 0.01)) ** 2)


def _char_ngrams(smiles: str, n: int = 3) -> set[str]:
    if len(smiles) < n:
        return {smiles}
    return {smiles[i : i + n] for i in range(len(smiles) - n + 1)}


def html_escape(value: object) -> str:
    return html.escape(str(value), quote=True)

