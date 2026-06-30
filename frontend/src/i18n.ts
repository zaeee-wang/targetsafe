export type Locale = "ko" | "en";
export type ThemeMode = "dark" | "light";

export const COPY = {
  en: {
    brand: {
      subtitle: "Molecular Evidence Twin",
      navAria: "Target-SAFE sections"
    },
    views: {
      console: "Run Console",
      atlas: "Molecule Atlas",
      twin: "Candidate Twin",
      graph: "Evidence Graph",
      known: "Known Drugs & Risks",
      reports: "Reports"
    },
    top: {
      eyebrow: "Evidence-gated triage console",
      computeProfile: "Compute profile",
      run: "Run triage",
      preferences: "Display controls",
      dark: "Dark",
      light: "Light",
      ko: "KO",
      en: "EN"
    },
    nav: {
      runLoaded: "Run loaded",
      noRunYet: "No run yet",
      ready: "CPU demo ready"
    },
    console: {
      eyebrow: "Run Console",
      heading: "Start with the smallest stable run, then inspect evidence by section.",
      body: "This app narrows early EGFR lead candidates with descriptors, model uncertainty, graph evidence, and known-drug context. It does not claim candidate safety or clinical efficacy.",
      runDemo: "Run CPU demo",
      disease: "Disease",
      target: "Target",
      seed: "Seed SMILES",
      goal: "Optimization goal",
      candidates: "Candidates",
      liveApis: "Live APIs",
      gpu: "GPU",
      llm: "LLM",
      computeProfile: "Compute profile",
      evidenceMode: "Evidence mode",
      liveEnabled: "Live APIs enabled",
      cachedDemo: "Cached/fallback demo",
      evidenceGraph: "Evidence graph",
      runPending: "Run pending",
      evidenceModes: {
        offline_fallback: "Offline fallback demo",
        live: "Live public evidence",
        cached: "Cached public evidence",
        mixed: "Mixed evidence",
        error_fallback: "API error fallback",
        unknown: "Unknown evidence mode"
      }
    },
    seedDrawer: {
      open: "Browse seed library",
      title: "Seed molecule drawer",
      subtitle: "Pick a known drug or control molecule instead of typing SMILES by hand.",
      warning: "Non-EGFR seeds are useful for stress-testing chemistry and UX, but EGFR Go/Hold/No-Go scoring still requires target-specific evidence.",
      search: "Search molecules",
      all: "All",
      apply: "Use as seed",
      close: "Close",
      invalid: "Invalid-control",
      noFigure: "No figure",
      smiles: "SMILES",
      sourceReference: "Reference drug",
      sourcePreset: "Curated preset"
    },
    profiles: {
      eyebrow: "Compute profiles",
      heading: "What changes when you switch compute mode",
      on: "on",
      off: "off",
      features: {
        allow_network: "Live evidence APIs",
        use_gpu: "GPU embeddings / retrieval",
        use_llm: "LLM graph-grounded report",
        train_qsar: "QSAR refresh",
        use_cached_demo: "Offline deterministic cache"
      },
      text: {
        "cpu-demo": {
          label: "CPU demo",
          description: "Stable offline walkthrough using cached/fallback evidence and deterministic scoring.",
          runtime: "Best for rehearsal and stable presentation."
        },
        "cpu-evidence": {
          label: "CPU evidence-grade",
          description: "Refreshes public ChEMBL, PubChem, ClinicalTrials.gov, and openFDA evidence on CPU.",
          runtime: "Slower but better for evidence freshness."
        },
        "gpu-accelerated": {
          label: "GPU accelerated",
          description: "Adds optional molecular embedding, nearest-neighbor retrieval, and uncertainty support when GPU is available.",
          runtime: "Useful for larger candidate sets."
        },
        "api-assisted": {
          label: "API assisted",
          description: "Adds optional LLM summarization and graph-grounded reporting while keeping tool evidence logged.",
          runtime: "Best for narrative clarity."
        },
        "full-research": {
          label: "Full research mode",
          description: "Combines live evidence, optional GPU modules, and API-assisted reporting.",
          runtime: "Slowest, highest-fidelity demo path."
        }
      }
    },
    scope: {
      eyebrow: "Target scope",
      heading: "EGFR is the scored pilot; other targets are expansion lanes.",
      body: "The app can browse broad public drug structures now. Scientific Go/Hold/No-Go scoring remains target-specific, so non-EGFR targets should not reuse the EGFR QSAR without their own assay evidence.",
      targets: {
        EGFR: ["full scoring pilot", "QSAR interval, AD check, known TKI context, and decision graph are enabled."],
        ALK: ["evidence expansion", "Reference atlas and live evidence hooks are ready; target-specific QSAR needs ALK assay refresh."],
        BRAF: ["evidence expansion", "Reference atlas and live evidence hooks are ready; target-specific QSAR needs BRAF assay refresh."],
        KRAS: ["evidence expansion", "Reference atlas and live evidence hooks are ready; target-specific covalent chemistry rules are needed."],
        HER2: ["evidence expansion", "Reference atlas and live evidence hooks are ready; target-specific assay set is needed."]
      }
    },
    atlas: {
      eyebrow: "Molecule Atlas",
      heading: "Candidate structures and known reference drugs.",
      openKnown: "Open known risks",
      emptyFigure: "Run triage to populate molecular figures.",
      primaryCandidate: "Primary candidate",
      noCandidate: "No candidate yet",
      note: "Large molecular figures are the first inspection surface. Decision evidence lives in the twin and graph views, not in a crowded landing page.",
      generated: "Generated and control set",
      shown: "shown",
      scored: "scored",
      emptyTitle: "No run yet",
      emptyText: "Use Run Console to create the first candidate atlas.",
      noStructure: "No structure",
      lowerPchembl: "lower pChEMBL",
      reference: "Reference library",
      knownDrugs: "Known and public drugs",
      noFigure: "No figure"
    },
    twin: {
      emptyTitle: "No candidate twin yet",
      emptyText: "Run triage, then select a molecule from the atlas.",
      eyebrow: "Candidate Twin",
      twoD: "2D structure",
      threeD: "3D conformer",
      no2d: "No 2D depiction",
      viewerWarning: "3D view is a computed conformer for spatial inspection, not a validated binding pose.",
      why: "Why this decision",
      inspectGraph: "Inspect graph evidence",
      targetFit: "Target fit",
      qedSa: "QED / SA",
      alerts: "Alerts",
      severeBlocker: "severe blocker present",
      reviewIfNonzero: "review if nonzero",
      graph: "Evidence graph",
      linkedNodes: "linked nodes",
      descriptors: "descriptors",
      knownContext: "Known-drug context",
      contextPending: "Known-drug context loads after a run.",
      sim: "sim",
      nextValidation: "Next validation",
      redesign: "Critic redesign",
      parentCandidate: "Parent candidate",
      childSuggestions: "Child suggestions",
      redesignReason: "Reason",
      redesignAction: "Action",
      noRedesign: "No redesign suggestion for this candidate."
    },
    conformer: {
      unavailable: "3D conformer unavailable",
      emptyMessage: "No conformer payload was returned.",
      controls: "3D viewer controls",
      rotateLeft: "Rotate left",
      rotateRight: "Rotate right",
      zoomIn: "Zoom in",
      zoomOut: "Zoom out",
      reset: "Reset view",
      exportXyz: "Export XYZ for PyMOL / Avogadro",
      xyzComment: "computed conformer from Target-SAFE; not a validated binding pose.",
      aria: "Interactive computed conformer"
    },
    graph: {
      eyebrow: "GraphRAG-lite evidence explorer",
      heading: "Zoomable decision graph.",
      scopeAria: "Graph scope",
      scopes: {
        selected: "selected candidate neighborhood",
        summary: "assay / risk / threshold summary",
        all: "all nodes, labels on zoom"
      },
      nodeFilter: "Node type filter",
      edgeFilter: "Edge type filter",
      all: "all",
      aria: "Zoomable evidence graph",
      emptyTitle: "No graph yet",
      emptyText: "Run triage to build a decision evidence graph."
    },
    known: {
      eyebrow: "Known Drugs & Risks",
      heading: "Reference context, not candidate-specific toxicity.",
      banner: "Known EGFR TKI adverse reactions and label warnings are used as review context. Target-SAFE does not infer that a generated candidate has these adverse events.",
      noStructure: "No structure",
      reference: "reference",
      nearest: "nearest known drugs",
      candidateContext: "Candidate context",
      selectCandidate: "Select a candidate after running triage.",
      sim: "sim",
      evidenceStatus: "Evidence status",
      cached: "cached"
    },
    reports: {
      eyebrow: "Reports",
      heading: "Model card, threshold registry, trace, and report.",
      openReport: "Open HTML report",
      modelCard: "Model card",
      evidenceMode: "Evidence mode",
      scientificValidation: "Scientific validation",
      validationStatus: "Validation status",
      datasetSize: "Dataset size",
      split: "Split",
      metrics: "Metrics",
      redesignReport: "Critic redesign loop",
      redesignChildren: "child suggestions",
      model: "Model",
      trainingSize: "Training size",
      applicability: "Applicability",
      thresholdRegistry: "Threshold registry",
      sourceRequired: "source required",
      agentTrace: "Agent trace",
      pendingTrace: "Run triage to create an agent trace.",
      phase: "Phase",
      action: "Action",
      status: "Status"
    },
    status: {
      Go: "Go",
      Hold: "Hold",
      "No-Go": "No-Go",
      Unscored: "Unscored"
    },
    criteria: {
      molecular_weight: "Molecular Weight",
      logp: "LogP",
      tpsa: "TPSA",
      qed: "QED",
      synthetic_accessibility: "Synthetic Accessibility",
      structural_alerts: "Structural Alerts",
      conservative_activity: "Conservative Activity",
      applicability_domain: "Applicability Domain",
      prediction_uncertainty: "Prediction Uncertainty",
      evidence_support: "Evidence Support",
      lipinski: "Lipinski"
    },
    criterionValues: {
      pass: "pass",
      review: "review",
      block: "block"
    }
  },
  ko: {
    brand: {
      subtitle: "분자 근거 디지털 트윈",
      navAria: "Target-SAFE 화면"
    },
    views: {
      console: "실행 콘솔",
      atlas: "분자 아틀라스",
      twin: "후보 트윈",
      graph: "근거 그래프",
      known: "기존 약물·위험",
      reports: "보고서"
    },
    top: {
      eyebrow: "근거 기반 리드 후보 분류 콘솔",
      computeProfile: "컴퓨트 프로필",
      run: "Triage 실행",
      preferences: "표시 설정",
      dark: "다크",
      light: "라이트",
      ko: "KO",
      en: "EN"
    },
    nav: {
      runLoaded: "실행 결과 로드됨",
      noRunYet: "아직 실행 없음",
      ready: "CPU 데모 준비됨"
    },
    console: {
      eyebrow: "실행 콘솔",
      heading: "안정적인 작은 실행부터 시작하고, 섹션별로 근거를 검토합니다.",
      body: "이 앱은 descriptor, 모델 불확실성, 그래프 근거, 기존 약물 맥락을 연결해 초기 EGFR 리드 후보를 좁힙니다. 후보의 안전성이나 임상 효능을 확정하지 않습니다.",
      runDemo: "CPU 데모 실행",
      disease: "질병",
      target: "타깃",
      seed: "Seed SMILES",
      goal: "최적화 목표",
      candidates: "후보 수",
      liveApis: "Live API",
      gpu: "GPU",
      llm: "LLM",
      computeProfile: "컴퓨트 프로필",
      evidenceMode: "근거 모드",
      liveEnabled: "Live API 사용",
      cachedDemo: "캐시/폴백 데모",
      evidenceGraph: "근거 그래프",
      runPending: "실행 대기",
      evidenceModes: {
        offline_fallback: "오프라인 폴백 데모",
        live: "Live 공개 근거",
        cached: "캐시된 공개 근거",
        mixed: "혼합 근거",
        error_fallback: "API 오류 폴백",
        unknown: "알 수 없는 근거 모드"
      }
    },
    seedDrawer: {
      open: "Seed 라이브러리 열기",
      title: "Seed 분자 drawer",
      subtitle: "SMILES를 직접 치지 않고 기존 약물이나 control 분자를 선택합니다.",
      warning: "비-EGFR seed는 화학/UX stress test에는 유용하지만, EGFR Go/Hold/No-Go scoring은 여전히 타깃 특이 근거가 필요합니다.",
      search: "분자 검색",
      all: "전체",
      apply: "Seed로 사용",
      close: "닫기",
      invalid: "Invalid-control",
      noFigure: "figure 없음",
      smiles: "SMILES",
      sourceReference: "Reference drug",
      sourcePreset: "Curated preset"
    },
    profiles: {
      eyebrow: "컴퓨트 프로필",
      heading: "컴퓨팅 방식을 바꾸면 무엇이 달라지는가",
      on: "사용",
      off: "미사용",
      features: {
        allow_network: "Live evidence API",
        use_gpu: "GPU 임베딩 / 검색",
        use_llm: "LLM 그래프 기반 보고",
        train_qsar: "QSAR 재학습",
        use_cached_demo: "오프라인 결정론적 캐시"
      },
      text: {
        "cpu-demo": {
          label: "CPU 데모",
          description: "캐시/폴백 근거와 결정론적 scoring으로 안정적으로 시연하는 모드입니다.",
          runtime: "리허설과 발표 안정성에 가장 적합합니다."
        },
        "cpu-evidence": {
          label: "CPU 근거 강화",
          description: "CPU만으로 ChEMBL, PubChem, ClinicalTrials.gov, openFDA 근거를 새로 조회합니다.",
          runtime: "느리지만 근거 최신성이 좋아집니다."
        },
        "gpu-accelerated": {
          label: "GPU 가속",
          description: "GPU가 있을 때 분자 임베딩, nearest-neighbor 검색, 불확실성 보조를 추가합니다.",
          runtime: "후보 수가 많을 때 유용합니다."
        },
        "api-assisted": {
          label: "API 보조",
          description: "도구 근거 로그는 유지하면서 LLM 요약과 그래프 기반 보고서 품질을 높입니다.",
          runtime: "설명력과 발표 서사에 적합합니다."
        },
        "full-research": {
          label: "Full research",
          description: "Live 근거, 선택적 GPU 모듈, API 보조 보고를 모두 결합합니다.",
          runtime: "가장 느리지만 본선 데모 품질이 높습니다."
        }
      }
    },
    scope: {
      eyebrow: "타깃 범위",
      heading: "EGFR은 scoring 파일럿이고, 다른 타깃은 확장 경로입니다.",
      body: "현재 앱은 다양한 공개 약물 구조를 탐색할 수 있습니다. 다만 과학적 Go/Hold/No-Go 판정은 타깃별 근거가 필요하므로, 비-EGFR 타깃에는 EGFR QSAR를 그대로 재사용하지 않습니다.",
      targets: {
        EGFR: ["scoring 파일럿", "QSAR 구간, 적용영역, EGFR TKI 맥락, decision graph를 사용합니다."],
        ALK: ["근거 확장", "Reference atlas와 live evidence hook은 준비되어 있으며 ALK assay 기반 QSAR 갱신이 필요합니다."],
        BRAF: ["근거 확장", "Reference atlas와 live evidence hook은 준비되어 있으며 BRAF assay 기반 QSAR 갱신이 필요합니다."],
        KRAS: ["근거 확장", "Reference atlas와 live evidence hook은 준비되어 있으며 KRAS 공유결합 화학 규칙이 필요합니다."],
        HER2: ["근거 확장", "Reference atlas와 live evidence hook은 준비되어 있으며 HER2 assay set이 필요합니다."]
      }
    },
    atlas: {
      eyebrow: "분자 아틀라스",
      heading: "후보 구조와 기존 reference 약물을 함께 봅니다.",
      openKnown: "기존 위험 보기",
      emptyFigure: "Triage를 실행하면 분자 figure가 표시됩니다.",
      primaryCandidate: "대표 후보",
      noCandidate: "후보 없음",
      note: "큰 분자 figure가 첫 번째 검토 표면입니다. 판정 근거는 복잡한 랜딩 화면이 아니라 후보 트윈과 그래프 화면에서 확인합니다.",
      generated: "생성 및 control 후보",
      shown: "개 표시",
      scored: "개 scoring",
      emptyTitle: "아직 실행 없음",
      emptyText: "실행 콘솔에서 첫 후보 atlas를 생성하세요.",
      noStructure: "구조 없음",
      lowerPchembl: "하한 pChEMBL",
      reference: "Reference library",
      knownDrugs: "기존·공개 약물",
      noFigure: "figure 없음"
    },
    twin: {
      emptyTitle: "후보 트윈 없음",
      emptyText: "Triage 실행 후 atlas에서 분자를 선택하세요.",
      eyebrow: "후보 트윈",
      twoD: "2D 구조",
      threeD: "3D conformer",
      no2d: "2D depiction 없음",
      viewerWarning: "3D view는 공간 검토용 계산 conformer이며, 검증된 binding pose가 아닙니다.",
      why: "왜 이 판정인가",
      inspectGraph: "그래프 근거 보기",
      targetFit: "타깃 적합도",
      qedSa: "QED / SA",
      alerts: "Alert",
      severeBlocker: "severe blocker 존재",
      reviewIfNonzero: "0이 아니면 검토",
      graph: "근거 그래프",
      linkedNodes: "연결 노드",
      descriptors: "descriptor",
      knownContext: "기존 약물 맥락",
      contextPending: "실행 후 기존 약물 맥락이 로드됩니다.",
      sim: "유사도",
      nextValidation: "다음 검증",
      redesign: "Critic 재설계",
      parentCandidate: "부모 후보",
      childSuggestions: "자식 제안",
      redesignReason: "이유",
      redesignAction: "행동",
      noRedesign: "이 후보에는 재설계 제안이 없습니다."
    },
    conformer: {
      unavailable: "3D conformer 사용 불가",
      emptyMessage: "conformer payload가 반환되지 않았습니다.",
      controls: "3D viewer controls",
      rotateLeft: "왼쪽 회전",
      rotateRight: "오른쪽 회전",
      zoomIn: "확대",
      zoomOut: "축소",
      reset: "초기화",
      exportXyz: "PyMOL / Avogadro용 XYZ 내보내기",
      xyzComment: "Target-SAFE 계산 conformer; 검증된 binding pose가 아님.",
      aria: "상호작용 가능한 계산 conformer"
    },
    graph: {
      eyebrow: "GraphRAG-lite 근거 탐색기",
      heading: "확대 가능한 decision graph.",
      scopeAria: "그래프 범위",
      scopes: {
        selected: "선택 후보 주변 근거망",
        summary: "assay / risk / threshold 요약",
        all: "전체 노드, 확대 시 라벨 표시"
      },
      nodeFilter: "노드 타입 필터",
      edgeFilter: "엣지 타입 필터",
      all: "전체",
      aria: "확대 가능한 근거 그래프",
      emptyTitle: "그래프 없음",
      emptyText: "Triage를 실행하면 decision evidence graph가 생성됩니다."
    },
    known: {
      eyebrow: "기존 약물·위험",
      heading: "후보 독성 결론이 아니라 reference 맥락입니다.",
      banner: "기존 EGFR TKI 부작용과 label warning은 검토 맥락으로만 사용합니다. Target-SAFE는 생성 후보가 해당 이상반응을 가진다고 단정하지 않습니다.",
      noStructure: "구조 없음",
      reference: "reference",
      nearest: "가장 가까운 기존 약물",
      candidateContext: "후보 맥락",
      selectCandidate: "Triage 실행 후 후보를 선택하세요.",
      sim: "유사도",
      evidenceStatus: "근거 상태",
      cached: "캐시"
    },
    reports: {
      eyebrow: "보고서",
      heading: "모델 카드, threshold registry, agent trace, HTML 보고서.",
      openReport: "HTML 보고서 열기",
      modelCard: "모델 카드",
      evidenceMode: "근거 모드",
      scientificValidation: "과학적 검증",
      validationStatus: "검증 상태",
      datasetSize: "데이터 크기",
      split: "Split",
      metrics: "지표",
      redesignReport: "Critic 재설계 루프",
      redesignChildren: "개 자식 제안",
      model: "모델",
      trainingSize: "학습 크기",
      applicability: "적용영역",
      thresholdRegistry: "Threshold registry",
      sourceRequired: "출처 필요",
      agentTrace: "Agent trace",
      pendingTrace: "Triage를 실행하면 agent trace가 생성됩니다.",
      phase: "단계",
      action: "행동",
      status: "상태"
    },
    status: {
      Go: "Go",
      Hold: "Hold",
      "No-Go": "No-Go",
      Unscored: "미채점"
    },
    criteria: {
      molecular_weight: "분자량",
      logp: "LogP",
      tpsa: "TPSA",
      qed: "QED",
      synthetic_accessibility: "합성 접근성",
      structural_alerts: "구조 alert",
      conservative_activity: "보수적 활성",
      applicability_domain: "적용영역",
      prediction_uncertainty: "예측 불확실성",
      evidence_support: "근거 지지도",
      lipinski: "Lipinski"
    },
    criterionValues: {
      pass: "통과",
      review: "검토",
      block: "차단"
    }
  }
} as const;

