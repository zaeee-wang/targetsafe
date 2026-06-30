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
  Languages,
  Maximize2,
  Moon,
  Network,
  Play,
  RotateCcw,
  Search,
  ShieldCheck,
  Sun,
  TestTube2,
  X,
  ZoomIn,
  ZoomOut
} from "lucide-react";
import { createRun, fetchDepiction, fetchKnownContext, fetchProfiles, fetchReferenceDrugs } from "./api";
import type {
  Candidate,
  ConformerPayload,
  EvidenceGraph,
  KnownContext,
  PipelineResult,
  ReferenceDrug,
  RunRequest,
  Status,
  StructureDepiction
} from "./types";
import {
  COPY,
  criterionLabel,
  criterionValue,
  getStoredLocale,
  getStoredTheme,
  localizedProfile,
  localizeBackendText,
  statusLabel
} from "./i18n";
import type { Copy, Locale, ThemeMode } from "./i18n";

const DEFAULT_REQUEST: RunRequest = {
  disease: "EGFR mutation-positive NSCLC",
  target: "EGFR",
  seed_smiles: "COc1cc2ncnc(Nc3ccc(F)c(Cl)c3)c2cc1OCCCN1CCOCC1",
  optimization_goal: "Maintain drug-likeness, reduce toxicity alerts, preserve EGFR evidence confidence",
  candidate_count: 160,
  compute_profile: "cpu-demo",
  allow_network: false,
  use_llm: false,
  use_gpu: false,
  enable_conformers: true
};

const STATUS_ORDER: Status[] = ["Go", "Hold", "No-Go"];
const VIEWS = [
  { id: "console", icon: <Activity size={18} /> },
  { id: "atlas", icon: <Layers3 size={18} /> },
  { id: "twin", icon: <BrainCircuit size={18} /> },
  { id: "graph", icon: <GitBranch size={18} /> },
  { id: "known", icon: <ShieldCheck size={18} /> },
  { id: "reports", icon: <FileText size={18} /> }
] as const;

type ViewId = (typeof VIEWS)[number]["id"];
type MoleculeView = "2d" | "3d";
type SeedPreset = {
  id: string;
  name: string;
  smiles: string;
  category: string;
  target: string;
  disease?: string;
  noteEn: string;
  noteKo: string;
  source: "reference" | "preset";
  structureSvg?: string | null;
};

const CURATED_SEED_PRESETS: SeedPreset[] = [
  {
    id: "caffeine",
    name: "Caffeine",
    smiles: "Cn1cnc2c1c(=O)n(C)c(=O)n2C",
    category: "General drug-like controls",
    target: "non-EGFR test",
    noteEn: "Small, familiar xanthine scaffold for UI and descriptor sanity checks.",
    noteKo: "UI와 descriptor sanity check용으로 익숙한 작은 xanthine scaffold입니다.",
    source: "preset"
  },
  {
    id: "aspirin",
    name: "Aspirin",
    smiles: "CC(=O)Oc1ccccc1C(=O)O",
    category: "General drug-like controls",
    target: "non-EGFR test",
    noteEn: "Simple approved-drug structure for quick non-EGFR smoke testing.",
    noteKo: "비-EGFR smoke test에 쓰기 쉬운 단순한 승인 약물 구조입니다.",
    source: "preset"
  },
  {
    id: "acetaminophen",
    name: "Acetaminophen",
    smiles: "CC(=O)Nc1ccc(O)cc1",
    category: "General drug-like controls",
    target: "non-EGFR test",
    noteEn: "Compact polar aromatic control; useful for descriptor contrast.",
    noteKo: "descriptor 대비를 보기 좋은 작은 polar aromatic control입니다.",
    source: "preset"
  },
  {
    id: "ibuprofen",
    name: "Ibuprofen",
    smiles: "CC(C)Cc1ccc(cc1)C(C)C(=O)O",
    category: "General drug-like controls",
    target: "non-EGFR test",
    noteEn: "Hydrophobic acid reference for drug-likeness and logP behavior checks.",
    noteKo: "drug-likeness와 logP 반응을 보기 좋은 hydrophobic acid reference입니다.",
    source: "preset"
  },
  {
    id: "metformin",
    name: "Metformin",
    smiles: "CN(C)C(=N)NC(=N)N",
    category: "General drug-like controls",
    target: "non-EGFR test",
    noteEn: "Highly polar small molecule; useful for testing property boundaries.",
    noteKo: "물성 경계값을 확인하기 좋은 highly polar small molecule입니다.",
    source: "preset"
  },
  {
    id: "long-alkane",
    name: "Long alkane stress control",
    smiles: "CCCCCCCCCCCCCCCCCCCC",
    category: "Negative / stress controls",
    target: "chemistry stress test",
    noteEn: "Hydrophobic stress control expected to expose drug-likeness weaknesses.",
    noteKo: "drug-likeness 약점을 드러내기 위한 hydrophobic stress control입니다.",
    source: "preset"
  },
  {
    id: "catechol-alert",
    name: "Catechol alert control",
    smiles: "Oc1ccc(O)cc1",
    category: "Negative / stress controls",
    target: "structural alert test",
    noteEn: "Small alert-like motif for checking review/alert behavior.",
    noteKo: "review/alert 동작을 확인하기 위한 작은 alert-like motif입니다.",
    source: "preset"
  },
  {
    id: "invalid-smiles",
    name: "Invalid SMILES control",
    smiles: "C1CC",
    category: "Negative / stress controls",
    target: "failure-path test",
    noteEn: "Intentional invalid input to verify No-Go/failure-path handling.",
    noteKo: "No-Go/failure path 처리를 검증하기 위한 의도적 invalid input입니다.",
    source: "preset"
  }
];

