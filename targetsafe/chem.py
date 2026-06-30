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
    from rdkit.Chem import AllChem
    from rdkit.Chem import Crippen, Descriptors, Draw, Lipinski, QED, rdMolDescriptors
    from rdkit.Chem.FilterCatalog import FilterCatalog, FilterCatalogParams

    RDKIT_AVAILABLE = True
except Exception:
    Chem = None
    AllChem = None
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
        CandidateRecord(
            candidate_id=f"C{i + 1:03d}",
            smiles=smi,
            source="seed_analog_library",
            library_source="seed_analog",
            source_compound_id=f"seed_analog_{i + 1:03d}",
            source_name="Seed-derived analog",
            screening_stage="library_proposed",
        )
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
        return _fallback_smiles_svg_data_uri(smiles)
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    try:
        svg = Draw.MolsToGridImage([mol], molsPerRow=1, subImgSize=(300, 180), useSVG=True)
        encoded = base64.b64encode(str(svg).encode("utf-8")).decode("ascii")
        return f"data:image/svg+xml;base64,{encoded}"
    except Exception:
        return None


def _fallback_smiles_svg_data_uri(smiles: str) -> str | None:
    if not _heuristic_valid_smiles(smiles):
        return None
    graph = _parse_smiles_graph(smiles, max_atoms=90)
    if not graph["atoms"]:
        return None
    coords = _layout_smiles_graph(graph["atoms"], graph["bonds"])
    svg = _render_bond_line_svg(graph["atoms"], graph["bonds"], coords)
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def _atom_color(atom: str) -> str:
    colors = {
        "C": "#eff7ef",
        "N": "#dfe9ff",
        "O": "#ffe3df",
        "F": "#e6f5dd",
        "Cl": "#e6f5dd",
        "Br": "#f2e8d7",
        "S": "#fff2bf",
    }
    return colors.get(atom, "#ffffff")


def _parse_smiles_graph(smiles: str, max_atoms: int = 90) -> dict[str, list[dict[str, object]]]:
    atoms: list[dict[str, object]] = []
    bonds: list[dict[str, object]] = []
    stack: list[int | None] = []
    rings: dict[str, tuple[int, float]] = {}
    current: int | None = None
    pending_order = 1.0
    i = 0
    while i < len(smiles) and len(atoms) < max_atoms:
        ch = smiles[i]
        if ch in "-:":
            pending_order = 1.0
            i += 1
            continue
        if ch == "=":
            pending_order = 2.0
            i += 1
            continue
        if ch == "#":
            pending_order = 3.0
            i += 1
            continue
        if ch in "/\\":
            i += 1
            continue
        if ch == "(":
            stack.append(current)
            i += 1
            continue
        if ch == ")":
            current = stack.pop() if stack else current
            i += 1
            continue
        if ch.isdigit():
            if current is not None:
                if ch in rings:
                    other, order = rings.pop(ch)
                    if other != current:
                        bonds.append({"begin": other, "end": current, "order": pending_order or order})
                else:
                    rings[ch] = (current, pending_order)
            pending_order = 1.0
            i += 1
            continue
        atom, jump = _read_smiles_atom(smiles, i)
        if atom:
            index = len(atoms)
            atoms.append({"index": index, "element": atom, "aromatic": smiles[i].islower()})
            if current is not None:
                bonds.append({"begin": current, "end": index, "order": pending_order})
            current = index
            pending_order = 1.0
            i += jump
            continue
        i += 1
    return {"atoms": atoms, "bonds": bonds}


def _read_smiles_atom(smiles: str, index: int) -> tuple[str | None, int]:
    if smiles[index] == "[":
        end = smiles.find("]", index + 1)
        if end == -1:
            return None, 1
        token = smiles[index + 1 : end]
        match = re.search(r"Cl|Br|[A-Z][a-z]?|[bcnops]", token)
        if not match:
            return None, end - index + 1
        return match.group(0).capitalize(), end - index + 1
    two = smiles[index : index + 2]
    if two in {"Cl", "Br"}:
        return two, 2
    ch = smiles[index]
    if ch in "BCNOFPSI" or ch in "bcnops":
        return ch.capitalize(), 1
    return None, 1