type WidenStrings<T> = T extends string
  ? string
  : T extends readonly (infer Item)[]
    ? readonly WidenStrings<Item>[]
    : T extends object
      ? { readonly [Key in keyof T]: WidenStrings<T[Key]> }
      : T;

export type Copy = WidenStrings<(typeof COPY)["en"]>;

export function getStoredLocale(): Locale {
  if (typeof window === "undefined") return "ko";
  const stored = window.localStorage.getItem("targetsafe-locale");
  return stored === "en" || stored === "ko" ? stored : "ko";
}

export function getStoredTheme(): ThemeMode {
  if (typeof window === "undefined") return "dark";
  const stored = window.localStorage.getItem("targetsafe-theme");
  return stored === "light" || stored === "dark" ? stored : "dark";
}

export function localizedProfile(profile: Record<string, unknown>, copy: Copy) {
  const id = String(profile.id ?? "");
  const local = copy.profiles.text[id as keyof typeof copy.profiles.text];
  return {
    label: local?.label ?? String(profile.label ?? id),
    description: local?.description ?? String(profile.description ?? ""),
    runtime: local?.runtime ?? String(profile.expected_runtime ?? "")
  };
}

export function statusLabel(status: string, copy: Copy) {
  return copy.status[status as keyof typeof copy.status] ?? status;
}

