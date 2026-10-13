# Scenario Group Agent 처음 이해하기

## 이 Agent는 무엇을 하나요?

Scenario Group Agent는 하나 이상의 시장 이벤트를 보고, 앞으로 상황이 어떻게 달라질 수 있는지를 몇 가지
경우로 나누어 보여주는 프로그램이다.

예를 들어 다음 뉴스가 들어왔다고 생각해 보자.

> 주요 LNG 생산시설의 가동이 중단됐고 복구 시점은 아직 정해지지 않았다.

Agent는 이 뉴스를 그대로 요약하는 데서 끝나지 않는다. 앞으로의 결과를 바꿀 질문을 찾는다.

- 생산시설이 언제 복구되는가?
- 다른 지역의 공급으로 부족분을 채울 수 있는가?
- 높은 가격 때문에 수요가 줄어드는가?

그런 다음 질문별 답을 조합해 다음과 같은 미래 상황을 만든다.

- 빠른 복구와 대체 공급 확보
- 복구 지연이지만 수요 감소로 충격 완화
- 장기 중단과 대체 공급 부족

이렇게 만든 여러 미래 상황을 한 묶음으로 보여주는 것이 Scenario Group이다.

## 결과를 만드는 전체 순서

```text
1. 분석할 Event를 고른다
   ↓
2. Agent가 여러 미래 Scenario를 만든다
   ↓
3. 사용자가 Scenario를 읽고 필요하면 수정한다
   ↓
4. Agent가 수정한 내용에 모순이나 중복이 없는지 검사한다
   ↓
5. 각 Scenario가 현실화되고 있음을 알려 줄 Signpost를 만든다
   ↓
6. 사용자가 최종 결과를 확정한다
```

각 단계는 서로 다른 목적을 가진다. Scenario 생성이 성공했다고 검사가 끝난 것도 아니고, Signpost가 만들어졌다고
최종 확정된 것도 아니다.

## 먼저 알아둘 용어

### Event

Scenario 분석의 출발점이 되는 뉴스나 시장 사건이다. 생산시설 중단, 제재, 수요 전망 변경, 이상기후 등이
예가 될 수 있다. 한 번에 Event 1~5개를 함께 분석할 수 있다.

Event는 항상 하나의 일관된 사실 문장이 아니다. LNG 뉴스·리포트 하나에도 확정된 과거 사실, 현재 관측,
운영사의 미래 예상, 기관별 전망이 함께 들어갈 수 있고, 같은 대상·기간에 대한 미래 견해가 서로 충돌할 수도
있다. Agent는 이를 하나의 결론으로 평균하거나 덮어쓰지 않고, 출처와 기준시점을 가진 별도 주장으로 구분한다.
확정·관측 사실은 현재 상태의 기준점으로, 미래 예상과 기관 View의 차이는 Scenario를 나누는 불확실성으로
사용한다.

### Dimension

미래를 나누는 핵심 질문 또는 판단 기준이다. 위 예시의 `생산시설 복구 시점`, `대체 공급 가능성`이
Dimension이다.

각 Dimension에는 선택할 수 있는 값이 있다.

```text
Dimension: 생산시설 복구 시점
값 1: 2주 안에 복구
값 2: 1~2개월 뒤 복구
값 3: 장기 중단
```

### Scenario

여러 Dimension 값을 한 개씩 골라 만든 하나의 미래 상황이다. 제목뿐 아니라 어떤 조건이 결합되었는지,
왜 그런 시장 결과가 예상되는지를 함께 가진다.

### Scenario Group

같은 Event를 바탕으로 만든 Scenario 여러 개의 묶음이다. 현재 방식에서는 보통 Scenario 3~5개를 만든다.

### Baseline

여러 Scenario 중 현재 정보로 보았을 때 가장 가능성이 높다고 판단한 대표 Scenario다. 한 Group에는 정확히
하나만 둔다.

Baseline은 확정된 미래나 기관 전망의 합의값을 뜻하지 않는다. 생성 기준시점의 증적을 바탕으로 선택한 대표
작업 가정이며, 상충하는 전망은 다른 Scenario 또는 명시적인 미반영 불확실성으로 계속 추적한다.

### JKM 가격 압력

JKM은 아시아 LNG 가격을 나타내는 대표 지표다. Agent는 정확한 미래 가격을 예측하지 않는다. 대신 각
Scenario가 JKM 가격을 올리는 쪽인지, 내리는 쪽인지, 그 압력이 얼마나 강한지를 표시한다.

### Signpost

