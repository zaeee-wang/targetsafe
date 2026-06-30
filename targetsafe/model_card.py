from __future__ import annotations

from pathlib import Path
from typing import Any
import json


def write_model_card(model_card: dict[str, Any], output_dir: str | Path) -> str:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    path = output / "model_card_egfr.json"
    path.write_text(json.dumps(model_card, indent=2), encoding="utf-8")
    return str(path)


def write_evidence_graph(graph: dict[str, Any], output_dir: str | Path) -> str:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    path = output / "evidence_graph.json"
    path.write_text(json.dumps(graph, indent=2), encoding="utf-8")
    return str(path)


def write_ablation_report(summary: dict[str, Any], output_dir: str | Path) -> str:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    path = output / "ablation_report.html"
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Target-SAFE Ablation Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #172033; }}
    h1, h2 {{ color: #14313d; }}
    pre {{ background: #f5f7fb; border: 1px solid #d8dee9; padding: 16px; overflow-x: auto; }}
  </style>
</head>
<body>
  <h1>Target-SAFE Ablation Report</h1>
  <p>This report compares decision-support layers. It is not an efficacy or safety claim.</p>
  <h2>Summary</h2>
  <pre>{json.dumps(summary, indent=2)}</pre>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")
    return str(path)
