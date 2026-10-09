# Interpret Agent API Spec

## 기준

- Interpret Agent 전용 FastAPI entrypoint는 `interpret.py`다.
- FastAPI·OpenAPI `info.version`은 `v4.1.7`이다.
- app 내부 업무 path는 `/scenario-groups/{scenario_group_id}/price-interpretations` 계열 두 개뿐이다.
- JSON 필드는 Pydantic alias 기준 camelCase로 표시한다.
- `scenario_group_id`는 path parameter이고 `scenarioIds`는 optional request body다.
- 동기 preview와 비동기 API는 같은 `interpret_price` graph를 실행한다.
- 두 endpoint 모두 현재 FastAPI 기본 HTTP status인 200을 사용한다.
- gateway prefix는 배포 환경이 소유하며 이 문서는 app 내부 path를 기준으로 한다.
- Interpret Agent는 API 결과나 operation 상태를 DB에 저장하지 않는다.

## API 목록

| 분류 | Method | Path | 역할 |
| --- | --- | --- | --- |
| preview | `POST` | `/scenario-groups/{scenario_group_id}/price-interpretations/preview` | 동기 해석 결과 반환, callback 없음 |
| async | `POST` | `/scenario-groups/{scenario_group_id}/price-interpretations` | 즉시 접수 후 background graph와 callback |

`main.py`의 Scenario Group Agent app에는 이 두 route가 등록되지 않는다. Interpret container는
`interpret.py`를 별도 app entrypoint로 사용한다.

## 공통 입력

### Path parameter

| 이름 | type | 현재 검증 |
| --- | --- | --- |
| `scenario_group_id` | integer | FastAPI integer 변환만 수행 |

양수 제약이나 Group 존재 여부 검사는 request schema 단계에 없다.

### Optional body

```json
{
  "scenarioIds": [1077, 1078]
}
```

body 전체를 생략하거나 `scenarioIds`를 빈 배열로 보내면 해당 Group에서 조회되는 proposal 전체를 해석한다.

```http
POST /scenario-groups/183/price-interpretations/preview
Content-Type: application/json

{}
```

현재 `scenarioIds`에는 최소·최대 개수, 양수, 중복 금지 제약이 없다. 문자열처럼 integer로 변환할 수 없는 값은
FastAPI request validation에서 HTTP 422가 된다.

### Scenario filter의 실제 의미

`scenarioIds`는 요청한 ID 전체가 존재하고 Group에 속하는지 strict하게 검증하는 계약이 아니다.

1. proposal 조회에 `scenario_group_id`와 `scenario_id IN (...)` filter를 적용한다.
2. 해당 Group에서 `PROPOSED` 또는 `CONFIRMED` proposal이 발견된 Scenario만 실제 target이 된다.
3. 요청 ID 일부만 발견되면 발견된 subset으로 정상 실행한다.
4. 한 건도 발견되지 않을 때만 `DATA_RETRIEVAL_FAILED`가 된다.

따라서 Client는 preview 결과의 `data.scenarios[*].scenarioId`를 확인해야 한다. 요청 배열 순서를 응답 순서로
보존하는 명시 계약도 없으며, 현재 repository 조회는 Scenario ID 순으로 정렬된다.

## 1. 동기 preview

### Request

```http
POST /scenario-groups/183/price-interpretations/preview
Content-Type: application/json
```

```json
{
  "scenarioIds": [1077]
}
```

preview는 같은 HTTP 요청 안에서 다음 작업을 모두 실행한다.

- proposal과 가격 결과 DB 조회
- MI Base 대비 결정적 차이 지표 계산
- Scenario별 LLM 호출
- Group synthesis LLM 호출
- 일반 텍스트 정규화와 최종 응답 조립

별도 timeout을 endpoint 코드에서 설정하지 않는다. Client와 gateway timeout은 LLM 실행 시간을 고려해 배포
환경에서 정해야 한다.

### Response

다음은 shape을 설명하기 위한 예시다. 문장과 Feature 목록은 실제 DB·LLM 결과에 따라 달라진다.

