# create scenario / create signpost 실행 시간 단축 검토

## 요약

`create scenario`와 `create signpost`의 실행 시간은 대부분 LLM 호출 횟수, structured output 재시도, 불필요하게 큰 LLM output에서 발생한다. 특히 `create scenario`는 Stage 3 value reduction이 dimension별 순차 호출이었고, Stage 5 quick validate compatibility가 통과/실패 전체 scenario를 모두 output으로 받는 구조였다. `create signpost`는 scenario별 병렬 실행은 되어 있지만, 각 scenario 내부에서 Stage 2/4/5가 순차로 3회 호출되던 구조였다.

이번 개선은 `create scenario`와 `create signpost` 모두에 적용한다.

- `reduce_values`: 선택 dimension 전체를 한 번의 batch LLM 호출로 받도록 변경
- `quick_validate`: compatibility judge가 incompatible 항목만 반환하도록 prompt/schema 변경
- `quick_validate retry`: 기본값 2회에서 1회로 축소
- `quick_validate feedback`: Stage 4 재생성 입력에 feedback, previous output, compatibility repair를 전달하는 경로 유지/강화
- `create signpost Stage 2`: 통과 후보만 output으로 받고 `passes_filter=false` 항목 제거
- `create signpost Stage 4+5`: strength/rationale/keyword_hints를 한 번의 LLM 호출로 통합
- `create signpost 병렬화`: scenario별 subgraph를 제한 병렬 실행하고, 각 scenario 내부는 Stage 2 → Stage 4+5 순서를 유지한다.
- `create signpost 부분 성공`: 성공 scenario의 signpost는 저장하고 실패 scenario는 기록하되 group stage는 진행하지 않는다.
- `create scenario 후반`: Stage 6 validation과 scenario group metadata 생성을 병렬화해 품질 변화 없이 wall-clock을 줄인다.

## 오래 걸리는 원인

| 영역 | 현재 병목 | 영향 | 개선내용 |
| --- | --- | --- | --- |
| create scenario Stage 3 | 선택 dimension 3~5개마다 LLM을 순차 호출 | scenario 생성마다 고정 LLM 호출 3~5회 발생 | `Stage3BatchStructuredOutput`으로 선택 dimension 전체를 1회 batch 호출. 누락/invalid dimension만 `_stage3_fallback()` |
| create scenario Stage 5 | compatibility judge가 모든 scenario의 compatible true/false를 반환 | 통과 항목까지 output token을 소비하고 parsing/검증 비용 증가 | quick validate 전용 prompt/schema로 incompatible 항목만 반환(`items=[]` 허용). `validate_scenarios`는 기존 full-output 유지 |
| quick validate retry | 기본 최대 retry가 2회 | Stage 4 narrative 생성 + Stage 5 compatibility가 반복되어 지연 증폭 | `REF_QUICK_VALIDATE_MAX_RETRIES` 기본값 2→1. 재생성 1회 후 실패 시 Stage 6 진행 |
| quick validate feedback | compatibility repair는 구조화되어 있으나 baseline/duplicate는 문자열 feedback 의존 | Stage 4가 피드백을 약하게 반영하면 같은 실패가 반복될 수 있음 | Stage 4에 `validation_feedback` / `validation_repairs` / `previous_stage4` 전달 경로 유지·강화. baseline/duplicate 구조화는 추가 후보 |
| create signpost | scenario별 병렬 처리 안에서 Stage 2/4/5 LLM을 순차 호출 | scenario 6개 기준 최대 18회 LLM 호출. semaphore가 낮거나 retry가 걸리면 전체 시간이 길어짐 | Stage 4+5 통합으로 scenario별 3회 → 2회 호출. scenario 간에는 semaphore 제한 병렬 실행 |
| create signpost Stage 2 | 후보 5~10개를 모두 output으로 받고 `passes_filter=true`만 코드에서 추출 | 탈락 후보의 label/reason까지 output token으로 소비 | 통과 후보(label 3~6개 + 사유)만 반환. 후보 수 범위 코드 검증 추가 |
| create signpost 전체 batch | prompt/output이 커지고 단일 요청 tail latency와 gateway timeout 위험 증가 | 2026-07-13 실측에서 평균 260,320ms, 최대 431,789ms | 전체 batch를 제거하고 scenario별 제한 병렬 실행으로 복원 |
| create scenario 후반 | Stage 6 validation 후 metadata 생성을 순차 실행 | 서로 독립적인 LLM 호출의 대기 시간이 합산됨 | `stage6_validate`와 metadata 생성을 `asyncio.gather()`로 병렬화. wall-clock만 단축 |
| 공통 retry | `_ainvoke_with_retry` 기본 `REF_MAX_RETRIES=5` + connector `max_retries=2` | schema validation 실패가 있으면 단일 stage도 길게 대기 | 미적용. batch 전용 retry 상한(2~3) 하향은 측정 후 검토 후보 |

