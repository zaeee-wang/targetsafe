# Target-SAFE 문제 정의와 최종 기여

## 1. 우리가 해결하려는 본질적 문제

Target-SAFE가 해결하려는 문제는 “AI가 신약을 발명했다”라고 주장하는 것이 아니다. 실제 목표는 초기 리드 후보 검토 단계에서 연구자가 다음 질문에 빠르고 투명하게 답하도록 돕는 것이다.

- 이 후보 분자는 구조적으로 유효한가?
- 기본 약물유사성, 합성가능성, 구조 alert 관점에서 즉시 제외해야 할 문제가 있는가?
- EGFR 활성 예측은 모델 적용영역 안에서 나온 값인가?
- 평균 예측값이 아니라 보수적 하한과 불확실성까지 고려했을 때 검토할 가치가 있는가?
- 알려진 EGFR TKI 및 공개 약물 구조와 어떤 맥락으로 비교되는가?
- 최종 Go/Hold/No-Go 판정은 어떤 계산값, threshold, 근거 그래프, critic finding에 의해 내려졌는가?

따라서 Target-SAFE의 핵심 주장은 다음과 같다.

> Target-SAFE는 초기 EGFR 리드 후보를 구조, 물성, 예측 불확실성, 적용영역, known-drug context, source-backed threshold, evidence graph를 기반으로 좁히는 투명한 의사결정 지원 agent이다.

## 2. 기존 접근의 문제 인식

초기 기획은 RDKit, ChEMBL, PubChem, openFDA, LLM을 조합한 lead triage agent라는 방향은 맞았지만, 냉정하게 보면 다음 한계가 있었다.

- 너무 rule-based table처럼 보일 위험이 있었다.
- threshold와 계수의 출처가 명확히 보이지 않으면 임의 점수처럼 보일 수 있었다.
- QSAR 예측만 제시하면 왜 Hold인지, 왜 No-Go인지 추적하기 어렵다.
- known drug의 부작용 정보를 후보 독성 결론처럼 오해할 위험이 있었다.
- UI가 한 화면에 너무 많은 정보를 담아 처음 사용자가 실행 순서를 이해하기 어려웠다.
- computed conformer가 실제 binding pose처럼 보이면 과학적으로 과장된 인상을 줄 수 있었다.
- 다른 seed 분자를 시험하려면 사용자가 SMILES를 직접 입력해야 해 데모 사용성이 낮았다.

## 3. 최종 해결 방향

Target-SAFE는 EGFR 변이 양성 NSCLC를 파일럿으로 하는 Evidence-Gated Lead Triage Agent로 재구성되었다.

- RDKit 또는 fallback evaluator로 분자 유효성, descriptor, QED, Lipinski, structural alert, SA score를 계산한다.
- EGFR reference activity와 analog similarity를 사용해 보수적 activity interval과 applicability domain을 제시한다.
- 모든 threshold는 threshold registry에서 source와 rationale을 함께 관리한다.
- evidence graph가 candidate, descriptor, prediction, threshold, known analog, risk, decision을 연결한다.
- Critic Agent가 invalid SMILES, severe alert, out-of-domain overclaim, API fallback, 근거 부족을 검토한다.
- UI는 Run Console, Molecule Atlas, Candidate Twin, Evidence Graph, Known Drugs & Risks, Reports로 분리했다.
- 다크/라이트 모드와 한/영 전환을 제공해 심사자와 사용자의 접근성을 높였다.
- Seed molecule drawer를 추가해 알려진 EGFR TKI, 일반 약물 control, negative/stress control을 구조 preview와 함께 선택할 수 있게 했다.

## 4. EGFR 파일럿과 타깃 확장 원칙

현재 Go/Hold/No-Go scoring은 EGFR 파일럿에 맞춰져 있다. 이는 약점이 아니라 과학적 안전장치다. 타깃마다 assay endpoint, 활성 기준, known inhibitor library, applicability domain, 구조 risk가 달라지기 때문이다.

- EGFR: 현재 scoring pilot. QSAR interval, applicability domain, known EGFR TKI context, evidence graph decision을 제공한다.
- ALK, BRAF, KRAS, HER2: public drug atlas와 UI lane은 제공하지만 EGFR QSAR를 그대로 재사용하지 않는다.
- 다른 타깃으로 확장하려면 해당 타깃의 ChEMBL assay set, known inhibitor library, threshold registry, model card를 별도로 구축해야 한다.

## 5. Known Drug와 부작용 정보 사용 방식

Gefitinib, Erlotinib, Afatinib, Osimertinib, Dacomitinib, Mobocertinib 같은 reference drug는 후보 독성 결론의 근거가 아니다. Target-SAFE는 이 정보를 다음 용도로만 사용한다.

