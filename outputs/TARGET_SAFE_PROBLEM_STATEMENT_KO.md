# Target-SAFE 문제정의 및 최종 목표

## 1. 한 문장 문제정의

Target-SAFE가 궁극적으로 해결하려는 문제는 **초기 리드 후보 검토 단계에서 AI가 생성하거나 제안한 분자를 연구자가 믿고 선별하기 어렵다는 문제**이다.

신약개발 현장에서는 후보 분자가 많아질수록 어떤 후보를 먼저 검증해야 하는지, 어떤 후보는 보류해야 하는지, 어떤 후보는 초기에 제외해야 하는지를 빠르게 판단해야 한다. 하지만 기존의 단순 생성형 AI 또는 점수 기반 랭킹은 “왜 이 후보가 좋은가”, “어떤 근거가 부족한가”, “모델이 어느 정도 확신하는가”, “어떤 추가 실험이 필요한가”를 충분히 설명하지 못한다.

## 2. 기존 접근에서 인식한 문제

기존 아이디어는 자율형 분자 생성과 최적화에 가까웠다. 이 방향은 대회 주제와 맞지만, 냉정하게 보면 다음 한계가 있었다.

- 다른 참가팀도 쉽게 떠올릴 수 있는 `LLM + RDKit + ChEMBL + ADMET + 리포트` 조합처럼 보일 수 있다.
- 새로 생성된 후보 분자에 대해 실제 실험 근거 없이 효능, 안전성, 임상 가능성을 과장할 위험이 있다.
- 고정 가중치 점수로 후보를 정렬하면, 특정 계수와 임계값이 왜 타당한지 설명하기 어렵다.
- 블랙박스 모델을 쓰면 최종 판정이 왜 나왔는지 심사위원과 연구자가 추적하기 어렵다.
- UI가 단순 표 중심이면, agentic AI가 어떤 근거를 모으고 어떤 판단 과정을 거쳤는지 직관적으로 전달하기 어렵다.

따라서 Target-SAFE는 “AI가 신약을 발명한다”는 방향이 아니라, **AI가 초기 리드 후보 검토를 근거와 불확실성 중심으로 투명하게 좁힌다**는 방향으로 재정의되었다.

## 3. 우리가 실제로 해결하려는 현장 문제

초기 리드 최적화 과정의 병목은 단순히 후보가 부족한 것이 아니다. 오히려 후보가 많을 때 다음 질문에 빠르게 답하기 어렵다는 것이 핵심 문제다.

- 이 후보는 구조적으로 유효한가?
- 약물유사성, 독성 경고, 합성 접근성 측면에서 초기에 제외해야 할 위험이 있는가?
- 타깃 활성 예측은 모델 적용영역 안에서 나온 것인가?
- 알려진 EGFR 저해제 또는 공개 assay evidence와 얼마나 연결되는가?
- 예측값의 평균이 아니라 보수적 하한값으로도 우선 검토할 만한가?
- 외부 API나 LLM이 실패했을 때도 판단 근거를 재현할 수 있는가?
- 최종 판정이 `Go`, `Hold`, `No-Go` 중 무엇이며, 그 이유와 다음 검증 단계는 무엇인가?

Target-SAFE는 이 질문들을 하나의 candidate digital twin 화면과 리포트로 묶어 보여주는 것을 목표로 한다.

## 4. Target-SAFE의 해결 방향

Target-SAFE는 후보 분자 생성 자체보다 **근거 기반 triage**를 핵심 가치로 둔다.

시스템은 사용자가 입력한 disease, target, seed SMILES, optimization goal을 바탕으로 후보를 생성하고, 각 후보에 대해 다음 정보를 계산하거나 수집한다.

- 분자 구조 유효성
- RDKit 또는 fallback descriptor
- QED, MW, LogP, TPSA, Lipinski violation, structural alert, SA score
- EGFR reference analog와의 유사도
- analog-supported QSAR 예측값과 prediction interval
- applicability domain 여부
- ChEMBL, ClinicalTrials.gov, openFDA 기반 class-level evidence
- 근거 기반 threshold 통과 여부
- Critic Agent의 downgrade 또는 보류 사유
- 다음 검증 단계

최종적으로 각 후보는 `Go`, `Hold`, `No-Go`로 분류된다.

