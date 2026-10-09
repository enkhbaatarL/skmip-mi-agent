# Interpret Agent Flow

## 범위

이 문서는 현재 Interpret Agent의 유일한 업무 graph인 `interpret_price`를 설명한다.

- Model Parameter proposal과 가격 결과 조회
- MI Base 대비 결정적 차이 계산
- Scenario별 LLM 해석
- Scenario Group 종합
- sync preview 반환과 async callback 전달

Scenario 생성, Model Parameter proposal·confirmation, 수급모델 실행은 범위에서 제외한다. 외부 계약은
[API Spec](02_INTERPRET_AGENT_API_SPEC.md), 읽는 table과 read-only 경계는
[DB Spec](04_INTERPRET_AGENT_DB_SPEC.md)을 참고한다.

## 공통 실행 원칙

- preview와 async endpoint는 같은 cached LangGraph를 사용한다.
- graph state는 `InterpretPriceState`로 검증한다.
- DB 조회는 `ProposalParameterService`를 거쳐 공유 repository를 호출한다.
- LLM보다 먼저 코드가 MI Base 대비 수치 근거를 계산한다.
- Scenario별 LLM 호출은 서로 병렬 실행하고, 모두 끝난 뒤 Group synthesis를 실행한다.
- LLM structured output을 API schema로 변환할 때 사용자 표시 문자열을 일반 텍스트로 정규화한다.
- graph 실행마다 하나의 `TraceContext`를 만들고 모든 LLM 호출에 같은 context와 callback을 전달한다.
- graph는 해석 결과나 진행 상태를 DB에 저장하지 않는다.

## 전체 graph

```mermaid
flowchart LR
    A[scenario_group_id + scenarioIds] --> B[load_input]
    B --> C[extract_diffs]
    C --> D[interpret_scenarios]
    D --> E[synthesize_group]
    E --> F[finalize]
    F --> G{delivery}
    G -->|preview| H[HTTP response]
    G -->|async| I[callback POST]
```

compiled graph는 `lru_cache(maxsize=1)`로 process 안에서 재사용한다. request마다 state, transaction ID,
session ID, trace context는 새로 만든다.

## 1. 입력 준비

### API state

graph 시작 state는 다음 두 값만 가진다.

```text
scenario_group_id: int
scenario_ids: list[int]
```

빈 `scenario_ids`는 `None` filter로 바꾸어 Group에서 조회되는 proposal 전체를 대상으로 한다.

### `load_input`

`load_input` node는 동기 DB session을 열고 `ProposalParameterService.load_interpret_input()`을 호출한다. 현재
node 자체도 동기 함수이며 Agent 코드에서 `asyncio.to_thread()`를 직접 사용하지 않는다. 실제 sync node 실행
방식은 LangGraph runtime에 따른다.

```mermaid
flowchart TD
    A[Group + optional Scenario filter] --> B[최신 proposal 조회]
    B --> C[proposal ID와 pinned MI Base case 검증]
    C --> D[MI Base / Scenario Feature 정규화]
    D --> E[JKM·TTF·HH 가격 및 run 증적 조회]
    E --> F[월 축·기준 가격 snapshot 정합성 검증]
    F --> G[InterpretInput]
```

## 2. proposal을 Feature 시계열로 바꾸는 법

### 대상 proposal 선택

repository는 다음 조건을 만족하는 row를 Scenario별로 모은다.

- 요청 `scenario_group_id`와 일치
- `del_yn='N'`
- `status IN ('PROPOSED', 'CONFIRMED')`
- `proposal_parameters IS NOT NULL`
- `scenarioIds`가 있으면 `scenario_id IN (...)`

Scenario별 `model_param_proposal_id`가 가장 큰 row 하나를 사용한다. `CONFIRMED`이고
`confirmation_parameters`가 non-empty이면 확정값을 사용하고, 그렇지 않으면 `proposal_parameters`를 사용한다.

