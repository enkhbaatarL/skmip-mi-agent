# Scenario Group Agent Skill 사용 가이드

## 이 문서는 누구를 위한 문서인가요?

이 문서는 테스트 script의 옵션을 직접 외우려는 개발자가 아니라, Codex나 Claude에게 자연어로 Scenario
Agent 테스트를 요청하려는 Skill 사용자를 위한 문서다.

사용자는 원하는 대상과 범위를 말하면 된다. Skill이 적절한 script와 옵션을 선택하고, 실행 결과를 모아
보고서로 만든다.

```text
사용자가 자연어로 요청
  → Skill이 테스트 종류를 선택
  → API 실행과 증적 저장
  → 성공·실패 또는 품질 평가
  → 결과 요약과 보고서 경로 전달
```

## 어떤 Skill을 사용하나요?

### `scenario-sync-pipeline`

Scenario Agent API를 실제로 호출해 정상 동작하는지 확인한다.

다음과 같은 질문에 답한다.

- Scenario 생성부터 최종 확정까지 성공했는가?
- 여러 Event가 한 Scenario Group에 제대로 들어갔는가?
- 생성 진행 메시지와 화면 조회 결과가 올바른가?
- 어느 단계에서 실패했고 얼마나 오래 걸렸는가?
- v2, v3, v4 결과가 어떻게 다른가?

### `scenario-quality-eval`

이미 실행한 pipeline 결과를 읽고 Scenario 내용의 품질을 평가한다.

다음과 같은 질문에 답한다.

- Scenario가 원래 Event를 제대로 반영했는가?
- Baseline과 극단 Scenario가 타당한가?
- Dimension과 Scenario 조합이 중복되거나 모순되지 않는가?
- Signpost가 실제로 관찰 가능하고 Scenario를 구분하는가?
- Validation이 일부러 넣은 오류를 제대로 잡는가?
- 문제가 어느 생성 단계에서 생겼는가?

보통은 `scenario-sync-pipeline`으로 테스트 자료를 만든 뒤 `scenario-quality-eval`로 내용을 평가한다.

## 바로 복사해서 요청하는 Skill 프롬프트

아래 예시는 Codex 또는 Claude 대화창에 그대로 붙여 넣어 사용할 수 있다. `<...>` 부분만 실제 값으로
바꾼다. Skill 이름을 명시하면 어떤 작업을 원하는지 더 정확하게 전달할 수 있다.

### 단일 Event 전체 pipeline

```text
scenario-sync-pipeline Skill을 사용해 주세요.

- 실행 환경: <로컬 서버 또는 외부 demo VM>
- 대상 Event: <Event ID>
- 실행 범위: Scenario 생성 → Validation → Signpost 생성 → Confirmation
- 기존 Scenario Group: 있으면 삭제하고 다시 생성
- 결과에 포함할 내용: 단계별 성공 여부, 실패 원인, Scenario Group ID, 수행시간,
  JSON·Markdown 보고서와 SQLite 경로

한 단계가 실패해도 실행 가능한 다음 단계가 있다면 Skill 규칙에 따라 계속 확인하고,
실제로 확인한 증적만 보고해 주세요.
```

작성 예시:

```text
scenario-sync-pipeline Skill을 사용해서 외부 demo VM의 Event ID 12345를 Scenario 생성부터
Validation, Signpost 생성, Confirmation까지 전체 테스트해 주세요. 기존 Scenario Group이 있으면
삭제하고 다시 생성해 주세요. 단계별 성공 여부와 실패 원인, 수행시간, 결과 파일 경로를 알려 주세요.
```

### 최신 Event 여러 건을 각각 실행

```text
scenario-sync-pipeline Skill을 사용해 주세요.

외부 demo VM에서 최신 Event <개수>건을 선택하고, Event마다 별도의 Scenario Group을 만들어
Scenario 생성 → Validation → Signpost 생성 → Confirmation을 실행해 주세요.
기존 Scenario Group이 있으면 삭제하고 다시 생성해 주세요.

전체 성공·실패 건수, 실패한 Event ID와 단계별 원인, 삭제·재시도 횟수,
평균·최대 수행시간, 느린 API, batch 보고서와 SQLite 경로를 알려 주세요.
```

