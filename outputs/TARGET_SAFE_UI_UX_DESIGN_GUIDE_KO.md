# Target-SAFE UI/UX Design Guide

## 1. 디자인 목표

Target-SAFE는 랜딩페이지가 아니라 실제 연구자가 사용하는 evidence-gated lead triage app이다. 따라서 멋진 첫 화면보다 중요한 것은 사용자가 다음 질문에 빠르게 답하도록 돕는 것이다.

- 무엇을 실행해야 하는가?
- 지금 어떤 근거와 계산 자원을 사용했는가?
- 왜 이 후보가 Go, Hold, No-Go인가?
- 불확실한 부분은 무엇이고, 다음 검증은 무엇인가?
- 이 시스템이 대회가 요구하는 agentic AI와 어떻게 연결되는가?

이번 UI/UX 업그레이드는 Pintel 웹사이트의 `dark immersive stage`, `blue flow visual`, `short section copy`, `workflow cards`, `metric band`, `presentation-ready flow`를 참고하되, Target-SAFE의 분자/근거/판정 맥락에 맞게 재해석한다.

## 2. Pintel에서 관찰한 구조

Pintel 웹사이트는 다음 패턴으로 구성되어 있었다.

- 본문은 `Wanted Sans`, 영문/숫자/utility 영역은 `Jost`를 사용한다.
- 배경은 `#060910`에 가까운 deep navy-black이다.
- 주요 accent는 vivid blue 계열이며, 흰색 큰 헤드라인과 muted gray 보조 문장이 대비된다.
- 각 섹션은 하나의 주장만 담는다.
- 큰 wave/particle visual은 장식이 아니라 AI flow와 operational intelligence를 설명하는 은유로 작동한다.
- workflow card, metric band, compact card를 통해 복잡한 기술을 빠르게 훑게 한다.

Target-SAFE는 이 구조를 그대로 복제하지 않는다. 대신 다음처럼 번역한다.

- AI flow -> molecular evidence flow
- physical world operation -> lead triage operation
- workflow card -> Plan/Act/Observe/Critique/Replan/Redesign decision loop
- mission metric band -> library screening and Go/Hold/No-Go metric band
- product cards -> candidate stories and evidence cards

## 3. Target-SAFE 디자인 시스템

기본 방향은 `Molecular Evidence Flow`다.

- 기본 폰트: Pretendard
- 영문, 숫자, metric, eyebrow: Jost
- 배경: Deep Lab Black
- 핵심 accent: Assay Blue
- 보조 accent: Cyan Evidence
- Hold: Amber Hold
- No-Go: Red Block
- 중립 정보: Muted Graphite

시각 요소는 무작위 gradient가 아니라 얇은 particle field, evidence wave, graph line, molecule stage로 제한한다. 장식이 기능을 가리면 안 된다.

## 4. 탭별 UX 원칙

### Run Console

Run Console은 설정과 실행의 공간이다. 첫 사용자가 헤매지 않도록 `Start here` guided strip을 둔다.

흐름은 다음과 같다.

1. Select evidence scope
2. Choose compute lane
3. Run staged triage
4. Inspect first candidate

실행 후에는 `What happened`, `Why many candidates are Hold`, `What needs validation`을 요약한다.

### Judge Demo

Judge Demo는 심사위원을 위한 presentation-ready tab이다. 한 run 결과를 다음 흐름으로 보여준다.

1. Why this problem
2. Agentic loop
3. Evidence-gated decision
4. Three candidate stories
5. Runtime truth
6. Contribution

핵심 메시지는 다음이다.

> Target-SAFE는 AI가 신약을 발명했다고 주장하지 않는다. 초기 후보 검토 범위를 근거, 적용영역, 불확실성, 위험 신호를 기준으로 투명하게 좁힌다.

### Library Browser

Molecule Atlas는 Library Browser에 가깝게 발전시켰다. 대규모 compound library를 전제로 raw input, valid unique, detailed evaluation, rendered structure, Go/Hold/No-Go count를 metric band로 보여준다.

필터는 다음 기준을 중심으로 한다.

- decision status
- source
- sort mode
- risk flag
- applicability domain
- QED quality

2~4개 후보 비교 drawer를 제공해 후보를 열기 전에 구조, lower pChEMBL, AD, QED, alerts, gate blocker를 나란히 볼 수 있게 한다.

### Candidate Twin

Candidate Twin은 한 후보의 molecular evidence twin이다. 긴 gate table을 바로 보여주기 전에 pass/review/block gate rail을 먼저 제공한다.

- pass: 기준을 통과한 gate
- review: Hold 또는 추가 검토의 이유가 되는 gate
- block: No-Go 또는 hard blocker의 이유가 되는 gate

상세 gate audit table은 펼침 영역에 둔다.

### Evidence Graph

Evidence Graph는 전체 노드를 보여주는 장면보다 selected candidate neighborhood를 기본으로 한다. label density control과 legend를 추가해 글자 겹침을 줄이고, 필요한 경우에만 all labels를 켠다.

## 5. 과장 방지 문구

모든 UI와 report는 다음 원칙을 지킨다.

- generated candidate의 실제 효능을 주장하지 않는다.
- computed conformer를 validated binding pose처럼 표현하지 않는다.
- known drug adverse reaction을 candidate-specific toxicity 결론처럼 표현하지 않는다.
- GPU/LLM/API를 요청했다는 사실과 실제 사용됐다는 사실을 분리한다.
- validation data가 부족하면 metric을 만들지 않고 `insufficient_data`로 표시한다.

## 6. 구현 방식

이번 업그레이드는 backend 변경을 최소화했다. 기존 run payload에서 frontend derived summary를 만든다.

- JudgeDemoSummary: 대표 Go/Hold/No-Go 후보, agentic event count, evaluation criteria map
- GuidedRunSummary: first inspection target, evidence mode, fallback explanation, next validation
- CandidateCompareSelection: 2~4개 후보 비교 상태

새 backend endpoint를 추가하지 않아도 기존 `PipelineResult`만으로 작동한다.

## 7. 검증 기준

시각 QA 기준은 다음이다.

- 한 탭에 모든 내용을 욱여넣지 않는다.
- Judge Demo는 3분 발표 흐름으로 읽힌다.
- Run Console은 처음 사용자에게 다음 행동을 알려준다.
- Library Browser는 많은 후보를 탐색하고 비교할 수 있다.
- Candidate Twin은 Go/Hold/No-Go 기준을 표 없이도 먼저 이해시킨다.
- Evidence Graph는 label density를 조절할 수 있다.
- dark/light, desktop/mobile에서 텍스트가 겹치지 않는다.
