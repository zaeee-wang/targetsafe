import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  Activity,
  AlertTriangle,
  BrainCircuit,
  Cpu,
  Download,
  FileText,
  GitBranch,
  Loader2,
  Network,
  Play,
  ShieldCheck,
  TestTube2,
  Zap
} from "lucide-react";
import { createRun, fetchProfiles } from "./api";
import type { Candidate, ConformerPayload, EvidenceGraph, PipelineResult, RunRequest, Status } from "./types";

const DEFAULT_REQUEST: RunRequest = {
  disease: "EGFR mutation-positive NSCLC",
  target: "EGFR",
  seed_smiles: "COc1cc2ncnc(Nc3ccc(F)c(Cl)c3)c2cc1OCCCN1CCOCC1",
  optimization_goal: "Maintain drug-likeness, reduce toxicity alerts, preserve EGFR evidence confidence",
  candidate_count: 60,
  compute_profile: "cpu-demo",
  allow_network: false,
  use_llm: false,
  use_gpu: false,
  enable_conformers: true
};

const STATUS_ORDER: Status[] = ["Go", "Hold", "No-Go"];

export default function App() {
  const [request, setRequest] = useState<RunRequest>(DEFAULT_REQUEST);
  const [profiles, setProfiles] = useState<Array<Record<string, unknown>>>([]);
  const [result, setResult] = useState<PipelineResult | null>(null);
  const [selectedId, setSelectedId] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    fetchProfiles()
      .then(setProfiles)
      .catch(() => {
        setProfiles([
          { id: "cpu-demo", label: "CPU demo", description: "Stable offline demo." },
          { id: "cpu-evidence", label: "CPU evidence-grade", description: "Live public evidence refresh." },
          { id: "gpu-accelerated", label: "GPU accelerated", description: "Optional GPU retrieval and uncertainty." },
          { id: "api-assisted", label: "API assisted", description: "Optional LLM graph-grounded summary." },
          { id: "full-research", label: "Full research mode", description: "Live evidence, GPU, and API support." }
        ]);
      });
  }, []);

  const selected = useMemo(() => {
    if (!result?.candidates.length) return null;
    return result.candidates.find((candidate) => candidate.candidate_id === selectedId) ?? result.candidates[0];
  }, [result, selectedId]);

  const counts = useMemo(() => {
    const seed: Record<Status, number> = { Go: 0, Hold: 0, "No-Go": 0, Unscored: 0 };
    for (const candidate of result?.candidates ?? []) {
      const status = candidate.decision?.final_status ?? "Unscored";
      seed[status] += 1;
    }
    return seed;
  }, [result]);

  async function runTriage(profileOverride?: string) {
    const nextRequest = profileOverride ? { ...request, compute_profile: profileOverride } : request;
    if (profileOverride && request.compute_profile !== profileOverride) {
      setRequest(nextRequest);
    }
    setLoading(true);
    setError("");
    try {
      const payload = await createRun(nextRequest);
      setResult(payload);
      setSelectedId(payload.candidates[0]?.candidate_id ?? "");
      window.setTimeout(() => {
        document.querySelector(".twin-layout")?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 80);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Target-SAFE run failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="topbar" aria-label="Target-SAFE run controls">
        <div className="brand-lockup">
          <div className="brand-mark"><Activity size={20} /></div>
          <div>
            <p className="eyebrow">Target-SAFE</p>
            <h1>Molecular Evidence Digital Twin</h1>
          </div>
        </div>
        <div className="run-actions">
          <select
            value={request.compute_profile}
            aria-label="Compute profile"
            onChange={(event) => setRequest({ ...request, compute_profile: event.target.value })}
          >
            {profiles.map((profile) => (
              <option key={String(profile.id)} value={String(profile.id)}>
                {String(profile.label)}
              </option>
            ))}
          </select>
          <button className="primary-action" onClick={() => runTriage()} disabled={loading}>
            {loading ? <Loader2 className="spin" size={17} /> : <Play size={17} />}
            Run triage
          </button>
        </div>
      </section>

      <section className="hero-guide" aria-label="How to use Target-SAFE">
        <div className="hero-copy">
          <p className="eyebrow">Evidence-gated lead triage</p>
          <h2>Pick a compute profile, run triage, inspect the molecular twin.</h2>
          <p>
            Start with CPU demo for a stable walkthrough. The system generates EGFR lead candidates,
            checks descriptor risks, estimates target fit, and explains each Go/Hold/No-Go decision.
          </p>
          <div className="hero-actions">
            <button className="primary-action hero-run" onClick={() => runTriage("cpu-demo")} disabled={loading}>
              {loading ? <Loader2 className="spin" size={17} /> : <Play size={17} />}
              Run CPU demo
            </button>
            <span>Then click a molecule card to review structure, 3D layout, evidence, and next validation.</span>
          </div>
        </div>
        <div className="guide-steps" aria-label="Workflow">
          <div><strong>1</strong><span>Select profile</span><small>CPU, GPU, API, or full research mode</small></div>
          <div><strong>2</strong><span>Run triage</span><small>Generate candidates and evidence graph</small></div>
          <div><strong>3</strong><span>Inspect twin</span><small>2D structure, 3D model, risk, and rationale</small></div>
        </div>
      </section>

      <section className="mission-grid">
        <div className="setup-panel">
          <label>
            Disease
            <input value={request.disease} onChange={(event) => setRequest({ ...request, disease: event.target.value })} />
          </label>
          <label>
            Target
            <input value={request.target} onChange={(event) => setRequest({ ...request, target: event.target.value })} />
          </label>
          <label className="wide">
            Seed SMILES
            <textarea
              value={request.seed_smiles}
              onChange={(event) => setRequest({ ...request, seed_smiles: event.target.value })}
            />
          </label>
          <label className="wide">
            Optimization goal
            <textarea
              value={request.optimization_goal}
              onChange={(event) => setRequest({ ...request, optimization_goal: event.target.value })}
            />
          </label>
          <div className="control-row">
            <label>
              Candidates
              <input
                type="number"
                min={20}
                max={120}
                value={request.candidate_count}
                onChange={(event) => setRequest({ ...request, candidate_count: Number(event.target.value) })}
              />
            </label>
            <Toggle label="Live APIs" value={request.allow_network} onChange={(allow_network) => setRequest({ ...request, allow_network })} />
            <Toggle label="GPU" value={request.use_gpu} onChange={(use_gpu) => setRequest({ ...request, use_gpu })} />
            <Toggle label="LLM" value={request.use_llm} onChange={(use_llm) => setRequest({ ...request, use_llm })} />
          </div>
        </div>

        <div className="run-summary">
          <Metric icon={<TestTube2 />} label="Disease / target" value={`${request.disease} / ${request.target}`} />
          <Metric icon={<Cpu />} label="Compute profile" value={String(result?.compute_profile?.label ?? profileLabel(profiles, request.compute_profile))} />
          <Metric icon={<ShieldCheck />} label="Evidence completeness" value={selected ? percent(selected.molecular_twin?.evidence_completeness) : "Run pending"} />
          <div className="status-strip">
            {STATUS_ORDER.map((status) => (
              <div className={`status-pill ${statusClass(status)}`} key={status}>
                <span>{status}</span>
                <strong>{counts[status]}</strong>
              </div>
            ))}
          </div>
          {error && <div className="error-box">{error}</div>}
        </div>
      </section>

      <section className="twin-layout">
        <MoleculeCatalog result={result} selectedId={selected?.candidate_id ?? ""} onSelect={setSelectedId} />
        <CandidateTwin candidate={selected} graph={result?.evidence_graph ?? null} />
      </section>

      <section className="lower-grid">
        <EvidenceGraphView graph={result?.evidence_graph ?? null} selected={selected} />
        <TracePanel result={result} />
        <ModelCardPanel result={result} />
      </section>
    </main>
  );
}

function Toggle({ label, value, onChange }: { label: string; value: boolean; onChange: (value: boolean) => void }) {
  return (
    <button className={`toggle ${value ? "on" : ""}`} onClick={() => onChange(!value)} type="button">
      <span>{label}</span>
      <i />
    </button>
  );
}

function Metric({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="metric">
      <span className="metric-icon">{icon}</span>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function MoleculeCatalog({ result, selectedId, onSelect }: { result: PipelineResult | null; selectedId: string; onSelect: (id: string) => void }) {
  const candidates = result?.candidates ?? [];
  return (
    <section className="candidate-board" aria-label="Molecule catalog">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Molecule catalog</p>
          <h2>Candidate structures</h2>
        </div>
        <span>{candidates.length || 0} molecules</span>
      </div>
      {candidates.length === 0 ? (
        <div className="catalog-empty">
          <Network size={26} />
          <strong>No run yet</strong>
          <span>Use Run triage to populate known references, generated analogs, and controls.</span>
        </div>
      ) : (
        <div className="molecule-grid">
          {candidates.slice(0, 18).map((candidate) => (
            <button
              className={`molecule-card ${selectedId === candidate.candidate_id ? "selected" : ""}`}
              onClick={() => onSelect(candidate.candidate_id)}
              key={candidate.candidate_id}
            >
              <span className={`mini-status ${statusClass(candidate.decision?.final_status ?? "Unscored")}`}>
                {candidate.decision?.final_status ?? "Unscored"}
              </span>
              <span className="molecule-thumb">
                {candidate.structure_svg ? <img src={candidate.structure_svg} alt="" /> : <i>No structure</i>}
              </span>
              <strong>{candidate.candidate_id}</strong>
              <small>lower pChEMBL {formatNumber(candidate.prediction_interval?.lower, 2)}</small>
              <small>AD {formatNumber(candidate.applicability_score, 2)} · {candidate.source.replaceAll("_", " ")}</small>
            </button>
          ))}
        </div>
      )}
      <div className="catalog-legend">
        <span className="status-go">Go</span>
        <span className="status-hold">Hold</span>
        <span className="status-nogo">No-Go</span>
      </div>
    </section>
  );
}

function CandidateTwin({ candidate, graph }: { candidate: Candidate | null; graph: EvidenceGraph | null }) {
  if (!candidate) {
    return (
      <section className="candidate-twin empty-state">
        <Network size={34} />
        <h2>Run a triage to build the first molecular twin.</h2>
        <p>The dashboard will connect structure, predicted target fit, risk flags, evidence, and next validation.</p>
      </section>
    );
  }
  const decision = candidate.decision;
  const desc = candidate.descriptors;
  return (
    <section className="candidate-twin">
      <div className="twin-header">
        <div>
          <p className="eyebrow">Candidate twin</p>
          <h2>{candidate.candidate_id}</h2>
        </div>
        <span className={`decision-badge ${statusClass(decision?.final_status ?? "Unscored")}`}>
          {decision?.final_status ?? "Unscored"}
        </span>
      </div>
      <div className="twin-grid">
        <div className="molecule-panel">
          <div className="panel-kicker">Molecular Identity</div>
          <div className="molecule-stage">
            {candidate.structure_svg ? <img src={candidate.structure_svg} alt={`${candidate.candidate_id} 2D structure`} /> : <span>No 2D depiction</span>}
          </div>
          <div className="structure-caption">
            <strong>2D structure</strong>
            <span>{desc?.method === "rdkit" ? "RDKit depiction" : "SMILES schematic fallback"}</span>
          </div>
          <ConformerView conformer={candidate.conformer} />
        </div>
        <div className="decision-core">
          <h3>Why this decision</h3>
          <ul className="reason-list">
            {(decision?.reasons ?? ["Run pending."]).slice(0, 4).map((reason) => <li key={reason}>{reason}</li>)}
          </ul>
          <div className="interval-band" aria-label="Predicted activity interval">
            <span style={{ width: `${boundedPercent(candidate.prediction_interval?.lower, 10)}%` }} />
            <strong>{formatNumber(candidate.prediction_interval?.lower, 2)} lower pChEMBL</strong>
          </div>
          <div className="criteria-grid">
            {Object.entries(decision?.criteria ?? {}).map(([key, value]) => (
              <div className={`criterion ${value}`} key={key}>
                <span>{labelize(key)}</span>
                <strong>{value}</strong>
              </div>
            ))}
          </div>
        </div>
        <div className="status-rails">
          <Rail icon={<BrainCircuit />} label="Target fit" value={formatNumber(candidate.predicted_activity, 2)} detail={`AD ${formatNumber(candidate.applicability_score, 2)}`} />
          <Rail icon={<ShieldCheck />} label="QED / SA" value={`${formatNumber(desc?.qed, 2)} / ${formatNumber(desc?.sa_score, 2)}`} detail={`${desc?.method ?? "unknown"} descriptors`} />
          <Rail icon={<AlertTriangle />} label="Alerts" value={`${desc?.alerts?.length ?? 0}`} detail={(desc?.severe_alerts?.length ?? 0) ? "severe blocker present" : "review if nonzero"} />
          <Rail icon={<GitBranch />} label="Evidence graph" value={`${graph?.summary?.node_count ?? 0} nodes`} detail={`${candidate.evidence_node_ids.length} linked nodes`} />
        </div>
      </div>
      <div className="twin-footer">
        <div>
          <h3>Nearest analogs</h3>
          <div className="analog-list">
            {candidate.nearest_analogs.slice(0, 3).map((analog) => (
              <span key={`${analog.name}-${analog.similarity}`}>{analog.name} · sim {formatNumber(analog.similarity, 2)}</span>
            ))}
          </div>
        </div>
        <div>
          <h3>Next validation</h3>
          <ul className="compact-list">
            {(decision?.follow_up ?? []).slice(0, 3).map((item) => <li key={item}>{item}</li>)}
          </ul>
        </div>
      </div>
    </section>
  );
}

function ConformerView({ conformer }: { conformer: ConformerPayload | null }) {
  const atoms = (conformer?.atoms ?? []).slice(0, 34);
  const bonds = (conformer?.bonds ?? []).slice(0, 42);
  if (!conformer?.available || atoms.length === 0) {
    return (
      <div className="conformer-view unavailable">
        <div className="conformer-label">3D model</div>
        {conformer?.message ?? "Computed conformer unavailable."}
      </div>
    );
  }
  const xs = atoms.map((atom) => atom.x);
  const ys = atoms.map((atom) => atom.y);
  const zs = atoms.map((atom) => atom.z);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const minZ = Math.min(...zs), maxZ = Math.max(...zs);
  const project = (index: number) => {
    const atom = atoms.find((item) => item.index === index) ?? atoms[0];
    const x = normalize(atom.x, minX, maxX) * 210 + 25 + normalize(atom.z, minZ, maxZ) * 16;
    const y = normalize(atom.y, minY, maxY) * 112 + 20 - normalize(atom.z, minZ, maxZ) * 14;
    return { x, y, z: normalize(atom.z, minZ, maxZ), element: atom.element };
  };
  return (
    <div className="conformer-view">
      <div className="conformer-label">3D model · {conformer.label}</div>
      <svg viewBox="0 0 260 160" role="img" aria-label="Computed conformer">
        {bonds.map((bond, index) => {
          const a = project(bond.begin);
          const b = project(bond.end);
          return <line key={index} x1={a.x} y1={a.y} x2={b.x} y2={b.y} strokeWidth={1.4 + bond.order * 0.5} />;
        })}
        {atoms.map((atom) => {
          const point = project(atom.index);
          return (
            <g key={atom.index}>
              <circle cx={point.x} cy={point.y} r={atom.element === "H" ? 3 : 5.2 + point.z * 2.8} className={`atom atom-${atom.element}`} />
              {atom.element !== "H" && <text x={point.x} y={point.y + 2}>{atom.element}</text>}
            </g>
          );
        })}
      </svg>
      <small>{conformer.message}</small>
    </div>
  );
}

function EvidenceGraphView({ graph, selected }: { graph: EvidenceGraph | null; selected: Candidate | null }) {
  const nodes = (graph?.nodes ?? []).slice(0, 40);
  const edges = (graph?.edges ?? []).slice(0, 80);
  const selectedSet = new Set(selected?.evidence_node_ids ?? []);
  return (
    <section className="evidence-graph-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">GraphRAG-lite</p>
          <h2>Evidence graph</h2>
        </div>
        <span>{graph ? `${graph.summary.node_count} nodes` : "Run pending"}</span>
      </div>
      <div className="graph-canvas">
        {nodes.length ? (
          <svg viewBox="0 0 720 360" role="img" aria-label="Evidence graph">
            {edges.map((edge, index) => {
              const sourceIndex = nodes.findIndex((node) => node.id === edge.source);
              const targetIndex = nodes.findIndex((node) => node.id === edge.target);
              if (sourceIndex < 0 || targetIndex < 0) return null;
              const source = graphPoint(sourceIndex, nodes.length);
              const target = graphPoint(targetIndex, nodes.length);
              return <line key={index} x1={source.x} y1={source.y} x2={target.x} y2={target.y} className={`edge ${edge.type}`} />;
            })}
            {nodes.map((node, index) => {
              const point = graphPoint(index, nodes.length);
              return (
                <g key={node.id} className={selectedSet.has(node.id) ? "active-node" : ""}>
                  <circle cx={point.x} cy={point.y} r={node.type === "candidate" ? 12 : 8} className={`node ${node.type}`} />
                  <text x={point.x + 12} y={point.y + 4}>{String(node.label ?? node.type).slice(0, 28)}</text>
                </g>
              );
            })}
          </svg>
        ) : (
          <div className="empty-inline">Run triage to build the evidence graph.</div>
        )}
      </div>
    </section>
  );
}

function TracePanel({ result }: { result: PipelineResult | null }) {
  return (
    <section className="trace-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Agent trace</p>
          <h2>Plan and tools</h2>
        </div>
        <Zap size={18} />
      </div>
      <ol className="trace-list">
        {(result?.plan ?? ["Run triage to create an agent trace."]).map((step) => <li key={step}>{step}</li>)}
      </ol>
      <div className="tool-log-list">
        {(result?.tool_logs ?? []).slice(0, 6).map((log, index) => (
          <div key={index}>
            <span>{String(log.source)}</span>
            <strong>{String(log.status)}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}

function ModelCardPanel({ result }: { result: PipelineResult | null }) {
  return (
    <section className="model-card-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Model card</p>
          <h2>EGFR QSAR context</h2>
        </div>
        <FileText size={18} />
      </div>
      <dl className="model-dl">
        <dt>Model</dt>
        <dd>{String(result?.model_card?.model_id ?? "Run pending")}</dd>
        <dt>Training size</dt>
        <dd>{String(result?.model_card?.training_size ?? "-")}</dd>
        <dt>Applicability</dt>
        <dd>{String((result?.model_card?.applicability_domain as Record<string, unknown> | undefined)?.method ?? "-")}</dd>
      </dl>
      {result?.run_id && (
        <a className="download-link" href={`/api/runs/${result.run_id}/report`} target="_blank" rel="noreferrer">
          <Download size={16} />
          Open HTML report
        </a>
      )}
    </section>
  );
}

function Rail({ icon, label, value, detail }: { icon: ReactNode; label: string; value: string; detail: string }) {
  return (
    <div className="rail">
      <span>{icon}</span>
      <div>
        <small>{label}</small>
        <strong>{value}</strong>
        <em>{detail}</em>
      </div>
    </div>
  );
}

function graphPoint(index: number, total: number) {
  const radiusX = 285;
  const radiusY = 132;
  const angle = (index / Math.max(total, 1)) * Math.PI * 2;
  const ring = index % 5 === 0 ? 0.62 : 1;
  return { x: 360 + Math.cos(angle) * radiusX * ring, y: 180 + Math.sin(angle) * radiusY * ring };
}

function normalize(value: number, min: number, max: number) {
  if (max - min < 0.001) return 0.5;
  return (value - min) / (max - min);
}

function statusClass(status: Status | string) {
  if (status === "Go") return "status-go";
  if (status === "No-Go") return "status-nogo";
  return "status-hold";
}

function labelize(value: string) {
  return value.replaceAll("_", " ");
}

function percent(value: unknown) {
  if (typeof value !== "number") return "Run pending";
  return `${Math.round(value * 100)}%`;
}

function boundedPercent(value: number | undefined, max: number) {
  if (typeof value !== "number") return 0;
  return Math.max(0, Math.min(100, (value / max) * 100));
}

function formatNumber(value: number | null | undefined, digits = 2) {
  if (typeof value !== "number" || Number.isNaN(value)) return "-";
  return value.toFixed(digits);
}

function profileLabel(profiles: Array<Record<string, unknown>>, id: string) {
  const profile = profiles.find((item) => item.id === id);
  return String(profile?.label ?? id);
}