어떤 Scenario가 실제로 벌어지고 있는지 판단하기 위해 앞으로 관찰할 신호다.

예를 들어 `빠른 복구` Scenario의 Signpost는 다음과 같을 수 있다.

- 운영사가 재가동 일정을 공식 발표한다.
- 실제 생산량이 중단 전 수준에 가까워진다.

Signpost는 Scenario 설명을 반복하는 문장이 아니라 뉴스, 수치, 공식 발표 등으로 확인할 수 있어야 한다.

### Validation

사용자가 Scenario 표를 수정한 뒤 내용에 문제가 없는지 검사하는 단계다. 중복 Scenario, 빠진 값, 서로
양립하기 어려운 조건 등을 확인한다. 경고만 있는 경우에는 계속 진행할 수 있고, 심각한 문제가 있으면 수정 후
다시 검사해야 한다.

### Confirmation

Scenario와 Signpost를 더 이상 초안이 아닌 최종 결과로 확정하는 단계다.

## Model Impact Lever는 왜 필요한가요?

Event에서 가격 결과로 바로 뛰어가면 근거가 약한 Scenario가 만들어질 수 있다. 그래서 Agent는 Event가 LNG
시장에 영향을 주는 경로를 중간에 확인한다.

예를 들면 다음과 같다.

```text
생산시설 중단
  → 공급 가능한 LNG 물량 감소
  → 아시아로 들어오는 물량 경쟁 증가
  → JKM 상승 압력
```

Model Impact Lever는 `생산량`, `수요`, `운송`, `재고`처럼 Event와 시장 결과를 연결할 때 참고하는 영향 경로
목록이다. Agent는 이 목록을 이용해 어떤 불확실성을 Scenario의 Dimension으로 만들지 판단한다.

처음 문서를 읽는 사람은 Lever의 DB 구조까지 알 필요는 없다. 우선 `Event가 시장에 영향을 미치는 과정을
빠뜨리지 않기 위한 중간 연결고리`라고 이해하면 된다.

## v4는 무엇인가요?

v4는 현재 사용하는 네 번째 Scenario 생성 방식의 이름이다.

v4는 다음 정보를 함께 사용한다.

- 선택한 Event에 실제로 적혀 있는 사실
- Event끼리 서로 영향을 키우거나 줄이는 관계
- LNG 시장에 영향을 전달하는 Model Impact Lever
- 아직 결과가 정해지지 않은 핵심 질문

이 정보를 이용해 Dimension 3~6개와 Scenario 3~5개를 만든다. v2와 v3는 이전 생성 방식을 비교하거나 과거
데이터를 확인할 때만 사용한다. 새로운 기능이나 품질 개선은 v4를 기준으로 이해하면 된다.

## 사용자는 단계별로 무엇을 보나요?

### 1. 생성 중

Scenario 생성은 시간이 오래 걸릴 수 있다. 화면은 다음과 같은 진행 상황을 순서대로 받는다.

- 요청을 접수했음
- Event를 분석하고 있음
- 미래를 나눌 Dimension을 설계하고 있음
- Scenario를 만들고 있음
- 결과를 저장하고 있음
- 생성이 완료되었거나 실패했음

화면 연결이 잠시 끊겨도 서버의 생성 작업은 계속될 수 있다. 화면은 작업 번호를 이용해 현재 상태를 다시
확인하고, 놓친 진행 메시지를 이어서 받을 수 있다.

### 2. 생성 완료 후

사용자는 다음 내용을 본다.

- 선택한 Event와 주요 영향 분석
- Scenario를 나누는 Dimension과 선택값
- Scenario별 제목, 설명, 확률, Baseline 여부
- Scenario별 JKM 가격 압력과 판단 근거
- 대표 Scenario를 선택한 이유

Agent는 처음 선택하지 않은 질문을 Additional Dimension 후보로 제안할 수도 있다. 사용자는 필요할 때 이
후보를 Scenario 표에 추가하고 다시 Validation을 실행한다.

### 3. 수정과 Validation

사용자는 Scenario 제목이나 Dimension 값 조합을 수정하거나 Scenario를 추가·삭제할 수 있다. Validation은
수정 결과가 다음 단계로 진행 가능한지 알려 준다.

| 결과 | 사용자 의미 |
| --- | --- |
| 통과 | Signpost 생성으로 진행 가능 |
| 경고와 함께 통과 | 경고를 읽고 그대로 진행하거나 다시 수정 가능 |
| 차단 | 표시된 문제를 수정한 뒤 다시 검사해야 함 |