선택한 proposal의 `model_param_proposal_id`와 `mi_base_case_id`를 입력 snapshot 증적으로 보존한다. proposal ID와
양수 `mi_base_case_id`가 모두 있어야 하며, 한 Group 해석에 포함된 proposal은 모두 같은 MI Base case를
가리켜야 한다. null·잘못된 ID 또는 mixed case는 fail-closed 처리한다.

요청한 Scenario ID 일부가 조회되지 않아도 나머지 row로 계속 실행한다. 전체 조회 결과가 0건일 때만 실패한다.

### 시간 축과 grouping 축

각 proposal parameter의 `modelTarget.slotAxesFieldNames`가 시계열 구조를 정한다.

| 조건 | 정규화 결과 |
| --- | --- |
| 축에 `Month`가 있음 | `monthly`, 기간 `YYYY-MM` |
| 축에 `Month`가 없음 | `annual`, 기간 `YYYY` |
| `Year`가 없음 | 해당 record skip |
| monthly인데 `Month`가 없음 | 해당 record skip |
| `Year`, `Month` 이외 축 | `groupKeys`로 보존 |

`parameterName`은 Feature 이름이 된다. 같은 Feature라도 Country, Region, DegreeDayType, energy source 같은
`groupKeys`가 다르면 별도 series다.

표시용 region은 이름에 `country`, `region`, `continent`, `area`, `zone`, `nation`이 들어간 첫 grouping 축에서
가져온다. 해당 축이 없으면 첫 grouping 축을 사용하고, 나머지 축은 qualifier로 합친다. grouping 축이 없으면
region은 빈 문자열이다.

### MI Base와 Scenario 값

```text
basecaseValue  → MI Base Feature series
proposedValue  → Scenario Feature series
```

여러 Scenario proposal의 `basecaseValue`는 하나의 MI Base store로 병합한다. 같은 Feature·grouping·기간이
여러 proposal에 있고 값이 같으면 한 값으로 합친다. 값이 다르면 어느 proposal을 기준으로 해석할지 결정할 수
없으므로 `DATA_RETRIEVAL_FAILED`로 중단한다.

Feature `unit`은 현재 빈 문자열이고 `index`도 `None`이다. Feature의 geo label을 JKM·TTF·HH 중 하나에
hard mapping하지 않는다.

## 3. 가격 시계열을 읽는 법

현재 지수와 모델 결과 지역명 mapping은 고정되어 있다.

| 지수 | `prc_rgn_nm` | 값 |
| --- | --- | --- |
| JKM | `East Asia Spot` | MI Base `base_case_prc`, Scenario `user_adj_prc` |
| TTF | `TTF` | MI Base `base_case_prc`, Scenario `user_adj_prc` |
| HH | `HH` | MI Base `base_case_prc`, Scenario `user_adj_prc` |

모든 가격은 `perd_unit_spt_cd='M'`인 월간 결과만 읽고 `perd_key`를 `YYYY-MM`으로 정규화한다.

MI Base는 전역 최신 case를 다시 고르지 않고 proposal에 고정된 정확한 `mi_base_case_id`의 완료
`MI_BASE` run을 사용한다. Scenario 가격은 Group의 active Scenario가 가진 최신 완료 run을 사용하고,
Scenario별 `run_seq`를 입력 snapshot 증적으로 보존한다.

각 Scenario 가격 row의 `base_case_prc`를 함께 읽어 같은 기간의 pinned MI Base `base_case_prc`와 비교한다.
모든 값이 허용 오차 안에서 같아야 하며, 한 Scenario 또는 MI Base에서 지수별로 서로 다른 `run_seq`가 섞이면
실패한다. 모델 결과 table에는 proposal ID와 run을 직접 잇는 FK가 없으므로, 이 기준 가격 검증이 현재 가능한
snapshot 일치 guard다.

조회된 각 가격 series는 `YYYY-MM` 형식의 오름차순·중복 없는 연속 월이어야 한다. 지수별 MI Base 축과 해당
Scenario 축도 완전히 같아야 한다. 화면의 실제 결과가 2026-04~2030-12라면 이 57개월을 그대로 사용하며
첫해를 1월로 확장하지 않는다.