```json
{
  "status": "success",
  "message": "가격전망 해석 미리보기 결과입니다.",
  "data": {
    "meta": {
      "scenarioGroupId": 183,
      "baseScenarioId": "MI Base",
      "features": ["Temperature", "PowerMix"],
      "indices": ["JKM", "TTF", "HH"],
      "periodStart": "2026-04",
      "periodEnd": "2030-12",
      "unit": "$/MMBtu"
    },
    "scenarios": [
      {
        "scenarioId": "1077",
        "identity": "추운 날씨와 가스 수요가 겹친 가격 상승 국면",
        "driverPhase": "기온 하락과 가스 발전 확대가 초기 수요를 높입니다. 이후 입력 차이는 점차 줄어듭니다.",
        "priceCharacter": "JKM과 TTF의 상승 폭이 HH보다 크게 나타납니다. 후반에는 MI Base 수준에 가까워집니다.",
        "summary": "초기 조달 부담이 큰 Scenario입니다. 재고와 지역별 헤지 수단을 함께 점검해야 합니다."
      }
    ],
    "synthesis": {
      "overallMessage": "이 Group은 초기 가격 부담과 이후 정상화 가능성을 함께 보여줍니다.\n■ Scenario 1077은 초기 조달 대응을 우선 점검해야 합니다."
    }
  }
}
```

### 응답 필드

#### `meta`

| 필드 | type | 의미 |
| --- | --- | --- |
| `scenarioGroupId` | integer 또는 null | 요청 Group ID |
| `baseScenarioId` | string | 현재 고정값 `MI Base` |
| `features` | string array | proposal에서 발견한 Feature 이름, 첫 등장 순서 |
| `indices` | string array | 현재 고정값 `JKM`, `TTF`, `HH` |
| `periodStart`, `periodEnd` | string 또는 null | 수급모델 월별 가격 결과의 실제 시작·종료 월 |
| `unit` | string | 현재 고정값 `$/MMBtu` |

Feature 기간은 `periodStart`, `periodEnd` 계산에 넣지 않는다. 가격 화면과 동일하게 실제 monthly 결과의 첫 월과
마지막 월을 쓰므로 부분 연도 시작도 보존한다. 예시의 `2026-04`~`2030-12`는 57개월이며 2026년 1월로
확장하지 않는다.

`indices`는 실제 조회 성공한 지수만 보여 주는 availability 목록이 아니다. 일부 지수 자료가 없어도 고정 세 지수가
표시될 수 있다.

#### `scenarios`

| 필드 | type | 의미 |
| --- | --- | --- |
| `scenarioId` | string | 실제 해석한 Scenario ID |
| `identity` | string | 한 줄 정체성 |
| `driverPhase` | string | Feature 동인·시장 국면·수렴 해석 |
| `priceCharacter` | string | 가격 지수별 반응·정상화 해석 |
| `summary` | string | 신뢰도와 실무 대응 요약 |

preview의 `scenarioId`는 string이다. async callback의 `scenarioId`는 integer이므로 Client schema에서 이 차이를
구분한다.

#### `synthesis`

`overallMessage` 한 필드만 가진다. Scenario별 identity·price character·데이터 품질 신호를 바탕으로 만든 Group
결론이다.

## 2. 비동기 해석 접수

### Request

```http
POST /scenario-groups/183/price-interpretations
Content-Type: application/json
```

```json
{
  "scenarioIds": [1077]
}
```

body 생략과 filter 규칙은 preview와 같다.

### 즉시 응답

현재 endpoint decorator에 `status_code=202`가 없으므로 실제 HTTP status는 200이다. `202-style`이라는 schema
주석은 응답 의미를 설명할 뿐 transport status 계약이 아니다.

```json
{
  "status": "success",
  "message": "accepted",
  "data": {
    "scenarioGroupId": 183,
    "status": "PROCESSING"
  }
}
```

접수 전에 수행하는 `prepare_price_interpretation`은 ID를 list로 복사할 뿐 DB를 조회하지 않는다. 따라서 이
응답은 다음 내용을 보장하지 않는다.

- Scenario Group이 실제로 존재함
- 요청한 Scenario가 Group에 속함
- proposal이나 가격 결과가 준비됨
- LLM 실행 또는 callback 전달이 성공함