## 5. Go/Hold/No-Go의 의미

`Go`는 “이 후보가 신약이라는 뜻”이 아니다. Target-SAFE에서 `Go`는 다음 의미다.

- 현재 계산값과 공개 근거 기준으로 초기 후속 검토 우선순위가 높다.
- 구조적 hard blocker가 없다.
- 모델 적용영역 안에서 보수적 예측 하한이 기준을 넘는다.
- evidence graph가 충분한 supporting evidence를 가진다.
- Critic Agent가 blocking issue를 발견하지 않았다.

`Hold`는 Target-SAFE에서 매우 중요한 판정이다.

- 가능성은 있지만 근거가 부족하다.
- 모델 불확실성이 크다.
- API fallback을 사용했다.
- applicability domain 밖이다.
- 구조 경고 또는 class-level risk 검토가 필요하다.

`No-Go`는 초기에 제외하거나 재설계해야 할 후보를 의미한다.

- invalid SMILES
- severe structural alert
- 극단적 descriptor risk
- 매우 낮은 QED
- 높은 합성 접근성 위험
- 적용영역 밖 후보에 대한 과도한 활성 주장

## 6. 왜 Digital Twin UI인가

Target-SAFE의 digital twin은 실제 실험 결과를 가장하는 가상 실험실이 아니다.

여기서 digital twin은 **후보 분자 하나의 현재 검토 상태를 구조, 계산값, 예측 불확실성, 외부 evidence, 판정 근거, 다음 검증 항목으로 통합한 연구용 상태판**을 뜻한다.

심사위원 또는 연구자는 후보를 클릭하면 다음을 한 화면에서 확인할 수 있다.

- 이 분자는 무엇인가?
- 어떤 구조와 descriptor를 가지는가?
- EGFR 활성 예측은 어느 정도이며 불확실성은 얼마인가?
- 알려진 analog와 얼마나 가까운가?
- 어떤 evidence가 판정을 지지하거나 약화하는가?
- 왜 `Go`, `Hold`, `No-Go`가 되었는가?
- 다음에 어떤 실험 또는 검증이 필요한가?

이 UI는 단순한 시각화가 아니라, agentic AI의 사고 과정과 도구 사용 결과를 심사위원이 빠르게 검증할 수 있게 하는 설명 장치다.

## 7. 대회 관점에서의 공여

Target-SAFE의 공여는 다음과 같다.

- 신약개발 문제를 “분자 생성”이 아니라 “근거 기반 리드 후보 선별”로 구체화했다.
- LLM 단독 판단이 아니라 RDKit, 공개 DB, QSAR, threshold registry, evidence graph를 결합했다.
- 모든 임계값과 판정 기준에 source와 rationale을 연결했다.
- 블랙박스 예측값을 그대로 믿지 않고 applicability domain과 prediction interval을 함께 제시한다.
- GPU와 API는 optional enhancer로 두어, 자원이 없어도 핵심 데모가 작동한다.
- React 기반 molecular evidence twin UI로 실제 연구자가 후보를 검토하는 흐름을 시각적으로 전달한다.
- 최종 리포트와 JSON 산출물로 재현성과 투명성을 남긴다.

## 8. 우리가 주장하지 않는 것

Target-SAFE는 다음을 주장하지 않는다.

- AI가 실제 신약을 발명했다.
- 생성 후보가 실제 효능을 가진다.
- 예측값이 실험값을 대체한다.
- class-level clinical/regulatory evidence가 후보별 안전성을 증명한다.
- computed conformer가 validated binding pose다.

Target-SAFE는 어디까지나 **초기 후보 검토를 더 빠르고, 더 투명하고, 더 재현 가능하게 만드는 decision-support system**이다.

## 9. 최종 메시지

Target-SAFE의 최종 메시지는 다음과 같다.

> AI 신약개발에서 중요한 것은 그럴듯한 후보를 많이 만드는 것만이 아니다. 연구자가 왜 그 후보를 믿거나 보류하거나 제외해야 하는지 추적할 수 있어야 한다. Target-SAFE는 후보 분자를 근거, 불확실성, 적용영역, 안전성 경고, 다음 검증 단계와 함께 보여주는 evidence-gated lead triage agent다.