export default function App() {
  const [locale, setLocale] = useState<Locale>(getStoredLocale);
  const [theme, setTheme] = useState<ThemeMode>(getStoredTheme);
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
  const copy = COPY[locale];

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.lang = locale;
    window.localStorage.setItem("targetsafe-theme", theme);
    window.localStorage.setItem("targetsafe-locale", locale);
  }, [theme, locale]);

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
      setSelectedId(payload.candidates.find((candidate) => candidate.candidate_id.startsWith("C"))?.candidate_id ?? payload.candidates[0]?.candidate_id ?? "");
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
    <main className="app-shell" data-theme={theme}>
      <NavRail activeView={activeView} onChange={setActiveView} result={result} copy={copy} />
      <section className="workspace">
        <TopCommand
          request={request}
          profiles={profiles}
          loading={loading}
          copy={copy}
          locale={locale}
          theme={theme}
          onRequestChange={setRequest}
          onLocaleChange={setLocale}
          onThemeChange={setTheme}
          onRun={() => runTriage()}
        />
        {activeView === "console" && (
          <RunConsole
            request={request}
            profiles={profiles}
            referenceDrugs={referenceDrugs}
            result={result}
            counts={counts}
            loading={loading}
            error={error}
            copy={copy}
            locale={locale}
            onRequestChange={setRequest}
            onRun={runTriage}
          />
        )}
        {activeView === "atlas" && (
          <MoleculeAtlas
            result={result}
            selectedId={selected?.candidate_id ?? ""}
            referenceDrugs={referenceDrugs}
            copy={copy}
            onSelectCandidate={(id) => selectCandidate(id)}
            onOpenKnown={() => setActiveView("known")}
          />
        )}
        {activeView === "twin" && (
          <CandidateTwin
            candidate={selected}
            result={result}
            graph={result?.evidence_graph ?? null}
            moleculeView={moleculeView}
            knownContext={knownContext}
            copy={copy}
            locale={locale}
            onMoleculeViewChange={setMoleculeView}
            onOpenGraph={() => setActiveView("graph")}
          />
        )}
        {activeView === "graph" && (
          <EvidenceGraphExplorer
            graph={result?.evidence_graph ?? null}
            selected={selected}
            copy={copy}
            onSelectCandidate={selectCandidate}
          />
        )}
        {activeView === "known" && (
          <KnownDrugsAndRisks
            referenceDrugs={referenceDrugs}
            result={result}
            selected={selected}
            knownContext={knownContext}
            copy={copy}
            locale={locale}
          />
        )}
        {activeView === "reports" && <Reports result={result} copy={copy} locale={locale} />}
      </section>
    </main>
  );
}

function NavRail({
  activeView,
  onChange,
  result,
  copy
}: {
  activeView: ViewId;
  onChange: (view: ViewId) => void;
  result: PipelineResult | null;
  copy: Copy;
}) {
  return (
    <aside className="nav-rail" aria-label={copy.brand.navAria}>
      <div className="brand-block">
        <div className="pulse-mark"><Activity size={18} /></div>
        <div>
          <span>Target-SAFE</span>
          <strong>{copy.brand.subtitle}</strong>
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
            <span>{copy.views[view.id]}</span>
          </button>
        ))}
      </nav>
      <div className="run-chip">
        <span>{result ? copy.nav.runLoaded : copy.nav.noRunYet}</span>
        <strong>{result?.run_id ?? copy.nav.ready}</strong>
      </div>
    </aside>
  );
}

function TopCommand({
  request,
  profiles,
  loading,
  copy,
  locale,
  theme,
  onRequestChange,
  onLocaleChange,
  onThemeChange,
  onRun
}: {
  request: RunRequest;
  profiles: Array<Record<string, unknown>>;
  loading: boolean;
  copy: Copy;
  locale: Locale;
  theme: ThemeMode;
  onRequestChange: (request: RunRequest) => void;
  onLocaleChange: (locale: Locale) => void;
  onThemeChange: (theme: ThemeMode) => void;
  onRun: () => void;
}) {
  return (
    <header className="top-command">
      <div>
        <p className="eyebrow">{copy.top.eyebrow}</p>
        <h1>{request.disease} / {request.target}</h1>
      </div>
      <div className="top-command-actions">
        <div className="utility-switches" aria-label={copy.top.preferences}>
          <span><Sun size={14} /> / <Moon size={14} /></span>
          <button className={theme === "dark" ? "active" : ""} onClick={() => onThemeChange("dark")} type="button">
            {copy.top.dark}
          </button>
          <button className={theme === "light" ? "active" : ""} onClick={() => onThemeChange("light")} type="button">
            {copy.top.light}
          </button>
        </div>
        <div className="utility-switches" aria-label="Language">
          <span><Languages size={14} /></span>
          <button className={locale === "ko" ? "active" : ""} onClick={() => onLocaleChange("ko")} type="button">
            {copy.top.ko}
          </button>
          <button className={locale === "en" ? "active" : ""} onClick={() => onLocaleChange("en")} type="button">
            {copy.top.en}
          </button>
        </div>
        <select
          value={request.compute_profile}
          aria-label={copy.top.computeProfile}
          onChange={(event) => onRequestChange({ ...request, compute_profile: event.target.value })}
        >
          {profiles.map((profile) => (
            <option key={String(profile.id)} value={String(profile.id)}>
              {localizedProfile(profile, copy).label}
            </option>
          ))}
        </select>
        <button className="primary-action" onClick={onRun} disabled={loading} type="button">
          {loading ? <Loader2 className="spin" size={17} /> : <Play size={17} />}
          {copy.top.run}
        </button>
      </div>
    </header>
  );
}

