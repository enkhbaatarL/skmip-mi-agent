# Expanded Event Cohort Proposal Campaign

## 사용 시점

기존 Scenario Group 수를 늘리는 것뿐 아니라 **baseline과 다른 Event cohort부터 확장**하라는 요청에 사용한다.
동일 Event를 다시 생성하는 `same_logical_inputs/add-only`와 구분하며, campaign ID와 보고서에도
`expanded_event_cohort/add-only`를 기록한다.

## 1. 쓰기 전 cohort manifest

Scenario create 전에 baseline campaign의 Event ID를 exclusion set으로 고정하고 다음을 manifest에 저장한다.

- baseline campaign과 ordered Event ID
- 정확히 20개의 고유 expanded Event ID, cohort order, Event Type과 제목
- 선택 규칙과 각 Event의 `scenarioSuggestYn`, prior Group 상태
- 두 Event 집합의 disjoint 판정
- Scenario Lever catalog version/full checksum과 후속 Proposal Flow release
- `add-only-preserve-existing` 및 Signpost 실행/생략 정책

추천 Event를 먼저 사용하고, 부족하면 완료 Group 이력이 있어 상세 payload 품질과 create 가능성이 검증된 Event를
사용한다. active·미완료 Group만 연결된 Event는 exact-set conflict를 피하기 위해 제외한다. Event Type 다양성을
최대화하되 Type parity를 맞추기 위해 품질 기준 미달 Event를 억지로 넣지 않는다.

## 2. Group 생성과 품질 gate

- expanded Event마다 Scenario API v4 Group 하나를 만든다.
- 기존 Group/Scenario는 수정·soft delete·hard delete하지 않는다.
- timeout, 결과 불명, active operation conflict는 자동 재시도하거나 삭제로 우회하지 않는다.
- Validation과 direct Confirmation까지 수행한다. Proposal 입력에 불필요한 Signpost는 이유를 남기고 생략할 수 있다.
- Group마다 API version, generation strategy, catalog pin, completed stage, `parameterMappingReady`, Dimension 3~6개,
  Scenario 3개 이상, baseline 정확히 1개, floor/ceiling, cell 조합 고유성을 검사한다.

campaign hard gate는 다음과 같다.

1. 완료 Group 20개와 고유 Group ID 20개
2. expanded Event ID 20개 고유성
3. baseline/expanded Event ID 완전 비중복
4. baseline/new Group ID 완전 비중복
5. 기존 Group 삭제 0과 실제 Group 순증 20
6. Scenario Lever version/full checksum 일치

동일 Event로 앞서 생성한 오범위 Group이나 Proposal은 삭제하지 않고 audit evidence로 보존한다. 단, 아래 preflight,
대표 선정, Proposal 실행, 최종 fixture에는 넣지 않는다.

## 3. 대표 3개 선정과 Proposal

완료된 신규 Group의 모든 Scenario를 먼저 `run_proposal_only.py` read-only 모드로 preflight한다. 그 결과와 campaign
summary를 `evaluate_representative_trios.py select`에 주고 Group마다 정확히 3개를 고정한다.

선정 우선순위는 다음과 같다.

1. proposal-eligible 및 uncovered guard 통과
2. baseline·floor·ceiling 대표성
3. runtime canonical Parameter type set 동일성·Jaccard overlap
4. pressure와 Scenario cell 다양성

선정된 Scenario만 proposal-only로 각 1회 실행한다. confirmation/callback/outer retry를 호출하지 않으며 Object
Storage 접근 불가 시 사용자가 허용한 `configured_fallback` 정책과 workbook identity를 evidence에 남긴다.

## 4. 평가와 재사용 fixture

기존 KPI와 함께 다음을 표로 보고한다.

- Proposal coverage와 preflight→Proposal 전환율
- structured semantic abstention 및 기타 실패 원인
- abstention stage/reason funnel과 종료 단계까지의 trace 완전성
- Group별 triple success
- triple-success Group의 Parameter type consistency
- type-consistent Group의 value signature differentiation
- exact common slot differentiation
- identity/integrity, 실패 무저장 원자성, retry/token, 성공/전체 시도 latency

semantic abstention은 `ABSTAINED` attempt와 campaign `REVIEW`로 기록한다. Step1.5/2/3의 reason/stage, candidate/slot/
value sanitizer 요약, LLM call/token/retry가 없으면 관측성 `REVIEW`를 추가한다. full prompt/messages/context는 저장하지
않는다.

최종 DB read-back으로 PROPOSED/Callback SKIPPED와 uncovered/coverage-limit의 건수뿐 아니라 Scenario ID 집합과
Scenario→Group identity를 exact 대조한다. 최종 평가 set을 재사용할 때는 `tests/fixtures/model_parameter_agent/`에
expanded cohort의 Group/Scenario/role/cell/release contract를 고정하고, 현재 LLM 결과와 KPI는
`observed_baseline`으로 분리한다. 최초 fixture 생성 뒤 재평가는 `--testset-input`으로 SHA-256 및 ordered
Group/Event/Scenario identity를 검증하며 fixture를 다시 쓰지 않는다.

코드 수정 후 동일 Scenario의 post-fix 실행을 합칠 때는 `--post-fix-execution-evidence`와
`--post-fix-reason`을 사용한다. baseline attempt를 묵시적으로 덮지 않고 superseded source/status/stage를 audit으로
남긴다. baseline/final attempt Scenario ID 집합 동일성을 hard gate로 검증하고 성공·semantic abstention·기타 실패·
structured/complete trace의 전후 값과 증감을 표로 남긴다. 최종 Markdown은 그룹 표, KPI 표, 개선 전후 비교 표의
컬럼 의미를 고정 섹션으로 포함하며 triple-success가 아닌 비교 지표는 `N/A`로 표시한다.
Object Storage 장애 fallback을 요구한 실행은 `--require-mi-base-fallback-mode configured_fallback`으로 runner를
fail-fast시키고 평가 시 `--expected-mi-base-fallback-mode configured_fallback`으로 모든 baseline/post-fix 증적의
실제 정책을 다시 hard gate한다.