### 4. Signpost와 최종 확정

Validation을 통과하면 Agent가 각 Scenario의 Signpost를 만든다. 사용자가 Scenario와 Signpost를 최종 확인한
뒤 Confirmation을 실행하면 전체 작업이 완료된다.

## 진행 상태를 읽는 법

시스템 내부에는 현재 단계를 나타내는 영문 값이 저장된다.

| 시스템 값 | 사람이 이해할 의미 |
| --- | --- |
| `ready` | 생성 시작 전 준비 상태 |
| `scenario_created` | Scenario 생성 완료 또는 Validation 수정 필요 |
| `scenario_validated` | Validation 통과 |
| `signpost_created` | Signpost 생성 완료 |
| `completed` | 사용자가 최종 확정함 |

`scenario_created`는 생성 성공 뒤에도, Validation에서 차단된 뒤에도 나타날 수 있다. 따라서 상태값만 보지
말고 Validation 결과의 설명을 함께 확인한다.

## 개발 문서에서 자주 나오는 기술 용어

| 용어 | 쉬운 설명 |
| --- | --- |
| API | 화면이나 다른 시스템이 Agent에게 일을 요청하는 통로 |
| endpoint | API 통로 하나의 주소와 기능 |
| canonical API | 같은 목적의 API가 여러 개일 때 현재 표준으로 사용하는 API |
| SSE | 서버가 긴 작업의 진행 메시지를 같은 연결로 계속 보내는 방식 |
| callback | Agent 작업이 끝난 뒤 다른 시스템에 최종 결과를 다시 보내는 요청 |
| operation | 생성·검증 같은 긴 작업 한 번을 추적하기 위한 실행 기록 |
| Presentation | DB 내용을 화면에서 바로 쓰기 좋은 모양으로 정리한 조회 결과 |
| sync API | 개발·테스트를 위해 요청 하나에서 작업 완료까지 기다리는 API |

현재 표준 생성 API는 `POST /scenario-groups`다. 문서에서 `canonical 생성 API`라고 쓰면 이 주소를 뜻한다.
처음 읽을 때는 주소를 외울 필요 없이 `화면에서 실제 Scenario 생성을 요청할 때 쓰는 현재 표준 통로`라고
이해하면 된다.

## 더 자세히 알고 싶다면

| 궁금한 것 | 다음 문서 |
| --- | --- |
| 화면이나 다른 시스템이 무엇을 보내고 받는지 | [API Spec](02_SCENARIO_GROUP_AGENT_API_SPEC.md) |
| Agent가 내부적으로 어떤 순서로 생각하고 저장하는지 | [v4 Flow](03_SCENARIO_GROUP_AGENT_FLOW.md) |
| 어떤 DB table에 무엇이 저장되는지 | [DB Spec](04_SCENARIO_GROUP_AGENT_DB_SPEC.md) |
| 자연어로 테스트를 요청하고 결과를 읽는 방법 | [테스트와 품질 평가](05_SCENARIO_GROUP_AGENT_TEST_AND_QUALITY.md) |
| Scenario 이전 Event의 사실·미래 예상·기관 View·상충 전망을 어떻게 나누고 어떤 대상·기간·수치 근거를 보존할지 | [Event 구조화 → Model Parameter 증적 가이드](06_EVENT_STRUCTURING_FOR_MODEL_PARAMETER.md) |
| 공통 프로젝트 폴더와 코드 배치 원칙 | [Project Directory Structure](../../architectures/project_directory_structure.md) |

## 코드를 맡은 사람이 처음 볼 위치

개념을 이해한 뒤 실제 코드를 찾을 때는 다음 순서가 가장 빠르다.

1. `main.py`: Scenario Group Agent 서버가 시작되는 곳
2. `apps/agents/scenario_group_agent/api.py`: 사용하는 API 묶음을 등록하는 곳
3. `apps/agents/scenario_group_agent/routers/`: API 요청을 받는 곳
4. `apps/agents/scenario_group_agent/flows/`: 생성, Validation, Signpost의 처리 순서
5. `apps/agents/scenario_group_agent/prompts/`: AI 모델에 전달하는 지시문
6. `apps/agents/scenario_group_agent/persistence/`: Scenario 업무에 필요한 DB 처리를 묶은 곳
7. `apps/persistence/`: 실제 DB table과 조회 코드

코드를 변경하기 전에는 [AGENTS.md](../../../AGENTS.md)와
[Python conventions](../../../.claude/rules/python-conventions.md)를 함께 확인한다.
