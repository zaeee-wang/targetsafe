import { useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import * as THREE from "three";
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Award,
  BarChart3,
  BrainCircuit,
  CheckCircle2,
  CircleDot,
  Cpu,
  Download,
  FileText,
  FlaskConical,
  GitBranch,
  Layers3,
  Loader2,
  Languages,
  Maximize2,
  Moon,
  Network,
  Plus,
  Play,
  RotateCcw,
  Save,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Sun,
  TestTube2,
  Trash2,
  X,
  ZoomIn,
  ZoomOut
} from "lucide-react";
import {
  checkMolecule,
  createRun,
  fetchCandidates,
  fetchConformer,
  fetchDepiction,
  fetchGpuDiagnostics,
  fetchKnownContext,
  fetchLlmProviders,
  fetchProfiles,
  fetchReferenceDrugs,
  fetchRuntimeStatus,
  fetchRunExamples,
  importLibrary,
  testLlmConnection
} from "./api";
import type {
  CandidatePage,
  Candidate,
  ConformerPayload,
  EvidenceGraph,
  KnownContext,
  LlmProvider,
  LlmTestResult,
  LibraryImportResult,
  MoleculeCheckResult,
  PipelineResult,
  ReferenceDrug,
  RunExample,
  RunRequest,
  RuntimeStatus,
  SavedMolecule,
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
  candidate_count: 96,
  compute_profile: "full-research",
  allow_network: true,
  use_llm: true,
  use_gpu: true,
  enable_conformers: true,
  library_sources: ["seed_analog", "chembl_target", "pubchem_reference"],
  library_limit: 2000,
  detailed_eval_limit: 300,
  display_limit: 96,
  conformer_limit: 24,
  uploaded_smiles: [],
  uploaded_library_id: null,
  llm_api_key: "",
  llm_provider: "openai",
  llm_base_url: "",
  llm_model: "gpt-4.1-mini",
  llm_custom_model: "",
  input_example_id: ""
};

const STATUS_ORDER: Status[] = ["Go", "Hold", "No-Go"];
const VIEWS = [
  { id: "console", icon: <Activity size={18} /> },
  { id: "judge", icon: <Award size={18} /> },
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
  const [navCollapsed, setNavCollapsed] = useState(() => window.localStorage.getItem("targetsafe-nav-collapsed") !== "false");
  const [request, setRequest] = useState<RunRequest>(DEFAULT_REQUEST);
  const [profiles, setProfiles] = useState<Array<Record<string, unknown>>>([]);
  const [referenceDrugs, setReferenceDrugs] = useState<ReferenceDrug[]>([]);
  const [runtimeStatus, setRuntimeStatus] = useState<RuntimeStatus | null>(null);
  const [result, setResult] = useState<PipelineResult | null>(null);
  const [selectedId, setSelectedId] = useState<string>("");
  const [activeView, setActiveView] = useState<ViewId>("console");
  const [moleculeView, setMoleculeView] = useState<MoleculeView>("2d");
  const [knownContext, setKnownContext] = useState<KnownContext | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>("");
  const copy = COPY[locale] as Copy;

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.lang = locale;
    window.localStorage.setItem("targetsafe-theme", theme);
    window.localStorage.setItem("targetsafe-locale", locale);
  }, [theme, locale]);

  useEffect(() => {
    window.localStorage.setItem("targetsafe-nav-collapsed", String(navCollapsed));
  }, [navCollapsed]);

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
    fetchRuntimeStatus().then(setRuntimeStatus).catch(() => setRuntimeStatus(null));
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
    const nextRequest = profileOverride ? { ...request, ...profileRequestDefaults(profileOverride), compute_profile: profileOverride } : request;
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
    <main className={`app-shell ${navCollapsed ? "nav-is-collapsed" : "nav-is-open"}`} data-theme={theme}>
      <NavRail
        activeView={activeView}
        onChange={setActiveView}
        result={result}
        copy={copy}
        collapsed={navCollapsed}
        onToggleCollapsed={() => setNavCollapsed((value) => !value)}
      />
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
            runtimeStatus={runtimeStatus}
            result={result}
            counts={counts}
            loading={loading}
            error={error}
            copy={copy}
            locale={locale}
            onRequestChange={setRequest}
            onRuntimeStatus={setRuntimeStatus}
            onRun={runTriage}
          />
        )}
        {activeView === "judge" && (
          <JudgeDemo
            result={result}
            counts={counts}
            loading={loading}
            copy={copy}
            locale={locale}
            onRun={runTriage}
            onOpenCandidate={selectCandidate}
            onOpenGraph={() => setActiveView("graph")}
            onOpenReports={() => setActiveView("reports")}
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
            onOpenAtlas={() => setActiveView("atlas")}
            onRun={() => runTriage()}
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
  copy,
  collapsed,
  onToggleCollapsed
}: {
  activeView: ViewId;
  onChange: (view: ViewId) => void;
  result: PipelineResult | null;
  copy: Copy;
  collapsed: boolean;
  onToggleCollapsed: () => void;
}) {
  return (
    <aside className={`nav-rail ${collapsed ? "collapsed" : "expanded"}`} aria-label={copy.brand.navAria}>
      <div className="brand-block">
        <div className="pulse-mark"><Activity size={18} /></div>
        <div>
          <span>Target-SAFE</span>
          <strong>{copy.brand.subtitle}</strong>
        </div>
      </div>
      <div className="nav-drawer-controls">
        <button className="icon-action" onClick={onToggleCollapsed} type="button" aria-label={collapsed ? copy.nav.expand : copy.nav.collapse}>
          {collapsed ? <ArrowRight size={17} /> : <ArrowLeft size={17} />}
        </button>
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
            <span>{copyText(copy, "views", view.id, fallbackViewLabel(view.id))}</span>
          </button>
        ))}
      </nav>
      <div className={`run-chip ${result ? "loaded" : "pending"}`}>
        <i aria-hidden="true" />
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
          onChange={(event) => {
            const profileId = event.target.value;
            onRequestChange({ ...request, ...profileRequestDefaults(profileId), compute_profile: profileId });
          }}
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

function InteractiveAtom() {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const [fallback, setFallback] = useState(false);

  useEffect(() => {
    const mount = mountRef.current;
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!mount || prefersReducedMotion) {
      setFallback(true);
      return;
    }

    let frame = 0;
    let renderer: THREE.WebGLRenderer;
    let disposed = false;
    const pointer = { x: 0, y: 0 };

    try {
      renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    } catch {
      setFallback(true);
      return;
    }

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
    camera.position.set(0, 0, 8);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setClearColor(0x000000, 0);
    mount.appendChild(renderer.domElement);

    const group = new THREE.Group();
    scene.add(group);

    const nucleus = new THREE.Mesh(
      new THREE.SphereGeometry(0.56, 48, 48),
      new THREE.MeshPhysicalMaterial({
        color: 0xeef7ff,
        emissive: 0x2766f8,
        emissiveIntensity: 0.28,
        roughness: 0.1,
        metalness: 0.02,
        transparent: true,
        opacity: 0.72,
        transmission: 0.35,
        thickness: 0.45
      })
    );
    group.add(nucleus);

    const orbitPalette = [0x36d7ff, 0x2766f8, 0xffffff, 0xffb84d, 0x7df9ff];
    const orbitLines: THREE.Line[] = [];
    const particles: THREE.Mesh[] = [];
    const particleGeometry = new THREE.SphereGeometry(0.035, 12, 12);

    for (let orbitIndex = 0; orbitIndex < 14; orbitIndex += 1) {
      const points: THREE.Vector3[] = [];
      const radiusX = 2.28 + (orbitIndex % 4) * 0.14;
      const radiusY = 0.76 + (orbitIndex % 5) * 0.06;
      const twist = orbitIndex * 0.41;
      for (let index = 0; index <= 220; index += 1) {
        const angle = (index / 220) * Math.PI * 2;
        points.push(new THREE.Vector3(
          Math.cos(angle) * radiusX,
          Math.sin(angle) * radiusY,
          Math.sin(angle * 2 + twist) * 0.08
        ));
      }
      const material = new THREE.LineBasicMaterial({
        color: orbitPalette[orbitIndex % orbitPalette.length],
        transparent: true,
        opacity: orbitIndex % 3 === 0 ? 0.68 : 0.42,
        blending: THREE.AdditiveBlending
      });
      const orbit = new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), material);
      orbit.rotation.set(
        orbitIndex * 0.34,
        orbitIndex * 0.19,
        (orbitIndex / 14) * Math.PI * 2
      );
      orbitLines.push(orbit);
      group.add(orbit);

      if (orbitIndex % 2 === 0) {
        const particle = new THREE.Mesh(
          particleGeometry,
          new THREE.MeshStandardMaterial({
            color: orbitPalette[(orbitIndex + 1) % orbitPalette.length],
            emissive: orbitPalette[(orbitIndex + 1) % orbitPalette.length],
            emissiveIntensity: 1.25,
            roughness: 0.15
          })
        );
        particles.push(particle);
        group.add(particle);
      }
    }

    scene.add(new THREE.AmbientLight(0xffffff, 0.72));
    const keyLight = new THREE.PointLight(0x6aa8ff, 3.6, 18);
    keyLight.position.set(2.6, 2.1, 3.8);
    scene.add(keyLight);
    const fillLight = new THREE.PointLight(0x36d7ff, 1.6, 14);
    fillLight.position.set(-2.4, -1.8, 2.6);
    scene.add(fillLight);
    const warmLight = new THREE.PointLight(0xffb84d, 0.9, 10);
    warmLight.position.set(0, -2.9, 2.2);
    scene.add(warmLight);

    const resize = () => {
      const rect = mount.getBoundingClientRect();
      const size = Math.max(220, Math.min(rect.width || 340, rect.height || 340));
      renderer.setSize(size, size, false);
      camera.aspect = 1;
      camera.updateProjectionMatrix();
    };
    const onPointerMove = (event: PointerEvent) => {
      const rect = mount.getBoundingClientRect();
      pointer.x = ((event.clientX - rect.left) / Math.max(rect.width, 1) - 0.5) * 0.7;
      pointer.y = ((event.clientY - rect.top) / Math.max(rect.height, 1) - 0.5) * 0.5;
    };
    const observer = new ResizeObserver(resize);
    observer.observe(mount);
    mount.addEventListener("pointermove", onPointerMove);
    resize();

    const animate = () => {
      if (disposed) return;
      const time = performance.now() * 0.001;
      group.rotation.y += 0.0034;
      group.rotation.x += (pointer.y - group.rotation.x) * 0.025;
      group.rotation.z += (pointer.x - group.rotation.z) * 0.022;
      orbitLines.forEach((orbit, index) => {
        orbit.rotation.z += 0.0008 + index * 0.00004;
      });
      particles.forEach((particle, index) => {
        const angle = time * (0.78 + index * 0.08) + index * 1.34;
        particle.position.set(
          Math.cos(angle) * (2.2 + (index % 3) * 0.12),
          Math.sin(angle) * (0.78 + (index % 4) * 0.07),
          Math.sin(angle * 1.7) * 0.42
        );
      });
      renderer.render(scene, camera);
      frame = requestAnimationFrame(animate);
    };
    frame = requestAnimationFrame(animate);

    return () => {
      disposed = true;
      cancelAnimationFrame(frame);
      observer.disconnect();
      mount.removeEventListener("pointermove", onPointerMove);
      scene.traverse((object) => {
        const mesh = object as THREE.Mesh;
        mesh.geometry?.dispose?.();
        const material = mesh.material as THREE.Material | THREE.Material[] | undefined;
        if (Array.isArray(material)) {
          material.forEach((item) => item.dispose());
        } else {
          material?.dispose?.();
        }
      });
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, []);

  return (
    <div className="orbital-visual atom3d-stage" aria-label="Interactive molecular evidence orbital">
      <div className="atom-glass-sheen" aria-hidden="true" />
      <div ref={mountRef} className="atom3d-canvas" aria-hidden="true" />
      {fallback && (
        <div className="atom3d-fallback" aria-hidden="true">
          <span />
          <i />
          <b />
        </div>
      )}
    </div>
  );
}

