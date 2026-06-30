import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  BrainCircuit,
  Cpu,
  Download,
  FileText,
  GitBranch,
  Layers3,
  Loader2,
  Maximize2,
  Network,
  Play,
  RotateCcw,
  Search,
  ShieldCheck,
  TestTube2,
  ZoomIn,
  ZoomOut
} from "lucide-react";
import { createRun, fetchKnownContext, fetchProfiles, fetchReferenceDrugs } from "./api";
import type {
  Candidate,
  ConformerPayload,
  EvidenceGraph,
  KnownContext,
  PipelineResult,
  ReferenceDrug,
  RunRequest,
  Status
} from "./types";

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
const VIEWS = [
  { id: "console", label: "Run Console", icon: <Activity size={18} /> },
  { id: "atlas", label: "Molecule Atlas", icon: <Layers3 size={18} /> },
  { id: "twin", label: "Candidate Twin", icon: <BrainCircuit size={18} /> },
  { id: "graph", label: "Evidence Graph", icon: <GitBranch size={18} /> },
  { id: "known", label: "Known Drugs & Risks", icon: <ShieldCheck size={18} /> },
  { id: "reports", label: "Reports", icon: <FileText size={18} /> }
] as const;

type ViewId = (typeof VIEWS)[number]["id"];
type MoleculeView = "2d" | "3d";

export default function App() {
  const [request, setRequest] = useState<RunRequest>(DEFAULT_REQUEST);
  const [profiles, setProfiles] = useState<Array<Record<string, unknown>>>([]);
  const [referenceDrugs, setReferenceDrugs] = useState<ReferenceDrug[]>([]);
  const [result, setResult] = useState<PipelineResult | null>(null);
  const [selectedId, setSelectedId] = useState<string>("");
  const [activeView, setActiveView] = useState<ViewId>("console");
  const [moleculeView, setMoleculeView] = useState<MoleculeView>("2d");
  const [knownContext, setKnownContext] = useState<KnownContext | null>(null);
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
    fetchReferenceDrugs().then(setReferenceDrugs).catch(() => setReferenceDrugs([]));
  }, []);

  const selected = useMemo(() => {
    if (!result?.candidates.length) return null;
    return result.candidates.find((candidate) => candidate.candidate_id === selectedId) ?? result.candidates[0];
  }, [result, selectedId]);

  useEffect(() => {
    if (!result?.run_id || !selected?.candidate_id) {
      setKnownContext(null);
      return;
    }
    fetchKnownContext(result.run_id, selected.candidate_id)
      .then(setKnownContext)
      .catch(() => setKnownContext(null));
  }, [result?.run_id, selected?.candidate_id]);

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
    if (profileOverride && request.compute_profile !== profileOverride) setRequest(nextRequest);
    setLoading(true);
    setError("");
    try {
      const payload = await createRun(nextRequest);
      setResult(payload);
      setSelectedId(payload.candidates[0]?.candidate_id ?? "");
      setMoleculeView("2d");
      setActiveView("atlas");
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Target-SAFE run failed.");
    } finally {
      setLoading(false);
    }
  }

  function selectCandidate(id: string, view: ViewId = "twin") {
    setSelectedId(id);
    setActiveView(view);
  }

  return (
    <main className="app-shell">
      <NavRail activeView={activeView} onChange={setActiveView} result={result} />
      <section className="workspace">
        <TopCommand
          request={request}
          profiles={profiles}
          loading={loading}
          onRequestChange={setRequest}
          onRun={() => runTriage()}
        />
        {activeView === "console" && (
          <RunConsole
            request={request}
            profiles={profiles}
            result={result}
            counts={counts}
            loading={loading}
            error={error}
            onRequestChange={setRequest}
            onRun={runTriage}
          />
        )}
        {activeView === "atlas" && (
          <MoleculeAtlas
            result={result}
            selectedId={selected?.candidate_id ?? ""}
            referenceDrugs={referenceDrugs}
            onSelectCandidate={(id) => selectCandidate(id)}
            onOpenKnown={() => setActiveView("known")}
          />
        )}
        {activeView === "twin" && (
          <CandidateTwin
            candidate={selected}
            graph={result?.evidence_graph ?? null}
            moleculeView={moleculeView}
            knownContext={knownContext}
            onMoleculeViewChange={setMoleculeView}
            onOpenGraph={() => setActiveView("graph")}
          />
        )}
        {activeView === "graph" && (
          <EvidenceGraphExplorer
            graph={result?.evidence_graph ?? null}
            selected={selected}
            onSelectCandidate={selectCandidate}
          />
        )}
        {activeView === "known" && (
          <KnownDrugsAndRisks
            referenceDrugs={referenceDrugs}
            result={result}
            selected={selected}
            knownContext={knownContext}
          />
        )}
        {activeView === "reports" && <Reports result={result} />}
      </section>
    </main>
  );
}

