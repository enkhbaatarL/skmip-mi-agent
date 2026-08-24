# Interpret Agent 처음 이해하기

## 이 Agent는 무엇을 하나요?

Interpret Agent는 Scenario별 수급모델 입력과 가격 예측 결과를 `MI Base`와 비교하고, 그 차이가 어떤 시장
의미를 가지는지 설명하는 프로그램이다.

예를 들어 어떤 Scenario에서 다음 결과가 나왔다고 생각해 보자.

- 한국의 기온 입력이 MI Base보다 낮다.
- 가스 발전 관련 입력이 MI Base보다 높다.
- JKM과 TTF 예측 가격은 크게 오르고 HH는 비교적 작게 움직인다.
- 몇 달 뒤 가격 차이가 MI Base 수준으로 줄어든다.

Agent는 수치를 그대로 나열하는 데서 끝나지 않는다. 여러 입력 변화를 함께 보고 다음 내용을 Scenario마다 같은
구조로 설명한다.

- 이 Scenario를 한 문장으로 규정하는 정체성
- 어떤 입력이 어느 국면에서 가격 변화를 이끄는지
- JKM·TTF·HH의 반응과 정상화 시점이 어떻게 다른지
- 데이터 품질을 얼마나 신뢰할 수 있고 실무에서는 무엇을 점검해야 하는지

마지막에는 Scenario별 해석을 모아 Scenario Group 전체의 결론과 제언을 만든다.

## 결과를 만드는 전체 순서

```text
1. Scenario Group ID와 선택적인 Scenario ID를 받는다
   ↓
2. 저장된 Model Parameter proposal에서 MI Base 입력과 Scenario 입력을 읽는다
   ↓
3. 완료된 수급모델 실행 결과에서 MI Base·Scenario 가격을 읽는다
   ↓
4. 같은 기간끼리 맞춰 입력·가격 차이와 이상 신호를 계산한다
   ↓
5. Scenario별 차이를 LNG 시장 관점의 일반 텍스트로 해석한다
   ↓
6. Scenario Group 전체의 종합 메시지를 만든다
   ↓
7. preview 응답으로 바로 반환하거나 비동기 callback으로 전달한다
```

Interpret Agent가 시작되기 전에 Model Parameter proposal과 가격 모델 실행 결과가 준비되어 있어야 한다. 이
Agent는 Scenario를 생성하거나 Model Parameter를 제안하거나 수급모델을 실행하지 않는다.

## 먼저 알아둘 용어

### Scenario Group

같은 분석 목적을 가진 Scenario 여러 개의 묶음이다. Interpret API의 path에는 분석할
`scenario_group_id`가 들어가고 JSON 응답에서는 `scenarioGroupId`로 표시된다.

### Scenario

Model Parameter 입력을 다르게 적용하고 가격을 계산한 하나의 미래 경우다. 요청 body의 `scenarioIds`로 일부
Scenario만 고를 수 있다. 이 목록을 비우거나 body를 생략하면, 해당 Group에서 읽을 수 있는 proposal 전체가
대상이 된다.

### MI Base

Scenario를 비교하는 기준 입력과 기준 가격이다. Interpret Agent는 결과를 항상 `MI Base 대비`로 설명한다.
MI Base의 절대값만 따로 평가하는 기능은 없다.

### Model Parameter proposal

Scenario별로 수급모델에 넣을 입력값을 저장한 자료다. 각 값은 보통 다음 두 값을 가진다.

| 값 | 의미 |
| --- | --- |
| `basecaseValue` | MI Base 입력 |
| `proposedValue` | 해당 Scenario 입력 |

확정된 proposal에 실제 확정값이 있으면 Interpret Agent는 최초 제안보다 확정값을 우선해서 읽는다.

### Feature

가격을 계산하는 데 사용한 입력 항목이다. `Temperature`, `PowerMix`, `GDP`처럼 proposal의
`parameterName`이 Feature 이름이 된다.

Feature에는 국가·지역·에너지원처럼 여러 분류 축이 함께 들어갈 수 있다. Agent는 `Year`, `Month`를 시간
축으로 사용하고 나머지 축은 같은 시계열을 구분하는 기준으로 보존한다.

### 가격 지수

현재 해석 대상은 다음 세 지수다.

| 지수 | 프롬프트에서 참고하는 시장 |
| --- | --- |
| `JKM` | 아시아 |
| `TTF` | 유럽 |
| `HH` | 미국 |