`PROCESSING`은 메모리나 DB에 저장되는 상태가 아니다. 별도 interpretation ID, operation ID, 결과 row도 없다.

### Background 실행

FastAPI `BackgroundTasks`가 같은 graph를 실행한다. graph가 성공하면 success callback을, 예외가 발생하면
failure callback을 한 번 구성해 전송한다.

callback URL은 다음 두 설정을 단순 결합한다.

```text
callback_base_url
  + callback_price_interpretations_path.format(scenario_group_id=...)
```

현재 설정의 path template은 다음 형태다.

```text
/api/v1/mi/next-gen/scenario-groups/{scenario_group_id}/price-interpretations/callback
```

이 callback 수신 path는 Interpret Agent가 제공하는 endpoint가 아니라 외부 backend 계약이다.

공통 설정 `skip_callback=true`이면 callback connector는 HTTP 요청을 보내지 않고 skip 로그만 남긴다. 이 경우도
Interpret Agent에는 결과를 대신 보관하거나 나중에 전송하는 row가 없다.

### Success callback

```json
{
  "result": "success",
  "reason": null,
  "interpretations": [
    {
      "scenarioId": 1077,
      "content": "추운 날씨와 가스 수요가 겹친 가격 상승 국면\n동인 및 국면\n기온 하락과 가스 발전 확대가 초기 수요를 높입니다.\n가격 특성\nJKM과 TTF의 상승 폭이 HH보다 크게 나타납니다.\n시나리오 요약\n재고와 지역별 헤지 수단을 함께 점검해야 합니다."
    }
  ]
}
```

`content`는 다음 순서를 개행으로 연결한 일반 텍스트다.

```text
{identity}
동인 및 국면
{driverPhase}
가격 특성
{priceCharacter}
시나리오 요약
{summary}
```

callback에는 preview의 `meta`와 `synthesis.overallMessage`가 포함되지 않는다.

### Failure callback

```json
{
  "result": "failure",
  "reason": "[DATA_RETRIEVAL_FAILED] 데이터 조회 중 문제가 발생했습니다. - 그룹 183의 해석 대상 제안 파라미터가 없습니다.",
  "interpretations": null
}
```

background wrapper는 모든 graph 예외를 잡아 `str(exc)`를 reason으로 사용한다. 응답 schema가 Markdown·HTML
표현 표식을 일반 텍스트로 정규화한다.

callback 자체 전송 실패는 callback body로 다시 알릴 곳이 없다. connector는 HTTP 401일 때 OAuth2 token을
갱신해 즉시 한 번 더 요청하지만, 그 밖의 durable retry queue나 operation 상태 갱신은 없다. 최종 실패는 로그에만
남는다.

## 3. 일반 텍스트 계약

다음 사용자 표시 필드는 schema validator에서 `to_plain_text()`를 거친다.

- `identity`
- `driverPhase`
- `priceCharacter`
- `summary`
- `synthesis.overallMessage`
- `meta.baseScenarioId`, `meta.features`, `meta.indices`, `meta.periodStart`, `meta.periodEnd`, `meta.unit`
- preview·accepted `message`
- callback `content`
- failure callback `reason`

정규화는 Markdown ATX·Setext heading, 중첩 blockquote, inline·reference link, 목록·task list·표·code fence,
강조·취소선 표식과 HTML tag·comment를 제거하거나 일반 텍스트로 바꾼다. 정상 HTML뿐 아니라 entity로 중첩
인코딩되거나 닫히지 않은 tag도 제거하고 `script`, `style`, `template`, `noscript` 내용은 버린다. URL은 일반
텍스트로 보존하며 `<JKM>`, `<TTF>`, `<HH>`, `<Base>`는 angle bracket 없이 이름만 보존한다.

프롬프트의 글자 수 제한은 다음과 같지만 Pydantic `max_length`로 강제하지는 않는다.

| 필드 | prompt 제한 |
| --- | --- |
| `identity` | 45자 |
| `driverPhase` | 220자 |
| `priceCharacter` | 220자 |
| `summary` | 260자 |
| `overallMessage` | 600자 |