`Event마다 별도의 Scenario Group` 또는 `각각 실행`이라는 표현이 중요하다. 이 표현이 있어야 여러 Event를
한 Group으로 묶는 테스트와 혼동하지 않는다.

### 여러 Event를 한 Scenario Group으로 실행

```text
scenario-sync-pipeline Skill을 사용해 주세요.

- 실행 환경: <로컬 서버 또는 외부 demo VM>
- 대상 Event ID: <ID 1>, <ID 2>, <ID 3>
- 묶는 방법: 모든 Event를 한 번의 create 요청에 넣어 Scenario Group 1개 생성
- 실행 범위: SSE create와 Presentation 확인 → Validation → Signpost 생성 → Confirmation
- 기존 Scenario Group: 있으면 삭제하고 다시 생성

최종 Group에 입력한 Event가 모두 연결되었는지 확인해 주세요.
Scenario Group ID, operation ID, 진행 메시지의 최종 상태, 단계별 성공 여부와
follow_up 요청·응답 파일 경로를 알려 주세요.
```

작성 예시:

```text
scenario-sync-pipeline Skill을 사용해서 Event ID 1463, 1464, 1433을 한 번의 create 요청에 넣어
Scenario Group 하나로 만들어 주세요. SSE와 Presentation을 확인한 뒤 같은 Group에 Validation,
Signpost 생성, Confirmation까지 실행해 주세요. 세 Event가 최종 Group 하나에 모두 연결되었는지도
확인하고 결과 파일 경로를 알려 주세요.
```

### 화면용 생성 API만 확인

```text
scenario-sync-pipeline Skill을 사용해 주세요.

외부 demo VM에서 Event ID <ID 목록>으로 신규 v4 SSE create와 Presentation API만 테스트해 주세요.
Validation, Signpost, Confirmation은 실행하지 마세요.

SSE 진행 메시지 순서와 sequence, terminal 상태, Presentation revision,
최종 화면 데이터, ETag 304 동작, report.md와 JSON 결과 경로를 알려 주세요.
```

### v4 생성만 단독 실행

```text
scenario-sync-pipeline Skill을 사용해 주세요.

Event ID <ID 목록>으로 v4만 단독 실행해 주세요. v2와 v3는 실행하지 말고,
Validation, Signpost, Confirmation도 실행하지 마세요.
결정적 품질검사는 포함해 주세요.

실제 Dimension과 Scenario, 생성 성공 여부, 수행시간과 token 사용량,
품질검사 결과, manifest와 v4-only 보고서 경로를 알려 주세요.
```

### v2·v3·v4 비교

```text
scenario-sync-pipeline Skill을 사용해 주세요.

- 실행 환경: <로컬 서버 또는 외부 demo VM>
- Event 선택: <Event ID 목록 / 최신 N건 / 키워드와 개수>
- 비교 version: v2, v3, v4
- 품질검사: 포함
- Agent Judge: 포함

같은 Event 목록으로 각 version을 비교해 주세요. version별 실제 Dimension과 Scenario,
수행시간과 token, 결정적 검사와 Agent Judge 판정, version별 장단점,
모든 version 쌍의 비교를 보여 주세요. 마지막에는 품질 우선 추천과 비용·속도를 고려한
실용 추천을 나누고 comparison_report.md 경로를 알려 주세요.
```

작성 예시:

```text
scenario-sync-pipeline Skill을 사용해서 `호르무즈`가 포함된 최신 Event 3건으로 v2, v3, v4를
비교해 주세요. 품질검사와 Agent Judge를 포함하고, 품질 우선 추천과 비용·속도를 고려한
실용 추천을 따로 작성해 주세요.
```

### pipeline 실행 후 품질까지 연속 평가