function NavRail({
  activeView,
  onChange,
  result
}: {
  activeView: ViewId;
  onChange: (view: ViewId) => void;
  result: PipelineResult | null;
}) {
  return (
    <aside className="nav-rail" aria-label="Target-SAFE sections">
      <div className="brand-block">
        <div className="pulse-mark"><Activity size={18} /></div>
        <div>
          <span>Target-SAFE</span>
          <strong>Molecular Evidence Twin</strong>
        </div>
      </div>
      <nav>
        {VIEWS.map((view) => (
          <button
            key={view.id}
            className={activeView === view.id ? "active" : ""}
            onClick={() => onChange(view.id)}
            type="button"
          >
            {view.icon}
            <span>{view.label}</span>
          </button>
        ))}
      </nav>
      <div className="run-chip">
        <span>{result ? "Run loaded" : "No run yet"}</span>
        <strong>{result?.run_id ?? "CPU demo ready"}</strong>
      </div>
    </aside>
  );
}

function TopCommand({
  request,
  profiles,
  loading,
  onRequestChange,
  onRun
}: {
  request: RunRequest;
  profiles: Array<Record<string, unknown>>;
  loading: boolean;
  onRequestChange: (request: RunRequest) => void;
  onRun: () => void;
}) {
  return (
    <header className="top-command">
      <div>
        <p className="eyebrow">Evidence-gated triage console</p>
        <h1>{request.disease} / {request.target}</h1>
      </div>
      <div className="top-command-actions">
        <select
          value={request.compute_profile}
          aria-label="Compute profile"
          onChange={(event) => onRequestChange({ ...request, compute_profile: event.target.value })}
        >
          {profiles.map((profile) => (
            <option key={String(profile.id)} value={String(profile.id)}>
              {String(profile.label)}
            </option>
          ))}
        </select>
        <button className="primary-action" onClick={onRun} disabled={loading} type="button">
          {loading ? <Loader2 className="spin" size={17} /> : <Play size={17} />}
          Run triage
        </button>
      </div>
    </header>
  );
}