function RunConsole({
  request,
  profiles,
  referenceDrugs,
  result,
  counts,
  loading,
  error,
  copy,
  locale,
  onRequestChange,
  onRun
}: {
  request: RunRequest;
  profiles: Array<Record<string, unknown>>;
  referenceDrugs: ReferenceDrug[];
  result: PipelineResult | null;
  counts: Record<Status, number>;
  loading: boolean;
  error: string;
  copy: Copy;
  locale: Locale;
  onRequestChange: (request: RunRequest) => void;
  onRun: (profileOverride?: string) => void;
}) {
  const [seedDrawerOpen, setSeedDrawerOpen] = useState(false);
  const seedOptions = useMemo(() => buildSeedPresets(referenceDrugs), [referenceDrugs]);

  function applySeedPreset(preset: SeedPreset) {
    onRequestChange({
      ...request,
      seed_smiles: preset.smiles,
      target: preset.target === "EGFR" ? "EGFR" : request.target,
      disease: preset.disease ?? request.disease
    });
    setSeedDrawerOpen(false);
  }

  return (
    <section className="view-frame console-view">
      <div className="console-stage">
        <div className="orbital-visual" aria-hidden="true">
          <span />
          <i />
          <b />
        </div>
        <div className="console-copy">
          <p className="eyebrow">{copy.console.eyebrow}</p>
          <h2>{copy.console.heading}</h2>
          <p>{copy.console.body}</p>
          <button className="primary-action large" onClick={() => onRun("cpu-demo")} disabled={loading} type="button">
            {loading ? <Loader2 className="spin" size={18} /> : <Play size={18} />}
            {copy.console.runDemo}
          </button>
        </div>
      </div>

      <div className="console-grid">
        <section className="input-deck">
          <label>
            {copy.console.disease}
            <input value={request.disease} onChange={(event) => onRequestChange({ ...request, disease: event.target.value })} />
          </label>
          <label>
            {copy.console.target}
            <input value={request.target} onChange={(event) => onRequestChange({ ...request, target: event.target.value })} />
          </label>
          <div className="wide field-block">
            <div className="field-label-row">
              <span>{copy.console.seed}</span>
              <button className="inline-action" onClick={() => setSeedDrawerOpen(true)} type="button">
                <Layers3 size={15} />
                {copy.seedDrawer.open}
              </button>
            </div>
            <textarea aria-label={copy.console.seed} value={request.seed_smiles} onChange={(event) => onRequestChange({ ...request, seed_smiles: event.target.value })} />
          </div>
          <label className="wide">
            {copy.console.goal}
            <textarea value={request.optimization_goal} onChange={(event) => onRequestChange({ ...request, optimization_goal: event.target.value })} />
          </label>
          <div className="control-row">
            <label>
              {copy.console.candidates}
              <input
                type="number"
                min={20}
                max={500}
                value={request.candidate_count}
                onChange={(event) => onRequestChange({ ...request, candidate_count: Number(event.target.value) })}
              />
            </label>
            <Toggle label={copy.console.liveApis} value={request.allow_network} onChange={(allow_network) => onRequestChange({ ...request, allow_network })} />
            <Toggle label={copy.console.gpu} value={request.use_gpu} onChange={(use_gpu) => onRequestChange({ ...request, use_gpu })} />
            <Toggle label={copy.console.llm} value={request.use_llm} onChange={(use_llm) => onRequestChange({ ...request, use_llm })} />
          </div>
        </section>

        <section className="status-deck">
          <Metric icon={<Cpu />} label={copy.console.computeProfile} value={profileLabel(profiles, request.compute_profile, copy)} />
          <Metric icon={<TestTube2 />} label={copy.console.evidenceMode} value={evidenceModeLabel(result, request, copy)} />
          <Metric icon={<Network />} label={copy.console.evidenceGraph} value={result ? `${result.evidence_graph.summary.node_count} nodes` : copy.console.runPending} />
          <div className="status-strip">
            {STATUS_ORDER.map((status) => (
              <div className={`status-pill ${statusClass(status)}`} key={status}>
                <span>{statusLabel(status, copy)}</span>
                <strong>{counts[status]}</strong>
              </div>
            ))}
          </div>
          {error && <div className="error-box">{error}</div>}
        </section>
      </div>
      <ProfileMatrix profiles={profiles} selectedProfile={request.compute_profile} copy={copy} />
      <TargetScopePanel copy={copy} />
      {seedDrawerOpen && (
        <SeedDrawer
          copy={copy}
          locale={locale}
          presets={seedOptions}
          onApply={applySeedPreset}
          onClose={() => setSeedDrawerOpen(false)}
        />
      )}
    </section>
  );
}

function ProfileMatrix({
  profiles,
  selectedProfile,
  copy
}: {
  profiles: Array<Record<string, unknown>>;
  selectedProfile: string;
  copy: Copy;
}) {
  const features = [
    ["allow_network", copy.profiles.features.allow_network],
    ["use_gpu", copy.profiles.features.use_gpu],
    ["use_llm", copy.profiles.features.use_llm],
    ["train_qsar", copy.profiles.features.train_qsar],
    ["use_cached_demo", copy.profiles.features.use_cached_demo]
  ];
  return (
    <section className="profile-matrix" aria-label={copy.profiles.heading}>
      <div>
        <p className="eyebrow">{copy.profiles.eyebrow}</p>
        <h3>{copy.profiles.heading}</h3>
      </div>
      <div className="profile-grid">
        {profiles.map((profile) => {
          const localized = localizedProfile(profile, copy);
          return (
          <article className={String(profile.id) === selectedProfile ? "selected" : ""} key={String(profile.id)}>
            <strong>{localized.label}</strong>
            <p>{localized.description}</p>
            <div className="profile-features">
              {features.map(([key, label]) => (
                <span className={profile[key] ? "on" : "off"} key={key}>
                  {profile[key] ? copy.profiles.on : copy.profiles.off} / {label}
                </span>
              ))}
            </div>
            <small>{localized.runtime}</small>
          </article>
        );
        })}
      </div>
    </section>
  );
}

