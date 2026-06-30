from __future__ import annotations

import json
import math
import hashlib
from pathlib import Path
from typing import Any

from targetsafe.chem import RDKIT_AVAILABLE, tanimoto_like_similarity
from targetsafe.models import EvidenceBundle
from targetsafe.qsar import EvidenceWeightedQSAR

try:
    from rdkit import Chem
    from rdkit.Chem import AllChem
    from rdkit.Chem.Scaffolds import MurckoScaffold
except Exception:
    Chem = None
    AllChem = None
    MurckoScaffold = None

try:
    from sklearn.ensemble import RandomForestRegressor
except Exception:
    RandomForestRegressor = None


def build_qsar_validation_report(
    evidence: EvidenceBundle,
    qsar: EvidenceWeightedQSAR,
    *,
    min_rows: int = 20,
) -> dict[str, Any]:
    rows = _validation_rows(qsar)
    source_statuses = _source_statuses(evidence)
    base = {
        "schema": "targetsafe.qsar_validation.v1",
        "target": evidence.target,
        "dataset_size": len(rows),
        "minimum_required_rows": min_rows,
        "source_statuses": source_statuses,
        "rdkit_available": RDKIT_AVAILABLE,
        "sklearn_available": RandomForestRegressor is not None,
        "claim_policy": "Metrics are reported only when enough structure/activity rows exist; demo fallback rows do not produce fake validation scores.",
    }
    if len(rows) < min_rows:
        return {
            **base,
            "status": "insufficient_data",
            "interpretation": (
                "QSAR validation was not run because available EGFR structure/activity rows are below the minimum. "
                "The current model remains analog-supported and demo-grade until live ChEMBL rows are added."
            ),
            "metrics": {},
            "split_summary": {"method": "not_run", "train_count": 0, "test_count": 0},
            "applicability_domain_performance": {},
        }
    train_rows, test_rows, split_summary = _split_rows(rows)
    if len(train_rows) < 4 or len(test_rows) < 3:
        return {
            **base,
            "status": "insufficient_split",
            "interpretation": "Rows exist, but deterministic scaffold/hash split did not leave enough train/test examples.",
            "metrics": {},
            "split_summary": split_summary,
            "applicability_domain_performance": {},
        }

    train_y = [row["pchembl"] for row in train_rows]
    test_y = [row["pchembl"] for row in test_rows]
    if RandomForestRegressor is not None:
        model = RandomForestRegressor(n_estimators=96, random_state=17, min_samples_leaf=1)
        train_x = [_fingerprint(row["smiles"]) for row in train_rows]
        test_x = [_fingerprint(row["smiles"]) for row in test_rows]
        model.fit(train_x, train_y)
        train_pred = [float(value) for value in model.predict(train_x)]
        test_pred = [float(value) for value in model.predict(test_x)]
        model_type = "Morgan fingerprint RandomForestRegressor" if RDKIT_AVAILABLE else "hashed SMILES fingerprint RandomForestRegressor"
    else:
        train_pred = [_nearest_activity_prediction(row["smiles"], train_rows, exclude_smiles=row["smiles"]) for row in train_rows]
        test_pred = [_nearest_activity_prediction(row["smiles"], train_rows) for row in test_rows]
        model_type = "deterministic nearest-analog validation fallback; scikit-learn unavailable"
    residual_std = _std([actual - pred for actual, pred in zip(train_y, train_pred)]) or 0.5
    interval_lower = [pred - residual_std for pred in test_pred]
    interval_upper = [pred + residual_std for pred in test_pred]
    coverage = sum(1 for actual, lo, hi in zip(test_y, interval_lower, interval_upper) if lo <= actual <= hi) / len(test_y)
    ad_flags = [_nearest_train_similarity(row["smiles"], train_rows) >= 0.18 for row in test_rows]

    report = {
        **base,
        "status": "validated",
        "model_type": model_type,
        "interpretation": "Validation metrics are model-quality diagnostics only; they do not establish clinical efficacy or safety.",
        "metrics": {
            "rmse": round(_rmse(test_y, test_pred), 3),
            "mae": round(_mae(test_y, test_pred), 3),
            "spearman": round(_spearman(test_y, test_pred), 3),
            "top_10_enrichment": _top_k_enrichment(test_y, test_pred, k=10),
            "prediction_interval_coverage": round(coverage, 3),
            "residual_interval_half_width": round(residual_std, 3),
        },
        "split_summary": split_summary,
        "applicability_domain_performance": _ad_performance(test_y, test_pred, ad_flags),
    }
    return report