- 후보가 알려진 EGFR TKI scaffold와 얼마나 유사한지 보여준다.
- 알려진 label-level adverse reaction과 warning을 review checklist로 제시한다.
- “유사하므로 같은 부작용이 발생한다”라고 말하지 않는다.
- UI에서 항상 reference context이며 candidate-specific toxicity가 아니라고 표시한다.

## 6. Digital Twin UI의 의미

Target-SAFE의 molecular digital twin은 가짜 실험 시뮬레이션이 아니다. 하나의 후보 분자에 대해 현재 확보된 계산값, 예측, 불확실성, 알려진 약물 맥락, 구조 risk, evidence graph, 의사결정 이유, 다음 검증 항목을 한 화면에서 연결해 보여주는 연구 상태판이다.

후보 상세 화면은 다음 질문에 답하도록 설계되었다.

- 이 분자는 무엇인가?
- 2D 구조와 computed 3D conformer는 어떻게 보이는가?
- 3D conformer가 binding pose가 아니라는 점이 명확한가?
- Go/Hold/No-Go 판정의 핵심 이유는 무엇인가?
- 어떤 criteria가 pass, review, block인가?
- 가장 가까운 known drug는 무엇이며, 어떤 follow-up 검증이 필요한가?

## 7. UI와 사용성 기여

이번 UI는 landing page가 아니라 실행 가능한 research app으로 구성되었다.

- Run Console에서 설정과 실행을 시작한다.
- Seed molecule drawer에서 구조를 보며 seed를 선택할 수 있다.
- Molecule Atlas에서 후보와 reference 구조를 넓게 훑는다.
- Candidate Twin에서 한 후보를 깊게 본다.
- Evidence Graph에서 선택 후보 주변 근거망을 확대/축소한다.
- Known Drugs & Risks에서 알려진 약물과 label-level risk를 맥락 정보로 확인한다.
- Reports에서 model card, threshold registry, trace, report를 확인한다.

## 8. Agentic AI와의 연결

Target-SAFE의 agentic 요소는 “LLM이 분자를 상상해서 답한다”가 아니라, 여러 도구와 근거 계층을 호출하고 그 결과에 따라 다음 행동과 판정을 바꾸는 루프에 있다.

- Planner Agent가 실행 계획을 만든다.
- Evidence Agent가 공개 DB 또는 fallback evidence를 수집하고 evidence mode를 기록한다.
- RDKit/QSAR evaluator가 구조, 물성, 예측 구간, 적용영역을 관찰한다.
- Decision module이 source-backed threshold로 1차 Go/Hold/No-Go를 만든다.
- Critic Agent가 out-of-domain, broad uncertainty, severe alert, fallback evidence, unsupported Go를 검토한다.
- Critic finding이 있으면 Replan 단계에서 constrained redesign action을 선택한다.
- Redesign Agent가 임의 SMILES 조작이 아니라 curated EGFR analog/template 기반 child candidate를 제안한다.
- child candidate는 같은 descriptor, QSAR, threshold, critic 절차로 재평가된다.
- Evidence Graph와 Reports는 이 과정을 agent event timeline과 parent/child comparison으로 남긴다.

따라서 Target-SAFE는 단순 scoring table이 아니라 `Plan -> Act -> Observe -> Critique -> Replan -> Redesign -> Re-evaluate -> Decide` 흐름을 가진 evidence-gated triage agent로 설명할 수 있다.

## 9. 과학적 검증과 솔직한 한계 표시

Target-SAFE는 QSAR 예측을 최종 실험값처럼 쓰지 않는다. EGFR validation module은 ChEMBL/live evidence row와 known EGFR reference row를 정제해 충분한 구조/활성 데이터가 있을 때만 RMSE, MAE, Spearman, top-k enrichment, interval coverage, applicability-domain 안/밖 성능을 계산한다.

데이터가 부족하면 `insufficient_data`로 표시하고 metric을 만들지 않는다. 이는 약점이 아니라 연구윤리와 심사 방어를 위한 설계다. 본선에서는 live ChEMBL evidence-grade mode를 통해 validation rows를 늘리고, model card와 `outputs/evaluation_metrics_egfr.json`에 결과를 남기는 방향으로 확장한다.

## 10. 우리가 주장하지 않는 것

Target-SAFE는 다음을 주장하지 않는다.

- AI가 실제 신약을 발명했다.
- 생성 후보가 임상적으로 유효하다.
- QSAR 예측이 실험값을 대체한다.
- known drug 부작용이 후보 분자에 그대로 적용된다.
- computed conformer가 validated binding pose이다.

Target-SAFE는 “초기 리드 후보 검토를 근거 기반으로 좁히고, 왜 그런 판정이 나왔는지 연구자가 추적할 수 있게 한다”는 현실적인 기여에 집중한다.