export function criterionLabel(key: string, copy: Copy) {
  return copy.criteria[key as keyof typeof copy.criteria] ?? key.replaceAll("_", " ");
}

export function criterionValue(value: string, copy: Copy) {
  return copy.criterionValues[value as keyof typeof copy.criterionValues] ?? value;
}

const BACKEND_TEXT_KO: Record<string, string> = {
  "Run pending.": "실행 대기 중입니다.",
  "Passed sourced hard gates, conservative activity bound, applicability-domain, and evidence checks.": "출처가 연결된 hard gate, 보수적 활성 하한, 적용영역, 근거 검사를 통과했습니다.",
  "Candidate remains plausible but needs additional evidence, uncertainty reduction, or risk review.": "후보는 가능성이 있지만 추가 근거, 불확실성 감소, 위험 검토가 필요합니다.",
  "Known-drug context loads after a run.": "실행 후 기존 약물 맥락이 로드됩니다.",
  "Confirm with orthogonal assay, ADMET panel, and expert medicinal chemistry review.": "직교 assay, ADMET 패널, 전문가 의약화학 검토로 확인하세요.",
  "Confirm critic findings with RDKit, assay data, and expert review.": "RDKit, assay 데이터, 전문가 검토로 critic findings를 확인하세요.",
  "Review nearest ChEMBL analogs or collect target-specific assay evidence.": "가까운 ChEMBL analog를 검토하거나 타깃 특이 assay 근거를 수집하세요.",
  "Require additional public or internal assay evidence before prioritization.": "우선순위화 전에 추가 공개 또는 내부 assay 근거가 필요합니다."
};

export function localizeBackendText(text: string, locale: Locale) {
  if (locale === "en") return text;
  return BACKEND_TEXT_KO[text] ?? text;
}