function TargetScopePanel({ copy }: { copy: Copy }) {
  const targets = [
    ["EGFR", ...copy.scope.targets.EGFR],
    ["ALK", ...copy.scope.targets.ALK],
    ["BRAF", ...copy.scope.targets.BRAF],
    ["KRAS", ...copy.scope.targets.KRAS],
    ["HER2", ...copy.scope.targets.HER2]
  ];
  return (
    <section className="target-scope-panel" aria-label={copy.scope.eyebrow}>
      <div>
        <p className="eyebrow">{copy.scope.eyebrow}</p>
        <h3>{copy.scope.heading}</h3>
        <p>{copy.scope.body}</p>
      </div>
      <div className="target-scope-grid">
        {targets.map(([target, status, text]) => (
          <article key={target} className={target === "EGFR" ? "active" : ""}>
            <strong>{target}</strong>
            <span>{status}</span>
            <p>{text}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function SeedDrawer({
  copy,
  locale,
  presets,
  onApply,
  onClose
}: {
  copy: Copy;
  locale: Locale;
  presets: SeedPreset[];
  onApply: (preset: SeedPreset) => void;
  onClose: () => void;
}) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState(copy.seedDrawer.all);
  const categories = [copy.seedDrawer.all, ...Array.from(new Set(presets.map((preset) => categoryLabel(preset.category, locale))))];
  const normalizedQuery = query.trim().toLowerCase();
  const visible = presets.filter((preset) => {
    const label = categoryLabel(preset.category, locale);
    const passCategory = category === copy.seedDrawer.all || label === category;
    const passQuery = !normalizedQuery || [preset.name, preset.smiles, preset.target, preset.category].join(" ").toLowerCase().includes(normalizedQuery);
    return passCategory && passQuery;
  });

  return (
    <div className="drawer-backdrop" role="presentation">
      <aside className="seed-drawer" aria-label={copy.seedDrawer.title}>
        <div className="drawer-header">
          <div>
            <p className="eyebrow">{copy.seedDrawer.open}</p>
            <h3>{copy.seedDrawer.title}</h3>
            <p>{copy.seedDrawer.subtitle}</p>
          </div>
          <button className="icon-action" onClick={onClose} type="button" title={copy.seedDrawer.close}>
            <X size={18} />
          </button>
        </div>
        <div className="drawer-warning">
          <AlertTriangle size={16} />
          <span>{copy.seedDrawer.warning}</span>
        </div>
        <div className="drawer-controls">
          <input
            aria-label={copy.seedDrawer.search}
            placeholder={copy.seedDrawer.search}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <div className="drawer-category-row">
            {categories.map((item) => (
              <button className={category === item ? "active" : ""} key={item} onClick={() => setCategory(item)} type="button">
                {item}
              </button>
            ))}
          </div>
        </div>
        <div className="seed-grid">
          {visible.map((preset) => (
            <article className="seed-card" key={preset.id}>
              <MoleculePreview preset={preset} copy={copy} />
              <div className="seed-card-body">
                <div>
                  <span>{categoryLabel(preset.category, locale)} / {preset.source === "reference" ? copy.seedDrawer.sourceReference : copy.seedDrawer.sourcePreset}</span>
                  <h4>{preset.name}</h4>
                  <p>{locale === "ko" ? preset.noteKo : preset.noteEn}</p>
                </div>
                <code title={preset.smiles}>{preset.smiles}</code>
                <button className="primary-action" onClick={() => onApply(preset)} type="button">
                  {copy.seedDrawer.apply}
                </button>
              </div>
            </article>
          ))}
        </div>
      </aside>
    </div>
  );
}

function MoleculePreview({ preset, copy }: { preset: SeedPreset; copy: Copy }) {
  const [depiction, setDepiction] = useState<StructureDepiction | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (preset.structureSvg || !preset.smiles) return;
    let cancelled = false;
    fetchDepiction(preset.smiles)
      .then((payload) => {
        if (!cancelled) setDepiction(payload);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [preset.smiles, preset.structureSvg]);

  const figure = preset.structureSvg ?? depiction?.structure_svg;
  return (
    <div className="seed-figure">
      {figure ? (
        <img src={figure} alt={`${preset.name} structure`} />
      ) : (
        <span>{failed || depiction?.valid === false ? copy.seedDrawer.invalid : copy.seedDrawer.noFigure}</span>
      )}
    </div>
  );
}

function MoleculeAtlas({
  result,
  selectedId,
  referenceDrugs,
  copy,
  onSelectCandidate,
  onOpenKnown
}: {
  result: PipelineResult | null;
  selectedId: string;
  referenceDrugs: ReferenceDrug[];
  copy: Copy;
  onSelectCandidate: (id: string) => void;
  onOpenKnown: () => void;
}) {
  const candidates = result?.candidates ?? [];
  const visibleCandidates = candidates.slice(0, 96);
  const heroCandidate = candidates[0];
  return (
    <section className="view-frame atlas-view">
      <div className="section-header">
        <div>
          <p className="eyebrow">{copy.atlas.eyebrow}</p>
          <h2>{copy.atlas.heading}</h2>
        </div>
        <button className="ghost-action" onClick={onOpenKnown} type="button">
          <ShieldCheck size={16} />
          {copy.atlas.openKnown}
        </button>
      </div>

      <div className="atlas-hero">
        <div className="molecule-spotlight">
          {heroCandidate?.structure_svg ? (
            <img src={heroCandidate.structure_svg} alt={`${heroCandidate.candidate_id} structure`} />
          ) : (
            <div className="empty-inline">{copy.atlas.emptyFigure}</div>
          )}
        </div>
        <div className="atlas-note">
          <span>{copy.atlas.primaryCandidate}</span>
          <strong>{heroCandidate?.candidate_id ?? copy.atlas.noCandidate}</strong>
          <p>{copy.atlas.note}</p>
        </div>
      </div>

      <div className="atlas-columns">
        <section>
          <div className="panel-heading">
            <div>
              <p className="eyebrow">{copy.atlas.generated}</p>
              <h3>{visibleCandidates.length || 0} {copy.atlas.shown} / {candidates.length || 0} {copy.atlas.scored}</h3>
            </div>
          </div>
          {candidates.length === 0 ? (
            <EmptyPanel icon={<Search />} title={copy.atlas.emptyTitle} text={copy.atlas.emptyText} />
          ) : (
            <div className="molecule-grid">
              {visibleCandidates.map((candidate) => (
                <button
                  className={`molecule-card ${selectedId === candidate.candidate_id ? "selected" : ""}`}
                  onClick={() => onSelectCandidate(candidate.candidate_id)}
                  key={candidate.candidate_id}
                  type="button"
                >
                  <span className={`mini-status ${statusClass(candidate.decision?.final_status ?? "Unscored")}`}>
                    {statusLabel(candidate.decision?.final_status ?? "Unscored", copy)}
                  </span>
                  <span className="molecule-thumb">
                    {candidate.structure_svg ? <img src={candidate.structure_svg} alt="" /> : <i>{copy.atlas.noStructure}</i>}
                  </span>
                  <strong>{candidate.candidate_id}</strong>
                  <small>{copy.atlas.lowerPchembl} {formatNumber(candidate.prediction_interval?.lower, 2)}</small>
                  <small>AD {formatNumber(candidate.applicability_score, 2)} / {candidate.source.replaceAll("_", " ")}</small>
                </button>
            ))}
          </div>
          )}
        </section>

        <section>
          <div className="panel-heading">
            <div>
              <p className="eyebrow">{copy.atlas.reference}</p>
              <h3>{copy.atlas.knownDrugs}</h3>
            </div>
          </div>
          <div className="reference-list">
            {referenceDrugs.slice(0, 24).map((drug) => (
              <article className="reference-card" key={drug.drug_id}>
                <div className="reference-structure">
                  {drug.structure_svg || drug.structure_image_url ? (
                    <img src={(drug.structure_svg || drug.structure_image_url) ?? undefined} alt={`${drug.name} structure`} />
                  ) : (
                    <span>{copy.atlas.noFigure}</span>
                  )}
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
  result,
  graph,
  moleculeView,
  knownContext,
  copy,
  locale,
  onMoleculeViewChange,
  onOpenGraph
}: {
  candidate: Candidate | null;
  result: PipelineResult | null;
  graph: EvidenceGraph | null;
  moleculeView: MoleculeView;
  knownContext: KnownContext | null;
  copy: Copy;
  locale: Locale;
  onMoleculeViewChange: (view: MoleculeView) => void;
  onOpenGraph: () => void;
}) {
  if (!candidate) {
    return (
      <section className="view-frame">
        <EmptyPanel icon={<BrainCircuit />} title={copy.twin.emptyTitle} text={copy.twin.emptyText} />
      </section>
    );
  }
  const decision = candidate.decision;
  const desc = candidate.descriptors;
  const redesignChildren = (result?.candidates ?? []).filter((item) => item.parent_candidate_id === candidate.candidate_id);
  const parentCandidate = candidate.parent_candidate_id
    ? (result?.candidates ?? []).find((item) => item.candidate_id === candidate.parent_candidate_id)
    : null;
  return (
    <section className="view-frame twin-view">
      <div className="section-header">
        <div>
          <p className="eyebrow">{copy.twin.eyebrow}</p>
          <h2>{candidate.candidate_id}</h2>
        </div>
        <span className={`decision-badge ${statusClass(decision?.final_status ?? "Unscored")}`}>{statusLabel(decision?.final_status ?? "Unscored", copy)}</span>
      </div>

      <div className="twin-stage-grid">
        <section className="visual-stage">
          <div className="stage-tabs">
            <button className={moleculeView === "2d" ? "active" : ""} onClick={() => onMoleculeViewChange("2d")} type="button">{copy.twin.twoD}</button>
            <button className={moleculeView === "3d" ? "active" : ""} onClick={() => onMoleculeViewChange("3d")} type="button">{copy.twin.threeD}</button>
          </div>
          {moleculeView === "2d" ? (
            <div className="structure-stage">
              {candidate.structure_svg ? <img src={candidate.structure_svg} alt={`${candidate.candidate_id} 2D structure`} /> : <span>{copy.twin.no2d}</span>}
            </div>
          ) : (
            <InteractiveConformerView conformer={candidate.conformer} candidateId={candidate.candidate_id} copy={copy} />
          )}
          <p className="viewer-warning">
            {copy.twin.viewerWarning}
          </p>
        </section>

        <section className="decision-stage">
          <div className="why-block">
            <h3>{copy.twin.why}</h3>
            <ul>
              {(decision?.reasons ?? ["Run pending."]).slice(0, 5).map((reason) => <li key={reason}>{localizeBackendText(reason, locale)}</li>)}
            </ul>
          </div>
          <div className="criteria-grid">
            {Object.entries(decision?.criteria ?? {}).map(([key, value]) => (
              <div className={`criterion ${value}`} key={key}>
                <span>{criterionLabel(key, copy)}</span>
                <strong>{criterionValue(value, copy)}</strong>
              </div>
            ))}
          </div>
          <button className="ghost-action" onClick={onOpenGraph} type="button">
            <GitBranch size={16} />
            {copy.twin.inspectGraph}
          </button>
        </section>

        <aside className="status-rails">
          <Rail icon={<BrainCircuit />} label={copy.twin.targetFit} value={formatNumber(candidate.predicted_activity, 2)} detail={`AD ${formatNumber(candidate.applicability_score, 2)}`} />
          <Rail icon={<ShieldCheck />} label={copy.twin.qedSa} value={`${formatNumber(desc?.qed, 2)} / ${formatNumber(desc?.sa_score, 2)}`} detail={`${desc?.method ?? "unknown"} ${copy.twin.descriptors}`} />
          <Rail icon={<AlertTriangle />} label={copy.twin.alerts} value={`${desc?.alerts?.length ?? 0}`} detail={(desc?.severe_alerts?.length ?? 0) ? copy.twin.severeBlocker : copy.twin.reviewIfNonzero} />
          <Rail icon={<GitBranch />} label={copy.twin.graph} value={`${graph?.summary?.node_count ?? 0} nodes`} detail={`${candidate.evidence_node_ids.length} ${copy.twin.linkedNodes}`} />
        </aside>
      </div>

      <div className="twin-detail-grid">
        <section className="detail-block">
          <h3>{copy.twin.knownContext}</h3>
          <p className="context-note">{knownContext?.interpretation ? localizeBackendText(knownContext.interpretation, locale) : copy.twin.contextPending}</p>
          <div className="analog-list">
            {(knownContext?.nearest_known_drugs ?? []).slice(0, 4).map((drug) => (
              <span key={drug.drug_id}>{drug.name} / {copy.twin.sim} {formatNumber(drug.similarity, 2)}</span>
            ))}
          </div>
        </section>
        <section className="detail-block">
          <h3>{copy.twin.nextValidation}</h3>
          <ul className="compact-list">
            {(decision?.follow_up ?? []).slice(0, 4).map((item) => <li key={item}>{localizeBackendText(item, locale)}</li>)}
          </ul>
        </section>
        <section className="detail-block redesign-block">
          <h3>{copy.twin.redesign}</h3>
          {candidate.redesign_reason || parentCandidate ? (
            <div className="redesign-summary">
              {parentCandidate && <span>{copy.twin.parentCandidate}: {parentCandidate.candidate_id}</span>}
              {candidate.redesign_reason && <span>{copy.twin.redesignReason}: {candidate.redesign_reason}</span>}
              {candidate.redesign_action && <p>{candidate.redesign_action}</p>}
            </div>
          ) : redesignChildren.length ? (
            <div className="redesign-summary">
              <span>{copy.twin.childSuggestions}: {redesignChildren.map((child) => child.candidate_id).join(", ")}</span>
              {redesignChildren.slice(0, 3).map((child) => (
                <p key={child.candidate_id}>
                  {child.candidate_id}: {child.redesign_reason} / {statusLabel(child.decision?.final_status ?? "Unscored", copy)}
                </p>
              ))}
            </div>
          ) : (
            <p className="context-note">{copy.twin.noRedesign}</p>
          )}
        </section>
      </div>
    </section>
  );
}

function InteractiveConformerView({ conformer, candidateId, copy }: { conformer: ConformerPayload | null; candidateId: string; copy: Copy }) {
  const [angle, setAngle] = useState(22);
  const [zoom, setZoom] = useState(1);
  const atoms = (conformer?.atoms ?? []).slice(0, 64);
  const bonds = (conformer?.bonds ?? []).slice(0, 90);
  if (!conformer?.available || atoms.length === 0) {
    return (
      <div className="conformer-stage unavailable">
        <span>{copy.conformer.unavailable}</span>
        <small>{conformer?.message ?? copy.conformer.emptyMessage}</small>
      </div>
    );
  }

  const projected = projectConformer(atoms, angle, zoom);
  const byIndex = new Map(projected.map((atom) => [atom.index, atom]));
  return (
    <div className="conformer-stage">
      <div className="viewer-controls" aria-label={copy.conformer.controls}>
        <button onClick={() => setAngle((value) => value - 18)} type="button" title={copy.conformer.rotateLeft}><ArrowLeft size={15} /></button>
        <button onClick={() => setAngle((value) => value + 18)} type="button" title={copy.conformer.rotateRight}><ArrowRight size={15} /></button>
        <button onClick={() => setZoom((value) => Math.min(1.8, value + 0.12))} type="button" title={copy.conformer.zoomIn}><ZoomIn size={15} /></button>
        <button onClick={() => setZoom((value) => Math.max(0.62, value - 0.12))} type="button" title={copy.conformer.zoomOut}><ZoomOut size={15} /></button>
        <button onClick={() => { setAngle(22); setZoom(1); }} type="button" title={copy.conformer.reset}><RotateCcw size={15} /></button>
      </div>
      <a className="xyz-export" href={xyzDataUri(candidateId, atoms, copy)} download={`${candidateId}_computed_conformer.xyz`}>
        {copy.conformer.exportXyz}
      </a>
      <svg viewBox="0 0 760 520" role="img" aria-label={copy.conformer.aria}>
        <defs>
          <radialGradient id="atom-C" cx="35%" cy="30%">
            <stop offset="0%" stopColor="#ffffff" />
            <stop offset="100%" stopColor="#c8c2b8" />
          </radialGradient>
          <radialGradient id="atom-N" cx="35%" cy="30%">
            <stop offset="0%" stopColor="#dceaff" />
            <stop offset="100%" stopColor="#4c88e8" />
          </radialGradient>
          <radialGradient id="atom-O" cx="35%" cy="30%">
            <stop offset="0%" stopColor="#ffe1dc" />
            <stop offset="100%" stopColor="#e6554f" />
          </radialGradient>
          <radialGradient id="atom-F" cx="35%" cy="30%">
            <stop offset="0%" stopColor="#e4ffd8" />
            <stop offset="100%" stopColor="#7cc55e" />
          </radialGradient>
          <radialGradient id="atom-Cl" cx="35%" cy="30%">
            <stop offset="0%" stopColor="#e4ffd8" />
            <stop offset="100%" stopColor="#6caf53" />
          </radialGradient>
        </defs>
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
              <circle
                cx={atom.x}
                cy={atom.y}
                r={atom.element === "H" ? 5 : 9 + atom.depth * 4}
                className={`atom atom-${atom.element}`}
                fill={`url(#atom-${["C", "N", "O", "F", "Cl"].includes(atom.element) ? atom.element : "C"})`}
              />
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
  copy,
  onSelectCandidate
}: {
  graph: EvidenceGraph | null;
  selected: Candidate | null;
  copy: Copy;
  onSelectCandidate: (id: string, view?: ViewId) => void;
}) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [dragStart, setDragStart] = useState<{ x: number; y: number; panX: number; panY: number } | null>(null);
  const [graphScope, setGraphScope] = useState("selected");
  const [nodeFilter, setNodeFilter] = useState("all");
  const [edgeFilter, setEdgeFilter] = useState("all");

  const nodes = graph?.nodes ?? [];
  const edges = graph?.edges ?? [];
  const scopedIds = useMemo(() => graphScopeIds(nodes, edges, graphScope, selected), [nodes, edges, graphScope, selected]);
  const scopedNodes = nodes.filter((node) => scopedIds.has(node.id));
  const nodeTypes = ["all", ...Array.from(new Set(scopedNodes.map((node) => node.type))).sort()];
  const edgeTypes = ["all", ...Array.from(new Set(edges.map((edge) => edge.type))).sort()];
  const visibleNodes = nodeFilter === "all" ? scopedNodes : scopedNodes.filter((node) => node.type === nodeFilter);
  const visibleIds = new Set(visibleNodes.map((node) => node.id));
  const visibleEdges = edges.filter((edge) => {
    const passType = edgeFilter === "all" || edge.type === edgeFilter;
    return passType && visibleIds.has(edge.source) && visibleIds.has(edge.target);
  });
  const layout = useMemo(() => graphLayout(visibleNodes), [visibleNodes]);
  const selectedSet = new Set(selected?.evidence_node_ids ?? []);
  const showLabels = visibleNodes.length < 90 || zoom >= 1.45;

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
          <p className="eyebrow">{copy.graph.eyebrow}</p>
          <h2>{copy.graph.heading}</h2>
        </div>
        <div className="graph-toolbar">
          <select value={graphScope} onChange={(event) => setGraphScope(event.target.value)} aria-label={copy.graph.scopeAria}>
            <option value="selected">{copy.graph.scopes.selected}</option>
            <option value="summary">{copy.graph.scopes.summary}</option>
            <option value="all">{copy.graph.scopes.all}</option>
          </select>
          <select value={nodeFilter} onChange={(event) => setNodeFilter(event.target.value)} aria-label={copy.graph.nodeFilter}>
            {nodeTypes.map((type) => <option key={type} value={type}>{type === "all" ? copy.graph.all : type}</option>)}
          </select>
          <select value={edgeFilter} onChange={(event) => setEdgeFilter(event.target.value)} aria-label={copy.graph.edgeFilter}>
            {edgeTypes.map((type) => <option key={type} value={type}>{type === "all" ? copy.graph.all : type}</option>)}
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
          <svg viewBox="0 0 960 580" role="img" aria-label={copy.graph.aria}>
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
                    {(showLabels || selectedSet.has(node.id) || node.type === "target" || node.type === "decision") && (
                      <text x={point.x + 16} y={point.y + 5}>{label.slice(0, 30)}</text>
                    )}
                  </g>
                );
              })}
            </g>
          </svg>
        ) : (
          <EmptyPanel icon={<GitBranch />} title={copy.graph.emptyTitle} text={copy.graph.emptyText} />
        )}
      </div>
    </section>
  );
}