## 적용한 개선

### 1. Stage 3 reduce_values batch 호출

기존에는 `stage3_reduce_values()`가 선택된 dimension마다 `Stage3StructuredOutput`을 별도 요청했다. 선택 dimension이 5개면 Stage 3만 LLM 5회다.

개선 후에는 `Stage3BatchStructuredOutput`을 추가해 모든 선택 dimension의 `selected_enum`을 한 번에 받는다. LLM이 실패하거나 일부 dimension이 누락되면 기존 `_stage3_fallback()`으로 해당 dimension만 보정한다.

예상 효과:

- create scenario 1건당 LLM 호출 2~4회 감소
- dimension별 retry 대기 누적 제거
- Stage 3 prompt 중복 token 감소

### 2. quick_validate compatibility output 축소

기존 compatibility judge는 모든 scenario에 대해 `compatible=true/false`를 반환해야 했다. 대부분 정상인 경우에도 정상 항목 전체가 output token을 차지했다.

개선 후 create scenario의 quick validate 전용 prompt/schema는 `items`에 incompatible scenario만 반환하도록 지시한다. 모든 scenario가 정상이면 `items=[]`다.

`validate_scenarios` flow는 별도 `COMPAT_SYSTEM_PROMPT`와 `CompatibilityStructuredOutput`을 계속 사용한다. 이 경로는 모든 scenario에 대해 `compatible=true/false`를 받으므로 사용자 검토 API의 설명 품질과 기존 contract가 quick validate 최적화에 영향을 받지 않는다.

예상 효과:

- 정상 케이스 output token 대폭 감소
- quick validate parsing/검증 단순화
- 재생성해야 하는 항목만 Stage 4 repair 후보로 전달

### 3. quick_validate retry 기본값 축소

`REF_QUICK_VALIDATE_MAX_RETRIES` 기본값을 `2`에서 `1`로 낮춘다. 현재 라우팅은 실패 시 `quick_validate_retry_count`를 증가시킨 뒤, count가 max를 초과하면 Stage 6으로 진행한다. 따라서 max=1이면 “실패 후 Stage 4 재생성 1회, 다시 실패하면 진행”이 된다.

예상 효과:

- quick validate 실패 케이스에서 Stage 4/5 반복 비용 상한 감소
- feedback이 약하게 반영되어 같은 실패가 반복되는 상황 완화

### 4. quick_validate feedback 반영 경로

Stage 5 실패 시 Stage 4에는 다음 입력이 전달된다.

- `validation_feedback`: 실패 유형과 재생성 지시 문자열
- `validation_repairs`: compatibility judge가 제안한 enum 내 권장 변경
- `previous_stage4`: 직전 scenario title/description/dimension 조합

Stage 4는 repair가 있으면 이전 scenario 조합을 기준으로 권장 값을 우선 적용하고, narrative를 새 조합에 맞춰 다시 생성한다. baseline/duplicate 실패는 현재 문자열 feedback과 deterministic combo selection 점수에 반영된다.

