from __future__ import annotations

import json
from pathlib import Path

from targetsafe.pipeline import PipelineConfig, run_pipeline


DEFAULT_DISEASE = "EGFR mutation-positive NSCLC"
DEFAULT_TARGET = "EGFR"
DEFAULT_SEED = "COc1cc2ncnc(Nc3ccc(F)c(Cl)c3)c2cc1OCCCN1CCOCC1"
DEFAULT_GOAL = "Maintain drug-likeness, reduce toxicity alerts, preserve EGFR evidence confidence"


def _run_cli() -> None:
    config = PipelineConfig(
        disease=DEFAULT_DISEASE,
        target=DEFAULT_TARGET,
        seed_smiles=DEFAULT_SEED,
        optimization_goal=DEFAULT_GOAL,
        candidate_count=60,
        allow_network=False,
        output_dir=Path("outputs"),
    )
    result = run_pipeline(config)
    print("Target-SAFE CLI demo")
    print("====================")
    print(f"Run ID: {result.run_id}")
    print(f"Candidates: {len(result.candidates)}")
    counts = {}
    for candidate in result.candidates:
        status = candidate.decision.final_status if candidate.decision else "Unscored"
        counts[status] = counts.get(status, 0) + 1
    print("Status counts:", counts)
    print(f"HTML report: {result.report_path}")
    print("Top candidates:")
    for candidate in result.candidates[:8]:
        decision = candidate.decision
        score = f"{decision.total_score:.3f}" if decision else "0.000"
        status = decision.final_status if decision else "NA"
        print(
            f"- {candidate.candidate_id}: {status} "
            f"score={score} smiles={candidate.smiles}"
        )


def _render_streamlit() -> None:
    import streamlit as st

    st.set_page_config(page_title="Target-SAFE Lead Agent", layout="wide")
    st.title("Target-SAFE Lead Agent")
    st.caption("Evidence-gated Go/Hold/No-Go triage for EGFR lead candidates")

    with st.sidebar:
        st.header("Input")
        disease = st.text_input("Disease", DEFAULT_DISEASE)
        target = st.text_input("Target", DEFAULT_TARGET)
        seed_smiles = st.text_area("Seed SMILES", DEFAULT_SEED, height=80)
        optimization_goal = st.text_area("Optimization goal", DEFAULT_GOAL, height=90)
        candidate_count = st.slider("Candidate count", 20, 120, 60, step=10)
        allow_network = st.toggle("Use public APIs", value=False)
        use_llm = st.toggle("Use optional LLM", value=False)
        run = st.button("Run triage", type="primary")

    if not run:
        st.info("Configure the inputs, then run triage.")
        return

    config = PipelineConfig(
        disease=disease,
        target=target,
        seed_smiles=seed_smiles,
        optimization_goal=optimization_goal,
        candidate_count=candidate_count,
        allow_network=allow_network,
        use_llm=use_llm,
        output_dir=Path("outputs"),
    )
    with st.spinner("Running Target-SAFE pipeline..."):
        result = run_pipeline(config)

    status_counts = {}
    for candidate in result.candidates:
        status = candidate.decision.final_status if candidate.decision else "Unscored"
        status_counts[status] = status_counts.get(status, 0) + 1

    cols = st.columns(4)
    cols[0].metric("Candidates", len(result.candidates))
    cols[1].metric("Go", status_counts.get("Go", 0))
    cols[2].metric("Hold", status_counts.get("Hold", 0))
    cols[3].metric("No-Go", status_counts.get("No-Go", 0))

    st.subheader("Agent Plan")
    st.write(result.plan)

    st.subheader("Decision Table")
    rows = []
    for c in result.candidates:
        d = c.decision
        descriptors = c.descriptors
        rows.append(
            {
                "id": c.candidate_id,
                "status": d.final_status if d else "",
                "score": round(d.total_score, 3) if d else None,
                "activity": round(c.predicted_activity, 3) if c.predicted_activity else None,
                "confidence": round(c.evidence_confidence, 3),
                "in_domain": c.in_applicability_domain,
                "QED": round(descriptors.qed, 3) if descriptors else None,
                "MW": round(descriptors.molecular_weight, 1) if descriptors else None,
                "LogP": round(descriptors.logp, 2) if descriptors else None,
                "TPSA": round(descriptors.tpsa, 1) if descriptors else None,
                "SA": round(descriptors.sa_score, 2) if descriptors else None,
                "alerts": len(descriptors.alerts) if descriptors else None,
                "smiles": c.smiles,
            }
        )
    st.dataframe(rows, use_container_width=True)

    st.subheader("Candidate Details")
    for c in result.candidates[:10]:
        d = c.decision
        with st.expander(f"{c.candidate_id} - {d.final_status if d else 'Unscored'}"):
            st.code(c.smiles)
            if c.structure_svg:
                st.image(c.structure_svg)
            st.json(c.to_public_dict())

    st.subheader("Tool Calls")
    st.dataframe([log.to_dict() for log in result.tool_logs], use_container_width=True)

    st.subheader("Reports")
    if result.report_path and Path(result.report_path).exists():
        report_text = Path(result.report_path).read_text(encoding="utf-8")
        st.download_button(
            "Download HTML report",
            report_text,
            file_name=Path(result.report_path).name,
            mime="text/html",
        )
    st.download_button(
        "Download JSON result",
        json.dumps(result.to_public_dict(), indent=2),
        file_name=f"{result.run_id}.json",
        mime="application/json",
    )


if __name__ == "__main__":
    try:
        import streamlit  # noqa: F401
    except Exception:
        _run_cli()
    else:
        _render_streamlit()
