from __future__ import annotations

import json
from pathlib import Path

from targetsafe.chem import html_escape
from targetsafe.models import PipelineResult


def write_html_report(result: PipelineResult, output_dir: str | Path = "outputs") -> str:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"{result.run_id}_targetsafe_report.html"
    status_counts: dict[str, int] = {}
    for c in result.candidates:
        status = c.decision.final_status if c.decision else "Unscored"
        status_counts[status] = status_counts.get(status, 0) + 1

    rows = []
    for c in result.candidates:
        d = c.decision
        desc = c.descriptors
        score = f"{d.total_score:.3f}" if d else "0.000"
        activity = f"{c.predicted_activity:.3f}" if c.predicted_activity is not None else ""
        lower = ""
        interval = c.prediction_interval or {}
        if interval:
            lower = f"{interval.get('lower', 0):.3f}"
        qed = f"{desc.qed:.3f}" if desc else ""
        logp = f"{desc.logp:.2f}" if desc else ""
        sa_score = f"{desc.sa_score:.2f}" if desc else ""
        alert_count = str(len(desc.alerts)) if desc else ""
        criteria = ", ".join(f"{key}:{value}" for key, value in (d.criteria if d else {}).items())
        rows.append(
            "<tr>"
            f"<td>{html_escape(c.candidate_id)}</td>"
            f"<td>{html_escape(d.final_status if d else '')}</td>"
            f"<td>{html_escape(c.parent_candidate_id or '')}</td>"
            f"<td>{html_escape(c.redesign_reason)}</td>"
            f"<td>{score}</td>"
            f"<td>{activity}</td>"
            f"<td>{lower}</td>"
            f"<td>{c.evidence_confidence:.3f}</td>"
            f"<td>{qed}</td>"
            f"<td>{logp}</td>"
            f"<td>{sa_score}</td>"
            f"<td>{alert_count}</td>"
            f"<td><code>{html_escape(c.smiles)}</code></td>"
            f"<td>{html_escape('; '.join(d.reasons[:2]) if d else '')}</td>"
            f"<td>{html_escape(criteria)}</td>"
            "</tr>"
        )

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Target-SAFE Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #172033; }}
    h1, h2 {{ color: #102a43; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
    th, td {{ border: 1px solid #d8dee9; padding: 8px; vertical-align: top; }}
    th {{ background: #f1f5f9; text-align: left; }}
    code {{ word-break: break-all; white-space: normal; }}
    .note {{ background: #fff7ed; border-left: 4px solid #f97316; padding: 12px; }}
    .badge {{ display: inline-block; border-radius: 999px; padding: 6px 10px; background: #f1f5f9; }}
    .grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }}
    .box {{ border: 1px solid #d8dee9; padding: 12px; background: #fbfcff; }}
  </style>
</head>
<body>
  <h1>Target-SAFE Lead Triage Report</h1>
  <p class="note">This report is a decision-support artifact. It does not claim clinical efficacy,
  safety, or synthesizability. All candidates require expert and experimental confirmation.</p>
  <h2>Run Summary</h2>
  <div class="grid">
    <div class="box"><b>Run ID</b><br>{html_escape(result.run_id)}</div>
    <div class="box"><b>Target / Disease</b><br>{html_escape(result.evidence.target)} / {html_escape(result.evidence.disease)}</div>
    <div class="box"><b>Compute profile</b><br>{html_escape((result.compute_profile or {}).get("label", ""))}</div>
    <div class="box"><b>Status counts</b><br>{html_escape(status_counts)}</div>
    <div class="box"><b>Evidence graph</b><br>{html_escape((result.evidence_graph or {}).get("summary", {}))}</div>
    <div class="box"><b>QSAR model</b><br>{html_escape((result.model_card or {}).get("model_id", ""))}</div>
    <div class="box"><b>Evidence mode</b><br><span class="badge">{html_escape((result.evidence_mode or {}).get("label", ""))}</span><br>{html_escape((result.evidence_mode or {}).get("interpretation", ""))}</div>
    <div class="box"><b>Validation status</b><br><span class="badge">{html_escape((result.validation_report or {}).get("status", ""))}</span><br>{html_escape((result.validation_report or {}).get("interpretation", ""))}</div>
    <div class="box"><b>Redesign loop</b><br>{html_escape((result.redesign_report or {}).get("created_children", 0))} child suggestions</div>
  </div>
  <h2>Agentic Trace</h2>
  <pre>{html_escape(json.dumps([event.to_dict() for event in result.agent_events], indent=2))}</pre>
  <h2>Agent Plan</h2>
  <ol>{''.join(f'<li>{html_escape(step)}</li>' for step in result.plan)}</ol>
  <h2>Candidate Decisions</h2>
  <table>
    <thead>
      <tr>
        <th>ID</th><th>Status</th><th>Parent</th><th>Redesign reason</th><th>Support</th><th>Pred pChEMBL</th><th>Lower</th><th>Evidence</th>
        <th>QED</th><th>LogP</th><th>SA</th><th>Alerts</th><th>SMILES</th><th>Reasons</th>
        <th>Criteria</th>
      </tr>
    </thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
  <h2>Threshold Registry</h2>
  <pre>{html_escape(json.dumps(result.threshold_registry, indent=2))}</pre>
  <h2>Model Card</h2>
  <pre>{html_escape(json.dumps(result.model_card, indent=2))}</pre>
  <h2>QSAR Validation</h2>
  <pre>{html_escape(json.dumps(result.validation_report, indent=2))}</pre>
  <h2>Critic Redesign Report</h2>
  <pre>{html_escape(json.dumps(result.redesign_report, indent=2))}</pre>
  <h2>Class-Level Clinical/Regulatory Risk Checklist</h2>
  <ul>{''.join(f'<li><b>{html_escape(r.get("risk", ""))}</b>: {html_escape(r.get("interpretation", ""))}</li>' for r in result.evidence.regulatory_risks)}</ul>
  <h2>Tool Trace</h2>
  <pre>{html_escape(json.dumps([log.to_dict() for log in result.tool_logs], indent=2))}</pre>
  <h2>Evaluation Report</h2>
  <pre>{html_escape(json.dumps(result.evaluation_report, indent=2))}</pre>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")
    return str(path)