추가 개선 후보:

- baseline/duplicate도 `Stage5RepairInstruction`으로 구조화해 특정 scenario/dim/value를 직접 override
- repair 적용 후 compatibility rule을 다시 돌려 invalid 조합이면 즉시 대체 조합 선택
- 같은 feedback으로 2회 이상 실패한 event type/template 조합을 trace에서 수집해 prompt를 조정

## create signpost 적용한 개선

기존 `create_signposts`는 scenario 단위로 `asyncio.gather()`와 `create_signposts_max_concurrent_scenarios` semaphore를 사용했다. 기존에는 각 scenario 내부에서 다음 3회 LLM 호출이 순차 실행됐다.

1. Stage 2 Observability Filter: 후보 생성 및 통과 여부 판정
2. Stage 4 Direction & Strength Assignment
3. Stage 5 Keyword Hint Mint

개선 후:

| 항목 | 변경 | 효과 |
| --- | --- | --- |
| Stage 2 output 축소 | 탈락 후보까지 받지 않고 통과 label 3~6개와 통과 사유만 반환 | output token 감소 |
| Stage 2 코드 검증 | 반환 후보 수가 `REF_SIGNPOSTS_PER_SCENARIO_MIN/MAX` 범위인지 검증 | LLM이 임의로 10개를 주는 상황 차단 |
| Stage 4+5 통합 | label별 `strength`, `rationale_ko`, `keyword_hints`를 한 structured output으로 반환 | scenario별 LLM 호출 3회 → 2회 |
| Scenario 제한 병렬 처리 | 대상 scenario마다 기존 subgraph를 실행하고 semaphore로 동시 실행 수 제한 | 큰 batch 응답의 tail latency와 timeout 위험 감소 |

추가 적용:

- partial success: scenario별 실행 결과를 `asyncio.gather(..., return_exceptions=True)`로 병합한다.
- 성공 scenario의 signpost는 저장하고, 실패 scenario가 있으면 group stage를 변경하지 않은 채 failure callback을 보낸다.
- 재요청 시 기존 signpost가 없는 scenario만 다시 처리하므로 성공 scenario를 중복 생성하지 않는다.

남은 추가 개선 후보:

- concurrency 계측: `create_signposts_max_concurrent_scenarios`를 7 기준으로 운영하고 rate limit·p95를 본 뒤 조정한다.
- retry 상한 조정: scenario별 호출도 retry가 겹치면 tail latency가 증가하므로 trace를 기준으로 전용 상한을 검토한다.

품질 유지를 위해 지금은 제외하는 후보:

- Stage 2 scenario prompt의 `price_direction` 제거는 보류한다. 가격 방향은 JKM/TTF/HH 관련 관측 신호를 만들 때 품질에 도움이 될 수 있으므로, token 절감만을 이유로 제거하지 않는다.
- Stage 2 `filter_reason` 제거는 보류한다. downstream 저장에는 쓰지 않지만, 초기 운영 trace에서 후보 품질을 진단하는 데 유용할 수 있다. 충분히 안정화된 뒤 labels-only output으로 줄일지 판단한다.

## 다음 권장 개선

### 1. Scenario별 partial success/retry

batch 호출은 호출 수를 줄이는 대신 prompt/output 크기와 단일 요청 tail latency가 커진다. signpost는 전체 batch 대신 scenario별 제한 병렬 실행을 사용하고, 정상 결과는 보존하며 실패 scenario만 다음 요청에서 재처리한다.

- Scenario Stage 3:
  - `Stage3BatchStructuredOutput`에서 정상 반환된 dimension은 그대로 사용한다.
  - 누락된 dimension, enum 범위 밖 값을 낸 dimension만 small retry 또는 `_stage3_fallback()`을 적용한다.
  - batch 전체를 다시 호출하지 않는다.