가격 지수와 모델 결과의 지역명은 코드에 고정되어 있다. 반면 Feature의 국가·지역 label을 어느 지수와 연결할지는
코드가 강제로 정하지 않고 LLM이 soft hint를 보고 해석한다.

### 결정적 차이 지표

LLM을 호출하기 전에 코드가 확정하는 수치 근거다. 같은 기간의 `Scenario - MI Base`를 계산해 평균 차이, 최대
상승·하락, 주요 편차 구간, 수렴 시점, 이상치 후보를 만든다.

LLM은 이 계산 결과를 받아 설명을 작성한다. API 결과에는 계산 중간값 전체가 노출되지 않고 최종 해석 문장만
포함된다.

### Scenario 해석

Scenario 하나의 결과는 다음 네 필드로 구성된다.

| 필드 | 의미 |
| --- | --- |
| `identity` | Scenario를 규정하는 짧은 헤드라인 |
| `driverPhase` | 입력 Feature와 시장 국면 해석 |
| `priceCharacter` | 지수별 가격 반응과 정상화 해석 |
| `summary` | 신뢰도와 실무 대응을 포함한 요약 |

### Group synthesis

모든 Scenario 해석을 보고 Group 전체의 공통 결론과 Scenario별 제언을 한 문자열로 정리한 결과다. preview의
`synthesis.overallMessage`에서 확인한다.

### Preview

요청 연결을 유지한 채 DB 조회, 수치 계산, LLM 해석을 모두 끝낸 뒤 결과를 바로 반환하는 동기 API다. 별도
callback을 보내지 않는다.

### Callback

비동기 API가 접수 응답을 먼저 보낸 뒤, 백그라운드 작업이 끝났을 때 설정된 외부 시스템으로 보내는 HTTP
요청이다. 성공 시 Scenario별 해석을, 실패 시 실패 이유를 보낸다.

### Plain text

사용자에게 보이는 해석은 Markdown이나 HTML이 아닌 일반 텍스트 계약을 따른다. 프롬프트가 일반 텍스트를
요구하고, 응답 schema가 남아 있는 표현용 서식도 한 번 더 제거한다. 문단 구분 개행과 Group synthesis의
`■ ` 문자는 허용된다.

## 사용자는 어떤 결과를 보나요?

### Scenario별 해석

각 Scenario는 같은 네 필드를 가지므로 서로 나란히 비교할 수 있다. 입력값과 가격의 실제 차이는 해석의 근거로
사용되지만, 응답은 현업이 읽기 쉬운 문장에 집중한다.

### Group 종합

Group 종합은 Scenario들이 어떤 성격으로 나뉘는지 정리하고, Scenario별 신뢰·검증·대응 방향을 제안한다.
Scenario별 상세 내용과 중복되는 표를 다시 만들지는 않는다.

### Meta 정보

preview 결과는 다음 공통 정보를 함께 제공한다.

- 요청한 Scenario Group ID
- 기준 ID인 `MI Base`
- 실제 proposal에서 발견한 Feature 이름
- 고정 가격 지수 순서 `JKM`, `TTF`, `HH`
- 월간 Feature와 가격 자료를 합쳐 계산한 전체 표시 기간
- 가격 단위 `$/MMBtu`

`meta.indices`는 해석 설정의 고정 지수 목록이다. 특정 지수의 DB 시계열이 없더라도 현재 구현은 이 목록 자체를
줄이지 않는다.

## 두 가지 실행 방식

| 방식 | API | 결과 전달 | 주된 용도 |
| --- | --- | --- | --- |
| 동기 preview | `POST /scenario-groups/{scenario_group_id}/price-interpretations/preview` | 같은 HTTP 응답 | 개발·검증·화면 미리보기 |
| 비동기 | `POST /scenario-groups/{scenario_group_id}/price-interpretations` | 즉시 접수 후 외부 callback | 실제 callback 연계 |

두 API는 같은 LangGraph를 사용한다. 비동기 API도 현재 실제 HTTP status는 200이며 body의
`data.status=PROCESSING`으로 접수 사실을 알린다.

비동기 접수 단계에서는 Group 존재 여부, proposal 존재 여부, 요청한 Scenario의 소속을 조회하지 않는다. 이런
오류는 백그라운드 실행 중 발견되어 failure callback의 `reason`으로 전달된다.

## DB에는 무엇을 저장하나요?

Interpret Agent의 업무 흐름은 DB read-only다.