def write_validation_outputs(report: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    metrics_path = output / "evaluation_metrics_egfr.json"
    scaffold_path = output / "scaffold_split_summary.json"
    html_path = output / "qsar_validation_report.html"
    metrics_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    scaffold_path.write_text(json.dumps(report.get("split_summary", {}), indent=2), encoding="utf-8")
    html_path.write_text(_validation_html(report), encoding="utf-8")
    return {
        "metrics_path": str(metrics_path),
        "scaffold_split_path": str(scaffold_path),
        "html_report_path": str(html_path),
    }


def _validation_rows(qsar: EvidenceWeightedQSAR) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in qsar.training_rows:
        smiles = str(row.get("smiles", "")).strip()
        try:
            pchembl = float(row.get("pchembl"))
        except (TypeError, ValueError):
            continue
        if not smiles or smiles in seen:
            continue
        seen.add(smiles)
        rows.append({"smiles": smiles, "pchembl": pchembl, "source": row.get("source", "")})
    return rows


def _source_statuses(evidence: EvidenceBundle) -> dict[str, int]:
    counts: dict[str, int] = {}
    for collection in [evidence.known_inhibitors, evidence.chembl_activities, evidence.pubchem_records, evidence.regulatory_risks]:
        for item in collection:
            status = str(item.get("source_status") or item.get("source") or "unknown")
            counts[status] = counts.get(status, 0) + 1
    return counts


def _split_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        key = _scaffold_key(row["smiles"])
        grouped.setdefault(key, []).append(row)
    method = "murcko_scaffold_split" if RDKIT_AVAILABLE and MurckoScaffold is not None else "hash_split"
    if len(grouped) < 4 and len(rows) >= 12:
        grouped = {}
        for row in rows:
            key = f"hash_{_stable_index(row['smiles'], 7)}"
            grouped.setdefault(key, []).append(row)
        method = "hash_split_after_low_scaffold_diversity"
    train: list[dict[str, Any]] = []
    test: list[dict[str, Any]] = []
    target_test = max(3, math.ceil(len(rows) * 0.25))
    for key in sorted(grouped):
        bucket = grouped[key]
        if len(test) < target_test:
            test.extend(bucket)
        else:
            train.extend(bucket)
    if len(train) < len(test):
        train, test = test, train
    return train, test, {"method": method, "train_count": len(train), "test_count": len(test), "group_count": len(grouped)}


def _scaffold_key(smiles: str) -> str:
    if RDKIT_AVAILABLE and Chem is not None and MurckoScaffold is not None:
        mol = Chem.MolFromSmiles(smiles)
        if mol is not None:
            scaffold = MurckoScaffold.MurckoScaffoldSmiles(mol=mol)
            if scaffold:
                return scaffold
    return str(_stable_index(smiles, 17))


def _fingerprint(smiles: str, n_bits: int = 512) -> list[int]:
    if RDKIT_AVAILABLE and Chem is not None and AllChem is not None:
        mol = Chem.MolFromSmiles(smiles)
        if mol is not None:
            bitvect = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=n_bits)
            return [int(bitvect.GetBit(i)) for i in range(n_bits)]
    bits = [0] * n_bits
    for width in (1, 2, 3):
        for index in range(0, max(0, len(smiles) - width + 1)):
            token = smiles[index : index + width]
            bits[_stable_index(token, n_bits)] = 1
    return bits


def _stable_index(value: str, modulo: int) -> int:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) % modulo


def _nearest_train_similarity(smiles: str, train_rows: list[dict[str, Any]]) -> float:
    if not train_rows:
        return 0.0
    return max(tanimoto_like_similarity(smiles, row["smiles"]) for row in train_rows)