```text
scenario-sync-pipeline Skill로 외부 demo VM의 Event ID <Event ID>를 Scenario 생성부터
Confirmation까지 전체 테스트해 주세요. pipeline이 끝나면 scenario-quality-eval Skill을 이어서
사용해 생성된 Scenario와 Signpost의 품질을 평가해 주세요.

Agent Judge를 포함하고 Validation mutation probe는 제외해 주세요.
pipeline 성공 여부와 품질 판정을 구분해서 설명하고, 주요 FAIL·WARN 근거,
quality_report.md, violation_plan_background.md, SQLite 경로를 알려 주세요.
```

### 이미 실행한 최신 batch 품질 평가

```text
scenario-quality-eval Skill을 사용해 주세요.

가장 최근에 성공한 Scenario pipeline batch를 대상으로 결정적 검사와 Agent Judge 품질 평가를
실행해 주세요. Validation mutation probe는 제외하고, MLflow trace는 접근 가능할 때만 분석해 주세요.

전체 PASS·WARN·FAIL·NEEDS_FACT 판정, 주요 위반 내용과 실제 근거, 수정 방향,
실행하지 못한 평가 계층과 이유, quality_report.md와 violation_plan_background.md 경로를 알려 주세요.
```

### 특정 batch의 Validation과 원인까지 평가

```text
scenario-quality-eval Skill을 사용해 batch ID `<batch_id>`를 평가해 주세요.

- 결정적 품질검사: 포함
- Agent Judge: 포함
- Validation mutation probe: V-00, V-01, V-04, V-05, V-06, V-07, V-08, V-09
- MLflow 원인 분석: trace가 있으면 포함

결함별 기대 결과와 실제 결과, Validation이 놓친 결함, false positive 후보,
Scenario·Signpost 주요 품질 문제, trace에서 확인한 원인과 증적만으로 추정한 원인을 구분해 주세요.
최종 보고서와 SQLite 경로도 알려 주세요.
```

### 프롬프트를 직접 만들 때의 기본 틀

```text
<사용할 Skill 이름>을 사용해 주세요.

- 어디에서: <로컬 / 외부 demo VM>
- 무엇을: <Event ID / 최신 N건 / 키워드 / batch ID>
- 어떻게 묶어서: <각각 별도 Group / 한 Group>
- 어디까지: <create만 / 화면 조회까지 / Confirmation까지 / 품질 평가까지>
- 기존 데이터: <삭제 후 재생성 / 보존>
- 추가 검사: <Agent Judge / mutation probe / MLflow / 없음>
- 받고 싶은 결과: <성공 여부 / 원인 / 수행시간 / 품질 문제 / 보고서 경로>
```

## 요청할 때 알려 주면 좋은 정보

아래 내용을 모두 알 필요는 없다. 알고 있는 것만 자연어로 적으면 되고, 실행에 꼭 필요한 정보가 없으면 Skill이
추가로 확인한다.

| 알려 줄 내용 | 예시 |
| --- | --- |
| 실행 환경 | 로컬 서버, 외부 demo VM |
| Event 선택 방법 | Event ID, 최신 3건, 오래된 5건, `호르무즈` 키워드 |
| Event를 묶는 방법 | 각각 따로 테스트, 여러 Event를 한 Group으로 생성 |
| 실행 범위 | 생성만, 생성과 화면 조회, 최종 확정까지 전체 흐름 |
| 품질 평가 | 포함, 제외, API 결과만 확인 |
| 기존 Group 처리 | 기존 Group 삭제 후 재생성, 기존 Group 보존 |
| 추가 진단 | Validation 오류 탐지, MLflow 원인 분석, Golden Case |

사용자 ID를 생략하면 Skill의 local 설정 또는 기본값을 사용한다. 실행 환경에서 그 ID를 사용할 수 없으면 Skill이
확인한다.

## 가장 중요한 요청 구분

복수 Event를 생성부터 Confirmation까지 테스트하라는 요청은 기본적으로 여러 Event를 한 Group으로
묶는 Multi-Event 전체 파이프라인으로 해석한다.