function RunConsole({
  request,
  profiles,
  referenceDrugs,
  runtimeStatus,
  result,
  counts,
  loading,
  error,
  copy,
  locale,
  onRequestChange,
  onRuntimeStatus,
  onRun
}: {
  request: RunRequest;
  profiles: Array<Record<string, unknown>>;
  referenceDrugs: ReferenceDrug[];
  runtimeStatus: RuntimeStatus | null;
  result: PipelineResult | null;
  counts: Record<Status, number>;
  loading: boolean;
  error: string;
  copy: Copy;
  locale: Locale;
  onRequestChange: (request: RunRequest) => void;
  onRuntimeStatus: (status: RuntimeStatus | null) => void;
  onRun: (profileOverride?: string) => void;
}) {
  const [seedDrawerOpen, setSeedDrawerOpen] = useState(false);
  const [exampleDrawerOpen, setExampleDrawerOpen] = useState(false);
  const [uploadText, setUploadText] = useState("");
  const [uploadResult, setUploadResult] = useState<LibraryImportResult | null>(null);
  const [uploading, setUploading] = useState(false);
  const [llmProviders, setLlmProviders] = useState<LlmProvider[]>([]);
  const [runExamples, setRunExamples] = useState<RunExample[]>([]);
  const [llmTest, setLlmTest] = useState<LlmTestResult | null>(null);
  const [llmTesting, setLlmTesting] = useState(false);
  const seedOptions = useMemo(() => buildSeedPresets(referenceDrugs), [referenceDrugs]);
  const activeRuntime = result?.runtime_status ?? runtimeStatus;
  const selectedProfile = localizedProfile(
    profiles.find((profile) => String(profile.id) === request.compute_profile) ?? { id: request.compute_profile },
    copy
  );
  const selectedProvider = llmProviders.find((provider) => provider.id === request.llm_provider) ?? llmProviders[0];
  const selectedProviderModels = selectedProvider?.models?.length ? selectedProvider.models : ["custom"];
  const [consoleSectionOpen, setConsoleSectionOpen] = useState<Record<string, boolean>>({
    inputs: true,
    design: true,
    library: true,
    llm: false
  });

  function toggleConsoleSection(id: string) {
    setConsoleSectionOpen((current) => ({ ...current, [id]: !current[id] }));
  }

  useEffect(() => {
    fetchLlmProviders().then(setLlmProviders).catch(() => {
      setLlmProviders([
        { id: "deterministic", label: "Deterministic fallback", requires_key: false, default_model: "none", models: ["none"], base_url: "", description: "No external LLM call." },
        { id: "openai", label: "OpenAI", requires_key: true, default_model: "gpt-4.1-mini", models: ["gpt-4.1-mini", "gpt-4.1", "o4-mini", "custom"], base_url: "https://api.openai.com/v1", description: "OpenAI chat-completions compatible endpoint." },
        { id: "anthropic", label: "Anthropic", requires_key: true, default_model: "claude-3-5-sonnet-latest", models: ["claude-3-5-sonnet-latest", "claude-3-5-haiku-latest", "custom"], base_url: "https://api.anthropic.com/v1", description: "Anthropic Messages API endpoint." },
        { id: "openai-compatible", label: "OpenAI-compatible custom", requires_key: true, default_model: "custom", models: ["custom"], base_url: "", description: "Custom /chat/completions compatible endpoint." }
      ]);
    });
    fetchRunExamples().then(setRunExamples).catch(() => setRunExamples([]));
  }, []);

  async function handleLibraryImport() {
    if (!uploadText.trim()) return;
    setUploading(true);
    try {
      const payload = await importLibrary("Pasted compound library", uploadText);
      setUploadResult(payload);
      onRequestChange({
        ...request,
        uploaded_library_id: payload.library_id,
        library_sources: Array.from(new Set([...request.library_sources, "uploaded"]))
      });
    } catch {
      setUploadResult(null);
    } finally {
      setUploading(false);
    }
  }

  async function refreshRuntimeStatus() {
    try {
      const [status, diagnostics] = await Promise.all([fetchRuntimeStatus(), fetchGpuDiagnostics()]);
      onRuntimeStatus({ ...status, gpu_diagnostics: diagnostics });
    } catch {
      onRuntimeStatus(null);
    }
  }

  function applySeedPreset(preset: SeedPreset) {
    onRequestChange({
      ...request,
      seed_smiles: preset.smiles,
      target: preset.target === "EGFR" ? "EGFR" : request.target,
      disease: preset.disease ?? request.disease
    });
    setSeedDrawerOpen(false);
  }

  function applyRunExample(example: RunExample) {
    onRequestChange({
      ...request,
      ...example.request,
      llm_api_key: request.llm_api_key,
      llm_provider: request.llm_provider,
      llm_model: request.llm_model,
      llm_custom_model: request.llm_custom_model,
      llm_base_url: request.llm_base_url,
      input_example_id: example.id
    });
    setExampleDrawerOpen(false);
  }

  async function handleLlmTest() {
    setLlmTesting(true);
    try {
      setLlmTest(await testLlmConnection(request));
    } catch (exc) {
      setLlmTest({
        ok: false,
        provider: request.llm_provider,
        used: false,
        message: exc instanceof Error ? exc.message : "LLM connection test failed."
      });
    } finally {
      setLlmTesting(false);
    }
  }

  return (
    <section className="view-frame console-view">
      <div className="console-stage">
        <InteractiveAtom />
        <div className="console-copy">
          <p className="eyebrow">{copy.console.eyebrow}</p>
          <h2>{copy.console.heading}</h2>
          <p>{copy.console.body}</p>
          <div className="run-action-row">
            <button className="primary-action large" onClick={() => onRun()} disabled={loading} type="button">
              {loading ? <Loader2 className="spin" size={18} /> : <Play size={18} />}
              {copyText(copy, "console", "runSelected", "Run {profile}").replace("{profile}", selectedProfile.label)}
            </button>
            <button className="ghost-action" onClick={() => onRun("cpu-demo")} disabled={loading} type="button">
              {copyText(copy, "console", "stableDemo", "Stable CPU demo")}
            </button>
            <button className="ghost-action" onClick={() => setExampleDrawerOpen(true)} type="button">
              <TestTube2 size={16} />
              {copyText(copy, "console", "openTargetScenarios", "Open target scenarios")}
            </button>
          </div>
        </div>
      </div>

      <GuidedSetupStrip
        request={request}
        result={result}
        loading={loading}
        copy={copy}
        onOpenExamples={() => setExampleDrawerOpen(true)}
      />

      <div className="console-grid">
        <section className="input-deck">
          <ConsoleSection
            id="inputs"
            title={copyText(copy, "console", "inputsSection", "Inputs")}
            open={consoleSectionOpen.inputs}
            onToggle={toggleConsoleSection}
          >
            <div className="console-section-grid">
          <label>
            {copy.console.disease}
            <input
              value={request.disease}
              placeholder="EGFR mutation-positive NSCLC"
              onChange={(event) => onRequestChange({ ...request, disease: event.target.value })}
            />
            <small className="field-help">{copyText(copy, "console", "diseaseHelp", "Clinical or research context used for evidence search and report framing.")}</small>
          </label>
          <label>
            {copy.console.target}
            <input
              value={request.target}
              placeholder="EGFR"
              onChange={(event) => onRequestChange({ ...request, target: event.target.value })}
            />
            <small className="field-help">{copyText(copy, "console", "targetHelp", "Molecular target. EGFR is the validated scoring pilot in this MVP.")}</small>
          </label>
          <div className="wide field-block">
            <div className="field-label-row">
              <span>{copy.console.seed}</span>
              <button className="inline-action" onClick={() => setSeedDrawerOpen(true)} type="button">
                <Layers3 size={15} />
                {copy.seedDrawer.open}
              </button>
            </div>
            <textarea
              aria-label={copy.console.seed}
              value={request.seed_smiles}
              placeholder="Paste one valid SMILES, or choose from the library drawer."
              onChange={(event) => onRequestChange({ ...request, seed_smiles: event.target.value })}
            />
            <small className="field-help">{copyText(copy, "console", "seedHelp", "Starting molecule used to generate seed analogs; invalid SMILES should become No-Go controls.")}</small>
          </div>
          <label className="wide">
            {copy.console.goal}
            <textarea
              value={request.optimization_goal}
              placeholder="Maintain drug-likeness, reduce toxicity alerts, preserve target evidence confidence"
              onChange={(event) => onRequestChange({ ...request, optimization_goal: event.target.value })}
            />
            <small className="field-help">{copyText(copy, "console", "goalHelp", "Natural-language optimization intent used by the planner and report summarizer; final decisions remain tool-gated.")}</small>
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
              <small className="field-help">{copyText(copy, "console", "candidatesHelp", "Requested candidate count before library staging and detailed evaluation limits.")}</small>
            </label>
            <Toggle label={copy.console.liveApis} value={request.allow_network} onChange={(allow_network) => onRequestChange({ ...request, allow_network })} />
            <Toggle label={copy.console.gpu} value={request.use_gpu} onChange={(use_gpu) => onRequestChange({ ...request, use_gpu })} />
            <Toggle label={copy.console.llm} value={request.use_llm} onChange={(use_llm) => onRequestChange({ ...request, use_llm })} />
          </div>
            </div>
          </ConsoleSection>
          <ConsoleSection
            id="design"
            title={copyText(copy, "console", "designBenchSection", "Molecule Design Bench")}
            open={consoleSectionOpen.design}
            onToggle={toggleConsoleSection}
          >
            <MoleculeDesignBench
              copy={copy}
              locale={locale}
              target={request.target}
              seedSmiles={request.seed_smiles}
              onUseAsSeed={(seed_smiles) => onRequestChange({ ...request, seed_smiles })}
            />
          </ConsoleSection>
          <ConsoleSection
            id="library"
            title={copyText(copy, "console", "librarySection", "Library")}
            open={consoleSectionOpen.library}
            onToggle={toggleConsoleSection}
          >
            <div className="console-section-grid">
          <div className="library-controls wide">
            <label>
              {copyText(copy, "console", "libraryLimit", "Library limit")}
              <input
                type="number"
                min={20}
                max={10000}
                value={request.library_limit}
                onChange={(event) => onRequestChange({ ...request, library_limit: Number(event.target.value) })}
              />
            </label>
            <label>
              {copyText(copy, "console", "detailedEvalLimit", "Detailed eval limit")}
              <input
                type="number"
                min={20}
                max={2000}
                value={request.detailed_eval_limit}
                onChange={(event) => onRequestChange({ ...request, detailed_eval_limit: Number(event.target.value) })}
              />
            </label>
            <label>
              {copyText(copy, "console", "displayLimit", "Rendered structures")}
              <input
                type="number"
                min={10}
                max={500}
                value={request.display_limit}
                onChange={(event) => onRequestChange({ ...request, display_limit: Number(event.target.value) })}
              />
            </label>
          </div>
          <div className="library-source-row wide">
            {["seed_analog", "chembl_target", "pubchem_reference", "uploaded"].map((source) => (
              <Toggle
                key={source}
                label={librarySourceLabel(source, copy)}
                value={request.library_sources.includes(source)}
                onChange={(checked) => {
                  const next = checked
                    ? Array.from(new Set([...request.library_sources, source]))
                    : request.library_sources.filter((item) => item !== source);
                  onRequestChange({ ...request, library_sources: next });
                }}
              />
            ))}
          </div>
          <div className="wide upload-panel">
            <label>
              {copyText(copy, "console", "uploadLibrary", "Paste SMILES library")}
              <textarea
                value={uploadText}
                placeholder={copyText(copy, "console", "uploadPlaceholder", "One SMILES per line, optionally: SMILES,name")}
                onChange={(event) => setUploadText(event.target.value)}
              />
            </label>
            <button className="ghost-action" onClick={handleLibraryImport} disabled={uploading || !uploadText.trim()} type="button">
              {uploading ? <Loader2 className="spin" size={16} /> : <Layers3 size={16} />}
              {copyText(copy, "console", "importLibrary", "Import pasted library")}
            </button>
            {uploadResult && (
              <span className="upload-result">
                {uploadResult.compound_count} {copyText(copy, "console", "importedCompounds", "compounds imported")} / {uploadResult.library_id}
              </span>
            )}
          </div>
            </div>
          </ConsoleSection>
          <ConsoleSection
            id="llm"
            title={copyText(copy, "console", "llmSection", "LLM / API")}
            open={consoleSectionOpen.llm}
            onToggle={toggleConsoleSection}
          >
          <div className="api-key-panel wide">
            <label>
              {copyText(copy, "console", "llmProvider", "LLM provider")}
              <select
                value={request.llm_provider}
                onChange={(event) => {
                  const provider = llmProviders.find((item) => item.id === event.target.value);
                  onRequestChange({
                    ...request,
                    llm_provider: event.target.value,
                    llm_model: provider?.default_model ?? "custom",
                    llm_base_url: provider?.base_url ?? "",
                    llm_custom_model: ""
                  });
                  setLlmTest(null);
                }}
              >
                {llmProviders.map((provider) => (
                  <option key={provider.id} value={provider.id}>{provider.label}</option>
                ))}
              </select>
              <small className="field-help">{selectedProvider?.description ?? "Optional LLM lane; deterministic fallback works without a key."}</small>
            </label>
            <label>
              {copyText(copy, "console", "llmModel", "LLM model")}
              <select
                value={request.llm_model}
                onChange={(event) => {
                  onRequestChange({ ...request, llm_model: event.target.value });
                  setLlmTest(null);
                }}
              >
                {selectedProviderModels.map((model) => <option key={model} value={model}>{model}</option>)}
              </select>
            </label>
            {(request.llm_model === "custom" || request.llm_provider === "openai-compatible") && (
              <label>
                {copyText(copy, "console", "llmCustomModel", "Custom model")}
                <input
                  value={request.llm_custom_model}
                  placeholder="provider-model-name"
                  onChange={(event) => onRequestChange({ ...request, llm_custom_model: event.target.value })}
                />
              </label>
            )}
            <label>
              {copyText(copy, "console", "llmApiKey", "LLM API key")}
              <input
                type="password"
                autoComplete="off"
                value={request.llm_api_key}
                placeholder={copyText(copy, "console", "llmApiKeyPlaceholder", "Optional; leave blank for deterministic fallback")}
                onChange={(event) => {
                  onRequestChange({ ...request, llm_api_key: event.target.value });
                  setLlmTest(null);
                }}
              />
            </label>
            <label>
              {copyText(copy, "console", "llmBaseUrl", "Provider base URL")}
              <input
                value={request.llm_base_url}
                placeholder={selectedProvider?.base_url || "https://api.openai.com/v1"}
                onChange={(event) => onRequestChange({ ...request, llm_base_url: event.target.value })}
              />
            </label>
            <button className="ghost-action" onClick={handleLlmTest} disabled={llmTesting || request.llm_provider === "deterministic"} type="button">
              {llmTesting ? <Loader2 className="spin" size={16} /> : <Network size={16} />}
              {copyText(copy, "console", "testLlm", "Test LLM connection")}
            </button>
            {llmTest && <span className={`connection-result ${llmTest.ok ? "ok" : "fail"}`}>{llmTest.message}</span>}
            <p>{copyText(copy, "console", "llmKeyNote", "The key is sent only with the run request and is not returned in reports or stored in run results.")}</p>
          </div>
          </ConsoleSection>
        </section>

        <section className="status-deck">
          <Metric icon={<Cpu />} label={copy.console.computeProfile} value={profileLabel(profiles, request.compute_profile, copy)} />
          <Metric icon={<TestTube2 />} label={copy.console.evidenceMode} value={evidenceModeLabel(result, request, copy)} />
          <Metric icon={<CircleDot />} label={copyText(copy, "reports", "targetReadiness", "Target readiness")} value={targetReadinessLabel(result)} />
          <Metric icon={<Network />} label={copy.console.evidenceGraph} value={result ? `${result.evidence_graph.summary.node_count} nodes` : copy.console.runPending} />
          <div className="status-strip">
            {STATUS_ORDER.map((status) => (
              <div className={`status-pill ${statusClass(status)}`} key={status}>
                <span>{statusLabel(status, copy)}</span>
                <strong>{counts[status]}</strong>
              </div>
            ))}
          </div>
          <div className="side-rulebook">
            <p className="eyebrow">{copyText(copy, "reports", "decisionRulebook", "Decision rulebook")}</p>
            <div>
              <strong>Go</strong>
              <span>{copyText(copy, "reports", "goRule", "All hard gates pass and evidence is sufficient.")}</span>
            </div>
            <div>
              <strong>Hold</strong>
              <span>{copyText(copy, "reports", "holdRule", "At least one review gate needs more evidence.")}</span>
            </div>
            <div>
              <strong>No-Go</strong>
              <span>{copyText(copy, "reports", "nogoRule", "Invalid structure, severe alert, or hard blocker.")}</span>
            </div>
          </div>
          {error && <div className="error-box">{error}</div>}
        </section>
      </div>
      <ExecutionRealityPanel
        request={request}
        result={result}
        runtimeStatus={activeRuntime}
        copy={copy}
        onRefresh={refreshRuntimeStatus}
      />
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
      {exampleDrawerOpen && (
        <ExampleDrawer
          examples={runExamples}
          copy={copy}
          onApply={applyRunExample}
          onClose={() => setExampleDrawerOpen(false)}
        />
      )}
    </section>
  );
}