def _nearest_activity_prediction(smiles: str, train_rows: list[dict[str, Any]], exclude_smiles: str | None = None) -> float:
    usable = [row for row in train_rows if row["smiles"] != exclude_smiles]
    if not usable:
        usable = train_rows
    if not usable:
        return 0.0
    analogs = sorted(
        ({**row, "similarity": tanimoto_like_similarity(smiles, row["smiles"])} for row in usable),
        key=lambda row: row["similarity"],
        reverse=True,
    )[:5]
    weights = [max(row["similarity"], 0.01) ** 2 for row in analogs]
    return sum(row["pchembl"] * weight for row, weight in zip(analogs, weights)) / sum(weights)


def _rmse(actual: list[float], pred: list[float]) -> float:
    return math.sqrt(sum((a - p) ** 2 for a, p in zip(actual, pred)) / len(actual))


def _mae(actual: list[float], pred: list[float]) -> float:
    return sum(abs(a - p) for a, p in zip(actual, pred)) / len(actual)


def _std(values: list[float]) -> float:
    if not values:
        return 0.0
    center = sum(values) / len(values)
    return math.sqrt(sum((value - center) ** 2 for value in values) / len(values))


def _spearman(actual: list[float], pred: list[float]) -> float:
    return _pearson(_rank(actual), _rank(pred))


def _rank(values: list[float]) -> list[float]:
    ordered = sorted((value, index) for index, value in enumerate(values))
    ranks = [0.0] * len(values)
    cursor = 0
    while cursor < len(ordered):
        end = cursor
        while end + 1 < len(ordered) and ordered[end + 1][0] == ordered[cursor][0]:
            end += 1
        rank = (cursor + end + 2) / 2.0
        for _, index in ordered[cursor : end + 1]:
            ranks[index] = rank
        cursor = end + 1
    return ranks


def _pearson(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        return 0.0
    lx = sum(left) / len(left)
    rx = sum(right) / len(right)
    num = sum((a - lx) * (b - rx) for a, b in zip(left, right))
    den_left = math.sqrt(sum((a - lx) ** 2 for a in left))
    den_right = math.sqrt(sum((b - rx) ** 2 for b in right))
    if den_left == 0 or den_right == 0:
        return 0.0
    return num / (den_left * den_right)


def _top_k_enrichment(actual: list[float], pred: list[float], k: int) -> float | None:
    if not actual:
        return None
    active = [value >= 7.0 for value in actual]
    baseline = sum(active) / len(active)
    if baseline == 0:
        return None
    top = sorted(range(len(pred)), key=lambda index: pred[index], reverse=True)[: min(k, len(pred))]
    top_rate = sum(1 for index in top if active[index]) / len(top)
    return round(top_rate / baseline, 3)


def _ad_performance(actual: list[float], pred: list[float], ad_flags: list[bool]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for label, flag in [("in_domain", True), ("out_of_domain", False)]:
        indices = [index for index, item in enumerate(ad_flags) if item is flag]
        if not indices:
            result[label] = {"count": 0}
            continue
        y = [actual[index] for index in indices]
        p = [pred[index] for index in indices]
        result[label] = {"count": len(indices), "rmse": round(_rmse(y, p), 3), "mae": round(_mae(y, p), 3)}
    return result


def _validation_html(report: dict[str, Any]) -> str:
    escaped = json.dumps(report, indent=2).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Target-SAFE EGFR QSAR Validation</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #1d1d1f; }}
    h1 {{ margin-bottom: 8px; }}
    .badge {{ display: inline-block; padding: 6px 10px; border-radius: 999px; background: #f5f5f7; }}
    pre {{ background: #f5f5f7; border: 1px solid #e0e0e0; padding: 16px; overflow-x: auto; }}
  </style>
</head>
<body>
  <h1>Target-SAFE EGFR QSAR Validation</h1>
  <p class="badge">{report.get("status", "unknown")}</p>
  <p>{report.get("interpretation", "")}</p>
  <pre>{escaped}</pre>
</body>
</html>
"""