### Event 3건을 각각 따로 테스트

```text
Event A → Scenario Group A
Event B → Scenario Group B
Event C → Scenario Group C
```

Event별로 Group을 나눠야 한다면 `각각`, `개별`, `Event마다 별도 Group`을 명시한다.

> 외부 demo VM에서 최신 Event 3건을 각각 Scenario 생성부터 Validation, Signpost, Confirmation까지 테스트해줘.

### Event 3건을 한 Group으로 테스트

```text
Event A + Event B + Event C → Scenario Group 1개
```

다음처럼 명시할 수도 있지만, 생성부터 Confirmation까지의 복수 Event 요청에서는 생략해도 이 방식이
기본값이다.

> 외부 demo VM에서 최신 Event 3건을 한 번의 create 요청에 넣어 하나의 Scenario Group으로 만들고,
> Validation, Signpost, Confirmation까지 테스트해줘.

따라서 다음처럼만 요청해도 같은 방식으로 실행한다.

> 외부 demo VM에서 최신 Event 3건을 Scenario 생성부터 Confirmation까지 테스트해줘.

이 요청은 Event 3건을 한 `miEventIds` 배열로 보내 create를 한 번 호출하고, 생성된 같은 Group에
Validation, Signpost, Confirmation을 각각 한 번씩 호출한다. Event별 파이프라인 3회로 나누지 않는다.

## `scenario-sync-pipeline` 요청 예시

### 1. Event 하나의 전체 흐름 테스트

요청 예시:

> 로컬 Scenario Agent에서 Event ID 12345를 생성부터 Validation, Signpost, Confirmation까지 전체 테스트해줘.

Skill이 하는 일:

1. 지정한 Event로 Scenario Group을 생성한다.
2. 생성 결과를 Validation에 전달한다.
3. Validation 결과로 Signpost를 만든다.
4. Scenario와 Signpost를 최종 확정한다.
5. 단계별 요청·응답, 성공 여부, 수행시간을 저장한다.

사용자가 받는 결과:

- 어느 단계까지 성공했는지
- 실패한 단계와 서버 응답 이유
- 생성된 Scenario Group ID
- 단계별 JSON과 Markdown 보고서 경로
- API별 수행시간이 저장된 SQLite 경로

### 2. 최신 Event 여러 건을 각각 테스트

요청 예시:

> 외부 demo VM의 최신 Event 20건을 각각 전체 pipeline으로 테스트해줘. 기존 Scenario Group이 있으면 삭제하고
> 다시 생성해줘.

Skill이 하는 일:

- 최신 Event 20건을 고른다.
- Event마다 별도의 Scenario Group을 생성한다.
- 한 Event가 실패해도 가능한 다음 Event를 계속 실행한다.
- 기존 Group 삭제, 재시도, 실패 단계, 느린 API를 함께 기록한다.

사용자가 받는 결과:

- 전체 성공·실패 건수
- 실패한 Event ID와 단계별 원인
- 기존 Group 삭제와 재시도 횟수
- 평균·최대 수행시간과 느린 API
- batch 보고서와 SQLite 경로

### 3. Event Type별 대표 테스트

요청 예시:

> 로컬 서버에서 모든 Event Type L2마다 대표 Event 1건씩 전체 pipeline을 테스트해줘.

Skill이 하는 일:

- 조회 가능한 Event Type별로 대상 Event를 선택한다.
- 각 Event를 별도 전체 pipeline으로 실행한다.
- Event Type별 성공 여부를 비교할 수 있게 기록한다.

사용자가 받는 결과:

- 테스트된 Event Type과 Event 목록
- Event Type별 성공·실패 단계
- 누락되거나 실행할 수 없었던 Event Type과 이유
- 전체 보고서와 증적 경로

### 4. 여러 Event를 한 Group으로 전체 테스트

요청 예시:

> Event ID 1463, 1464, 1433을 한 Scenario Group으로 생성하고 Validation, Signpost, Confirmation까지
> 전체 테스트해줘.