function RunConsole({
  request,
  profiles,
  result,
  counts,
  loading,
  error,
  onRequestChange,
  onRun
}: {
  request: RunRequest;
  profiles: Array<Record<string, unknown>>;
  result: PipelineResult | null;
  counts: Record<Status, number>;
  loading: boolean;
  error: string;
  onRequestChange: (request: RunRequest) => void;
  onRun: (profileOverride?: string) => void;
}) {
  return (
    <section className="view-frame console-view">
      <div className="console-stage">
        <div className="orbital-visual" aria-hidden="true">
          <span />
          <i />
          <b />
        </div>
        <div className="console-copy">
          <p className="eyebrow">Run Console</p>
          <h2>Start with the smallest stable run, then inspect evidence by section.</h2>
          <p>
            This app narrows early EGFR lead candidates with descriptors, model uncertainty,
            graph evidence, and known-drug context. It does not claim candidate safety or clinical efficacy.
          </p>
          <button className="primary-action large" onClick={() => onRun("cpu-demo")} disabled={loading} type="button">
            {loading ? <Loader2 className="spin" size={18} /> : <Play size={18} />}
            Run CPU demo
          </button>
        </div>
      </div>

      <div className="console-grid">
        <section className="input-deck">
          <label>
            Disease
            <input value={request.disease} onChange={(event) => onRequestChange({ ...request, disease: event.target.value })} />
          </label>
          <label>
            Target
            <input value={request.target} onChange={(event) => onRequestChange({ ...request, target: event.target.value })} />
          </label>
          <label className="wide">
            Seed SMILES
            <textarea value={request.seed_smiles} onChange={(event) => onRequestChange({ ...request, seed_smiles: event.target.value })} />
          </label>
          <label className="wide">
            Optimization goal
            <textarea value={request.optimization_goal} onChange={(event) => onRequestChange({ ...request, optimization_goal: event.target.value })} />
          </label>
          <div className="control-row">
            <label>
              Candidates
              <input
                type="number"
                min={20}
                max={120}
                value={request.candidate_count}
                onChange={(event) => onRequestChange({ ...request, candidate_count: Number(event.target.value) })}
              />
            </label>
            <Toggle label="Live APIs" value={request.allow_network} onChange={(allow_network) => onRequestChange({ ...request, allow_network })} />
            <Toggle label="GPU" value={request.use_gpu} onChange={(use_gpu) => onRequestChange({ ...request, use_gpu })} />
            <Toggle label="LLM" value={request.use_llm} onChange={(use_llm) => onRequestChange({ ...request, use_llm })} />
          </div>
        </section>

        <section className="status-deck">
          <Metric icon={<Cpu />} label="Compute profile" value={profileLabel(profiles, request.compute_profile)} />
          <Metric icon={<TestTube2 />} label="Evidence mode" value={request.allow_network ? "Live APIs enabled" : "Cached/fallback demo"} />
          <Metric icon={<Network />} label="Evidence graph" value={result ? `${result.evidence_graph.summary.node_count} nodes` : "Run pending"} />
          <div className="status-strip">
            {STATUS_ORDER.map((status) => (
              <div className={`status-pill ${statusClass(status)}`} key={status}>
                <span>{status}</span>
                <strong>{counts[status]}</strong>
              </div>
            ))}
          </div>
          {error && <div className="error-box">{error}</div>}
        </section>
      </div>
    </section>
  );
}