def _layout_smiles_graph(
    atoms: list[dict[str, object]],
    bonds: list[dict[str, object]],
) -> list[tuple[float, float]]:
    n = len(atoms)
    if n == 1:
        return [(0.0, 0.0)]
    adjacency: list[list[int]] = [[] for _ in range(n)]
    for bond in bonds:
        a = int(bond["begin"])
        b = int(bond["end"])
        if a < n and b < n:
            adjacency[a].append(b)
            adjacency[b].append(a)

    coords: list[tuple[float, float]] = []
    for idx in range(n):
        angle = idx * 2.399963
        radius = 36.0 * math.sqrt(idx + 1)
        coords.append((math.cos(angle) * radius, math.sin(angle) * radius))

    for _ in range(120):
        forces = [[0.0, 0.0] for _ in range(n)]
        for i in range(n):
            xi, yi = coords[i]
            for j in range(i + 1, n):
                xj, yj = coords[j]
                dx = xi - xj
                dy = yi - yj
                dist_sq = max(20.0, dx * dx + dy * dy)
                force = 720.0 / dist_sq
                dist = math.sqrt(dist_sq)
                fx = force * dx / dist
                fy = force * dy / dist
                forces[i][0] += fx
                forces[i][1] += fy
                forces[j][0] -= fx
                forces[j][1] -= fy
        for bond in bonds:
            a = int(bond["begin"])
            b = int(bond["end"])
            if a >= n or b >= n:
                continue
            ax, ay = coords[a]
            bx, by = coords[b]
            dx = bx - ax
            dy = by - ay
            dist = max(1.0, math.sqrt(dx * dx + dy * dy))
            target = 46.0 if float(bond.get("order", 1.0)) < 2 else 42.0
            force = (dist - target) * 0.034
            fx = force * dx / dist
            fy = force * dy / dist
            forces[a][0] += fx
            forces[a][1] += fy
            forces[b][0] -= fx
            forces[b][1] -= fy
        coords = [
            (x + max(-6.0, min(6.0, fx)), y + max(-6.0, min(6.0, fy)))
            for (x, y), (fx, fy) in zip(coords, forces)
        ]
    return coords


def _render_bond_line_svg(
    atoms: list[dict[str, object]],
    bonds: list[dict[str, object]],
    coords: list[tuple[float, float]],
) -> str:
    width = 640
    height = 420
    xs = [x for x, _ in coords]
    ys = [y for _, y in coords]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max(1.0, max_x - min_x)
    span_y = max(1.0, max_y - min_y)
    scale = min((width - 90) / span_x, (height - 80) / span_y, 3.2)

    def project(point: tuple[float, float]) -> tuple[float, float]:
        x, y = point
        return (
            45 + (x - min_x) * scale + ((width - 90) - span_x * scale) / 2,
            40 + (y - min_y) * scale + ((height - 80) - span_y * scale) / 2,
        )

    lines: list[str] = []
    for bond in bonds:
        a = int(bond["begin"])
        b = int(bond["end"])
        if a >= len(coords) or b >= len(coords):
            continue
        x1, y1 = project(coords[a])
        x2, y2 = project(coords[b])
        order = float(bond.get("order", 1.0))
        if order == 2.0:
            dx, dy = x2 - x1, y2 - y1
            dist = max(1.0, math.sqrt(dx * dx + dy * dy))
            ox, oy = -dy / dist * 4.0, dx / dist * 4.0
            lines.append(_svg_line(x1 + ox, y1 + oy, x2 + ox, y2 + oy, 2.2))
            lines.append(_svg_line(x1 - ox, y1 - oy, x2 - ox, y2 - oy, 2.2))
        elif order >= 3.0:
            lines.append(_svg_line(x1, y1, x2, y2, 4.0))
        else:
            lines.append(_svg_line(x1, y1, x2, y2, 2.7))

    labels: list[str] = []
    for atom, point in zip(atoms, coords):
        element = str(atom["element"])
        if element == "C":
            continue
        x, y = project(point)
        color = {
            "N": "#1657d9",
            "O": "#d0342c",
            "F": "#2f8a25",
            "Cl": "#2f8a25",
            "Br": "#8b4a17",
            "S": "#b88400",
        }.get(element, "#111111")
        labels.append(
            f'<text x="{x:.1f}" y="{y + 5:.1f}" text-anchor="middle" '
            f'font-family="Arial, sans-serif" font-size="18" font-weight="700" '
            f'fill="{color}" stroke="#ffffff" stroke-width="4" paint-order="stroke">{html.escape(element)}</text>'
        )

    return "".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<rect width="100%" height="100%" fill="transparent"/>',
            "".join(lines),
            "".join(labels),
            "</svg>",
        ]
    )