Skill이 하는 일:

1. 세 Event를 한 번의 v4 생성 요청에 넣는다.
2. 진행 메시지와 화면 조회 결과를 확인한다.
3. 생성된 같은 Scenario Group에 Validation을 실행한다.
4. 같은 Group에 Signpost를 만들고 Confirmation까지 실행한다.
5. 세 Event가 최종 Group 하나에 모두 연결되었는지 확인한다.

사용자가 받는 결과:

- 입력 Event ID와 생성된 Scenario Group ID
- 생성 진행 메시지의 최종 상태
- Validation, Signpost, Confirmation 성공 여부
- 최종 Group의 상태와 Event 연결 확인 결과
- create batch의 `follow_up/`에 저장된 단계별 요청·응답

### 5. 생성 진행 화면만 테스트

요청 예시:

> 외부 demo VM에서 Event ID 1463, 1464, 1433으로 신규 v4 SSE create와 Presentation API만 테스트해줘.

Skill이 하는 일:

- 여러 Event를 한 번의 생성 요청에 넣는다.
- 접수, 분석, Dimension 설계, Scenario 생성, 완료 진행 메시지가 순서대로 오는지 검사한다.
- 생성 중 화면 데이터가 준비될 때마다 Presentation API를 조회한다.
- 연결 재사용용 sequence, 최종 화면 내용, ETag 캐시 동작을 확인한다.
- Validation, Signpost, Confirmation은 실행하지 않는다.

사용자가 받는 결과:

- Scenario Group ID와 operation ID
- 전체 진행 메시지 순서와 마지막 sequence
- 최종 성공·실패·중단 상태
- 화면 조회 횟수와 최종 Presentation
- `report.md`, `sse_events.json`, `presentation_final.json`, `result.json` 경로

### 6. 현재 v4 생성 결과만 확인

요청 예시:

> Event ID 101, 202로 v4 create만 단독 실행하고 품질검사도 포함해줘.

Skill이 하는 일:

- v2와 v3를 실행하지 않고 v4 생성만 실행한다.
- v4 결과의 구조와 결정적으로 확인 가능한 품질 조건을 검사한다.
- Validation, Signpost, Confirmation은 실행하지 않는다.
- 비교 대상이 없으므로 `가장 좋은 버전`은 선정하지 않는다.

사용자가 받는 결과:

- 입력 Event와 생성된 Scenario·Dimension 실제 값
- 생성 성공·실패와 시간·token 사용량
- v4 결정적 품질검사 결과
- v4-only report와 manifest 경로

### 7. v2·v3·v4 결과 비교

요청 예시:

> `호르무즈`가 포함된 최신 Event 3건으로 v2, v3, v4를 비교해줘. 품질검사와 Agent Judge를 포함해줘.

Skill이 하는 일:

1. 같은 Event 목록으로 v2, v3, v4를 순서대로 실행한다.
2. 다음 version 실행 전에 앞 version에서 만든 Group을 삭제한다.
3. version별 실제 Scenario, Dimension, 근거, 수행시간, token을 모은다.
4. 품질검사를 요청했다면 각 version을 평가하고 version 쌍을 직접 비교한다.
5. 품질 우선 추천과 비용·속도를 고려한 실용 추천을 나누어 작성한다.

사용자가 받는 결과:

- version별 성공·실패와 실제 Scenario 비교
- Dimension과 Scenario별 선택 근거
- 결정적 검사와 Agent Judge 점수
- version별 잘한 점과 아쉬운 점
- 모든 version 쌍의 비교와 최종 추천
- `comparison_report.md`와 관련 JSON 경로

품질검사 포함 여부를 요청에 쓰지 않으면 Skill이 실행 전에 확인한다.

## `scenario-quality-eval` 요청 예시

이 Skill은 이미 생성된 pipeline 증적을 입력으로 사용한다. 먼저 pipeline을 실행하지 않았다면 다음처럼 두 작업을
한 번에 요청할 수 있다.