## 4. 오류 계약

### FastAPI request validation

path 또는 body type이 맞지 않으면 HTTP 422와 `detail` 배열을 반환한다.

```json
{
  "detail": [
    {
      "type": "int_parsing",
      "loc": ["body", "scenarioIds", 0],
      "msg": "Input should be a valid integer, unable to parse string as an integer",
      "input": "not-an-int"
    }
  ]
}
```

Pydantic/FastAPI 버전에 따라 `detail`의 보조 필드는 달라질 수 있으므로 Client는 배열 shape과 `loc`를 기준으로
처리한다.

### Preview domain 오류

preview graph에서 `MIBaseError`가 발생하면 공통 envelope를 반환한다.

```json
{
  "status": "error",
  "message": "데이터 조회 중 문제가 발생했습니다. - 그룹 183의 해석 대상 제안 파라미터가 없습니다.",
  "data": {
    "error_code": -4000,
    "error_name": "DATA_RETRIEVAL_FAILED"
  }
}
```

현재 입력 loader가 명시적으로 사용하는 주요 오류는 다음과 같다.

| 상황 | HTTP | error_name |
| --- | --- | --- |
| direct flow 호출에서 `scenario_group_id=None` | 400 | `INVALID_REQUEST` |
| 대상 proposal이 0건 | 500 | `DATA_RETRIEVAL_FAILED` |
| proposal ID 또는 pinned `mi_base_case_id`가 없거나 유효하지 않음 | 500 | `DATA_RETRIEVAL_FAILED` |
| 한 요청의 proposal이 서로 다른 MI Base case를 가리킴 | 500 | `DATA_RETRIEVAL_FAILED` |
| MI Base 가격이 세 지수 모두 없음 | 500 | `DATA_RETRIEVAL_FAILED` |
| 대상 Scenario 하나라도 세 지수 가격이 모두 없음 | 500 | `DATA_RETRIEVAL_FAILED` |
| 가격 월 축 중복·누락·역순 또는 Base/Scenario 축 불일치 | 500 | `DATA_RETRIEVAL_FAILED` |
| Scenario run의 `base_case_prc`가 pinned MI Base와 불일치 | 500 | `DATA_RETRIEVAL_FAILED` |
| 한 해석에 서로 다른 Base 또는 Scenario run이 섞임 | 500 | `DATA_RETRIEVAL_FAILED` |
| 처리되지 않은 예외 | 500 | `UNKNOWN_ERROR` |

일부 지수만 없는 경우는 현재 loader가 차단하지 않는다. 공통 기간이 없는 Feature series는 metric을 빈 근거로
만들 수 있지만, 조회된 가격 series는 pinned MI Base와 Scenario의 월 축이 완전히 같아야 한다.

### Async 오류

request schema 검증을 통과하면 DB 상태와 무관하게 HTTP 200 접수 응답을 보낸다. 이후 graph 오류는 HTTP
응답이 아니라 failure callback 대상이다. callback 전달까지 실패하면 Client가 조회할 terminal 상태가 없다.

## 5. 현재 없는 API

다음 기능은 현재 구현되어 있지 않다.

- interpretation 결과 조회
- 작업 상태 polling
- callback replay 또는 수동 재전송
- 과거 interpretation 목록
- interpretation 삭제
- stream 또는 SSE
- 입력 diff metric 원문 조회

비동기 timeout 뒤 같은 POST를 다시 보내면 새 DB row가 생기지는 않지만 LLM 실행과 callback이 다시 발생할 수
있다. 서버 측 idempotency key나 중복 실행 차단이 없으므로 자동 재요청 여부는 Client가 결정해야 한다.

## 구현 정본

- FastAPI app: `interpret.py`
- router: `apps/agents/interpret_agent/api.py`
- request·response·callback schema: `apps/agents/interpret_agent/flows/interpret_price/api_schema.py`
- sync·background·callback runner: `apps/agents/interpret_agent/flows/interpret_price/flow.py`
- 공통 exception envelope: `apps/common/middleware/exception_handler.py`
- callback connector: `apps/connectors/callback/callback_client.py`
