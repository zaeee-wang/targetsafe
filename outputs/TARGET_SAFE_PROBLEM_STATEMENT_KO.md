# Target-SAFE 문제 정의와 최종 기여

## 1. 우리가 해결하려는 본질적 문제

Target-SAFE가 해결하려는 문제는 "AI가 신약 후보를 멋지게 생성하는 것"이 아니다. 실제 목표는 초기 리드 후보 검토 단계에서 연구자가 다음 질문에 빠르게 답하도록 돕는 것이다.

- 이 후보 분자는 구조적으로 유효한가?
- 기본적인 약물유사성, 합성가능성, 구조적 경고 측면에서 즉시 제외해야 할 문제가 있는가?
- EGFR 활성 예측은 모델 적용영역 안에서 나온 값인가?
- 예측값은 평균값만이 아니라 보수적 하한과 불확실성까지 보았을 때도 검토할 만한가?
- 알려진 EGFR 저해제와 얼마나 유사하며, 알려진 약물의 부작용과 label risk는 어떤 검토 항목을 시사하는가?
- 최종적으로 Go, Hold, No-Go 중 어떤 판단이 합리적이며, 그 판단의 근거는 추적 가능한가?

즉 Target-SAFE는 "AI가 약을 발명했다"가 아니라 "AI가 초기 후보 검토를 근거 기반으로 좁히고, 왜 그렇게 판단했는지 연구자가 확인할 수 있게 한다"를 목표로 한다.

## 2. 기존 접근에서 인식한 문제

초기 기획은 RDKit, ChEMBL, PubChem, openFDA, LLM을 조합한 lead triage agent였다. 방향 자체는 대회 주제와 맞지만, 냉정하게 보면 다음 한계가 있었다.

- 너무 rule-based처럼 보일 위험이 있었다.
- 어떤 수치와 threshold가 왜 쓰였는지 설명이 부족하면 임의 가중치 시스템처럼 보일 수 있었다.
- 블랙박스 QSAR 예측만 제시하면 심사위원이 "왜 이 후보가 Hold인가"를 추적하기 어렵다.
- 후보 분자와 알려진 약물의 관계, 알려진 부작용 정보가 사용자에게 충분히 보이지 않았다.
- UI가 한 페이지에 모든 내용을 담아 처음 쓰는 사람이 실행 순서와 해석 방법을 파악하기 어려웠다.
- computed conformer가 실제 binding pose처럼 오해될 수 있는 위험이 있었다.

따라서 Target-SAFE는 단순 점수표가 아니라 evidence graph, model card, threshold registry, known drug context, candidate twin을 함께 보여주는 구조로 재설계되었다.

## 3. 최종 해결 방향

Target-SAFE는 EGFR 변이 양성 NSCLC를 파일럿으로 하는 Evidence-Gated Lead Triage Agent이다.

핵심 구조는 다음과 같다.

- RDKit 또는 fallback evaluator로 분자 유효성, descriptor, QED, Lipinski, PAINS/Brenk 계열 alert, SA score를 계산한다.
- ChEMBL 기반 reference activity와 analog similarity를 이용해 EGFR activity를 보수적으로 추정한다.
- prediction interval과 applicability domain을 함께 제시한다.
- threshold registry에 모든 기준값의 출처와 rationale을 연결한다.
- evidence graph가 candidate, descriptor, prediction, threshold, known analog, risk, decision을 연결한다.
- Critic Agent가 invalid SMILES, severe alert, out-of-domain overclaim, API fallback, 근거 부족을 검토한다.
- UI는 Run Console, Molecule Atlas, Candidate Twin, Evidence Graph, Known Drugs & Risks, Reports로 분리한다.
- EGFR은 점수화가 가능한 파일럿 타깃으로 유지하고, 다른 타깃은 public drug atlas와 target expansion lane으로 분리해 과장된 범용성을 주장하지 않는다.

## 4. Known drug와 부작용 정보를 쓰는 방식

알려진 EGFR TKI의 부작용 정보는 후보 분자의 독성을 확정하는 근거로 쓰지 않는다. 이는 매우 중요하다.

Target-SAFE에서 Gefitinib, Erlotinib, Afatinib, Osimertinib, Dacomitinib, Mobocertinib 같은 reference drug는 다음 용도로 사용된다.

