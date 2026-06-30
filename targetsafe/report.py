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
        gate_summary = "; ".join(
            f"{gate.gate_id}:{gate.status} ({gate.observed_value} vs {gate.threshold_value or 'n/a'})"
            for gate in ((d.gate_audit if d else [])[:5])
        )
        rows.append(
            "<tr>"
            f"<td>{html_escape(c.candidate_id)}</td>"
            f"<td>{html_escape(d.final_status if d else '')}</td>"
            f"<td>{html_escape(c.library_source or c.source)}</td>"
            f"<td>{html_escape(c.screening_stage)}</td>"
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
            f"<td>{html_escape(gate_summary)}</td>"
            "</tr>"
        )

    gpu = (result.runtime_status or {}).get("gpu", {})
    gpu_diagnostics = result.gpu_diagnostics or (result.runtime_status or {}).get("gpu_diagnostics", {})
    llm = (result.runtime_status or {}).get("llm", {})
    library = result.library_report or {}
    tool_errors = result.tool_error_summary or {}
    top_candidates = [candidate for candidate in result.candidates if candidate.decision][:8]
    top_cards = []
    for candidate in top_candidates:
        decision = candidate.decision
        interval = candidate.prediction_interval or {}
        top_cards.append(
            "<div class='candidate-card'>"
            f"<b>{html_escape(candidate.candidate_id)}</b>"
            f"<span class='badge'>{html_escape(decision.final_status if decision else 'Unscored')}</span>"
            f"<p>{html_escape('; '.join((decision.reasons if decision else [])[:2]))}</p>"
            f"<p><b>Review/block:</b> {html_escape('; '.join((decision.hard_gate_failures + decision.uncertainty)[:2]) if decision else '')}</p>"
            f"<dl><dt>Source</dt><dd>{html_escape(candidate.library_source or candidate.source)}</dd>"
            f"<dt>Lower pChEMBL</dt><dd>{html_escape(interval.get('lower', '-'))}</dd>"
            f"<dt>Applicability</dt><dd>{candidate.applicability_score:.3f}</dd></dl>"
            "</div>"
        )

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Target-SAFE Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; color: #172033; background: #f5f7fb; }}
    main {{ max-width: 1240px; margin: 0 auto; padding: 32px; }}
    h1, h2 {{ color: #102a43; }}
    h1 {{ font-size: 40px; margin-bottom: 10px; }}
    h2 {{ margin-top: 34px; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
    th, td {{ border: 1px solid #d8dee9; padding: 8px; vertical-align: top; }}
    th {{ background: #f1f5f9; text-align: left; }}
    code {{ word-break: break-all; white-space: normal; }}
    .note {{ background: #fff7ed; border-left: 4px solid #f97316; padding: 12px; }}
    .badge {{ display: inline-block; border-radius: 999px; padding: 6px 10px; background: #f1f5f9; }}
    .grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }}
    .box, .candidate-card {{ border: 1px solid #d8dee9; border-radius: 12px; padding: 16px; background: #ffffff; }}
    .hero {{ display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 18px; align-items: stretch; }}
    .hero-panel {{ border-radius: 18px; padding: 24px; background: #0b1220; color: #fff; }}
    .hero-panel p {{ color: #d6deea; line-height: 1.6; }}
    .truth-table {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 18px; }}
    .truth-table .box b {{ display: block; margin-bottom: 8px; }}
    .candidate-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }}
    .candidate-card p {{ min-height: 54px; color: #42526e; }}
    .candidate-card dl {{ display: grid; grid-template-columns: 90px 1fr; gap: 4px 8px; font-size: 12px; }}
    details {{ margin-top: 20px; border: 1px solid #d8dee9; border-radius: 12px; background: #fff; padding: 12px; }}
    summary {{ cursor: pointer; font-weight: 700; }}
    @media (max-width: 900px) {{ .hero, .grid, .truth-table, .candidate-grid {{ grid-template-columns: 1fr; }} main {{ padding: 18px; }} }}
  </style>
</head>
<body>
<main>
  <h1>Target-SAFE Lead Triage Report</h1>
  <section class="box">
    <h2>한글 요약</h2>
    <p>Target-SAFE는 후보물질을 임상적으로 유효하거나 안전하다고 선언하는 시스템이 아니라, 초기 리드 후보를 구조 유효성, 물성 hard gate, QSAR 적용영역, 예측 불확실성, 외부 근거, Critic Agent 검토 기준으로 <b>Go / Hold / No-Go</b>로 좁히는 근거 기반 의사결정 보조 시스템입니다.</p>
    <p><b>No-Go</b>는 invalid SMILES, severe alert, 극단적 descriptor blocker처럼 즉시 중단해야 하는 경우입니다. <b>Hold</b>는 분자는 유효하지만 activity, applicability domain, uncertainty, evidence confidence, API fallback 중 하나 이상이 부족하여 추가 검증이 필요한 경우입니다. <b>Go</b>는 hard blocker가 없고 주요 gate가 모두 통과한 경우에만 붙습니다.</p>
  </section>
  <section class="hero">
    <div class="hero-panel">
      <h2>What this run did</h2>
      <p>Target-SAFE assembled a staged compound library, removed invalid or duplicate structures, evaluated a detailed subset with descriptors, analog-supported QSAR, applicability-domain checks, evidence graph links, and critic review, then assigned Go/Hold/No-Go triage labels.</p>
    </div>
    <div class="box">
      <h2>What it does not claim</h2>
      <p class="note">This report is a decision-support artifact. It does not claim clinical efficacy, candidate safety, binding pose validity, or synthesizability. All candidates require expert and experimental confirmation.</p>
    </div>
  </section>
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
    <div class="box"><b>Runtime status</b><br>{html_escape((result.runtime_status or {}).get("gpu", {}).get("message", ""))}<br>{html_escape((result.runtime_status or {}).get("llm", {}).get("message", ""))}</div>
    <div class="box"><b>Library scale</b><br>{html_escape((result.library_report or {}).get("valid_unique_count", 0))} valid unique / {html_escape((result.library_report or {}).get("detailed_evaluation_count", 0))} detailed</div>
    <div class="box"><b>Screening stages</b><br>{html_escape(result.screening_stages)}</div>
  </div>
  <h2>Execution Reality</h2>
  <div class="truth-table">
    <div class="box"><b>GPU requested</b>{html_escape(gpu.get("requested", ""))}<br><b>Available</b>{html_escape(gpu.get("available", ""))}<br><b>Used</b>{html_escape(gpu.get("used", ""))}</div>
    <div class="box"><b>GPU device</b>{html_escape(gpu.get("device_name", gpu.get("backend", "unknown")))}<br>{html_escape(gpu.get("message", ""))}<br>{html_escape(gpu.get("fallback_reason", ""))}</div>
    <div class="box"><b>LLM requested</b>{html_escape(llm.get("requested", ""))}<br><b>Configured/Provided</b>{html_escape(llm.get("configured", ""))}<br><b>Used</b>{html_escape(llm.get("used", ""))}</div>
    <div class="box"><b>Public APIs</b>ChEMBL, PubChem, ClinicalTrials.gov, openFDA<br>Key required: false<br>{html_escape((result.evidence_mode or {}).get("label", ""))}</div>
  </div>
  <div class="grid">
    <div class="box"><b>System GPU detected</b><br>{html_escape((gpu_diagnostics.get("system_gpu") or {}).get("detected", ""))}<br>{html_escape((gpu_diagnostics.get("system_gpu") or {}).get("message", ""))}</div>
    <div class="box"><b>PyTorch CUDA usable</b><br>{html_escape((gpu_diagnostics.get("torch_cuda") or {}).get("usable", ""))}<br>{html_escape((gpu_diagnostics.get("torch_cuda") or {}).get("message", ""))}</div>
    <div class="box"><b>Action hint</b><br>{html_escape(gpu_diagnostics.get("action_hint", ""))}</div>
  </div>
  <h2>Tool Error / Fallback Summary</h2>
  <div class="grid">
    <div class="box"><b>Total tool calls</b><br>{html_escape(tool_errors.get("total_calls", 0))}</div>
    <div class="box"><b>Error categories</b><br>{html_escape(tool_errors.get("categories", {}))}</div>
    <div class="box"><b>Interpretation</b><br>{html_escape(tool_errors.get("interpretation", ""))}</div>
  </div>
  <h2>Library-Scale Screening</h2>
  <div class="grid">
    <div class="box"><b>Raw input</b><br>{html_escape(library.get("raw_input_count", 0))}</div>
    <div class="box"><b>Valid unique</b><br>{html_escape(library.get("valid_unique_count", 0))}</div>
    <div class="box"><b>Detailed evaluation</b><br>{html_escape(library.get("detailed_evaluation_count", 0))}</div>
    <div class="box"><b>Duplicates removed</b><br>{html_escape(library.get("duplicate_count", 0))}</div>
    <div class="box"><b>Invalid rows</b><br>{html_escape(library.get("invalid_or_unparseable_count", 0))}</div>
    <div class="box"><b>Rendered structures</b><br>{html_escape(library.get("display_asset_count", 0))} 2D / {html_escape(library.get("conformer_asset_count", 0))} 3D</div>
  </div>
  <h2>How to Read Decisions</h2>
  <div class="grid">
    <div class="box"><b>Go</b><br>Passes hard gates, is in domain, has conservative activity support, and has no critic blocker.</div>
    <div class="box"><b>Hold</b><br>Plausible but needs more evidence, uncertainty reduction, analog review, or additional assay validation.</div>
    <div class="box"><b>No-Go</b><br>Invalid structure, severe blocker, unsupported activity claim, or hard descriptor/risk failure.</div>
  </div>
  <h2>Decision Gate Semantics</h2>
  <div class="grid">
    <div class="box"><b>pass</b><br>Gate supports advancement.</div>
    <div class="box"><b>review</b><br>Gate blocks a confident Go but keeps the molecule inspectable.</div>
    <div class="box"><b>block</b><br>Hard blocker; candidate is No-Go unless corrected or regenerated.</div>
  </div>
  <h2>Top Candidate Readout</h2>
  <div class="candidate-grid">{''.join(top_cards)}</div>
  <h2>Agentic Trace</h2>
  <pre>{html_escape(json.dumps([event.to_dict() for event in result.agent_events], indent=2))}</pre>
  <h2>Agent Plan</h2>
  <ol>{''.join(f'<li>{html_escape(step)}</li>' for step in result.plan)}</ol>
  <h2>Candidate Decisions</h2>
  <table>
    <thead>
      <tr>
        <th>ID</th><th>Status</th><th>Source</th><th>Stage</th><th>Parent</th><th>Redesign reason</th><th>Support</th><th>Pred pChEMBL</th><th>Lower</th><th>Evidence</th>
        <th>QED</th><th>LogP</th><th>SA</th><th>Alerts</th><th>SMILES</th><th>Reasons</th>
        <th>Criteria</th><th>Gate audit excerpt</th>
      </tr>
    </thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
  <details>
    <summary>Raw technical appendices</summary>
  <h2>Threshold Registry</h2>
  <pre>{html_escape(json.dumps(result.threshold_registry, indent=2))}</pre>
  <h2>Model Card</h2>
  <pre>{html_escape(json.dumps(result.model_card, indent=2))}</pre>
  <h2>QSAR Validation</h2>
  <pre>{html_escape(json.dumps(result.validation_report, indent=2))}</pre>
  <h2>Critic Redesign Report</h2>
  <pre>{html_escape(json.dumps(result.redesign_report, indent=2))}</pre>
  <h2>Library Screening Report</h2>
  <pre>{html_escape(json.dumps(result.library_report, indent=2))}</pre>
  <h2>Class-Level Clinical/Regulatory Risk Checklist</h2>
  <ul>{''.join(f'<li><b>{html_escape(r.get("risk", ""))}</b>: {html_escape(r.get("interpretation", ""))}</li>' for r in result.evidence.regulatory_risks)}</ul>
  <h2>Tool Trace</h2>
  <pre>{html_escape(json.dumps([log.to_dict() for log in result.tool_logs], indent=2))}</pre>
  <h2>Evaluation Report</h2>
  <pre>{html_escape(json.dumps(result.evaluation_report, indent=2))}</pre>
  </details>
</main>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")
    return str(path)