function MoleculeAtlas({
  result,
  selectedId,
  referenceDrugs,
  onSelectCandidate,
  onOpenKnown
}: {
  result: PipelineResult | null;
  selectedId: string;
  referenceDrugs: ReferenceDrug[];
  onSelectCandidate: (id: string) => void;
  onOpenKnown: () => void;
}) {
  const candidates = result?.candidates ?? [];
  const heroCandidate = candidates[0];
  return (
    <section className="view-frame atlas-view">
      <div className="section-header">
        <div>
          <p className="eyebrow">Molecule Atlas</p>
          <h2>Candidate structures and known EGFR references.</h2>
        </div>
        <button className="ghost-action" onClick={onOpenKnown} type="button">
          <ShieldCheck size={16} />
          Open known risks
        </button>
      </div>

      <div className="atlas-hero">
        <div className="molecule-spotlight">
          {heroCandidate?.structure_svg ? (
            <img src={heroCandidate.structure_svg} alt={`${heroCandidate.candidate_id} structure`} />
          ) : (
            <div className="empty-inline">Run triage to populate molecular figures.</div>
          )}
        </div>
        <div className="atlas-note">
          <span>Primary candidate</span>
          <strong>{heroCandidate?.candidate_id ?? "No candidate yet"}</strong>
          <p>
            Large molecular figures are the first inspection surface. Decision evidence lives in the twin and graph views,
            not in a crowded landing page.
          </p>
        </div>
      </div>

      <div className="atlas-columns">
        <section>
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Generated and control set</p>
              <h3>{candidates.length || 0} molecules</h3>
            </div>
          </div>
          {candidates.length === 0 ? (
            <EmptyPanel icon={<Search />} title="No run yet" text="Use Run Console to create the first candidate atlas." />
          ) : (
            <div className="molecule-grid">
              {candidates.slice(0, 24).map((candidate) => (
                <button
                  className={`molecule-card ${selectedId === candidate.candidate_id ? "selected" : ""}`}
                  onClick={() => onSelectCandidate(candidate.candidate_id)}
                  key={candidate.candidate_id}
                  type="button"
                >
                  <span className={`mini-status ${statusClass(candidate.decision?.final_status ?? "Unscored")}`}>
                    {candidate.decision?.final_status ?? "Unscored"}
                  </span>
                  <span className="molecule-thumb">
                    {candidate.structure_svg ? <img src={candidate.structure_svg} alt="" /> : <i>No structure</i>}
                  </span>
                  <strong>{candidate.candidate_id}</strong>
                  <small>lower pChEMBL {formatNumber(candidate.prediction_interval?.lower, 2)}</small>
                  <small>AD {formatNumber(candidate.applicability_score, 2)} / {candidate.source.replaceAll("_", " ")}</small>
                </button>
              ))}
            </div>
          )}
        </section>

        <section>
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Reference library</p>
              <h3>Known EGFR drugs</h3>
            </div>
          </div>
          <div className="reference-list">
            {referenceDrugs.map((drug) => (
              <article className="reference-card" key={drug.drug_id}>
                <div className="reference-structure">
                  {drug.structure_svg ? <img src={drug.structure_svg} alt={`${drug.name} structure`} /> : <span>No figure</span>}
                </div>
                <div>
                  <strong>{drug.name}</strong>
                  <span>{drug.chembl_id} / PubChem {drug.pubchem_cid}</span>
                  <p>{drug.context}</p>
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>
    </section>
  );
}

function CandidateTwin({
  candidate,
  graph,
  moleculeView,
  knownContext,
  onMoleculeViewChange,
  onOpenGraph
}: {
  candidate: Candidate | null;
  graph: EvidenceGraph | null;
  moleculeView: MoleculeView;
  knownContext: KnownContext | null;
  onMoleculeViewChange: (view: MoleculeView) => void;
  onOpenGraph: () => void;
}) {
  if (!candidate) {
    return (
      <section className="view-frame">
        <EmptyPanel icon={<BrainCircuit />} title="No candidate twin yet" text="Run triage, then select a molecule from the atlas." />
      </section>
    );
  }
  const decision = candidate.decision;
  const desc = candidate.descriptors;
  return (
    <section className="view-frame twin-view">
      <div className="section-header">
        <div>
          <p className="eyebrow">Candidate Twin</p>
          <h2>{candidate.candidate_id}</h2>
        </div>
        <span className={`decision-badge ${statusClass(decision?.final_status ?? "Unscored")}`}>{decision?.final_status ?? "Unscored"}</span>
      </div>

      <div className="twin-stage-grid">
        <section className="visual-stage">
          <div className="stage-tabs">
            <button className={moleculeView === "2d" ? "active" : ""} onClick={() => onMoleculeViewChange("2d")} type="button">2D structure</button>
            <button className={moleculeView === "3d" ? "active" : ""} onClick={() => onMoleculeViewChange("3d")} type="button">3D conformer</button>
          </div>
          {moleculeView === "2d" ? (
            <div className="structure-stage">
              {candidate.structure_svg ? <img src={candidate.structure_svg} alt={`${candidate.candidate_id} 2D structure`} /> : <span>No 2D depiction</span>}
            </div>
          ) : (
            <InteractiveConformerView conformer={candidate.conformer} />
          )}
          <p className="viewer-warning">
            3D view is a computed conformer for spatial inspection, not a validated binding pose.
          </p>
        </section>

        <section className="decision-stage">
          <div className="why-block">
            <h3>Why this decision</h3>
            <ul>
              {(decision?.reasons ?? ["Run pending."]).slice(0, 5).map((reason) => <li key={reason}>{reason}</li>)}
            </ul>
          </div>
          <div className="criteria-grid">
            {Object.entries(decision?.criteria ?? {}).map(([key, value]) => (
              <div className={`criterion ${value}`} key={key}>
                <span>{labelize(key)}</span>
                <strong>{value}</strong>
              </div>
            ))}
          </div>
          <button className="ghost-action" onClick={onOpenGraph} type="button">
            <GitBranch size={16} />
            Inspect graph evidence
          </button>
        </section>

        <aside className="status-rails">
          <Rail icon={<BrainCircuit />} label="Target fit" value={formatNumber(candidate.predicted_activity, 2)} detail={`AD ${formatNumber(candidate.applicability_score, 2)}`} />
          <Rail icon={<ShieldCheck />} label="QED / SA" value={`${formatNumber(desc?.qed, 2)} / ${formatNumber(desc?.sa_score, 2)}`} detail={`${desc?.method ?? "unknown"} descriptors`} />
          <Rail icon={<AlertTriangle />} label="Alerts" value={`${desc?.alerts?.length ?? 0}`} detail={(desc?.severe_alerts?.length ?? 0) ? "severe blocker present" : "review if nonzero"} />
          <Rail icon={<GitBranch />} label="Evidence graph" value={`${graph?.summary?.node_count ?? 0} nodes`} detail={`${candidate.evidence_node_ids.length} linked nodes`} />
        </aside>
      </div>

      <div className="twin-detail-grid">
        <section className="detail-block">
          <h3>Known-drug context</h3>
          <p className="context-note">{knownContext?.interpretation ?? "Known-drug context loads after a run."}</p>
          <div className="analog-list">
            {(knownContext?.nearest_known_drugs ?? []).slice(0, 4).map((drug) => (
              <span key={drug.drug_id}>{drug.name} / sim {formatNumber(drug.similarity, 2)}</span>
            ))}
          </div>
        </section>
        <section className="detail-block">
          <h3>Next validation</h3>
          <ul className="compact-list">
            {(decision?.follow_up ?? []).slice(0, 4).map((item) => <li key={item}>{item}</li>)}
          </ul>
        </section>
      </div>
    </section>
  );
}

function InteractiveConformerView({ conformer }: { conformer: ConformerPayload | null }) {
  const [angle, setAngle] = useState(22);
  const [zoom, setZoom] = useState(1);
  const atoms = (conformer?.atoms ?? []).slice(0, 64);
  const bonds = (conformer?.bonds ?? []).slice(0, 90);
  if (!conformer?.available || atoms.length === 0) {
    return (
      <div className="conformer-stage unavailable">
        <span>3D conformer unavailable</span>
        <small>{conformer?.message ?? "No conformer payload was returned."}</small>
      </div>
    );
  }

  const projected = projectConformer(atoms, angle, zoom);
  const byIndex = new Map(projected.map((atom) => [atom.index, atom]));
  return (
    <div className="conformer-stage">
      <div className="viewer-controls" aria-label="3D viewer controls">
        <button onClick={() => setAngle((value) => value - 18)} type="button" title="Rotate left"><ArrowLeft size={15} /></button>
        <button onClick={() => setAngle((value) => value + 18)} type="button" title="Rotate right"><ArrowRight size={15} /></button>
        <button onClick={() => setZoom((value) => Math.min(1.8, value + 0.12))} type="button" title="Zoom in"><ZoomIn size={15} /></button>
        <button onClick={() => setZoom((value) => Math.max(0.62, value - 0.12))} type="button" title="Zoom out"><ZoomOut size={15} /></button>
        <button onClick={() => { setAngle(22); setZoom(1); }} type="button" title="Reset view"><RotateCcw size={15} /></button>
      </div>
      <svg viewBox="0 0 760 520" role="img" aria-label="Interactive computed conformer">
        <rect width="760" height="520" rx="26" />
        {bonds.map((bond, index) => {
          const a = byIndex.get(bond.begin);
          const b = byIndex.get(bond.end);
          if (!a || !b) return null;
          return <line key={index} x1={a.x} y1={a.y} x2={b.x} y2={b.y} strokeWidth={1.2 + bond.order * 0.5} />;
        })}
        {projected
          .slice()
          .sort((a, b) => a.depth - b.depth)
          .map((atom) => (
            <g key={atom.index}>
              <circle cx={atom.x} cy={atom.y} r={atom.element === "H" ? 5 : 9 + atom.depth * 4} className={`atom atom-${atom.element}`} />
              {atom.element !== "H" && <text x={atom.x} y={atom.y + 3}>{atom.element}</text>}
            </g>
          ))}
      </svg>
      <small>{conformer.message}</small>
    </div>
  );
}

function EvidenceGraphExplorer({
  graph,
  selected,
  onSelectCandidate
}: {
  graph: EvidenceGraph | null;
  selected: Candidate | null;
  onSelectCandidate: (id: string, view?: ViewId) => void;
}) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [dragStart, setDragStart] = useState<{ x: number; y: number; panX: number; panY: number } | null>(null);
  const [nodeFilter, setNodeFilter] = useState("all");
  const [edgeFilter, setEdgeFilter] = useState("all");

  const nodes = graph?.nodes ?? [];
  const edges = graph?.edges ?? [];
  const nodeTypes = ["all", ...Array.from(new Set(nodes.map((node) => node.type))).sort()];
  const edgeTypes = ["all", ...Array.from(new Set(edges.map((edge) => edge.type))).sort()];
  const visibleNodes = nodeFilter === "all" ? nodes : nodes.filter((node) => node.type === nodeFilter);
  const visibleIds = new Set(visibleNodes.map((node) => node.id));
  const visibleEdges = edges.filter((edge) => {
    const passType = edgeFilter === "all" || edge.type === edgeFilter;
    return passType && visibleIds.has(edge.source) && visibleIds.has(edge.target);
  });
  const layout = useMemo(() => graphLayout(visibleNodes), [visibleNodes]);
  const selectedSet = new Set(selected?.evidence_node_ids ?? []);

  function fitView() {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }

  function centerSelected() {
    if (!selected) return;
    const candidateNode = layout.get(`candidate_${selected.candidate_id}`);
    if (!candidateNode) return;
    setZoom(1.35);
    setPan({ x: 480 - candidateNode.x, y: 290 - candidateNode.y });
  }

  return (
    <section className="view-frame graph-view">
      <div className="section-header">
        <div>
          <p className="eyebrow">GraphRAG-lite evidence explorer</p>
          <h2>Zoomable decision graph.</h2>
        </div>
        <div className="graph-toolbar">
          <select value={nodeFilter} onChange={(event) => setNodeFilter(event.target.value)} aria-label="Node type filter">
            {nodeTypes.map((type) => <option key={type} value={type}>{type}</option>)}
          </select>
          <select value={edgeFilter} onChange={(event) => setEdgeFilter(event.target.value)} aria-label="Edge type filter">
            {edgeTypes.map((type) => <option key={type} value={type}>{type}</option>)}
          </select>
          <button onClick={() => setZoom((value) => Math.min(2.8, value + 0.15))} type="button"><ZoomIn size={16} /></button>
          <button onClick={() => setZoom((value) => Math.max(0.45, value - 0.15))} type="button"><ZoomOut size={16} /></button>
          <button onClick={fitView} type="button"><Maximize2 size={16} /></button>
          <button onClick={centerSelected} type="button"><Search size={16} /></button>
        </div>
      </div>
      <div
        className="graph-stage"
        onWheel={(event) => {
          event.preventDefault();
          setZoom((value) => Math.max(0.45, Math.min(2.8, value + (event.deltaY < 0 ? 0.08 : -0.08))));
        }}
        onMouseDown={(event) => setDragStart({ x: event.clientX, y: event.clientY, panX: pan.x, panY: pan.y })}
        onMouseMove={(event) => {
          if (!dragStart) return;
          setPan({ x: dragStart.panX + event.clientX - dragStart.x, y: dragStart.panY + event.clientY - dragStart.y });
        }}
        onMouseUp={() => setDragStart(null)}
        onMouseLeave={() => setDragStart(null)}
      >
        {visibleNodes.length ? (
          <svg viewBox="0 0 960 580" role="img" aria-label="Zoomable evidence graph">
            <g transform={`translate(${pan.x} ${pan.y}) scale(${zoom})`}>
              {visibleEdges.map((edge, index) => {
                const source = layout.get(edge.source);
                const target = layout.get(edge.target);
                if (!source || !target) return null;
                return <line key={index} x1={source.x} y1={source.y} x2={target.x} y2={target.y} className={`edge ${edge.type}`} />;
              })}
              {visibleNodes.map((node) => {
                const point = layout.get(node.id) ?? { x: 0, y: 0 };
                const label = String(node.label ?? node.type);
                const candidateId = node.id.startsWith("candidate_") ? node.id.replace("candidate_", "") : "";
                return (
                  <g
                    key={node.id}
                    className={selectedSet.has(node.id) ? "active-node" : ""}
                    onDoubleClick={() => candidateId && onSelectCandidate(candidateId, "twin")}
                  >
                    <circle cx={point.x} cy={point.y} r={node.type === "candidate" ? 15 : 10} className={`node ${node.type}`} />
                    <text x={point.x + 16} y={point.y + 5}>{label.slice(0, 30)}</text>
                  </g>
                );
              })}
            </g>
          </svg>
        ) : (
          <EmptyPanel icon={<GitBranch />} title="No graph yet" text="Run triage to build a decision evidence graph." />
        )}
      </div>
    </section>
  );
}

function KnownDrugsAndRisks({
  referenceDrugs,
  result,
  selected,
  knownContext
}: {
  referenceDrugs: ReferenceDrug[];
  result: PipelineResult | null;
  selected: Candidate | null;
  knownContext: KnownContext | null;
}) {
  return (
    <section className="view-frame known-view">
      <div className="section-header">
        <div>
          <p className="eyebrow">Known Drugs & Risks</p>
          <h2>Reference context, not candidate-specific toxicity.</h2>
        </div>
      </div>
      <div className="risk-banner">
        <AlertTriangle size={20} />
        <p>
          Known EGFR TKI adverse reactions and label warnings are used as review context.
          Target-SAFE does not infer that a generated candidate has these adverse events.
        </p>
      </div>
      <div className="known-grid">
        <section className="known-drug-table">
          {referenceDrugs.map((drug) => (
            <article className="known-drug-card" key={drug.drug_id}>
              <div className="known-drug-figure">
                {drug.structure_svg ? <img src={drug.structure_svg} alt={`${drug.name} structure`} /> : <span>No structure</span>}
              </div>
              <div>
                <p className="eyebrow">{drug.chembl_id} / PubChem {drug.pubchem_cid}</p>
                <h3>{drug.name}</h3>
                <p>{drug.activity_evidence}</p>
                <div className="risk-list">
                  {drug.label_risk_context.map((risk) => <span key={risk}>{risk}</span>)}
                </div>
              </div>
            </article>
          ))}
        </section>
        <aside className="known-context-panel">
          <h3>{selected ? `${selected.candidate_id} nearest known drugs` : "Candidate context"}</h3>
          <p>{knownContext?.interpretation ?? "Select a candidate after running triage."}</p>
          <div className="analog-list vertical">
            {(knownContext?.nearest_known_drugs ?? []).map((drug) => (
              <span key={drug.drug_id}>{drug.name} / sim {formatNumber(drug.similarity, 2)}</span>
            ))}
          </div>
          <h3>Evidence status</h3>
          <div className="tool-log-list">
            {(result?.tool_logs ?? []).filter((log) => String(log.source).includes("PubChem") || String(log.source).includes("openFDA")).slice(0, 8).map((log, index) => (
              <div key={index}>
                <span>{String(log.source)}</span>
                <strong>{String(log.status)}{log.cached ? " cached" : ""}</strong>
              </div>
            ))}
          </div>
        </aside>
      </div>
    </section>
  );
}

function Reports({ result }: { result: PipelineResult | null }) {
  return (
    <section className="view-frame reports-view">
      <div className="section-header">
        <div>
          <p className="eyebrow">Reports</p>
          <h2>Model card, threshold registry, trace, and report.</h2>
        </div>
        {result?.run_id && (
          <a className="primary-action" href={`/api/runs/${result.run_id}/report`} target="_blank" rel="noreferrer">
            <Download size={16} />
            Open HTML report
          </a>
        )}
      </div>
      <div className="reports-grid">
        <section className="report-panel">
          <h3>Model card</h3>
          <dl className="model-dl">
            <dt>Model</dt>
            <dd>{String(result?.model_card?.model_id ?? "Run pending")}</dd>
            <dt>Training size</dt>
            <dd>{String(result?.model_card?.training_size ?? "-")}</dd>
            <dt>Applicability</dt>
            <dd>{String((result?.model_card?.applicability_domain as Record<string, unknown> | undefined)?.method ?? "-")}</dd>
          </dl>
        </section>
        <section className="report-panel">
          <h3>Threshold registry</h3>
          <div className="threshold-list">
            {Object.entries(result?.threshold_registry?.rules ?? {}).slice(0, 8).map(([id, rule]) => (
              <div key={id}>
                <strong>{String(rule.label ?? id)}</strong>
                <span>{String(rule.value)} {String(rule.units ?? "")}</span>
                <small>{String(rule.source ?? "source required")}</small>
              </div>
            ))}
          </div>
        </section>
        <section className="report-panel">
          <h3>Agent trace</h3>
          <ol className="trace-list">
            {(result?.plan ?? ["Run triage to create an agent trace."]).map((step) => <li key={step}>{step}</li>)}
          </ol>
        </section>
      </div>
    </section>
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

function EmptyPanel({ icon, title, text }: { icon: ReactNode; title: string; text: string }) {
  return (
    <div className="empty-panel">
      <span>{icon}</span>
      <strong>{title}</strong>
      <p>{text}</p>
    </div>
  );
}

function graphLayout(nodes: Array<Record<string, unknown> & { id: string; type: string; label?: string }>) {
  const typeOrder = ["target", "disease", "candidate", "descriptor", "model_prediction", "decision", "known_analog", "threshold", "assay", "class_risk", "structural_alert"];
  const byType = new Map<string, typeof nodes>();
  for (const node of nodes) {
    const bucket = byType.get(node.type) ?? [];
    bucket.push(node);
    byType.set(node.type, bucket);
  }
  const points = new Map<string, { x: number; y: number }>();
  typeOrder.forEach((type, typeIndex) => {
    const bucket = byType.get(type) ?? [];
    const centerX = 120 + (typeIndex % 4) * 240;
    const centerY = 100 + Math.floor(typeIndex / 4) * 170;
    bucket.forEach((node, index) => {
      const angle = (index / Math.max(bucket.length, 1)) * Math.PI * 2;
      const radius = type === "candidate" ? 84 : 52;
      points.set(node.id, {
        x: centerX + Math.cos(angle) * radius,
        y: centerY + Math.sin(angle) * radius
      });
    });
  });
  nodes.forEach((node, index) => {
    if (!points.has(node.id)) {
      points.set(node.id, { x: 120 + (index % 5) * 180, y: 100 + Math.floor(index / 5) * 120 });
    }
  });
  return points;
}

function projectConformer(atoms: ConformerPayload["atoms"], angle: number, zoom: number) {
  const rad = (angle / 180) * Math.PI;
  const rotated = atoms.map((atom) => {
    const x = atom.x * Math.cos(rad) - atom.z * Math.sin(rad);
    const z = atom.x * Math.sin(rad) + atom.z * Math.cos(rad);
    return { ...atom, rx: x, rz: z };
  });
  const xs = rotated.map((atom) => atom.rx);
  const ys = rotated.map((atom) => atom.y);
  const zs = rotated.map((atom) => atom.rz);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const minZ = Math.min(...zs), maxZ = Math.max(...zs);
  return rotated.map((atom) => {
    const depth = normalize(atom.rz, minZ, maxZ);
    return {
      index: atom.index,
      element: atom.element,
      x: 380 + (normalize(atom.rx, minX, maxX) - 0.5) * 520 * zoom + depth * 18,
      y: 260 + (normalize(atom.y, minY, maxY) - 0.5) * 330 * zoom - depth * 16,
      depth
    };
  });
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

function formatNumber(value: number | null | undefined, digits = 2) {
  if (typeof value !== "number" || Number.isNaN(value)) return "-";
  return value.toFixed(digits);
}

function profileLabel(profiles: Array<Record<string, unknown>>, id: string) {
  const profile = profiles.find((item) => item.id === id);
  return String(profile?.label ?? id);
}