- 후보와 알려진 EGFR 약물의 구조적 유사성을 보여준다.
- 알려진 약물의 label-level adverse reaction과 warning을 후속 검토 체크리스트로 제시한다.
- 후보가 특정 약물과 유사하더라도 "동일한 부작용이 발생한다"고 말하지 않는다.
- UI에는 항상 "reference context, not candidate-specific toxicity"를 표시한다.

이 설계는 과장된 AI 주장과 안전성 오해를 피하기 위한 연구 윤리 장치이다.

## 5. Digital Twin UI의 의미

Target-SAFE의 digital twin은 가짜 실험 시뮬레이션이 아니다.

여기서 molecular digital twin은 후보 하나에 대해 현재 확보된 계산값, 예측, 불확실성, 알려진 약물과의 관계, 구조적 risk, evidence graph, 의사결정 사유, 다음 검증 항목을 한 화면에서 연결해 보여주는 연구 상태판이다.

후보 상세 화면은 다음 질문에 답해야 한다.

- 이 분자는 무엇인가?
- 2D 구조와 computed 3D conformer는 어떻게 보이는가?
- 3D conformer는 실제 결합 포즈가 아니라는 점이 명확한가?
- Go/Hold/No-Go 판단의 핵심 이유는 무엇인가?
- 어떤 기준은 통과했고, 어떤 기준은 review 또는 block인가?
- 가장 가까운 known drug는 무엇이며, 그 약물의 알려진 risk는 어떤 follow-up을 요구하는가?
- 다음 검증은 무엇인가?

## 6. 대회 관점에서의 기여

Target-SAFE의 기여는 다음과 같이 정리된다.

- 신약개발 전주기 중 "초기 리드 후보 검토"라는 구체적 병목을 잡았다.
- 생성형 AI의 과장된 novelty보다, 실제 연구자가 쓸 수 있는 근거 기반 triage를 목표로 했다.
- 모든 판단을 descriptor, QSAR 적용영역, threshold source, evidence graph, critic finding에 연결했다.
- GPU와 LLM이 없어도 동작하고, 있을 때는 embedding, uncertainty, graph-grounded report 품질 향상에 사용하도록 분리했다.
- UI를 단일 landing page가 아니라 실행 가능한 research app으로 구성했다.
- known drug adverse effect를 candidate toxicity처럼 오해하지 않도록 별도 evidence layer로 분리했다.
- RDKit이 없는 환경에서도 더 나은 2D bond-line fallback을 제공하고, computed conformer를 PyMOL/Avogadro에서 열 수 있는 XYZ 파일로 내보낼 수 있게 했다.
- Evidence graph는 전체 노드를 한꺼번에 보여주지 않고, 기본적으로 선택 후보 주변 근거를 보여주어 라벨 겹침과 해석 불가능성을 줄였다.

## 7. 왜 EGFR 파일럿인가

현재 Go/Hold/No-Go 점수화는 EGFR 변이 양성 NSCLC 파일럿에 맞춰져 있다. 그 이유는 타깃마다 assay endpoint, 활성 기준, 구조적 risk, applicability domain, known drug context가 달라지기 때문이다.

따라서 Target-SAFE는 다음처럼 범위를 나눈다.

- EGFR: 현재 scoring pilot. QSAR interval, applicability domain, known EGFR TKI context, evidence graph decision을 제공한다.
- ALK, BRAF, KRAS, HER2 등: public drug atlas와 UI lane은 제공하지만, EGFR QSAR를 그대로 재사용하지 않는다.
- 다른 타깃으로 확장하려면 해당 타깃의 ChEMBL assay set, known inhibitor library, threshold registry, model card를 별도로 구축해야 한다.

이 제한을 드러내는 것은 약점이 아니라 연구 윤리와 과학적 타당성을 위한 장치이다. "아무 타깃이나 점수화한다"는 주장은 심사에서 오히려 위험하다.

## 8. 우리가 주장하지 않는 것

Target-SAFE는 다음을 주장하지 않는다.

- AI가 실제 신약을 발명했다.
- 생성 후보가 임상적으로 유효하다.
- QSAR 예측이 실험값을 대체한다.
- known drug 부작용이 후보 분자에 그대로 적용된다.
- computed conformer가 validated binding pose이다.

Target-SAFE의 정확한 주장은 다음이다.

> Target-SAFE는 초기 EGFR 리드 후보를 구조, 예측, 불확실성, 적용영역, 알려진 약물 context, threshold source, evidence graph를 기반으로 Go/Hold/No-Go로 좁히는 투명한 의사결정 지원 agent이다.