세 지수 모두 MI Base 결과가 없으면 실패한다. 대상 Scenario별로도 세 지수 가격이 모두 없으면 실패한다. 특정
지수 하나 또는 둘만 없는 경우는 남은 series로 계속 진행한다.

## 4. `extract_diffs`

이 node는 LLM을 호출하지 않는다. Feature와 가격 series를 공통 기간에 맞추고 Scenario별
`ScenarioDiffBundle`을 만든다.

```text
diff = scenario value - MI Base value
```

### Feature matching

Feature는 `(feature 이름, 정렬된 groupKeys)`가 같은 MI Base series와 짝을 이룬다. Scenario에만 있거나
MI Base에만 있어 짝이 없는 series는 diff 결과에 포함하지 않는다.

Feature의 공통 기간이 하나도 없으면 해당 metric의 자동 요약은 `공통 구간 없음`이 된다. graph 전체를
실패시키지는 않는다. 가격은 load 단계에서 Base와 Scenario의 월 축 완전 일치를 이미 검증한다.

### Feature 지표

각 Feature series에서 다음 값을 계산한다.

- 평균 차이
- 최대 양수 차이와 최대 음수 차이
- 임계값 이상 차이가 같은 방향으로 연속되는 주요 구간
- 이후 모든 구간이 허용 차이 안에 머무는 최초 수렴 시점
- 극단 편차 anomaly
- 위 값을 합친 자동 요약

Feature와 가격 모두 첫 기간부터 모든 차이가 convergence tolerance 안이면 별도의 "수렴 시작"으로 보지
않고 수렴 시점을 `null`로 둔다. 한 번 tolerance 밖으로 벗어난 뒤 안쪽에 머무르기 시작할 때만 최초
수렴 시점을 기록한다.

현재 고정 Feature 임계값은 다음과 같다.

| Feature | notable | extreme | convergence |
| --- | ---: | ---: | ---: |
| `Temperature` | 2.0 | 6.0 | 1.0 |
| `PowerMix` | 1.0 | 3.0 | 0.5 |

등록되지 않은 Feature는 그 series의 최대 절대 차이에 `0.3`, `0.8`, `0.15`를 곱해 각각 notable,
extreme, convergence 임계값을 만든다. 모든 차이가 0이면 `0.1`, `1.0`, `0.05`를 사용한다.

### 가격 지표

각 지수에서 다음 값을 계산한다.

- MI Base 평균, Scenario 평균, 평균 차이
- 최대 상승과 최대 하락 시점
- 이후 전 기간 차이가 허용 범위에 머무는 수렴 시점
- 음수 가격 anomaly
- MI Base 대비 급변 anomaly

가격 수렴 tolerance는 `1.0 $/MMBtu`와 MI Base 평균 절대값의 5% 중 큰 값이다. 급변은 MI Base 대비
절대 비율이 25% 이상이면서 절대 차이가 `1.0 $/MMBtu` 이상일 때 잡는다. Scenario 가격이 음수면 음수
anomaly로 분류하고 같은 지점의 급변 검사는 생략한다.

### 데이터 품질 flag

Scenario bundle에는 다음 신호를 중복 제거해 남긴다.

- Feature에 extreme diff가 있음
- 가격에 negative price가 있음
- 가격에 spike가 있음

이 flag는 LLM이 해석 신뢰도를 낮추거나 모델 안정성 검증을 권고할 때 사용하는 힌트다. 자동으로 Scenario를
차단하지는 않는다.

## 5. `interpret_scenarios`

```mermaid
flowchart TD
    A[ScenarioDiffBundle 1..N] --> B1[Scenario 1 LLM]
    A --> B2[Scenario 2 LLM]
    A --> BN[Scenario N LLM]
    B1 --> C[asyncio.gather]
    B2 --> C
    BN --> C
    C --> D[ScenarioComparisonOut list]
```