- Signpost Stage 2/4+5:
  - scenario별 subgraph 안에서 Stage 2와 Stage 4+5를 순차 실행한다.
  - scenario 간에는 semaphore 제한 병렬 실행한다.
  - 실패 scenario는 signpost를 저장하지 않고 결과에 실패 사유를 남긴다.
- 이렇게 하면 품질 좋은 정상 scenario 결과를 버리지 않고, 전체 batch의 긴 tail latency를 피할 수 있다.

적용 상태:

- Stage 3는 정상 dimension 결과를 보존하고, 누락/invalid enum dimension만 `_stage3_fallback()`으로 보정한다.
- Signpost는 scenario별 실행 결과를 병합해 정상 signpost를 보존한다.
- 후보 수, label 순서, strength quota, keyword_hints 검증 또는 LLM 호출이 최종 실패한 scenario는 실패 처리하고 fallback으로 임의 데이터를 저장하지 않는다.

예상 효과:

- LLM 호출 수 감소 효과는 유지한다.
- batch schema 오류 1건 때문에 정상 dimension/scenario까지 재처리하는 비용을 줄인다.
- 정상 scenario 결과는 보존하고, 실패 scenario만 기존 retry 정책과 다음 요청의 미생성 대상 재처리를 적용한다.

### 2. Compatibility prompt 분리

`quick_validate`와 `validate_scenarios`는 모두 compatibility judge를 쓰지만 목적이 다르다.

- `quick_validate`: create scenario 내부 자동 보정용. 재생성이 필요한 incompatible 항목만 있으면 충분하다.
- `validate_scenarios`: 사용자 편집 테이블 검토용. 사용자에게 설명할 검토 결과와 warning 품질이 중요하다.

따라서 prompt/schema를 분리한다.

- quick validate 전용 prompt:
  - incompatible-only output 유지
  - `recommended_value_b`와 repair 정보 중심
  - output token 최소화
- validate_scenarios 전용 prompt:
  - 사용자 검토 설명 품질 우선
  - 필요하면 full-output 또는 더 자세한 reason을 허용
  - quick validate 최적화가 validation API 품질에 영향을 주지 않도록 격리

예상 효과:

- create scenario의 token 절감 효과는 유지한다.
- validation API의 품질/설명력을 보존한다.
- 한 flow의 prompt 변경이 다른 flow로 전파되는 리스크를 줄인다.

적용 상태:

- quick validate: `QUICK_COMPAT_SYSTEM_PROMPT` + `QuickCompatibilityStructuredOutput`
- validate_scenarios: `COMPAT_SYSTEM_PROMPT` + `CompatibilityStructuredOutput`

### 3. Stage 6 validation과 metadata 병렬화

`create scenario` 후반의 `stage6_validate()`와 `stage_generate_scenario_group_metadata()`는 둘 다 Stage 4 결과를 읽는 독립 LLM 호출이다. 서로의 출력에 의존하지 않으므로 `asyncio.gather()`로 동시에 실행할 수 있다.

예상 효과:

- LLM 호출 수는 그대로다.
- 전체 대기 시간은 `stage6 + metadata` 합산에서 `max(stage6, metadata)`에 가까워진다.
- 생성 품질은 유지한다. 입력과 출력 contract는 바뀌지 않고 실행 순서만 병렬화하기 때문이다.

## 측정 방법

MLflow trace 또는 LLM connector span 기준으로 다음을 기록한다.

- flow별 총 elapsed time
- LLM span count
- stage별 latency p50/p95
- retry 발생 stage와 retry count
- prompt/output token 추정치
- `quick_validate_retry_count`
- `validation_feedback` 유형별 빈도: `baseline_contrast`, `duplicate`, `compatibility`
- signpost scenario별 성공/실패 수와 retry count
- signpost 동시 실행 수와 가장 느린 scenario의 Stage 2/4+5 latency
- Stage 6/metadata 병렬화 전후 create scenario 후반 elapsed time

수동 확인 대상 API:

- `POST /scenario-groups/sync`
- `POST /scenario-groups/{scenarioGroupId}/signposts/sync`

## 남은 리스크

- Stage 3 batch output은 한 번의 응답에 여러 dimension을 담으므로, LLM이 특정 dimension을 누락하면 fallback이 적용된다.
- compatibility prompt/schema를 quick validate와 validation API로 분리해 cross-flow 영향은 줄였다. 운영 trace에서는 quick validate의 `items=[]` 비율과 incompatible feedback 반영률을 확인해야 한다.
- quick validate retry를 1회로 줄이면 일부 event에서 품질 보정 기회가 줄 수 있다. 대신 callback 지연 상한은 낮아진다.
- signpost scenario 병렬 호출은 동시 LLM 요청 수가 늘 수 있다. semaphore 설정과 connector retry가 겹치면 rate limit과 tail latency가 증가할 수 있다.
- Stage 2의 `price_direction`과 `filter_reason`은 품질/디버깅 용도로 유지한다. 토큰 절감만 보고 제거하면 observability 품질 진단력이 떨어질 수 있다.

## 리스크 보완 방안

| 리스크 | 보완 |
| --- | --- |
| Stage 3 batch 일부 dimension 누락 | 정상 dimension은 보존하고 누락/invalid dimension만 small retry 또는 fallback |
| signpost 일부 scenario 누락/검증 실패 | 정상 scenario signpost는 저장하고 group stage는 유지. 다음 요청에서 미생성 scenario만 재처리 |
| quick validate prompt 변경이 validation API에 영향 | quick validate compatibility prompt/schema와 validate_scenarios compatibility prompt/schema 분리 |
| quick validate retry 1회로 품질 보정 기회 감소 | 실패 유형별 보정 우선순위 적용: deterministic 보정 가능 항목은 코드 보정, compatibility repair만 제한적 재시도 |
| signpost 동시 요청 증가 | semaphore 설정을 유지하고 운영 trace의 rate limit·p95에 따라 동시 실행 수 조정 |

## 2026-07-13 재검토 및 최종 결정

전체 scenario를 Stage 2 batch 1회와 Stage 4+5 batch 1회로 처리한 방식은 호출 수는 줄였지만 실제 wall-clock이 크게 증가했다.
batch 응답이 커지면서 단일 호출의 생성 시간이 길어지고 timeout/retry 영향 범위도 전체 scenario로 확대된 것이 주원인으로 판단된다.

최종 적용 구조:

- create scenario의 Stage 3 batch와 Stage 6/metadata 병렬화는 유지한다.
- create signpost의 전체 scenario batch schema/prompt/helper는 제거한다.
- scenario별 subgraph를 `asyncio.gather()`로 병렬 실행하고 동시 실행 수는 설정으로 제한한다.
- 각 scenario 내부는 Stage 2 → 통합 Stage 4+5의 2회 LLM 호출을 순차 실행한다.
- 일부 scenario 실패 시 성공 결과는 저장하고 group stage는 진행하지 않는다.
- retry 소진 시 마지막 원인 예외를 `MIBaseError`의 cause로 보존한다.

localhost 최근 3개 이벤트 최종 실측:

| API | 평균 | 최소 | 최대 |
| --- | ---: | ---: | ---: |
| create_scenarios | 67,614ms | 54,581ms | 75,895ms |
| validate_scenarios | 293ms | 263ms | 331ms |
| create_signposts | 73,071ms | 58,989ms | 95,251ms |
| confirm_generation | 1,063ms | 1,029ms | 1,106ms |

- 최종 pipeline 성공: 3/3
- whole-event batch 평균 260,320ms 대비 create_signposts 약 71.9% 단축
- v0.1.1 평균 67,045ms 대비 약 9% 느리지만 LLM 응답 편차를 고려하면 기존 병렬 방식과 유사한 범위
- fallback 사용 흔적 없음
- 증적 batch: `20260713_203050`, `20260713_203636`