function ConsoleSection({
  id,
  title,
  open,
  onToggle,
  children
}: {
  id: string;
  title: string;
  open: boolean;
  onToggle: (id: string) => void;
  children: ReactNode;
}) {
  return (
    <section className={`console-section ${open ? "open" : "closed"}`}>
      <button className="console-section-trigger" onClick={() => onToggle(id)} type="button" aria-expanded={open}>
        <span>{title}</span>
        <b>{open ? "-" : "+"}</b>
      </button>
      {open && <div className="console-section-body">{children}</div>}
    </section>
  );
}

function MoleculeDesignBench({
  copy,
  locale,
  target,
  seedSmiles,
  onUseAsSeed
}: {
  copy: Copy;
  locale: Locale;
  target: string;
  seedSmiles: string;
  onUseAsSeed: (smiles: string) => void;
}) {
  const [name, setName] = useState("");
  const [smiles, setSmiles] = useState(seedSmiles);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<MoleculeCheckResult | null>(null);
  const [saved, setSaved] = useState<SavedMolecule[]>(() => loadSavedMolecules());

  useEffect(() => {
    if (!smiles.trim()) setSmiles(seedSmiles);
  }, [seedSmiles]);

  function persist(next: SavedMolecule[]) {
    setSaved(next);
    window.localStorage.setItem("targetsafe-saved-molecules", JSON.stringify(next.slice(0, 24)));
  }

  async function handleCheck() {
    if (!smiles.trim()) return;
    setChecking(true);
    setError("");
    try {
      setResult(await checkMolecule(smiles, name, target));
    } catch (exc) {
      setResult(null);
      setError(exc instanceof Error ? exc.message : copyText(copy, "console", "designCheckFailed", "Molecule check failed."));
    } finally {
      setChecking(false);
    }
  }

  function handleSave() {
    if (!result?.valid) return;
    const item: SavedMolecule = {
      id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
      name: result.name || name || copyText(copy, "console", "designUntitled", "Untitled molecule"),
      smiles: result.canonical_smiles || result.input_smiles,
      target: result.target,
      viability: result.viability,
      saved_at: new Date().toISOString(),
      structure_svg: result.structure_svg
    };
    persist([item, ...saved.filter((savedItem) => savedItem.smiles !== item.smiles)]);
  }

  return (
    <div className="design-bench">
      <div className="bench-editor">
        <div>
          <p className="eyebrow">{copyText(copy, "console", "designBenchEyebrow", "Research workspace")}</p>
          <h3>{copyText(copy, "console", "designBenchTitle", "Check, save, and reuse molecule ideas.")}</h3>
          <p>{copyText(copy, "console", "designBenchBody", "Paste or edit a SMILES idea, run a quick structure sanity check, then save plausible seeds for later triage.")}</p>
        </div>
        <label>
          {copyText(copy, "console", "designName", "Molecule name")}
          <input value={name} placeholder="EGFR idea A1" onChange={(event) => setName(event.target.value)} />
        </label>
        <label className="wide">
          {copyText(copy, "console", "designSmiles", "Design SMILES")}
          <textarea value={smiles} placeholder="Paste, edit, or compose a candidate SMILES" onChange={(event) => setSmiles(event.target.value)} />
        </label>
        <div className="bench-actions">
          <button className="primary-action" type="button" onClick={handleCheck} disabled={checking || !smiles.trim()}>
            {checking ? <Loader2 className="spin" size={16} /> : <FlaskConical size={16} />}
            {copyText(copy, "console", "designCheck", "Check feasibility")}
          </button>
          <button className="ghost-action" type="button" onClick={() => setSmiles(seedSmiles)}>
            <Plus size={16} />
            {copyText(copy, "console", "designLoadSeed", "Load current seed")}
          </button>
          <button className="ghost-action" type="button" onClick={() => result?.can_use_as_seed && onUseAsSeed(result.canonical_smiles || result.input_smiles)} disabled={!result?.can_use_as_seed}>
            <Play size={16} />
            {copyText(copy, "console", "designUseAsSeed", "Use as seed")}
          </button>
          <button className="ghost-action" type="button" onClick={handleSave} disabled={!result?.valid}>
            <Save size={16} />
            {copyText(copy, "console", "designSave", "Save molecule")}
          </button>
        </div>
        {error && <p className="error-box">{error}</p>}
      </div>

      <div className="bench-result">
        {result ? (
          <>
            <div className="bench-figure">
              <StructureImage
                src={result.structure_svg}
                alt={`${result.name || "molecule"} structure`}
                smiles={result.canonical_smiles || result.input_smiles}
                fallback={copy.atlas.noStructure}
              />
            </div>
            <div className={`bench-verdict ${result.viability}`}>
              <strong>{moleculeViabilityLabel(result.viability, copy)}</strong>
              <span>{result.valid ? result.canonical_smiles : result.input_smiles}</span>
            </div>
            <dl className="bench-descriptors">
              <div><dt>MW</dt><dd>{formatNumber(result.descriptors.molecular_weight, 1)}</dd></div>
              <div><dt>LogP</dt><dd>{formatNumber(result.descriptors.logp, 2)}</dd></div>
              <div><dt>QED</dt><dd>{formatNumber(result.descriptors.qed, 2)}</dd></div>
              <div><dt>SA</dt><dd>{formatNumber(result.descriptors.sa_score, 2)}</dd></div>
            </dl>
            <ul className="compact-list">
              {result.reasons.map((reason) => <li key={reason}>{localizeBackendText(reason, locale)}</li>)}
              {result.suggestions.map((suggestion) => <li key={suggestion}>{localizeBackendText(suggestion, locale)}</li>)}
            </ul>
            <p className="context-note">{localizeBackendText(result.interpretation, locale)}</p>
          </>
        ) : (
          <div className="bench-placeholder">
            <FlaskConical size={28} />
            <strong>{copyText(copy, "console", "designPlaceholderTitle", "No molecule checked yet")}</strong>
            <p>{copyText(copy, "console", "designPlaceholderText", "Run a quick check to see structure validity, descriptor limits, alerts, and whether it can become a seed.")}</p>
          </div>
        )}
      </div>

      <div className="saved-molecules">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">{copyText(copy, "console", "designSavedEyebrow", "Saved workspace")}</p>
            <h3>{copyText(copy, "console", "designSavedTitle", "Molecules to revisit")}</h3>
          </div>
          <span>{saved.length}</span>
        </div>
        {saved.length ? (
          <div className="saved-molecule-grid">
            {saved.slice(0, 8).map((item) => (
              <article key={item.id}>
                <span className="saved-structure">
                  <StructureImage src={item.structure_svg} alt={`${item.name} structure`} smiles={item.smiles} fallback={copy.atlas.noStructure} />
                </span>
                <div>
                  <strong>{item.name}</strong>
                  <small>{moleculeViabilityLabel(item.viability, copy)} / {item.target}</small>
                  <code>{item.smiles}</code>
                </div>
                <button type="button" className="icon-button" onClick={() => onUseAsSeed(item.smiles)} aria-label={copyText(copy, "console", "designUseAsSeed", "Use as seed")}>
                  <Play size={14} />
                </button>
                <button type="button" className="icon-button" onClick={() => persist(saved.filter((candidate) => candidate.id !== item.id))} aria-label={copyText(copy, "console", "designDelete", "Delete saved molecule")}>
                  <Trash2 size={14} />
                </button>
              </article>
            ))}
          </div>
        ) : (
          <p className="context-note">{copyText(copy, "console", "designNoSaved", "Saved molecules stay in this browser so research ideas are not lost between runs.")}</p>
        )}
      </div>
    </div>
  );
}

function GuidedSetupStrip({
  request,
  result,
  loading,
  copy,
  onOpenExamples
}: {
  request: RunRequest;
  result: PipelineResult | null;
  loading: boolean;
  copy: Copy;
  onOpenExamples: () => void;
}) {
  const summary = buildGuidedRunSummary(result, copy);
  const steps = [
    {
      index: "01",
      title: copyText(copy, "console", "guideScope", "Select evidence scope"),
      text: request.allow_network
        ? copyText(copy, "console", "guideScopeLive", "Live public evidence is requested; fallback will be labelled if APIs fail.")
        : copyText(copy, "console", "guideScopeDemo", "Offline demo evidence is selected for stable rehearsal.")
    },
    {
      index: "02",
      title: copyText(copy, "console", "guideCompute", "Choose compute lane"),
      text: request.use_gpu
        ? copyText(copy, "console", "guideComputeGpu", "GPU lane is requested and runtime truth will show whether it was actually used.")
        : copyText(copy, "console", "guideComputeCpu", "CPU lane keeps the run reproducible without local acceleration.")
    },
    {
      index: "03",
      title: copyText(copy, "console", "guideRun", "Run staged triage"),
      text: loading
        ? copyText(copy, "console", "guideRunning", "Candidates are moving through validity, descriptors, QSAR, evidence, and critic review.")
        : copyText(copy, "console", "guideRunReady", "Run the selected profile or open a test case to verify expected behavior.")
    },
    {
      index: "04",
      title: copyText(copy, "console", "guideInspect", "Inspect first candidate"),
      text: summary.firstInspection
    }
  ];
  return (
    <section className="guided-strip" aria-label={copyText(copy, "console", "guidedSetup", "Guided setup")}>
      <div className="flow-heading">
        <span className="eyebrow">{copyText(copy, "console", "startHere", "Start here")}</span>
        <strong>{summary.title}</strong>
        <button className="ghost-action compact" onClick={onOpenExamples} type="button">
          <TestTube2 size={14} />
          {copyText(copy, "console", "openTargetScenarios", "Open target scenarios")}
        </button>
      </div>
      <div className="workflow-cards">
        {steps.map((step) => (
          <article className="workflow-card" key={step.index}>
            <span>{step.index}</span>
            <h3>{step.title}</h3>
            <p>{step.text}</p>
          </article>
        ))}
      </div>
      {result && (
        <div className="guided-run-summary">
          <div>
            <small>{copyText(copy, "console", "whatHappened", "What happened")}</small>
            <strong>{summary.whatHappened}</strong>
          </div>
          <div>
            <small>{copyText(copy, "console", "whyHold", "Why many candidates are Hold")}</small>
            <strong>{summary.whyHold}</strong>
          </div>
          <div>
            <small>{copyText(copy, "console", "needsValidation", "What needs validation")}</small>
            <strong>{summary.needsValidation}</strong>
          </div>
        </div>
      )}
    </section>
  );
}