대상 Scenario마다 structured-output LLM 호출을 하나 만든 뒤 `asyncio.gather`로 동시에 실행한다. Agent
flow에는 별도 semaphore나 Scenario 개수 제한이 없지만 공통 LLM connector의 LLM·HTTP semaphore는 각 호출에
적용된다. 한 호출이 최종 예외로 끝나면 부분 결과를 callback하거나 저장하지 않고 graph 전체가 실패한다.

LLM 호출 설정은 다음과 같다.

- `ModelPreference.QUALITY`
- node 호출부는 `temperature=0.0`을 전달하지만, 현재 structured-output connector는 이 값을 provider
  request parameter로 전달하지 않는다.
- `max_retries`는 명시하지 않아 공통 connector 기본값 2 사용
- `llm_stream_enabled` 설정 전달
- `llm_reasoning_effort` 설정 전달
- 실행 전체의 `TraceContext` 전달

### LLM에 전달하는 근거

가격 근거는 JKM, TTF, HH 순으로 정렬한다. 각 지수에는 평균·최대 차이·수렴·anomaly·자동 요약이 들어간다.

Feature 근거는 특정 지수 bucket에 넣지 않고 flat list로 전달한다. Feature 이름, geo label, geo level, 단위,
평균 차이, 주요 구간, 수렴, anomaly를 포함한다.

프롬프트는 geo label을 보고 LLM이 시장을 추론하도록 soft hint를 준다.

- JKM은 아시아
- TTF는 유럽
- HH는 미국
- 모호하면 특정 지수에 억지로 귀속하지 않고 시장 공통 영향으로 설명

### structured output

각 호출은 `identity`, `driver_phase`, `price_character`, `summary`를 반환한다. 프롬프트는 MI Base 대비
관점, 일반 텍스트, 근거 수치 보존과 함께 다음 분석 순서를 요구한다.

1. `identity`: 원인과 지수별 방향을 압축한 market call
2. `driver_phase`: 입력 변화에서 물리적 수급과 지역별 가격으로 이어지는 전이 경로
3. `price_character`: 지수별 상대 민감도, 최대·평균 변화, 비동조와 정상화
4. `summary`: 방향·수치 신뢰도 분리, 근거 기반 모니터링 항목, 조건부 헤지·조달·검증 제언

근거에 없는 사건·회사·물량·확률은 만들지 않는다. `data_quality` 신호가 있으면 수치 신뢰도와 활용 범위를
낮추고 재검증 대상을 summary에 명시한다. 분량 상한은 기존의 두 배를 넘지 않는 70·340·340·420자다.
가격의 `max_pos`·`max_neg` month는 동일한 최대 편차가 여러 달 지속될 때도 대표 한 점만 담을 수 있으므로,
별도 지속 구간 근거 없이 특정 월 집중·계절성·유일한 피크를 추론하지 않는다.

Pydantic API schema로 변환할 때 Markdown·HTML 표현 문법을 제거한다. 글자 수와 문체는 validator가 아니라
프롬프트로만 통제한다.

## 6. `synthesize_group`

Scenario별 호출이 모두 끝난 뒤 Group synthesis LLM을 한 번 호출한다.

이 호출에 전달하는 Scenario별 brief는 다음 값만 가진다.

- `scenario_id`
- `identity`
- `price_character`
- `data_quality_signals`

`driver_phase`와 `summary`, 원래 diff metric 전체는 Group synthesis 입력에 직접 포함하지 않는다. 종합 결과는
`overall_message` 한 문자열이고 API schema에서 일반 텍스트로 정규화한다.

## 7. `finalize`

finalize는 LLM을 호출하거나 DB를 조회하지 않는다. 다음 값을 조립해 `PriceInterpretationResult`를 만든다.

- meta: Group ID, `MI Base`, Feature 목록, 고정 지수 목록, 수급모델 가격 축의 실제 시작·종료 월, 단위
- scenarios: Scenario별 해석
- synthesis: Group 종합

