+# Scenario·Signpost event 문맥 및 signpost 품질 개선

## 목적

시나리오 서술과 signpost 생성에서 이벤트의 조건·시간축·인과 경계를 더 정확히 반영하고,
시나리오별 signpost를 3~6개로 제한하며, 같은 시나리오 안의 유사한 관측 신호 생성을 줄인다.

## 원인 분석

- Observability Filter는 scenario 하나만 보고 후보를 생성하며, label의 완전 중복만 스키마에서 막는다.
  따라서 같은 사실을 표현만 바꾼 후보나 관측 대상·판정 기준·시간축이 겹치는 후보가 함께 생성될 수 있다.
- 후보 수 최소값(3개)을 충족하려는 과정에서, scenario와 직접 연결되는 신호가 적으면 일반적인 시장 신호나
  유사한 사건 단계를 여러 표현으로 생성할 수 있다.
- Enrich Stage는 Stage 2에서 확정된 label에 strength·rationale·keyword hints를 부여할 뿐 label을 교체하거나
  의미 중복을 판정하지 않는다. Stage 2의 유사성이 그대로 저장 결과에 남는다.
- 기존 event 문맥은 title, one-line summary, 첫 key bullet 160자뿐이다. 인허가 조건, 상업화 시점,
  직접 영향의 한계, 별도 시장 배경처럼 signpost를 구분하는 사실이 뒤의 key bullet이나 detail_analysis에 있으면
  후보가 일반론으로 수렴할 수 있다.
- 이번 범위에서는 추가 LLM 호출·임베딩 모델을 넣지 않으므로, 동의어 수준의 의미 중복을 코드로 완전히 제거하지는 않는다.
  대신 event 문맥 보강과 후보 차별성 프롬프트로 발생 빈도를 낮춘다.

## 고객에게 달라지는 점

- 생성된 시나리오는 단순히 이벤트 제목을 반복하지 않고, 실제 이벤트에 포함된 조건과 시간 순서를 더 반영한다.
  예를 들어 조건부 투자결정 사건이라면 인허가 진행, 최종 투자결정, 상업화 일정처럼 다음에 확인할 단계가
  시나리오 서술에 드러난다.
- Signpost는 같은 내용을 말만 바꿔 여러 개 나열하는 경우가 줄어든다. 사용자는 각 signpost에서 서로 다른
  관측 대상, 확인할 사실, 또는 진행 단계를 확인하게 된다.
- 이벤트와 직접 관계없는 일반 시장 뉴스는 signpost로 덜 선택된다. 이벤트의 직접 영향과 동시점 시장 배경이
  구분되어, 무엇을 실제로 추적해야 하는지 더 명확해진다.
- 각 scenario에는 항상 3~6개의 signpost만 제공된다. 너무 많아 검토가 어려운 결과는 6개로 제한하고,
  의미 있는 신호를 충분히 만들지 못한 경우에는 불완전한 결과를 저장하지 않는다.
- 처리 흐름은 추가 외부 조회나 LLM 호출을 늘리지 않는다. 기존 event 정보 중 이미 저장된 핵심 사실을 더 잘
  활용하므로, 품질을 높이면서 응답 시간에 미치는 영향은 작다.

## 변경

- `driver`의 첫 key bullet 160자 정책은 유지한다.
- `C1BaseEvent`에 `occurred_at`, `key_facts`, `tags`를 추가한다.
  - `key_facts`: 비어 있지 않은 `key_bullets` 최대 5개, 항목별 280자.
  - bullet이 3개 미만이거나 총 300자 미만이면 `detail_analysis` 앞 600자를 fallback fact로 보강한다.
  - tags는 최대 8개로 제한한다.
- Scenario Stage 2·3·4·6 프롬프트에 compact event context를 추가한다. Stage 2·metadata의 기존
  `detail_analysis` 발췌 길이는 늘리지 않는다.
- Signpost Stage 2와 Stage 4+5에 같은 compact event context를 전달한다.
- Signpost 후보 프롬프트에 동일 scenario 내 관측 대상·판정 사실·시간축/단계 분산, 표현만 다른
  동일 사건 중복 금지, 시나리오 고유성 우선 정렬을 명시한다.
- 후보가 7개 이상이면 앞의 6개만 사용하고, 3개 미만·조립 결과 길이 불일치는 저장 전에 실패 처리한다.

## 검증

- compact context의 normal/fallback 정규화 단위 테스트
- scenario/signpost 프롬프트 문맥 및 차별성 계약 테스트
- signpost 2·3·6·7개 결과의 재시도·절단·조립 차단 테스트
- 관련 자동 테스트와 ruff 검사