> Event ID 12345 전체 pipeline을 실행한 뒤 Scenario와 Signpost 품질까지 평가해줘.

### 1. 방금 실행한 최신 batch 품질 평가

요청 예시:

> 가장 최근 Scenario pipeline batch의 품질을 평가해줘. Agent Judge를 포함하고 Validation mutation probe는
> 제외해줘.

Skill이 하는 일:

- 가장 최근의 올바른 batch를 찾는다.
- API pipeline 자체가 실패한 Event는 품질 대상에서 제외해 별도로 표시한다.
- 표 구조, Baseline, 중복 조합, Signpost 필수값 등을 코드로 검사한다.
- Event 반영, Scenario 다양성, Dimension 타당성, Signpost 품질을 Agent Judge가 평가한다.

사용자가 받는 결과:

- 전체 `PASS`, `WARN`, `FAIL`, `NEEDS_FACT` 판정
- 주요 품질 문제와 실제 근거
- 문제가 있는 Scenario·Signpost와 수정 방향
- `quality_report.md`와 품질 지표가 반영된 SQLite 경로
- 후속 개선 논의를 위한 `violation_plan_background.md`

### 2. 특정 batch 평가

요청 예시:

> batch ID `20260824_153000`의 Scenario 품질을 평가해줘. MLflow trace가 있으면 원인 단계도 분석해줘.

Skill이 하는 일:

- 지정한 batch만 평가한다.
- MLflow 설정과 trace가 있으면 문제를 create, Validation, Signpost 단계와 연결한다.
- trace가 없거나 접근할 수 없으면 품질 실패로 처리하지 않고 진단을 생략한 이유를 남긴다.

사용자가 받는 결과:

- batch 전체 품질 판정과 주요 위반 사항
- trace로 확인된 원인과 증적만 보고 추정한 원인의 구분
- 실행하지 못한 진단 계층과 이유
- 품질 보고서와 개선 배경 문서 경로

### 3. 빠른 구조 검사만 실행

요청 예시:

> 최신 batch는 Agent Judge 없이 결정적 품질검사와 성능 통계만 확인해줘.

Skill이 하는 일:

- 의미 판단을 위한 Agent Judge를 실행하지 않는다.
- table 구조, Baseline, 중복, 빈 값, Signpost 필드와 수행시간만 검사한다.

사용자가 받는 결과:

- 결정적 규칙의 PASS·WARN·FAIL
- API별 평균·최소·최대·p95 수행시간
- Agent Judge를 실행하지 않았다는 명시적인 안내

### 4. Validation이 오류를 잘 잡는지 테스트

요청 예시:

> batch ID `20260824_153000`으로 Validation mutation probe를 실행해줘. 중복 Scenario, 필수값 누락,
> 의미 충돌, 유사 제목을 모두 확인해줘.

Skill이 하는 일:

- 정상 Scenario table을 그대로 보내 빠른 통과가 되는지 확인한다.
- 한 번에 결함 하나씩을 넣어 Validation을 반복 호출한다.
- 중복 조합, 값 다양성 부족, 의미 모순, 필수 Dimension 누락, 중복·유사 제목 탐지 여부를 기록한다.

사용자가 받는 결과:

- 결함별 기대 결과와 실제 결과
- Validation이 잡은 결함과 놓친 결함
- 정상 입력을 잘못 경고한 false positive 후보
- mutation별 결과와 seeded-defect recall

### 5. Golden Case로 평가 기준 점검

요청 예시:

> 등록된 Golden Case로 Scenario Agent Judge의 recall을 평가해줘.

Skill이 하는 일:

- 전문가 피드백이 등록된 Event와 기존 Judge 결과를 나란히 보여준다.
- 검토자가 기록한 matched, missed, extra를 집계한다.
- 전문가가 지적한 문제를 Judge가 얼마나 찾았는지 계산한다.

사용자가 받는 결과:

- Golden Case별 전문가 지적과 Judge 판정
- matched·missed·extra와 recall
- 평가 기준에서 놓치고 있는 문제 유형

## 결과 파일은 어디에 생기나요?

사용자는 모든 파일을 직접 읽을 필요가 없다. Skill의 최종 답변에 핵심 결론과 중요한 경로가 함께 나온다.

### 전체 pipeline

```text
local/output/sync_pipeline_api_test/<batch_id>/
```

여기에는 선택 Event, 단계별 요청·응답, 실행 보고서가 들어간다. 여러 batch의 성공률과 수행시간은
`local/output/sync_pipeline_api_test/sync_pipeline_metrics.sqlite3`에 누적된다.

### SSE create와 Presentation

```text
local/output/sse_scenario_group_api_test/<batch_id>/
```

주요 파일은 다음과 같다.

- `report.md`: 사람이 읽는 실행 결과
- `sse_events.json`: 받은 진행 메시지 전체
- `presentations/presentation_final.json`: 최종 화면 데이터
- `result.json`: 성공 여부와 주요 ID

### v2·v3·v4 비교 또는 v4-only

```text
local/output/multi_event_scenario_comparison/<batch_id>/
```

주요 파일은 `manifest.json`, version별 create 응답, 삭제 결과, `comparison_report.md`다. 품질검사를 포함하면
Agent Judge 입력과 판정 JSON도 생성된다.

### 품질 평가

pipeline batch 안에 다음 파일이 추가된다.

- `quality_report.md`: 품질 점수보다 실제 문제와 근거를 중심으로 읽는 보고서
- `violation_plan_background.md`: 비슷한 원인과 수정 방향을 묶은 후속 개선 논의 자료
- `quality_judge_input.json`: Agent Judge가 읽은 조건과 증적
- `quality_judge.json`: Agent Judge의 구조화된 판정

## Skill이 사용자에게 다시 물을 수 있는 것

다음 정보가 결과를 크게 바꾸면 Skill이 실행 전에 확인한다.

- 복수 Event create-only 요청에서 v4 단독·버전 비교·SSE 화면 확인 중 범위가 불분명한 경우
- v2·v3·v4 비교에서 품질검사를 포함할지 정하지 않은 경우
- 실행 환경이나 Event 선택 조건이 없는 경우
- 기존 Group을 삭제해야 하지만 관리자 토큰을 찾지 못한 경우
- 품질 평가할 batch를 고를 수 없는 경우

MLflow trace가 없거나 접근할 수 없는 것은 전체 품질 평가를 막지 않는다. 해당 진단만 `SKIP` 또는 infra 문제로
보고한다.

## 요청할 때 주의할 점

### 같은 create를 자동 재시도하지 않기

Scenario Group 생성은 같은 요청을 다시 보내면 새 Group이 생길 수 있다. timeout이나 연결 오류가 난 뒤에는
다음처럼 요청한다.

> 방금 create가 timeout 났어. 같은 create를 다시 보내지 말고 operation과 DB 증적으로 실제 상태부터 확인해줘.

### 기존 Group 보존 여부를 분명히 하기

기존 데이터를 지우면 안 되는 테스트라면 요청에 명시한다.

> 기존 Scenario Group은 삭제하지 말고 테스트 가능한지 먼저 확인해줘.

기존 Group 삭제가 필요한 테스트에서는 관리자 토큰이 필요하다. Skill은 토큰 값을 출력하거나 보고서에 넣지
않는다.

### API 성공과 품질 성공을 구분하기

API가 모두 성공해도 Scenario 내용이 부실할 수 있다. 내용까지 확인하려면 다음처럼 말한다.

> 전체 pipeline 성공 여부뿐 아니라 Scenario와 Signpost 품질 평가도 포함해줘.

세부 실행 규칙의 정본은 [`scenario-sync-pipeline`](../../../.claude/skills/scenario-sync-pipeline/SKILL.md)과
[`scenario-quality-eval`](../../../.claude/skills/scenario-quality-eval/SKILL.md)이다.