`meta.indices`는 실제 price diff bundle에 존재하는 지수 목록이 아니라 고정 `INDEX_ORDER` 전체다.

## 8. Sync와 async delivery

### Preview

```mermaid
flowchart LR
    A[preview POST] --> B[run_interpret_price]
    B --> C[graph ainvoke]
    C --> D[PriceInterpretationResult]
    D --> E[HTTP 200 response]
```

`run_interpret_price`가 result를 찾지 못하면 `UNKNOWN_ERROR`를 올린다. graph 또는 DB·LLM 예외는 FastAPI 공통
exception handler가 HTTP 오류로 변환한다.

### Async

```mermaid
flowchart LR
    A[async POST] --> B[ID만 복사]
    B --> C[HTTP 200 PROCESSING]
    B --> D[FastAPI BackgroundTask]
    D --> E[같은 graph]
    E -->|success| F[success callback]
    E -->|exception| G[failure callback]
    F --> H[외부 backend]
    G --> H
```

async prepare에는 DB 사전 검증이 없다. callback success body에는 Scenario별 일반 텍스트만 들어가고 Group
synthesis는 들어가지 않는다.

callback 전송 오류는 graph 오류와 분리해 로그에 남긴다. callback connector는 401에 한해 token refresh 후
즉시 한 번 재요청한다. 전송 결과를 기록하는 DB row, 일반 오류 retry queue, polling, replay는 없다.
`skip_callback=true`이면 connector가 외부 HTTP 요청 없이 반환하며 결과를 별도 저장하지도 않는다.

## 9. Tracing과 startup

`run_interpret_price`는 실행마다 새 transaction ID와 다음 trace 정보를 만든다.

| 값 | 현재 source |
| --- | --- |
| `app_identifier` | `agents.interpret_agent.aip_app_id` |
| `agent_name` | `interpret_agent` |
| `api_identifier` | `interpret_price` |
| `session_id` | `scenario_group_id` 문자열 |
| tag `interpret_agent_version` | `v4.1.7` |

같은 context를 LangGraph config, runtime context, MLflow context에 사용한다. Scenario별 LLM과 Group synthesis
LLM에도 이 context와 graph callback handler를 전달한다.

app lifespan은 logging, Interpret Agent MLflow profile, ORM/DB schema validation, callback OAuth2 token
pre-fetch를 수행한다. token pre-fetch가 실패해도 startup은 계속한다.

## 실패와 복구 경계

- Agent graph에는 node 단위 retry나 fallback 분기가 없다. 공통 LLM connector는 기본 `max_retries=2`로
  non-stream SDK retry 또는 stream 전체 요청 retry를 적용할 수 있다.
- Scenario별 LLM 하나가 실패하면 Group synthesis와 finalize를 실행하지 않는다.
- preview는 같은 HTTP 요청에서 실패한다.
- async는 failure callback을 시도한다.
- callback 전달까지 실패하면 로그 외에 조회 가능한 결과가 없다.
- process가 중단되면 BackgroundTask를 DB operation에서 재개하지 않는다.
- 같은 async 요청을 다시 보내는 중복 방지나 idempotency key가 없다.

## 변경 시 함께 확인할 것

| 변경 대상 | 함께 확인할 영역 |
| --- | --- |
| request·response schema | preview, accepted response, callback type 차이, OpenAPI route isolation |
| proposal JSON parsing | Model Parameter proposal·confirmation 계약, annual/monthly 축, MI Base 병합 |
| 가격 SQL | JKM·TTF·HH mapping, 완료 run 선택, monthly period, read-only 보장 |
| diff threshold | prompt evidence, data quality flag, deterministic unit test |
| Scenario prompt | structured output, plain-text sanitizer, 글자 수 smoke warning |
| Group prompt | 전달 brief 범위, `overallMessage`, callback 미포함 경계 |
| callback | URL 설정, OAuth2, failure body, 실제 HTTP 200 접수 계약 |
| tracing | Interpret agent profile, shared TraceContext, graph callback 전달 |