- Model Parameter proposal을 읽는다.
- MI Base와 Scenario 가격 결과를 읽는다.
- 해석 결과, 진행 상태, operation, callback 전송 상태를 DB에 저장하지 않는다.
- DB transaction으로 상태를 확정하거나 갱신하는 단계가 없다.

비동기 방식은 외부 callback HTTP 요청을 보내므로 시스템 전체 관점에서는 외부 통신 side effect가 있다. 여기서
`read-only`는 Interpret Agent가 사용하는 DB에 대해 `INSERT`, `UPDATE`, `DELETE`를 하지 않는다는 의미다.

callback 전송에 실패하면 로그만 남고, 다시 조회할 Interpret operation ID나 결과 row는 만들어지지 않는다.
일반적인 durable retry·polling·replay API도 현재 없다.

## 이 Agent가 하지 않는 일

- Event 기사나 Scenario 제목·설명·Dimension을 읽지 않는다.
- Scenario의 사실관계를 원본 Event와 대조하지 않는다.
- Model Parameter를 생성·수정·확정하지 않는다.
- 수급모델을 실행하거나 가격을 다시 계산하지 않는다.
- 해석 결과를 DB에 보관하거나 과거 결과를 조회하지 않는다.
- 정확한 가격 예측의 적중 여부를 평가하지 않는다.
- 요청한 `scenarioIds`가 모두 존재하는지 all-or-nothing으로 검증하지 않는다.

현재 LLM에 전달되는 업무 근거는 proposal에서 계산한 Feature 차이와 모델 결과에서 계산한 가격 차이다. Scenario
원문이나 Event grounding이 필요한 품질 판단은 이 Agent의 현재 입력 범위 밖이다.

## 진행 상태를 읽는 법

현재 Interpret Agent에는 저장되는 업무 stage나 operation 상태가 없다.

| 보이는 값 | 의미 |
| --- | --- |
| preview HTTP 응답 대기 | 같은 요청 안에서 DB 조회·LLM 해석 실행 중 |
| 비동기 `PROCESSING` | background task를 FastAPI에 등록했다는 접수 응답 |
| success callback | graph 실행 성공 후 Scenario별 해석 전달 |
| failure callback | graph 실행 실패 이유 전달 시도 |

`PROCESSING`은 DB에 기록된 상태가 아니며 이후 성공을 보장하지 않는다. callback이 오지 않았을 때 Agent 자체
상태 조회 API로 복구할 수 없으므로 서버 로그와 callback 수신 시스템을 함께 확인해야 한다.

## 더 자세히 알고 싶다면

| 궁금한 것 | 다음 문서 |
| --- | --- |
| 요청·응답·callback에 무엇이 들어가는지 | [API Spec](02_INTERPRET_AGENT_API_SPEC.md) |
| 내부에서 어떤 순서로 읽고 계산하고 해석하는지 | [Flow](03_INTERPRET_AGENT_FLOW.md) |
| 어떤 table을 어떤 조건으로 읽고 무엇을 저장하지 않는지 | [DB Spec](04_INTERPRET_AGENT_DB_SPEC.md) |
| 자동·배포 테스트와 현재 품질 검증 범위 | [테스트와 품질](05_INTERPRET_AGENT_TEST_AND_QUALITY.md) |
| 공통 프로젝트 폴더와 코드 배치 원칙 | [Project Directory Structure](../../architectures/project_directory_structure.md) |

## 코드를 맡은 사람이 처음 볼 위치

개념을 이해한 뒤 실제 코드를 찾을 때는 다음 순서가 가장 빠르다.

1. `interpret.py`: Interpret Agent 전용 FastAPI 서버와 startup
2. `apps/agents/interpret_agent/api.py`: preview·비동기 endpoint
3. `apps/agents/interpret_agent/flows/interpret_price/flow.py`: graph와 callback 실행
4. `apps/agents/interpret_agent/flows/interpret_price/nodes.py`: 조회·차이 계산·LLM·최종화 node
5. `apps/agents/interpret_agent/persistence/proposal_parameter_service.py`: proposal·가격 입력 조립
6. `apps/agents/interpret_agent/utils/series_metrics.py`: MI Base 대비 결정적 수치 계산
7. `apps/agents/interpret_agent/prompts/`: Scenario 해석과 Group 종합 지시문
8. `apps/persistence/model_parameter/repository.py`: proposal 조회
9. `apps/persistence/model_result/repository.py`: 모델 결과 가격 read-only SQL

코드를 변경하기 전에는 [AGENTS.md](../../../AGENTS.md)와
[Python conventions](../../../.claude/rules/python-conventions.md)를 함께 확인한다.