def _svg_line(x1: float, y1: float, x2: float, y2: float, width: float) -> str:
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="#111111" stroke-width="{width:.1f}" stroke-linecap="round"/>'
    )


def mol_conformer_payload(smiles: str) -> dict[str, object] | None:
    if not RDKIT_AVAILABLE:
        return _fallback_conformer_payload(smiles)
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    try:
        mol = Chem.AddHs(mol)
        status = AllChem.EmbedMolecule(mol, randomSeed=13)
        if status != 0:
            return {
                "available": False,
                "label": "computed conformer unavailable",
                "message": "RDKit could not embed a conformer for this molecule.",
                "atoms": [],
                "bonds": [],
            }
        AllChem.UFFOptimizeMolecule(mol, maxIters=80)
        conformer = mol.GetConformer()
        atoms = []
        for atom in mol.GetAtoms():
            pos = conformer.GetAtomPosition(atom.GetIdx())
            atoms.append(
                {
                    "index": atom.GetIdx(),
                    "element": atom.GetSymbol(),
                    "x": round(float(pos.x), 3),
                    "y": round(float(pos.y), 3),
                    "z": round(float(pos.z), 3),
                }
            )
        bonds = [
            {"begin": bond.GetBeginAtomIdx(), "end": bond.GetEndAtomIdx(), "order": float(bond.GetBondTypeAsDouble())}
            for bond in mol.GetBonds()
        ]
        return {
            "available": True,
            "label": "computed conformer",
            "message": "RDKit ETKDG/UFF conformer for spatial inspection only; not a validated binding pose.",
            "atoms": atoms,
            "bonds": bonds,
        }
    except Exception as exc:
        return {
            "available": False,
            "label": "computed conformer unavailable",
            "message": f"Conformer generation failed: {exc.__class__.__name__}.",
            "atoms": [],
            "bonds": [],
        }


def _fallback_conformer_payload(smiles: str) -> dict[str, object] | None:
    if not _heuristic_valid_smiles(smiles):
        return None
    atoms = re.findall(r"Cl|Br|[BCNOFPSI]|[bcnops]", smiles)
    atoms = [atom.capitalize() for atom in atoms if atom.strip()][:34]
    if not atoms:
        return {
            "available": False,
            "label": "computed 3D layout unavailable",
            "message": "No displayable atoms were detected in the SMILES fallback parser.",
            "atoms": [],
            "bonds": [],
        }
    coords = []
    for idx, atom in enumerate(atoms):
        angle = idx * 0.72
        radius = 1.4 + 0.08 * (idx % 5)
        coords.append(
            {
                "index": idx,
                "element": atom,
                "x": round(math.cos(angle) * radius + idx * 0.18, 3),
                "y": round(math.sin(angle) * radius, 3),
                "z": round((idx % 7 - 3) * 0.32, 3),
            }
        )
    bonds = [
        {"begin": idx, "end": idx + 1, "order": 1.0}
        for idx in range(max(0, len(coords) - 1))
    ]
    return {
        "available": True,
        "label": "computed 3D layout",
        "message": (
            "Fallback spatial layout from SMILES atoms for UI inspection only; install RDKit "
            "for ETKDG/UFF conformers and do not interpret this as a binding pose."
        ),
        "atoms": coords,
        "bonds": bonds,
    }


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
    if smiles.count("[") != smiles.count("]"):
        return False
    for digit in "123456789":
        if smiles.count(digit) % 2:
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