function KnownDrugsAndRisks({
  referenceDrugs,
  result,
  selected,
  knownContext,
  copy,
  locale
}: {
  referenceDrugs: ReferenceDrug[];
  result: PipelineResult | null;
  selected: Candidate | null;
  knownContext: KnownContext | null;
  copy: Copy;
  locale: Locale;
}) {
  return (
    <section className="view-frame known-view">
      <div className="section-header">
        <div>
          <p className="eyebrow">{copy.known.eyebrow}</p>
          <h2>{copy.known.heading}</h2>
        </div>
      </div>
      <div className="risk-banner">
        <AlertTriangle size={20} />
        <p>{copy.known.banner}</p>
      </div>
      <div className="known-grid">
        <section className="known-drug-table">
          {referenceDrugs.map((drug) => (
            <article className="known-drug-card" key={drug.drug_id}>
              <div className="known-drug-figure">
                {drug.structure_svg || drug.structure_image_url ? (
                  <img src={(drug.structure_svg || drug.structure_image_url) ?? undefined} alt={`${drug.name} structure`} />
                ) : (
                  <span>{copy.known.noStructure}</span>
                )}
              </div>
              <div>
                <p className="eyebrow">
                  {drug.category ?? copy.known.reference} {drug.chembl_id ? `/ ${drug.chembl_id}` : ""} {drug.pubchem_cid ? `/ PubChem ${drug.pubchem_cid}` : ""}
                </p>
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
          <h3>{selected ? `${selected.candidate_id} ${copy.known.nearest}` : copy.known.candidateContext}</h3>
          <p>{knownContext?.interpretation ? localizeBackendText(knownContext.interpretation, locale) : copy.known.selectCandidate}</p>
          <div className="analog-list vertical">
            {(knownContext?.nearest_known_drugs ?? []).map((drug) => (
              <span key={drug.drug_id}>{drug.name} / {copy.known.sim} {formatNumber(drug.similarity, 2)}</span>
            ))}
          </div>
          <h3>{copy.known.evidenceStatus}</h3>
          <div className="tool-log-list">
            {(result?.tool_logs ?? []).filter((log) => String(log.source).includes("PubChem") || String(log.source).includes("openFDA")).slice(0, 8).map((log, index) => (
              <div key={index}>
                <span>{String(log.source)}</span>
                <strong>{String(log.status)}{log.cached ? ` ${copy.known.cached}` : ""}</strong>
              </div>
            ))}
          </div>
        </aside>
      </div>
    </section>
  );
}

function Reports({ result, copy, locale }: { result: PipelineResult | null; copy: Copy; locale: Locale }) {
  return (
    <section className="view-frame reports-view">
      <div className="section-header">
        <div>
          <p className="eyebrow">{copy.reports.eyebrow}</p>
          <h2>{copy.reports.heading}</h2>
        </div>
        {result?.run_id && (
          <a className="primary-action" href={`/api/runs/${result.run_id}/report`} target="_blank" rel="noreferrer">
            <Download size={16} />
            {copy.reports.openReport}
          </a>
        )}
      </div>
      <div className="reports-grid">
        <section className="report-panel">
          <h3>{copy.reports.evidenceMode}</h3>
          <dl className="model-dl">
            <dt>{copy.reports.status}</dt>
            <dd>{evidenceModeLabel(result, DEFAULT_REQUEST, copy)}</dd>
            <dt>{copy.reports.sourceRequired}</dt>
            <dd>{String(result?.evidence_mode?.interpretation ?? "-")}</dd>
          </dl>
        </section>
        <section className="report-panel">
          <h3>{copy.reports.modelCard}</h3>
          <dl className="model-dl">
            <dt>{copy.reports.model}</dt>
            <dd>{String(result?.model_card?.model_id ?? copy.console.runPending)}</dd>
            <dt>{copy.reports.trainingSize}</dt>
            <dd>{String(result?.model_card?.training_size ?? "-")}</dd>
            <dt>{copy.reports.applicability}</dt>
            <dd>{String((result?.model_card?.applicability_domain as Record<string, unknown> | undefined)?.method ?? "-")}</dd>
          </dl>
        </section>
        <section className="report-panel">
          <h3>{copy.reports.scientificValidation}</h3>
          <dl className="model-dl">
            <dt>{copy.reports.validationStatus}</dt>
            <dd>{String(result?.validation_report?.status ?? copy.console.runPending)}</dd>
            <dt>{copy.reports.datasetSize}</dt>
            <dd>{String(result?.validation_report?.dataset_size ?? "-")}</dd>
            <dt>{copy.reports.split}</dt>
            <dd>{String(result?.validation_report?.split_summary?.method ?? "-")}</dd>
          </dl>
          <div className="metric-list">
            {Object.entries(result?.validation_report?.metrics ?? {}).slice(0, 6).map(([key, value]) => (
              <span key={key}>{key}: {String(value)}</span>
            ))}
          </div>
        </section>
        <section className="report-panel">
          <h3>{copy.reports.redesignReport}</h3>
          <dl className="model-dl">
            <dt>{copy.reports.redesignChildren}</dt>
            <dd>{String(result?.redesign_report?.created_children ?? 0)}</dd>
            <dt>{copy.reports.status}</dt>
            <dd>{String(result?.redesign_report?.schema ?? "-")}</dd>
          </dl>
          <div className="metric-list">
            {(result?.redesign_report?.comparisons ?? []).slice(0, 4).map((item, index) => (
              <span key={index}>
                {String(item["parent_candidate_id"] ?? "")} → {String(item["child_candidate_id"] ?? "")}: {String(item["reason"] ?? "")}
              </span>
            ))}
          </div>
        </section>
        <section className="report-panel">
          <h3>{copy.reports.thresholdRegistry}</h3>
          <div className="threshold-list">
            {Object.entries(result?.threshold_registry?.rules ?? {}).slice(0, 8).map(([id, rule]) => (
              <div key={id}>
                <strong>{String(rule.label ?? id)}</strong>
                <span>{String(rule.value)} {String(rule.units ?? "")}</span>
                <small>{String(rule.source ?? copy.reports.sourceRequired)}</small>
              </div>
            ))}
          </div>
        </section>
        <section className="report-panel">
          <h3>{copy.reports.agentTrace}</h3>
          <ol className="trace-list">
            {result?.agent_events?.length ? result.agent_events.map((event) => (
              <li key={`${event.step}-${event.phase}-${event.action}`}>
                <strong>{event.step}. {event.phase}</strong>
                <span>{event.agent} / {event.action} / {event.status}</span>
                {event.candidate_id && <em>{event.candidate_id}</em>}
              </li>
            )) : <li>{copy.reports.pendingTrace}</li>}
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

function buildSeedPresets(referenceDrugs: ReferenceDrug[]) {
  const referenceSeeds: SeedPreset[] = referenceDrugs
    .filter((drug) => Boolean(drug.smiles))
    .map((drug) => ({
      id: `ref-${drug.drug_id}`,
      name: drug.name,
      smiles: drug.smiles,
      category: "EGFR reference seeds",
      target: "EGFR",
      disease: DEFAULT_REQUEST.disease,
      noteEn: drug.activity_evidence || "Known EGFR reference seed from the reference-drug layer.",
      noteKo: "EGFR reference drug layer에서 가져온 알려진 EGFR 계열 seed입니다.",
      source: "reference" as const,
      structureSvg: drug.structure_svg ?? null
    }));
  const seen = new Set<string>();
  return [...referenceSeeds, ...CURATED_SEED_PRESETS].filter((preset) => {
    const key = `${preset.name}:${preset.smiles}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function categoryLabel(category: string, locale: Locale) {
  if (locale === "en") return category;
  return {
    "EGFR reference seeds": "EGFR reference seed",
    "General drug-like controls": "일반 약물 control",
    "Negative / stress controls": "Negative / stress control"
  }[category] ?? category;
}

function graphScopeIds(
  nodes: Array<Record<string, unknown> & { id: string; type: string; label?: string }>,
  edges: Array<{ source: string; target: string; type: string; weight?: number }>,
  scope: string,
  selected: Candidate | null
) {
  if (scope === "all") return new Set(nodes.map((node) => node.id));
  if (scope === "summary") {
    const summaryTypes = new Set(["target", "disease", "threshold", "assay", "class_risk"]);
    return new Set(nodes.filter((node) => summaryTypes.has(node.type)).map((node) => node.id));
  }
  if (!selected) return new Set(nodes.filter((node) => ["target", "disease", "threshold", "assay", "class_risk"].includes(node.type)).map((node) => node.id));
  const ids = new Set<string>([
    "target_EGFR",
    "disease_context",
    `candidate_${selected.candidate_id}`,
    `descriptor_${selected.candidate_id}`,
    `prediction_${selected.candidate_id}`,
    `decision_${selected.candidate_id}`,
    `alert_${selected.candidate_id}`
  ]);
  for (let depth = 0; depth < 2; depth += 1) {
    for (const edge of edges) {
      if (ids.has(edge.source) || ids.has(edge.target)) {
        ids.add(edge.source);
        ids.add(edge.target);
      }
    }
  }
  return ids;
}

function graphLayout(nodes: Array<Record<string, unknown> & { id: string; type: string; label?: string }>) {
  const typeOrder = ["target", "disease", "candidate", "redesign_action", "descriptor", "model_prediction", "decision", "known_analog", "threshold", "assay", "class_risk", "structural_alert"];
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

function xyzDataUri(candidateId: string, atoms: ConformerPayload["atoms"], copy: Copy) {
  const body = [
    String(atoms.length),
    `${candidateId} ${copy.conformer.xyzComment}`,
    ...atoms.map((atom) => `${atom.element} ${atom.x.toFixed(4)} ${atom.y.toFixed(4)} ${atom.z.toFixed(4)}`)
  ].join("\n");
  return `data:chemical/x-xyz;charset=utf-8,${encodeURIComponent(body)}`;
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

function formatNumber(value: number | null | undefined, digits = 2) {
  if (typeof value !== "number" || Number.isNaN(value)) return "-";
  return value.toFixed(digits);
}

function profileLabel(profiles: Array<Record<string, unknown>>, id: string, copy: Copy) {
  const profile = profiles.find((item) => item.id === id);
  return profile ? localizedProfile(profile, copy).label : id;
}

function evidenceModeLabel(result: PipelineResult | null, request: RunRequest, copy: Copy) {
  const mode = result?.evidence_mode?.mode;
  if (mode) {
    return copy.console.evidenceModes[mode as keyof typeof copy.console.evidenceModes] ?? result?.evidence_mode?.label ?? mode;
  }
  return request.allow_network ? copy.console.liveEnabled : copy.console.cachedDemo;
}