function JudgeDemo({
  result,
  counts,
  loading,
  copy,
  locale,
  onRun,
  onOpenCandidate,
  onOpenGraph,
  onOpenReports
}: {
  result: PipelineResult | null;
  counts: Record<Status, number>;
  loading: boolean;
  copy: Copy;
  locale: Locale;
  onRun: (profileOverride?: string) => void;
  onOpenCandidate: (id: string, view?: ViewId) => void;
  onOpenGraph: () => void;
  onOpenReports: () => void;
}) {
  const summary = buildJudgeDemoSummary(result, counts, copy);
  if (!result) {
    return (
      <section className="view-frame judge-view">
        <div className="judge-hero">
          <EvidenceWave />
          <div>
            <p className="eyebrow">Judge Demo</p>
            <h2>{copyText(copy, "judge", "emptyHeading", "Show the agentic triage story after one run.")}</h2>
            <p>{copyText(copy, "judge", "emptyBody", "Run Full research for a high-fidelity demo, or use Stable CPU demo when network/API conditions are uncertain.")}</p>
            <div className="run-action-row">
              <button className="primary-action large" onClick={() => onRun()} disabled={loading} type="button">
                {loading ? <Loader2 className="spin" size={18} /> : <Play size={18} />}
                {copyText(copy, "console", "runSelected", "Run Full research").replace("{profile}", "Full research")}
              </button>
              <button className="ghost-action" onClick={() => onRun("cpu-demo")} disabled={loading} type="button">
                {copyText(copy, "console", "stableDemo", "Stable CPU demo")}
              </button>
            </div>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="view-frame judge-view">
      <div className="judge-hero">
        <EvidenceWave />
        <div>
          <p className="eyebrow">Molecular Evidence Flow</p>
          <h2>{copyText(copy, "judge", "heading", "A judge-ready path from problem to defensible triage.")}</h2>
          <p>{copyText(copy, "judge", "body", "Target-SAFE narrows an early compound library by showing what was planned, which tools acted, what evidence was observed, and why each candidate is Go, Hold, or No-Go.")}</p>
          <div className="judge-actions">
            <button className="ghost-action" onClick={onOpenGraph} type="button"><GitBranch size={16} />{copy.graph.heading}</button>
            <button className="ghost-action" onClick={onOpenReports} type="button"><FileText size={16} />{copy.reports.heading}</button>
          </div>
        </div>
      </div>

      <div className="judge-metric-band">
        <MetricNumber label={copyText(copy, "judge", "problem", "Problem clarity")} value={copyText(copy, "judge", "problemValue", "Lead triage")} detail={copyText(copy, "judge", "problemDetail", "Not drug invention")} />
        <MetricNumber label={copyText(copy, "judge", "agenticLoop", "Agentic loop")} value={`${summary.eventCount}`} detail={copyText(copy, "judge", "events", "events recorded")} />
        <MetricNumber label={copyText(copy, "judge", "library", "Library screened")} value={formatInteger(result.library_report?.valid_unique_count)} detail={copyText(copy, "judge", "unique", "valid unique")} />
        <MetricNumber label={copyText(copy, "judge", "decisionMix", "Decision mix")} value={`${counts.Go}/${counts.Hold}/${counts["No-Go"]}`} detail="Go / Hold / No-Go" />
        <MetricNumber label={copyText(copy, "judge", "runtimeTruth", "Runtime truth")} value={summary.runtimeLabel} detail={summary.runtimeDetail} />
      </div>

      <div className="judge-section-grid">
        <section className="judge-panel wide">
          <span className="eyebrow">01 / Why this problem</span>
          <h3>{copyText(copy, "judge", "whyProblemTitle", "Generated candidates are cheap; defensible prioritization is not.")}</h3>
          <p>{copyText(copy, "judge", "whyProblemBody", "The system is designed to show validity, drug-likeness, uncertainty, applicability domain, evidence mode, and next validation before anyone treats a molecule as promising.")}</p>
        </section>
        <section className="judge-panel">
          <span className="eyebrow">02 / Agentic loop</span>
          <AgentLoopTimeline result={result} />
        </section>
        <section className="judge-panel">
          <span className="eyebrow">03 / Evaluation criteria</span>
          <div className="criteria-map">
            {summary.criteriaMap.map((item) => (
              <div key={item.label}>
                <strong>{item.label}</strong>
                <span>{item.evidence}</span>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="judge-panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">04 / Three candidate stories</span>
            <h3>{copyText(copy, "judge", "candidateStories", "One Go, one Hold, one No-Go when available.")}</h3>
          </div>
        </div>
        <div className="story-grid">
          {summary.stories.map((story) => (
            <CandidateStoryCard
              key={story.status}
              story={story}
              copy={copy}
              locale={locale}
              onOpenCandidate={onOpenCandidate}
            />
          ))}
        </div>
      </section>

      <div className="judge-section-grid">
        <section className="judge-panel">
          <span className="eyebrow">05 / Redesign loop</span>
          <h3>{formatInteger(result.redesign_report?.created_children)} {copyText(copy, "judge", "redesignChildren", "critic-triggered children")}</h3>
          <p>{copyText(copy, "judge", "redesignBody", "Critic findings can become constrained analog suggestions, then those children are re-evaluated rather than accepted on narrative alone.")}</p>
          <div className="metric-list">
            {(result.redesign_report?.comparisons ?? []).slice(0, 4).map((item, index) => (
              <span key={index}>{String(item.parent_candidate_id ?? "")} {"->"} {String(item.child_candidate_id ?? "")}</span>
            ))}
          </div>
        </section>
        <section className="judge-panel">
          <span className="eyebrow">06 / Contribution</span>
          <h3>{copyText(copy, "judge", "contributionTitle", "Transparent narrowing of early lead review.")}</h3>
          <p>{copyText(copy, "judge", "contributionBody", "The contribution is not claiming efficacy. It is making the first review pass faster, auditable, and honest about uncertainty.")}</p>
        </section>
      </div>
    </section>
  );
}

function ExecutionRealityPanel({
  request,
  result,
  runtimeStatus,
  copy,
  onRefresh
}: {
  request: RunRequest;
  result: PipelineResult | null;
  runtimeStatus: RuntimeStatus | null;
  copy: Copy;
  onRefresh: () => void;
}) {
  const gpu = (result?.compute_profile?.gpu_status as Record<string, unknown> | undefined) ?? runtimeStatus?.gpu ?? {};
  const gpuDiagnostics = (result?.gpu_diagnostics as Record<string, unknown> | undefined) ?? runtimeStatus?.gpu_diagnostics ?? (gpu.diagnostics as Record<string, unknown> | undefined) ?? {};
  const systemGpu = (gpuDiagnostics.system_gpu as Record<string, unknown> | undefined) ?? {};
  const torchCuda = (gpuDiagnostics.torch_cuda as Record<string, unknown> | undefined) ?? {};
  const directml = (gpuDiagnostics.directml as Record<string, unknown> | undefined) ?? {};
  const llm = runtimeStatus?.llm ?? (result?.compute_profile?.llm_status as Record<string, unknown> | undefined) ?? {};
  const llmKeyProvided = Boolean(request.llm_api_key.trim());
  const llmAvailable = truthValue(llm, "configured") || llmKeyProvided;
  const library = result?.library_report;
  const evidence = result?.evidence_mode;
  const toolErrors = result?.tool_error_summary;
  const performance = result?.performance_summary;
  const cache = result?.cache_summary;
  const circuit = result?.api_circuit_breaker_summary;
  return (
    <section className="execution-reality">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">{copyText(copy, "console", "executionReality", "Execution reality")}</p>
          <h3>{copyText(copy, "console", "runtimeTruth", "Requested, available, and actually used resources")}</h3>
        </div>
        <button className="ghost-action" onClick={onRefresh} type="button">
          <RotateCcw size={15} />
          {copyText(copy, "console", "refreshRuntime", "Refresh runtime")}
        </button>
      </div>
      <div className="reality-grid">
        <RealityCard
          label="GPU"
          value={truthValue(gpu, "used") ? copyText(copy, "console", "used", "used") : truthValue(gpu, "available") ? copyText(copy, "console", "available", "available") : copyText(copy, "console", "fallback", "fallback")}
          detail={[
            `${copyText(copy, "console", "requested", "requested")}: ${request.use_gpu || request.compute_profile.includes("gpu") || request.compute_profile === "full-research" ? copy.profiles.on : copy.profiles.off}`,
            `${copyText(copy, "console", "device", "device")}: ${String(gpu.device_name ?? gpu.backend ?? "unknown")}`,
            String(gpu.fallback_reason ?? gpu.message ?? ""),
            String(gpu.action_hint ?? gpuDiagnostics.action_hint ?? "")
          ].filter(Boolean).join(" / ")}
        />
        <RealityCard
          label={copyText(copy, "console", "systemGpu", "System GPU detected")}
          value={truthValue(systemGpu, "detected") ? copyText(copy, "console", "available", "available") : copyText(copy, "console", "fallback", "fallback")}
          detail={String(systemGpu.message ?? "nvidia-smi diagnostics pending.")}
        />
        <RealityCard
          label={copyText(copy, "console", "torchCuda", "Torch CUDA usable")}
          value={truthValue(torchCuda, "usable") ? copyText(copy, "console", "available", "available") : copyText(copy, "console", "fallback", "fallback")}
          detail={[String(torchCuda.message ?? ""), `DirectML: ${truthValue(directml, "usable") ? "usable" : "not usable"}`].filter(Boolean).join(" / ")}
        />
        <RealityCard
          label="LLM"
          value={truthValue(llm, "used") ? copyText(copy, "console", "used", "used") : llmAvailable ? copyText(copy, "console", "available", "available") : copyText(copy, "console", "fallback", "fallback")}
          detail={[
            `${copyText(copy, "console", "requested", "requested")}: ${request.use_llm || request.compute_profile === "api-assisted" || request.compute_profile === "full-research" ? copy.profiles.on : copy.profiles.off}`,
            `provider: ${request.llm_provider}`,
            llmKeyProvided ? copyText(copy, "console", "llmKeyProvided", "API key provided in the run form.") : String(llm.message ?? "LLM key status unknown.")
          ].join(" / ")}
        />
        <RealityCard
          label={copy.console.evidenceMode}
          value={evidence?.label ?? evidenceModeLabel(result, request, copy)}
          detail={evidence?.interpretation ?? copyText(copy, "console", "publicApiNoKey", "Public evidence APIs do not require a user-provided key; API failures fall back to cache or demo evidence.")}
        />
        <RealityCard
          label={copyText(copy, "console", "libraryScale", "Library scale")}
          value={`${formatInteger(library?.valid_unique_count)} ${copyText(copy, "console", "uniqueCompounds", "unique compounds")}`}
          detail={`${formatInteger(library?.detailed_evaluation_count)} ${copyText(copy, "console", "detailedEvaluated", "detailed evaluated")} / ${formatInteger(library?.display_asset_count)} ${copyText(copy, "console", "rendered", "rendered")}`}
        />
        <RealityCard
          label={copyText(copy, "console", "toolErrors", "Tool calls")}
          value={toolErrors?.has_live_errors ? copyText(copy, "console", "fallback", "fallback") : copyText(copy, "console", "available", "available")}
          detail={`${formatInteger(toolErrors?.total_calls)} calls / ${String(toolErrors?.interpretation ?? "Run pending.")}`}
        />
        <RealityCard
          label={copyText(copy, "console", "performance", "Performance")}
          value={performance?.duration_ms ? `${Math.round(Number(performance.duration_ms))} ms` : copy.console.runPending}
          detail={`${formatInteger(performance?.candidate_count)} candidates / ${formatInteger(performance?.tool_call_count)} tool calls`}
        />
        <RealityCard
          label={copyText(copy, "console", "cache", "Cache")}
          value={`${formatInteger(cache?.entries)} entries`}
          detail={`${formatInteger((cache?.runtime as Record<string, unknown> | undefined)?.hits)} hits / ${formatInteger((cache?.runtime as Record<string, unknown> | undefined)?.misses)} misses / ${formatInteger(cache?.stale_entries)} stale`}
        />
        <RealityCard
          label={copyText(copy, "console", "circuitBreaker", "API circuit breaker")}
          value={`${Object.keys((circuit?.open_sources as Record<string, unknown> | undefined) ?? {}).length} open`}
          detail={String(circuit?.policy ?? "Per-run source circuit status appears after a run.")}
        />
      </div>
    </section>
  );
}

function RealityCard({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <article className="reality-card">
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{detail}</p>
    </article>
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

function ExampleDrawer({
  examples,
  copy,
  onApply,
  onClose
}: {
  examples: RunExample[];
  copy: Copy;
  onApply: (example: RunExample) => void;
  onClose: () => void;
}) {
  const [scenarioDrawerFilter, setScenarioDrawerFilter] = useState("all");
  const modes = ["all", ...Array.from(new Set(examples.map((example) => String(example.scoring_mode ?? "scenario"))))];
  const visibleExamples = examples.filter((example) => scenarioDrawerFilter === "all" || String(example.scoring_mode ?? "scenario") === scenarioDrawerFilter);
  return (
    <div className="drawer-backdrop" role="presentation">
      <aside className="seed-drawer example-drawer" aria-label={copyText(copy, "console", "targetScenarioTitle", "Target Scenario Library")}>
        <div className="drawer-header">
          <div>
            <p className="eyebrow">{copyText(copy, "console", "targetScenarioEyebrow", "Target scenarios")}</p>
            <h3>{copyText(copy, "console", "targetScenarioTitle", "Target Scenario Library")}</h3>
            <p>{copyText(copy, "console", "targetScenarioBody", "Choose scored pilots, evidence-only targets, and stress controls. Non-EGFR targets show readiness without overclaiming confident Go decisions.")}</p>
          </div>
          <button className="icon-action" onClick={onClose} type="button" title={copy.seedDrawer.close}>
            <X size={18} />
          </button>
        </div>
        <div className="drawer-category-row example-filter-row">
          {modes.map((mode) => (
            <button className={scenarioDrawerFilter === mode ? "active" : ""} key={mode} onClick={() => setScenarioDrawerFilter(mode)} type="button">
              {mode === "all" ? copy.graph.all : mode.replaceAll("_", " ")}
            </button>
          ))}
        </div>
        <div className="example-grid">
          {visibleExamples.map((example) => (
            <article className="example-card" key={example.id}>
              <div className="example-card-top">
                <span>{example.id}</span>
                <b className={`scenario-badge ${scenarioClass(example.scoring_mode)}`}>{example.scoring_mode ?? "scenario"}</b>
              </div>
              <h4>{example.label}</h4>
              <p>{example.description}</p>
              {example.interpretation_limit && <p className="scenario-limit">{example.interpretation_limit}</p>}
              <div className="drawer-warning">
                <TestTube2 size={15} />
                <small>{example.expected_behavior}</small>
              </div>
              <dl className="example-dl">
                <dt>Disease</dt><dd>{String(example.request.disease ?? "-")}</dd>
                <dt>Target</dt><dd>{String(example.request.target ?? "-")}</dd>
                <dt>Seed</dt><dd><code>{String(example.request.seed_smiles ?? "-")}</code></dd>
                <dt>Sources</dt><dd>{(example.request.library_sources ?? []).join(", ")}</dd>
                <dt>Mode</dt><dd>{example.scoring_mode ?? "-"}</dd>
              </dl>
              <button className="primary-action" onClick={() => onApply(example)} type="button">
                {copyText(copy, "console", "applyExample", "Apply example")}
              </button>
            </article>
          ))}
          {!visibleExamples.length && <p className="context-note">{copyText(copy, "console", "examplesLoading", "Examples are loading or unavailable.")}</p>}
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

function LazyStructureImage({ candidate, fallback }: { candidate: Candidate; fallback: string }) {
  const [structure, setStructure] = useState(candidate.structure_svg);
  const [status, setStatus] = useState<"loading" | "rendered" | "fallback" | "failed">(candidate.structure_svg ? "rendered" : "fallback");
  useEffect(() => {
    setStructure(candidate.structure_svg);
    setStatus(candidate.structure_svg ? "rendered" : candidate.smiles ? "loading" : "fallback");
    if (candidate.structure_svg || !candidate.smiles) return;
    let cancelled = false;
    fetchDepiction(candidate.smiles)
      .then((payload) => {
        if (!cancelled) setStructure(payload.structure_svg);
        if (!cancelled) setStatus(payload.structure_svg ? "rendered" : "fallback");
      })
      .catch(() => {
        if (!cancelled) setStructure(null);
        if (!cancelled) setStatus("failed");
      });
    return () => {
      cancelled = true;
    };
  }, [candidate.candidate_id, candidate.smiles, candidate.structure_svg]);
  return (
    <StructureImage
      src={structure}
      alt={`${candidate.candidate_id} structure`}
      smiles={candidate.smiles}
      fallback={fallback}
      initialStatus={status}
    />
  );
}

function StructureImage({
  src,
  alt,
  smiles,
  fallback,
  initialStatus = "fallback"
}: {
  src?: string | null;
  alt: string;
  smiles?: string;
  fallback: string;
  initialStatus?: "loading" | "rendered" | "fallback" | "failed";
}) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [src]);
  const status = src && !failed ? "rendered" : initialStatus === "loading" ? "loading" : failed ? "failed" : "fallback";
  return (
    <span className={`structure-render ${status}`}>
      {src && !failed ? (
        <img src={src} alt={alt} onError={() => setFailed(true)} />
      ) : (
        <MoleculeSchematic smiles={smiles ?? ""} fallback={fallback} />
      )}
      <small>{structureRenderLabel(status, fallback)}</small>
    </span>
  );
}

function MoleculeSchematic({ smiles, fallback }: { smiles: string; fallback: string }) {
  const atoms = smiles.match(/Cl|Br|Si|Na|Li|Mg|Ca|[A-Z][a-z]?|[cnops]/g)?.slice(0, 14) ?? [];
  if (!atoms.length) return <i>{fallback}</i>;
  return (
    <span className="smiles-schematic" aria-hidden="true">
      {atoms.map((atom, index) => (
        <b key={`${atom}-${index}`} className={`atom-token atom-${atom.toLowerCase()}`}>
          {atom[0].toUpperCase() + atom.slice(1)}
        </b>
      ))}
    </span>
  );
}

function structureRenderLabel(status: string, fallback: string) {
  if (status === "rendered") return "2D";
  if (status === "loading") return "...";
  if (status === "failed") return "fallback";
  return fallback;
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
  const [statusFilter, setStatusFilter] = useState("all");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [sortMode, setSortMode] = useState("rank");
  const [riskFilter, setRiskFilter] = useState("all");
  const [domainFilter, setDomainFilter] = useState("all");
  const [qualityFilter, setQualityFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [page, setPage] = useState(0);
  const [candidatePage, setCandidatePage] = useState<CandidatePage | null>(null);
  const pageSize = 48;
  const heroCandidate = candidates[0];
  const sourceOptions = ["all", ...Array.from(new Set(candidates.map((candidate) => candidate.library_source || candidate.source))).sort()];
  const normalizedQuery = query.trim().toLowerCase();
  const pageCandidates = candidatePage?.items ?? candidates.slice(page * pageSize, page * pageSize + pageSize);
  const visibleCandidates = pageCandidates.filter((candidate) => {
    const alerts = candidate.descriptors?.alerts?.length ?? 0;
    const severe = candidate.descriptors?.severe_alerts?.length ?? 0;
    const qed = candidate.descriptors?.qed ?? 0;
    const textHaystack = [
      candidate.candidate_id,
      candidate.smiles,
      candidate.source_name,
      candidate.source_compound_id,
      candidate.library_source,
      candidate.decision?.final_status,
      ...(candidate.decision?.reasons ?? [])
    ].join(" ").toLowerCase();
    if (normalizedQuery && !textHaystack.includes(normalizedQuery)) return false;
    if (riskFilter === "alerts" && alerts === 0) return false;
    if (riskFilter === "blockers" && severe === 0 && !(candidate.decision?.hard_gate_failures?.length)) return false;
    if (domainFilter === "in" && !candidate.in_applicability_domain) return false;
    if (domainFilter === "review" && candidate.in_applicability_domain) return false;
    if (qualityFilter === "high-qed" && qed < 0.7) return false;
    if (qualityFilter === "low-qed" && qed >= 0.5) return false;
    return true;
  });
  const totalCandidates = candidatePage?.total ?? candidates.length;
  const comparedCandidates = compareIds
    .map((id) => candidates.find((candidate) => candidate.candidate_id === id))
    .filter(Boolean) as Candidate[];

  useEffect(() => {
    if (!result?.run_id) {
      setCandidatePage(null);
      return;
    }
    let cancelled = false;
    fetchCandidates(result.run_id, {
      limit: pageSize,
      offset: page * pageSize,
      status: statusFilter,
      source: sourceFilter,
      sort: sortMode,
      q: query
    })
      .then((payload) => {
        if (!cancelled) setCandidatePage(payload);
      })
      .catch(() => {
        if (!cancelled) setCandidatePage(null);
      });
    return () => {
      cancelled = true;
    };
  }, [result?.run_id, page, statusFilter, sourceFilter, sortMode, query]);

  function updateFilter(next: { status?: string; source?: string; sort?: string }) {
    if (next.status !== undefined) setStatusFilter(next.status);
    if (next.source !== undefined) setSourceFilter(next.source);
    if (next.sort !== undefined) setSortMode(next.sort);
    setPage(0);
  }

  function updateQuery(value: string) {
    setQuery(value);
    setPage(0);
  }

  function toggleCompare(candidateId: string) {
    setCompareIds((ids) => {
      if (ids.includes(candidateId)) return ids.filter((id) => id !== candidateId);
      return [...ids, candidateId].slice(-4);
    });
  }

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
            <StructureImage
              src={heroCandidate.structure_svg}
              alt={`${heroCandidate.candidate_id} structure`}
              smiles={heroCandidate.smiles}
              fallback={copy.atlas.noStructure}
              initialStatus="rendered"
            />
          ) : (
            <ReferencePreviewStage referenceDrugs={referenceDrugs} copy={copy} />
          )}
        </div>
        <div className="atlas-note">
          <span>{copy.atlas.primaryCandidate}</span>
          <strong>{heroCandidate?.candidate_id ?? copy.atlas.noCandidate}</strong>
          <p>{copy.atlas.note}</p>
        </div>
      </div>

      <LibraryMetricBand result={result} copy={copy} />

      <div className="atlas-columns">
        <section>
          <div className="panel-heading">
            <div>
              <p className="eyebrow">{copy.atlas.generated}</p>
              <h3>{visibleCandidates.length || 0} {copy.atlas.shown} / {totalCandidates || 0} {copy.atlas.scored}</h3>
            </div>
            <button className="ghost-action compact" disabled={comparedCandidates.length < 2} type="button">
              <SlidersHorizontal size={15} />
              {copyText(copy, "atlas", "compare", "Compare")} {comparedCandidates.length}/4
            </button>
          </div>
          <div className="atlas-filters">
            <label className="atlas-search">
              <Search size={15} />
              <input
                value={query}
                placeholder={copyText(copy, "atlas", "searchPlaceholder", "Search ID, SMILES, source, or rationale")}
                onChange={(event) => updateQuery(event.target.value)}
              />
            </label>
            <select value={statusFilter} onChange={(event) => updateFilter({ status: event.target.value })}>
              <option value="all">{copy.graph.all}</option>
              {STATUS_ORDER.map((status) => <option key={status} value={status}>{statusLabel(status, copy)}</option>)}
            </select>
            <select value={sourceFilter} onChange={(event) => updateFilter({ source: event.target.value })}>
              {sourceOptions.map((source) => (
                <option key={source} value={source}>{source === "all" ? copy.graph.all : librarySourceLabel(source, copy)}</option>
              ))}
            </select>
            <select value={sortMode} onChange={(event) => updateFilter({ sort: event.target.value })}>
              <option value="rank">{copyText(copy, "atlas", "sortRank", "Ranked order")}</option>
              <option value="activity">{copyText(copy, "atlas", "sortActivity", "Predicted activity")}</option>
              <option value="applicability">{copyText(copy, "atlas", "sortApplicability", "Applicability")}</option>
              <option value="qed">{copyText(copy, "atlas", "sortQed", "QED")}</option>
            </select>
            <select value={riskFilter} onChange={(event) => setRiskFilter(event.target.value)}>
              <option value="all">{copyText(copy, "atlas", "riskAll", "all risk flags")}</option>
              <option value="alerts">{copyText(copy, "atlas", "riskAlerts", "alerts only")}</option>
              <option value="blockers">{copyText(copy, "atlas", "riskBlockers", "blockers only")}</option>
            </select>
            <select value={domainFilter} onChange={(event) => setDomainFilter(event.target.value)}>
              <option value="all">{copyText(copy, "atlas", "domainAll", "all domains")}</option>
              <option value="in">{copyText(copy, "atlas", "domainIn", "in-domain")}</option>
              <option value="review">{copyText(copy, "atlas", "domainReview", "AD review")}</option>
            </select>
            <select value={qualityFilter} onChange={(event) => setQualityFilter(event.target.value)}>
              <option value="all">{copyText(copy, "atlas", "qualityAll", "all quality")}</option>
              <option value="high-qed">{copyText(copy, "atlas", "qualityHigh", "QED >= 0.70")}</option>
              <option value="low-qed">{copyText(copy, "atlas", "qualityLow", "QED < 0.50")}</option>
            </select>
          </div>
          {candidates.length === 0 ? (
            <AtlasPreRunPanel referenceDrugs={referenceDrugs} copy={copy} onOpenKnown={onOpenKnown} />
          ) : (
            <div className="molecule-grid">
              {visibleCandidates.map((candidate) => (
                <article
                  className={`molecule-card ${selectedId === candidate.candidate_id ? "selected" : ""}`}
                  key={candidate.candidate_id}
                >
                  <span className={`mini-status ${statusClass(candidate.decision?.final_status ?? "Unscored")}`}>
                    {statusLabel(candidate.decision?.final_status ?? "Unscored", copy)}
                  </span>
                  <button className="molecule-open" onClick={() => onSelectCandidate(candidate.candidate_id)} type="button">
                    <span className="molecule-thumb">
                      <LazyStructureImage candidate={candidate} fallback={copy.atlas.noStructure} />
                    </span>
                    <strong>{candidate.candidate_id}</strong>
                    <small>{copy.atlas.lowerPchembl} {formatNumber(candidate.prediction_interval?.lower, 2)}</small>
                    <small>AD {formatNumber(candidate.applicability_score, 2)} / {librarySourceLabel(candidate.library_source || candidate.source, copy)}</small>
                    <em>{inspectionHint(candidate, copy)}</em>
                  </button>
                  <button
                    className={`compare-toggle ${compareIds.includes(candidate.candidate_id) ? "on" : ""}`}
                    onClick={() => toggleCompare(candidate.candidate_id)}
                    type="button"
                  >
                    {compareIds.includes(candidate.candidate_id) ? <CheckCircle2 size={15} /> : <CircleDot size={15} />}
                    {copyText(copy, "atlas", "compare", "Compare")}
                  </button>
                </article>
            ))}
          </div>
          )}
          <div className="pager-row">
            <button className="ghost-action" onClick={() => setPage((value) => Math.max(0, value - 1))} disabled={page === 0} type="button">
              <ArrowLeft size={15} />
              {copyText(copy, "atlas", "prevPage", "Previous")}
            </button>
            <span>{page + 1} / {Math.max(1, Math.ceil(totalCandidates / pageSize))}</span>
            <button className="ghost-action" onClick={() => setPage((value) => value + 1)} disabled={(page + 1) * pageSize >= totalCandidates} type="button">
              {copyText(copy, "atlas", "nextPage", "Next")}
              <ArrowRight size={15} />
            </button>
          </div>
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
                  <StructureImage
                    src={drug.structure_svg || drug.structure_image_url}
                    alt={`${drug.name} structure`}
                    smiles={drug.smiles}
                    fallback={copy.atlas.noFigure}
                    initialStatus={drug.structure_svg || drug.structure_image_url ? "rendered" : "fallback"}
                  />
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
      {comparedCandidates.length >= 2 && (
        <CompareDrawer
          candidates={comparedCandidates}
          copy={copy}
          onRemove={(candidateId) => setCompareIds((ids) => ids.filter((id) => id !== candidateId))}
          onClear={() => setCompareIds([])}
          onOpenCandidate={onSelectCandidate}
        />
      )}
    </section>
  );
}

function LibraryMetricBand({ result, copy }: { result: PipelineResult | null; copy: Copy }) {
  const report = result?.library_report;
  const counts = result?.evaluation_report?.status_counts;
  const items = [
    { label: copyText(copy, "reports", "rawInput", "Raw input"), value: formatInteger(report?.raw_input_count), detail: copyText(copy, "atlas", "libraryRawDetail", "from selected sources") },
    { label: copyText(copy, "reports", "validUnique", "Valid unique"), value: formatInteger(report?.valid_unique_count), detail: copyText(copy, "atlas", "libraryUniqueDetail", "deduplicated molecules") },
    { label: copyText(copy, "reports", "detailedEvaluation", "Detailed evaluation"), value: formatInteger(report?.detailed_evaluation_count), detail: copyText(copy, "atlas", "libraryDetailedDetail", "descriptor + QSAR pass") },
    { label: copyText(copy, "reports", "renderedStructures", "Rendered structures"), value: formatInteger(report?.display_asset_count), detail: copyText(copy, "atlas", "libraryRenderedDetail", "lazy 2D assets") },
    { label: "Go / Hold / No-Go", value: `${counts?.Go ?? 0}/${counts?.Hold ?? 0}/${counts?.["No-Go"] ?? 0}`, detail: copyText(copy, "atlas", "libraryDecisionDetail", "decision rail") }
  ];
  return (
    <section className="library-metric-band" aria-label={copyText(copy, "atlas", "libraryMetrics", "Library screening metrics")}>
      {items.map((item) => (
        <div key={item.label}>
          <span>{item.label}</span>
          <strong>{item.value}</strong>
          <small>{item.detail}</small>
        </div>
      ))}
    </section>
  );
}

function ReferencePreviewStage({ referenceDrugs, copy }: { referenceDrugs: ReferenceDrug[]; copy: Copy }) {
  const preview = referenceDrugs.filter((drug) => drug.smiles).slice(0, 6);
  if (!preview.length) return <div className="empty-inline">{copy.atlas.emptyFigure}</div>;
  return (
    <div className="reference-preview-stage" aria-label={copyText(copy, "atlas", "referencePreview", "Reference molecule preview")}>
      {preview.map((drug) => (
        <span key={drug.drug_id}>
          <StructureImage
            src={drug.structure_svg || drug.structure_image_url}
            alt={`${drug.name} structure`}
            smiles={drug.smiles}
            fallback={copy.atlas.noFigure}
            initialStatus={drug.structure_svg || drug.structure_image_url ? "rendered" : "fallback"}
          />
          <b>{drug.name}</b>
        </span>
      ))}
    </div>
  );
}

function AtlasPreRunPanel({
  referenceDrugs,
  copy,
  onOpenKnown
}: {
  referenceDrugs: ReferenceDrug[];
  copy: Copy;
  onOpenKnown: () => void;
}) {
  const preview = referenceDrugs.filter((drug) => drug.smiles).slice(0, 8);
  return (
    <div className="atlas-empty-panel">
      <div>
        <p className="eyebrow">{copyText(copy, "atlas", "beforeRun", "Before a run")}</p>
        <h3>{copyText(copy, "atlas", "emptyUsefulTitle", "Start from reference structures, then run triage to score candidates.")}</h3>
        <p>{copyText(copy, "atlas", "emptyUsefulText", "The atlas is not blank: reference molecules are available now, and generated candidates will appear here with search, filters, and lazy 2D rendering after a run.")}</p>
        <button className="primary-action" onClick={onOpenKnown} type="button">
          <ShieldCheck size={16} />
          {copy.atlas.openKnown}
        </button>
      </div>
      <div className="reference-mini-grid">
        {preview.map((drug) => (
          <article key={drug.drug_id}>
            <StructureImage
              src={drug.structure_svg || drug.structure_image_url}
              alt={`${drug.name} structure`}
              smiles={drug.smiles}
              fallback={copy.atlas.noFigure}
              initialStatus={drug.structure_svg || drug.structure_image_url ? "rendered" : "fallback"}
            />
            <strong>{drug.name}</strong>
            <small>{drug.category ?? copy.atlas.reference}</small>
          </article>
        ))}
      </div>
    </div>
  );
}

function TwinPreRunPanel({ copy, onRun, onOpenAtlas }: { copy: Copy; onRun: () => void; onOpenAtlas: () => void }) {
  const steps = [
    [copyText(copy, "twin", "emptyStepRun", "Run triage"), copyText(copy, "twin", "emptyStepRunText", "Create or import candidates and let the tool gates evaluate them.")],
    [copyText(copy, "twin", "emptyStepPick", "Select a molecule"), copyText(copy, "twin", "emptyStepPickText", "Open a candidate from the atlas by decision, source, risk, or search.")],
    [copyText(copy, "twin", "emptyStepInspect", "Inspect gates"), copyText(copy, "twin", "emptyStepInspectText", "Review 2D/3D structure, gate audit, known-drug context, and next validation.")]
  ];
  return (
    <section className="empty-action-stage">
      <BrainCircuit size={28} />
      <div>
        <p className="eyebrow">{copy.twin.eyebrow}</p>
        <h2>{copy.twin.emptyTitle}</h2>
        <p>{copy.twin.emptyText}</p>
      </div>
      <div className="empty-step-grid">
        {steps.map(([title, text], index) => (
          <article key={title}>
            <span>{String(index + 1).padStart(2, "0")}</span>
            <strong>{title}</strong>
            <p>{text}</p>
          </article>
        ))}
      </div>
      <div className="run-action-row">
        <button className="primary-action" onClick={onRun} type="button">
          <Play size={16} />
          {copy.top.run}
        </button>
        <button className="ghost-action" onClick={onOpenAtlas} type="button">
          <Layers3 size={16} />
          {copy.views.atlas}
        </button>
      </div>
    </section>
  );
}

function CompareDrawer({
  candidates,
  copy,
  onRemove,
  onClear,
  onOpenCandidate
}: {
  candidates: Candidate[];
  copy: Copy;
  onRemove: (candidateId: string) => void;
  onClear: () => void;
  onOpenCandidate: (candidateId: string) => void;
}) {
  return (
    <aside className="compare-drawer" aria-label={copyText(copy, "atlas", "compareDrawer", "Candidate comparison drawer")}>
      <div className="panel-heading">
        <div>
          <p className="eyebrow">{copyText(copy, "atlas", "compareEyebrow", "Side-by-side review")}</p>
          <h3>{copyText(copy, "atlas", "compareHeading", "Compare candidate evidence before opening a twin.")}</h3>
        </div>
        <button className="ghost-action compact" onClick={onClear} type="button">
          <X size={15} />
          {copyText(copy, "atlas", "clearCompare", "Clear")}
        </button>
      </div>
      <div className="compare-grid">
        {candidates.map((candidate) => (
          <article className="compare-card" key={candidate.candidate_id}>
            <button className="compare-remove" onClick={() => onRemove(candidate.candidate_id)} type="button" aria-label={`Remove ${candidate.candidate_id}`}>
              <X size={14} />
            </button>
            <div className="compare-figure">
              <LazyStructureImage candidate={candidate} fallback={copy.atlas.noStructure} />
            </div>
            <h4>{candidate.candidate_id}</h4>
            <span className={`mini-status ${statusClass(candidate.decision?.final_status ?? "Unscored")}`}>
              {statusLabel(candidate.decision?.final_status ?? "Unscored", copy)}
            </span>
            <dl>
              <dt>{copy.atlas.lowerPchembl}</dt>
              <dd>{formatNumber(candidate.prediction_interval?.lower, 2)}</dd>
              <dt>AD</dt>
              <dd>{formatNumber(candidate.applicability_score, 2)}</dd>
              <dt>QED</dt>
              <dd>{formatNumber(candidate.descriptors?.qed, 2)}</dd>
              <dt>Alerts</dt>
              <dd>{candidate.descriptors?.alerts?.length ?? 0}</dd>
              <dt>Gate</dt>
              <dd>{topGateEffect(candidate)}</dd>
            </dl>
            <button className="ghost-action compact" onClick={() => onOpenCandidate(candidate.candidate_id)} type="button">
              {copyText(copy, "atlas", "openTwin", "Open twin")}
            </button>
          </article>
        ))}
      </div>
    </aside>
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
  onOpenGraph,
  onOpenAtlas,
  onRun
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
  onOpenAtlas: () => void;
  onRun: () => void;
}) {
  const [lazyConformer, setLazyConformer] = useState<ConformerPayload | null>(null);
  const [conformerLoading, setConformerLoading] = useState(false);
  useEffect(() => {
    setLazyConformer(null);
    if (!candidate || moleculeView !== "3d" || !result?.run_id || candidate.conformer) return;
    let cancelled = false;
    setConformerLoading(true);
    fetchConformer(result.run_id, candidate.candidate_id)
      .then((payload) => {
        if (!cancelled) setLazyConformer(payload);
      })
      .catch(() => {
        if (!cancelled) setLazyConformer(null);
      })
      .finally(() => {
        if (!cancelled) setConformerLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [candidate?.candidate_id, candidate?.conformer, moleculeView, result?.run_id]);

  if (!candidate) {
    return (
      <section className="view-frame">
        <TwinPreRunPanel copy={copy} onRun={onRun} onOpenAtlas={onOpenAtlas} />
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
              <StructureImage
                src={candidate.structure_svg}
                alt={`${candidate.candidate_id} 2D structure`}
                smiles={candidate.smiles}
                fallback={copy.twin.no2d}
                initialStatus={candidate.structure_svg ? "rendered" : "fallback"}
              />
            </div>
          ) : (
            <InteractiveConformerView
              conformer={candidate.conformer ?? lazyConformer}
              candidateId={candidate.candidate_id}
              copy={copy}
              loading={conformerLoading}
            />
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
          <GateAuditRail decision={decision} copy={copy} />
          <CandidateDecisionFlow candidate={candidate} copy={copy} locale={locale} />
          <details className="gate-details">
            <summary>{copyText(copy, "twin", "openGateTable", "Open detailed gate audit")}</summary>
            <GateAuditTable decision={decision} copy={copy} />
          </details>
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
        <section className="detail-block">
          <h3>{copyText(copy, "twin", "nextAssay", "Next assay")}</h3>
          <p className="context-note">{candidate.target_specific_interpretation || copyText(copy, "twin", "targetInterpretationPending", "Target-specific interpretation appears after a run.")}</p>
          <div className="assay-list">
            {(candidate.assay_recommendations ?? []).slice(0, 4).map((item, index) => (
              <article key={index} className={`assay-card ${String(item["priority"] ?? "review")}`}>
                <strong>{String(item["assay"] ?? "Assay recommendation")}</strong>
                <span>{String(item["priority"] ?? "review")} / {String(item["cost_time_class"] ?? "-")}</span>
                <p>{String(item["decision_impact"] ?? item["rationale"] ?? "")}</p>
              </article>
            ))}
            {!(candidate.assay_recommendations ?? []).length && <p className="context-note">{copyText(copy, "twin", "noAssayPlan", "No assay recommendation was generated for this candidate.")}</p>}
          </div>
        </section>
        <section className="detail-block">
          <h3>{copyText(copy, "twin", "cliffAndErrors", "Cliff / error flags")}</h3>
          <div className="flag-list">
            {(candidate.activity_cliff_flags ?? []).slice(0, 3).map((item, index) => (
              <span key={`cliff-${index}`}>
                {copyText(copy, "twin", "activityCliff", "Activity cliff")} {String(item["risk_level"] ?? "review")} / Δ {String(item["activity_delta"] ?? "-")}
              </span>
            ))}
            {(candidate.candidate_errors ?? []).slice(0, 3).map((item, index) => (
              <span key={`error-${index}`} className="error-flag">
                {String(item["error_code"] ?? item["category"] ?? "error")}: {String(item["user_message"] ?? "")}
              </span>
            ))}
            {!(candidate.activity_cliff_flags ?? []).length && !(candidate.candidate_errors ?? []).length && <p className="context-note">{copyText(copy, "twin", "noFlags", "No candidate-level cliff or error flag recorded.")}</p>}
          </div>
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

function GateAuditRail({ decision, copy }: { decision: Candidate["decision"]; copy: Copy }) {
  const gates = decision?.gate_audit ?? [];
  const groups = [
    { status: "pass", label: copyText(copy, "criterionValues", "pass", "pass") },
    { status: "review", label: copyText(copy, "criterionValues", "review", "review") },
    { status: "block", label: copyText(copy, "criterionValues", "block", "block") }
  ];
  if (!gates.length) return null;
  return (
    <div className="gate-rail" aria-label={copyText(copy, "twin", "gateRail", "Decision gate rail")}>
      {groups.map((group) => {
        const subset = gates.filter((gate) => gate.status === group.status);
        return (
          <article className={`gate-rail-card ${group.status}`} key={group.status}>
            <span>{group.label}</span>
            <strong>{subset.length}</strong>
            <p>{subset.slice(0, 2).map((gate) => gate.label || gate.gate_id).join(" / ") || copyText(copy, "twin", "noGate", "none")}</p>
          </article>
        );
      })}
    </div>
  );
}

function CandidateDecisionFlow({ candidate, copy, locale }: { candidate: Candidate; copy: Copy; locale: Locale }) {
  const nodes = candidate.candidate_decision_flow ?? [];
  if (!nodes.length) return null;
  return (
    <div className="candidate-flow" aria-label={copyText(copy, "twin", "candidateDecisionFlow", "Candidate decision flow")}>
      <div className="candidate-flow-head">
        <h4>{copyText(copy, "twin", "candidateDecisionFlow", "Candidate decision flow")}</h4>
        <span>{copyText(copy, "twin", "flowHint", "Read left to right: gate observations become a decision.")}</span>
      </div>
      <div className="candidate-flow-track">
        {nodes.map((node, index) => (
          <article className={`candidate-flow-node ${flowStatusClass(node.status)}`} key={`${node.id}-${index}`}>
            <span>{index + 1}</span>
            <strong>{localizeFlowLabel(node.label, locale)}</strong>
            <p>{localizeBackendText(node.summary, locale)}</p>
          </article>
        ))}
      </div>
    </div>
  );
}

function GateAuditTable({ decision, copy }: { decision: Candidate["decision"]; copy: Copy }) {
  const gates = decision?.gate_audit ?? [];
  if (!gates.length) {
    return <p className="context-note">{copyText(copy, "twin", "gateAuditPending", "Gate audit will appear after a run.")}</p>;
  }
  return (
    <div className="gate-audit">
      <div className="gate-audit-head">
        <h4>{copyText(copy, "twin", "gateAudit", "Gate audit")}</h4>
        <span>{copyText(copy, "twin", "gatePassRatio", "gate pass ratio")}: {formatNumber(decision?.total_score, 2)}</span>
      </div>
      <div className="gate-table" role="table" aria-label={copyText(copy, "twin", "gateAudit", "Gate audit")}>
        <div className="gate-row gate-header" role="row">
          <span>{copyText(copy, "twin", "gate", "Gate")}</span>
          <span>{copyText(copy, "twin", "observed", "Observed")}</span>
          <span>{copyText(copy, "twin", "threshold", "Threshold")}</span>
          <span>{copyText(copy, "twin", "effect", "Effect")}</span>
        </div>
        {gates.slice(0, 10).map((gate, index) => (
          <div className={`gate-row ${gate.status}`} role="row" key={`${gate.gate_id}-${index}`}>
            <span>
              <strong>{gate.label || gate.gate_id}</strong>
              <small>{gate.source}</small>
            </span>
            <span>{formatGateValue(gate.observed_value)}</span>
            <span>{gate.threshold_id ? `${formatGateValue(gate.threshold_value)} ${gate.threshold_units}` : "n/a"}</span>
            <span>
              <b>{gate.status}</b>
              <small>{gate.message}</small>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function InteractiveConformerView({
  conformer,
  candidateId,
  copy,
  loading = false
}: {
  conformer: ConformerPayload | null;
  candidateId: string;
  copy: Copy;
  loading?: boolean;
}) {
  const [angle, setAngle] = useState(22);
  const [zoom, setZoom] = useState(1);
  const atoms = (conformer?.atoms ?? []).slice(0, 64);
  const bonds = (conformer?.bonds ?? []).slice(0, 90);
  if (loading) {
    return (
      <div className="conformer-stage unavailable">
        <Loader2 className="spin" size={22} />
        <span>{copyText(copy, "conformer", "loading", "Computing conformer")}</span>
      </div>
    );
  }
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
  const [labelMode, setLabelMode] = useState("auto");

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
  const showLabels = labelMode === "all" || (labelMode === "auto" && (visibleNodes.length < 90 || zoom >= 1.45));

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
        {nodes.length > 0 && (
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
          <select value={labelMode} onChange={(event) => setLabelMode(event.target.value)} aria-label={copyText(copy, "graph", "labelDensity", "Label density")}>
            <option value="auto">{copyText(copy, "graph", "labelsAuto", "labels auto")}</option>
            <option value="focus">{copyText(copy, "graph", "labelsFocus", "focus labels")}</option>
            <option value="all">{copyText(copy, "graph", "labelsAll", "all labels")}</option>
            <option value="none">{copyText(copy, "graph", "labelsNone", "no labels")}</option>
          </select>
          <button onClick={() => setZoom((value) => Math.min(2.8, value + 0.15))} type="button"><ZoomIn size={16} /></button>
          <button onClick={() => setZoom((value) => Math.max(0.45, value - 0.15))} type="button"><ZoomOut size={16} /></button>
          <button onClick={fitView} type="button"><Maximize2 size={16} /></button>
          <button onClick={centerSelected} type="button"><Search size={16} /></button>
        </div>
        )}
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
                    {labelMode !== "none" && (showLabels || selectedSet.has(node.id) || node.type === "target" || node.type === "decision") && (
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
      <GraphLegend copy={copy} visibleNodeCount={visibleNodes.length} visibleEdgeCount={visibleEdges.length} />
    </section>
  );
}

function GraphLegend({ copy, visibleNodeCount, visibleEdgeCount }: { copy: Copy; visibleNodeCount: number; visibleEdgeCount: number }) {
  const items = [
    ["candidate", copyText(copy, "graph", "legendCandidate", "candidate")],
    ["model_prediction", copyText(copy, "graph", "legendPrediction", "prediction")],
    ["threshold", copyText(copy, "graph", "legendThreshold", "threshold")],
    ["decision", copyText(copy, "graph", "legendDecision", "decision")],
    ["class_risk", copyText(copy, "graph", "legendRisk", "risk context")]
  ];
  return (
    <div className="graph-legend">
      <strong>{copyText(copy, "graph", "legend", "Graph legend")}</strong>
      {items.map(([type, label]) => (
        <span key={type}><i className={`legend-dot ${type}`} />{label}</span>
      ))}
      <em>{visibleNodeCount} nodes / {visibleEdgeCount} edges</em>
    </div>
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
  const [query, setQuery] = useState("");
  const normalizedQuery = query.trim().toLowerCase();
  const visibleReferenceDrugs = referenceDrugs.filter((drug) => {
    if (!normalizedQuery) return true;
    return [
      drug.name,
      drug.smiles,
      drug.chembl_id,
      drug.pubchem_cid,
      drug.category,
      drug.context,
      drug.activity_evidence,
      drug.source_status,
      ...drug.label_risk_context
    ].join(" ").toLowerCase().includes(normalizedQuery);
  });
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
      <div className="known-search-strip">
        <label>
          <Search size={15} />
          <input
            value={query}
            placeholder={copyText(copy, "known", "searchPlaceholder", "Search drug, risk, ChEMBL, PubChem, or source")}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
        <span>{visibleReferenceDrugs.length} / {referenceDrugs.length}</span>
      </div>
      <div className="known-grid">
        <section className="known-drug-table">
          {visibleReferenceDrugs.map((drug) => (
            <article className="known-drug-card" key={drug.drug_id}>
              <div className="known-drug-figure">
                <StructureImage
                  src={drug.structure_svg || drug.structure_image_url}
                  alt={`${drug.name} structure`}
                  smiles={drug.smiles}
                  fallback={copy.known.noStructure}
                  initialStatus={drug.structure_svg || drug.structure_image_url ? "rendered" : "fallback"}
                />
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

function ReportPreRunPanel({ copy }: { copy: Copy }) {
  const outputs = [
    [copy.reports.modelCard, copyText(copy, "reports", "modelCardPreview", "QSAR context, validation status, and interpretation limits.")],
    [copy.reports.thresholdRegistry, copyText(copy, "reports", "thresholdPreview", "Every gate keeps its value, source, direction, and rationale.")],
    [copy.reports.agentTrace, copyText(copy, "reports", "tracePreview", "Plan, tool calls, critic review, redesign, and fallback events.")],
    [copy.reports.libraryScreening, copyText(copy, "reports", "libraryPreview", "Raw input, unique valid molecules, detailed evaluation, rendered structures.")]
  ];
  return (
    <section className="report-pre-run">
      <div>
        <p className="eyebrow">{copyText(copy, "reports", "beforeRun", "Before a run")}</p>
        <h3>{copyText(copy, "reports", "preRunTitle", "Reports become the audit trail, not a marketing summary.")}</h3>
        <p>{copyText(copy, "reports", "preRunBody", "After triage, this tab collects evidence mode, tool failures, decision rules, validation, cache status, and downloadable HTML output.")}</p>
      </div>
      <div>
        {outputs.map(([title, text]) => (
          <article key={title}>
            <CheckCircle2 size={16} />
            <strong>{title}</strong>
            <span>{text}</span>
          </article>
        ))}
      </div>
    </section>
  );
}

function AgentFlowDiagram({ result, copy, locale }: { result: PipelineResult | null; copy: Copy; locale: Locale }) {
  const summary = result?.agent_trace_summary;
  const nodes = summary?.flow_nodes ?? [];
  const [selectedId, setSelectedId] = useState<string>(nodes[0]?.id ?? "");
  const activeNode = nodes.find((node) => node.id === selectedId) ?? nodes[0];
  const eventSteps = new Set((activeNode?.event_steps ?? []).map((step) => Number(step)));
  const relatedEvents = (result?.agent_events ?? []).filter((event) => eventSteps.has(Number(event.step)));

  if (!result || !summary || !nodes.length) {
    return (
      <div className="agent-flow-empty">
        <Network size={18} />
        <p>{copyText(copy, "reports", "agentFlowPending", "Run triage to generate a readable agent flow diagram.")}</p>
      </div>
    );
  }

  return (
    <div className="agent-flow-shell">
      <div className="plain-agent-summary">
        <h4>{copyText(copy, "reports", "plainAgentSummary", "Plain-language agent summary")}</h4>
        <ul>
          {(summary.plain_summary ?? []).slice(0, 4).map((item) => (
            <li key={item}>{localizeBackendText(item, locale)}</li>
          ))}
        </ul>
      </div>
      <div className="agent-flow-diagram" role="list" aria-label={copyText(copy, "reports", "agentFlowDiagram", "Agent Flow Diagram")}>
        {nodes.map((node, index) => (
          <button
            className={`agent-flow-node ${flowStatusClass(node.status)} ${activeNode?.id === node.id ? "selected" : ""}`}
            key={node.id}
            onClick={() => setSelectedId(node.id)}
            type="button"
          >
            <span>{String(index + 1).padStart(2, "0")}</span>
            <strong>{localizeFlowLabel(node.label, locale)}</strong>
            <em>{copyText(copy, "reports", String(node.status), String(node.status))}</em>
          </button>
        ))}
      </div>
      <div className="agent-flow-detail">
        <div>
          <span className={`flow-status-pill ${flowStatusClass(activeNode?.status)}`}>
            {copyText(copy, "reports", String(activeNode?.status ?? "review"), String(activeNode?.status ?? "review"))}
          </span>
          <h4>{localizeFlowLabel(activeNode?.label ?? "", locale)}</h4>
          <p>{localizeBackendText(String(activeNode?.summary ?? ""), locale)}</p>
        </div>
        <dl>
          <dt>{copyText(copy, "reports", "fallbackEvents", "Fallback events")}</dt>
          <dd>{summary.fallback_events_count}</dd>
          <dt>{copyText(copy, "reports", "criticFindings", "Critic findings")}</dt>
          <dd>{summary.critic_findings_count}</dd>
          <dt>{copyText(copy, "reports", "relatedEvents", "Related raw events")}</dt>
          <dd>{relatedEvents.length}</dd>
        </dl>
      </div>
      <div className="decision-impact">
        <h4>{copyText(copy, "reports", "whatChangedDecision", "What changed the decision")}</h4>
        <p>{localizeBackendText(summary.decision_impact, locale)}</p>
      </div>
      <details className="technical-trace">
        <summary>{copyText(copy, "reports", "technicalTrace", "Technical trace")}</summary>
        <ol className="trace-list">
          {result.agent_events.length ? result.agent_events.map((event) => (
            <li key={`${event.step}-${event.phase}-${event.action}`}>
              <strong>{event.step}. {event.phase}</strong>
              <span>{event.agent} / {event.action} / {event.status}</span>
              {event.candidate_id && <em>{event.candidate_id}</em>}
            </li>
          )) : <li>{copy.reports.pendingTrace}</li>}
        </ol>
      </details>
    </div>
  );
}

function Reports({ result, copy, locale }: { result: PipelineResult | null; copy: Copy; locale: Locale }) {
  const toolSummary = result?.tool_error_summary;
  const categories = Object.entries(toolSummary?.categories ?? {});
  const cacheRuntime = result?.cache_summary?.runtime as Record<string, unknown> | undefined;
  const circuitOpen = result?.api_circuit_breaker_summary?.open_sources as Record<string, unknown> | undefined;
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
      {!result && <ReportPreRunPanel copy={copy} />}
      <div className="reports-grid">
        <section className="report-panel agent-flow-panel">
          <h3>{copyText(copy, "reports", "agentFlowDiagram", "Agent Flow Diagram")}</h3>
          <AgentFlowDiagram result={result} copy={copy} locale={locale} />
        </section>
        <section className="report-panel">
          <h3>{copy.reports.evidenceMode}</h3>
          <dl className="model-dl">
            <dt>{copy.reports.status}</dt>
            <dd>{evidenceModeLabel(result, DEFAULT_REQUEST, copy)}</dd>
            <dt>{copy.reports.sourceRequired}</dt>
            <dd>{String(result?.evidence_mode?.interpretation ?? copyText(copy, "reports", "preRunEvidenceNote", "Run triage to populate source-backed evidence mode and fallback status."))}</dd>
          </dl>
        </section>
        <section className="report-panel">
          <h3>{copyText(copy, "reports", "decisionRulebook", "Decision rulebook")}</h3>
          <div className="rulebook-list">
            <div><b>Go</b><span>{copyText(copy, "reports", "goRule", "All hard gates pass, evidence and applicability are sufficient, and critic finds no blocker.")}</span></div>
            <div><b>Hold</b><span>{copyText(copy, "reports", "holdRule", "Molecule is inspectable, but at least one review gate needs more evidence or uncertainty reduction.")}</span></div>
            <div><b>No-Go</b><span>{copyText(copy, "reports", "nogoRule", "Invalid structure, severe alert, or hard descriptor blocker.")}</span></div>
          </div>
        </section>
        <section className="report-panel">
          <h3>{copyText(copy, "reports", "toolErrors", "Tool error / fallback summary")}</h3>
          <dl className="model-dl">
            <dt>{copyText(copy, "reports", "totalCalls", "Total calls")}</dt>
            <dd>{formatInteger(toolSummary?.total_calls)}</dd>
            <dt>{copy.reports.status}</dt>
            <dd>{toolSummary?.has_live_errors ? copyText(copy, "console", "fallback", "fallback") : copyText(copy, "console", "available", "available")}</dd>
            <dt>{copy.reports.sourceRequired}</dt>
            <dd>{String(toolSummary?.interpretation ?? copyText(copy, "reports", "preRunToolNote", "Tool calls and fallback categories will appear after a run."))}</dd>
          </dl>
          <div className="metric-list">
            {categories.map(([key, value]) => <span key={key}>{key}: {value}</span>)}
          </div>
        </section>
        <section className="report-panel">
          <h3>{copyText(copy, "reports", "runtimeOps", "Runtime / cache")}</h3>
          <dl className="model-dl">
            <dt>{copyText(copy, "console", "performance", "Performance")}</dt>
            <dd>{result?.performance_summary?.duration_ms ? `${Math.round(Number(result.performance_summary.duration_ms))} ms` : "-"}</dd>
            <dt>{copyText(copy, "reports", "cache", "Cache")}</dt>
            <dd>{formatInteger(result?.cache_summary?.entries)} entries / {formatInteger(cacheRuntime?.hits)} hits / {formatInteger(cacheRuntime?.misses)} misses</dd>
            <dt>{copyText(copy, "console", "circuitBreaker", "Circuit breaker")}</dt>
            <dd>{Object.keys(circuitOpen ?? {}).length} open sources</dd>
          </dl>
          <p className="context-note">{String(result?.api_circuit_breaker_summary?.policy ?? "-")}</p>
        </section>
        <section className="report-panel">
          <h3>{copyText(copy, "reports", "targetReadiness", "Target readiness")}</h3>
          <dl className="model-dl">
            <dt>{copy.reports.status}</dt>
            <dd>{String(result?.target_readiness?.status ?? copy.console.runPending)}</dd>
            <dt>{copyText(copy, "reports", "scoringMode", "Scoring mode")}</dt>
            <dd>{String(result?.scoring_mode ?? "-")}</dd>
            <dt>{copyText(copy, "reports", "pchemblRows", "pChEMBL rows")}</dt>
            <dd>{String(result?.target_readiness?.pchembl_rows ?? "-")}</dd>
            <dt>{copy.reports.sourceRequired}</dt>
            <dd>{String(result?.target_readiness?.interpretation ?? "-")}</dd>
          </dl>
          <div className="metric-list">
            {((result?.target_readiness?.blockers as string[] | undefined) ?? []).map((item) => <span key={item}>{item}</span>)}
          </div>
        </section>
        <section className="report-panel">
          <h3>{copyText(copy, "reports", "scientificExtensions", "Scientific extensions")}</h3>
          <dl className="model-dl">
            <dt>{copyText(copy, "reports", "assayRecommendations", "Assay recommendations")}</dt>
            <dd>{String(result?.assay_plan?.recommendation_count ?? 0)}</dd>
            <dt>{copyText(copy, "reports", "activityCliffs", "Activity cliff pairs")}</dt>
            <dd>{String(result?.activity_cliff_report?.pair_count ?? 0)}</dd>
            <dt>{copy.reports.status}</dt>
            <dd>{String(result?.scientific_extensions?.target_readiness_status ?? "-")}</dd>
          </dl>
          <p className="context-note">{String(result?.scientific_extensions?.novelty_positioning ?? "-")}</p>
        </section>
        <section className="report-panel">
          <h3>{copyText(copy, "reports", "errorSummary", "Error / exception summary")}</h3>
          <dl className="model-dl">
            <dt>{copyText(copy, "reports", "totalErrors", "Total errors")}</dt>
            <dd>{String(result?.error_summary?.total_errors ?? 0)}</dd>
            <dt>{copyText(copy, "reports", "blocking", "Blocking")}</dt>
            <dd>{String(Boolean(result?.error_summary?.has_blocking_error))}</dd>
            <dt>{copyText(copy, "reports", "logPath", "Log path")}</dt>
            <dd>{String(result?.log_path ?? "-")}</dd>
          </dl>
          <div className="metric-list">
            {Object.entries(result?.error_summary?.categories ?? {}).map(([key, value]) => <span key={key}>{key}: {String(value)}</span>)}
          </div>
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
          <h3>{copyText(copy, "reports", "libraryScreening", "Library-scale screening")}</h3>
          <dl className="model-dl">
            <dt>{copyText(copy, "reports", "rawInput", "Raw input")}</dt>
            <dd>{formatInteger(result?.library_report?.raw_input_count)}</dd>
            <dt>{copyText(copy, "reports", "validUnique", "Valid unique")}</dt>
            <dd>{formatInteger(result?.library_report?.valid_unique_count)}</dd>
            <dt>{copyText(copy, "reports", "detailedEvaluation", "Detailed evaluation")}</dt>
            <dd>{formatInteger(result?.library_report?.detailed_evaluation_count)}</dd>
            <dt>{copyText(copy, "reports", "renderedStructures", "Rendered structures")}</dt>
            <dd>{formatInteger(result?.library_report?.display_asset_count)}</dd>
          </dl>
          <div className="metric-list">
            {(result?.screening_stages ?? []).map((stage) => (
              <span key={stage.stage}>{stage.stage}: {stage.count}</span>
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

function flowStatusClass(status: string | undefined) {
  const normalized = String(status ?? "review").toLowerCase();
  if (normalized === "done" || normalized === "pass") return "flow-done";
  if (normalized === "blocked" || normalized === "block") return "flow-blocked";
  if (normalized === "fallback") return "flow-fallback";
  return "flow-review";
}

function localizeFlowLabel(label: string, locale: Locale) {
  if (locale !== "ko") return label;
  const labels: Record<string, string> = {
    "Valid SMILES": "SMILES 유효성",
    "Structural alerts": "구조 alert",
    "Descriptor gates": "물성 gate",
    "Conservative activity": "보수적 활성 추정",
    "Applicability domain": "적용영역",
    "Prediction uncertainty": "예측 불확실성",
    "Evidence support": "근거 충분성",
    "Critic review": "Critic 검토",
    "Redesign context": "재설계 맥락",
    "Final decision": "최종 판정",
    "Plan": "계획 생성",
    "Evidence search": "근거 검색",
    "Library build": "라이브러리 구성",
    "Molecular evaluation": "분자 평가",
    "QSAR / AD": "QSAR / 적용영역",
    "Replan / Redesign": "재계획 / 재설계",
    "Decision": "판정",
    "Report": "보고서"
  };
  return labels[label] ?? label;
}

function EvidenceWave() {
  return (
    <div className="evidence-wave" aria-hidden="true">
      {Array.from({ length: 30 }).map((_, index) => {
        const top = index % 3 === 0 ? 38 : index % 3 === 1 ? 56 : 48;
        return (
          <span
            key={index}
            style={{
              left: `${-4 + index * 3.8}%`,
              top: `${top}%`,
              transform: `rotate(${index * 8}deg)`
            } as CSSProperties}
          />
        );
      })}
    </div>
  );
}

function MetricNumber({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <article>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

function AgentLoopTimeline({ result }: { result: PipelineResult }) {
  const phases = ["Plan", "Act", "Observe", "Critique", "Replan", "Redesign", "Re-evaluate", "Decide"];
  const phaseCounts = result.agent_events.reduce<Record<string, number>>((acc, event) => {
    const phase = String(event.phase ?? "");
    acc[phase] = (acc[phase] ?? 0) + 1;
    return acc;
  }, {});
  return (
    <ol className="agent-loop-timeline">
      {phases.map((phase, index) => (
        <li className={phaseCounts[phase] ? "active" : ""} key={phase}>
          <span>{String(index + 1).padStart(2, "0")}</span>
          <strong>{phase}</strong>
          <em>{phaseCounts[phase] ?? 0}</em>
        </li>
      ))}
    </ol>
  );
}

function CandidateStoryCard({
  story,
  copy,
  locale,
  onOpenCandidate
}: {
  story: ReturnType<typeof candidateDecisionStory>;
  copy: Copy;
  locale: Locale;
  onOpenCandidate: (id: string, view?: ViewId) => void;
}) {
  const candidate = story.candidate;
  return (
    <article className={`candidate-story ${statusClass(story.status)}`}>
      <span className={`mini-status ${statusClass(story.status)}`}>{statusLabel(story.status, copy)}</span>
      {candidate ? (
        <>
          <div className="story-figure">
            <LazyStructureImage candidate={candidate} fallback={copy.atlas.noStructure} />
          </div>
          <h4>{candidate.candidate_id}</h4>
          <p>{localizeBackendText(story.reason, locale)}</p>
          <dl>
            <dt>{copy.atlas.lowerPchembl}</dt>
            <dd>{formatNumber(candidate.prediction_interval?.lower, 2)}</dd>
            <dt>AD</dt>
            <dd>{formatNumber(candidate.applicability_score, 2)}</dd>
            <dt>Gate</dt>
            <dd>{topGateEffect(candidate)}</dd>
          </dl>
          <button className="ghost-action compact" onClick={() => onOpenCandidate(candidate.candidate_id, "twin")} type="button">
            {copyText(copy, "judge", "openStory", "Open candidate twin")}
          </button>
        </>
      ) : (
        <>
          <h4>{copyText(copy, "judge", "missingStory", "No representative in this run")}</h4>
          <p>{story.reason}</p>
        </>
      )}
    </article>
  );
}

function buildGuidedRunSummary(result: PipelineResult | null, copy: Copy) {
  if (!result) {
    return {
      title: copyText(copy, "console", "guidedPreRunTitle", "Evidence-gated setup, not a black-box chat."),
      firstInspection: copyText(copy, "console", "guidedPreRunInspection", "After the run, open the first Hold or No-Go candidate to see uncertainty and blockers."),
      whatHappened: "-",
      whyHold: "-",
      needsValidation: "-"
    };
  }
  const counts = result.evaluation_report?.status_counts ?? { Go: 0, Hold: 0, "No-Go": 0, Unscored: 0 };
  const firstHold = result.candidates.find((candidate) => candidate.decision?.final_status === "Hold");
  const firstNoGo = result.candidates.find((candidate) => candidate.decision?.final_status === "No-Go");
  const firstGo = result.candidates.find((candidate) => candidate.decision?.final_status === "Go");
  const first = firstHold ?? firstNoGo ?? firstGo ?? result.candidates[0];
  return {
    title: copyText(copy, "console", "guidedPostRunTitle", "Follow the evidence flow before trusting a candidate."),
    firstInspection: first
      ? copyText(copy, "console", "guidedInspectCandidate", "Inspect {candidate}: {hint}")
          .replace("{candidate}", first.candidate_id)
          .replace("{hint}", inspectionHint(first, copy))
      : copyText(copy, "console", "guidedNoCandidate", "Run triage to create a first inspection target."),
    whatHappened: copyText(copy, "console", "guidedWhatHappenedValue", "{unique} valid unique molecules became {detailed} detailed evaluations.")
      .replace("{unique}", formatInteger(result.library_report?.valid_unique_count))
      .replace("{detailed}", formatInteger(result.library_report?.detailed_evaluation_count)),
    whyHold: copyText(copy, "console", "guidedWhyHoldValue", "{hold} candidates need evidence, AD, uncertainty, or risk review.")
      .replace("{hold}", formatInteger(counts.Hold ?? 0)),
    needsValidation: result.validation_report?.status === "sufficient_data"
      ? copyText(copy, "console", "guidedValidationSufficient", "Use validation metrics and assay follow-up.")
      : copyText(copy, "console", "guidedValidationLimited", "Validation data are limited; confirm with assay and expert review.")
  };
}

function buildJudgeDemoSummary(result: PipelineResult | null, counts: Record<Status, number>, copy: Copy) {
  const eventCount = result?.agent_events?.length ?? 0;
  const runtimeLabel = result?.compute_profile?.id ? String(result.compute_profile.id) : result?.runtime_status ? copyText(copy, "judge", "runtimeReported", "reported") : copyText(copy, "judge", "runtimePending", "pending");
  const runtimeDetail = result?.tool_error_summary?.has_live_errors ? copyText(copy, "judge", "runtimeFallback", "fallback labelled") : copyText(copy, "judge", "runtimeLogged", "resources logged");
  const criteriaMap = [
    { label: copyText(copy, "judge", "criteriaScientific", "Scientific validity"), evidence: copyText(copy, "judge", "criteriaScientificEvidence", "Gate audit, threshold registry, QSAR validation status") },
    { label: copyText(copy, "judge", "criteriaAgentic", "Agent autonomy"), evidence: copyText(copy, "judge", "criteriaAgenticEvidence", "Plan/Act/Observe/Critique/Replan/Redesign timeline") },
    { label: copyText(copy, "judge", "criteriaTools", "Tool integration"), evidence: copyText(copy, "judge", "criteriaToolsEvidence", "RDKit, ChEMBL/PubChem/openFDA logs, evidence graph") },
    { label: copyText(copy, "judge", "criteriaResource", "Resource efficiency"), evidence: copyText(copy, "judge", "criteriaResourceEvidence", "CPU/GPU/API requested vs used runtime truth") },
    { label: copyText(copy, "judge", "criteriaDemo", "Demo completeness"), evidence: copyText(copy, "judge", "criteriaDemoEvidence", "Candidate twin, report, known risk context, next validation") }
  ];
  return {
    eventCount,
    runtimeLabel,
    runtimeDetail,
    criteriaMap,
    stories: [
      candidateDecisionStory(result, "Go", copy, counts),
      candidateDecisionStory(result, "Hold", copy, counts),
      candidateDecisionStory(result, "No-Go", copy, counts)
    ]
  };
}

function candidateDecisionStory(result: PipelineResult | null, status: Status, copy: Copy, counts?: Record<Status, number>) {
  const candidate = result?.candidates.find((item) => item.decision?.final_status === status) ?? null;
  if (!candidate) {
    return {
      status,
      candidate: null,
      reason: copyText(copy, "judge", "storyMissingReason", "This run has {count} {status} candidates.")
        .replace("{count}", formatInteger(counts?.[status] ?? 0))
        .replace("{status}", statusLabel(status, copy))
    };
  }
  const primaryReason = candidate.decision?.reasons?.[0] ?? inspectionHint(candidate, copy);
  return { status, candidate, reason: primaryReason };
}

function topGateEffect(candidate: Candidate) {
  const gates = candidate.decision?.gate_audit ?? [];
  const blocker = gates.find((gate) => gate.status === "block");
  const review = gates.find((gate) => gate.status === "review");
  const pass = gates.find((gate) => gate.status === "pass");
  return blocker?.label ?? review?.label ?? pass?.label ?? "-";
}

function inspectionHint(candidate: Candidate, copy: Copy) {
  const status = candidate.decision?.final_status ?? "Unscored";
  const severe = candidate.descriptors?.severe_alerts?.length ?? 0;
  const alerts = candidate.descriptors?.alerts?.length ?? 0;
  if (status === "No-Go") {
    return severe
      ? copyText(copy, "console", "hintSevereAlert", "hard blocker: severe structural alert")
      : copyText(copy, "console", "hintHardBlocker", "hard blocker or invalid structure");
  }
  if (status === "Hold") {
    if (!candidate.in_applicability_domain) return copyText(copy, "console", "hintAdReview", "review AD before prioritization");
    if ((candidate.prediction_interval?.width ?? 0) > 1.2) return copyText(copy, "console", "hintWideUncertainty", "wide uncertainty interval");
    if (alerts) return copyText(copy, "console", "hintRiskAlert", "risk alert needs review");
    return copyText(copy, "console", "hintMoreEvidence", "needs more evidence before prioritization");
  }
  if (status === "Go") return copyText(copy, "console", "hintGoValidation", "passes hard gates; still needs assay validation");
  return copyText(copy, "console", "hintUnscored", "not scored yet");
}

function fallbackViewLabel(id: string) {
  const labels: Record<string, string> = {
    console: "Run Console",
    judge: "Judge Demo",
    atlas: "Library Browser",
    twin: "Candidate Twin",
    graph: "Evidence Graph",
    known: "Known Drugs & Risks",
    reports: "Reports"
  };
  return labels[id] ?? id;
}

function formatNumber(value: unknown, digits = 2) {
  const numeric = typeof value === "number" ? value : typeof value === "string" && value.trim() ? Number(value) : NaN;
  if (!Number.isFinite(numeric)) return "-";
  return numeric.toFixed(digits);
}

function formatInteger(value: unknown) {
  const numeric = typeof value === "number" ? value : typeof value === "string" && value.trim() ? Number(value) : NaN;
  if (!Number.isFinite(numeric)) return "-";
  return Math.round(numeric).toLocaleString();
}

function formatGateValue(value: unknown) {
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(3);
  if (Array.isArray(value)) return value.length ? value.slice(0, 3).join(", ") : "none";
  if (value === null || value === undefined || value === "") return "-";
  return String(value);
}

function truthValue(record: Record<string, unknown>, key: string) {
  return record[key] === true;
}

function copyText(copy: Copy, section: string, key: string, fallback: string) {
  const sectionMap = (copy as unknown as Record<string, Record<string, unknown>>)[section] ?? {};
  const value = sectionMap[key];
  return typeof value === "string" ? value : fallback;
}

function loadSavedMolecules(): SavedMolecule[] {
  if (typeof window === "undefined") return [];
  try {
    const parsed = JSON.parse(window.localStorage.getItem("targetsafe-saved-molecules") ?? "[]");
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter((item) => item && typeof item.smiles === "string")
      .slice(0, 24)
      .map((item) => ({
        id: String(item.id ?? `${Date.now()}-${item.smiles}`),
        name: String(item.name ?? "Untitled molecule"),
        smiles: String(item.smiles),
        target: String(item.target ?? "EGFR"),
        viability: String(item.viability ?? "review"),
        saved_at: String(item.saved_at ?? ""),
        structure_svg: typeof item.structure_svg === "string" ? item.structure_svg : null
      }));
  } catch {
    return [];
  }
}

function moleculeViabilityLabel(viability: string, copy: Copy) {
  const labels: Record<string, string> = {
    plausible_seed: copyText(copy, "console", "viabilityPlausible", "Plausible seed"),
    review: copyText(copy, "console", "viabilityReview", "Needs review"),
    blocked: copyText(copy, "console", "viabilityBlocked", "Blocked"),
    invalid: copyText(copy, "console", "viabilityInvalid", "Invalid")
  };
  return labels[viability] ?? viability;
}

function librarySourceLabel(source: string, copy: Copy) {
  const labels = (copy as unknown as { librarySources?: Record<string, string> }).librarySources ?? {};
  return labels[source] ?? source.replaceAll("_", " ");
}

function profileRequestDefaults(profileId: string): Partial<RunRequest> {
  if (profileId === "cpu-demo") {
    return {
      allow_network: false,
      use_gpu: false,
      use_llm: false,
      library_sources: ["seed_analog"],
      library_limit: 500,
      detailed_eval_limit: 96,
      display_limit: 72,
      conformer_limit: 12
    };
  }
  if (profileId === "cpu-evidence") {
    return { allow_network: true, use_gpu: false, use_llm: false, library_sources: ["seed_analog", "chembl_target", "pubchem_reference"] };
  }
  if (profileId === "gpu-accelerated") {
    return { allow_network: true, use_gpu: true, use_llm: false, library_sources: ["seed_analog", "chembl_target", "pubchem_reference"] };
  }
  if (profileId === "api-assisted") {
    return { allow_network: true, use_gpu: false, use_llm: true, library_sources: ["seed_analog", "chembl_target", "pubchem_reference"] };
  }
  return {
    allow_network: true,
    use_gpu: true,
    use_llm: true,
    library_sources: ["seed_analog", "chembl_target", "pubchem_reference"],
    library_limit: 2000,
    detailed_eval_limit: 300,
    display_limit: 96,
    conformer_limit: 24
  };
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

function targetReadinessLabel(result: PipelineResult | null) {
  if (!result) return "pending";
  const mode = result.scoring_mode || String(result.target_readiness?.scoring_mode ?? "unknown");
  const status = String(result.target_readiness?.status ?? "unknown");
  return `${mode} / ${status}`;
}

function scenarioClass(mode?: string) {
  const normalized = String(mode ?? "").toLowerCase().replace(/_/g, "-");
  if (normalized.includes("scored")) return "scored";
  if (normalized.includes("stress")) return "stress";
  return "evidence";
}
