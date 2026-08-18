---
name: scenario-sync-pipeline
description: MI Scenario Group Agent API 파이프라인을 실행하고 증적과 보고서를 생성한다. 사용자가 기존·단일 이벤트 create→validation→signpost→confirmation 테스트, eventTypeL2Id별 또는 최근 이벤트 sync 테스트, 신규 Multi-Event SSE create·Presentation API 테스트, v4 단독 실행, v2/v3/v4 비교, multi-event·멀티 이벤트·멀티 시나리오 테스트, 이벤트 ID·최신/오래된 순·키워드 기반 이벤트 선택, 버전별 Scenario 품질 비교, comparison_report.md 생성·형식 수정을 요청할 때 사용한다.
---

# Scenario Sync Pipeline

요청을 먼저 `기존 전체 파이프라인`, `신규 Multi-Event SSE·Presentation`,
`Multi-Event v4 단독 실행`, `Multi-Event 버전 비교` 중 하나로 분류한다. 네 흐름을 섞지 않는다.

## 요청 라우팅

- 사용자가 기존 API, 단일 이벤트, 최근 이벤트 sync, event type별 테스트를 요청하면 **기존 전체 파이프라인**을 실행한다.
- 사용자가 `SSE create`, `POST /scenario-groups`, `Presentation API`, `section_ready`,
  신규 업무 API 테스트를 요청하면 **신규 Multi-Event SSE·Presentation**을 실행한다.
- 사용자가 `v4 only`, `v4 단독`, `v4만 실행`을 요청하면 **Multi-Event v4 단독 실행**을 실행한다.
- 사용자가 `v2/v3/v4 비교`, 둘 이상의 version 비교, `multi-event`, 멀티 이벤트, 멀티 시나리오를 요청하면 **Multi-Event 버전 비교**를 실행한다.
- version이나 multi-event 의도가 불분명하면 어떤 흐름인지 확인한다.

## 관리자 토큰 로딩

기존 Scenario Group을 soft delete하는 실행에서는 다음 우선순위로
`SCENARIO_GROUP_ADMIN_TOKEN`을 사용한다.

1. 명령행 `--admin-token`으로 전달된 환경변수 참조
2. 현재 프로세스의 `SCENARIO_GROUP_ADMIN_TOKEN`
3. 프로젝트 `envs/.env`의 `SCENARIO_GROUP_ADMIN_TOKEN`

`envs/.env`를 사용할 때는 값을 출력하지 말고 프로세스 환경에 로드한 뒤 실행기가
환경변수를 읽게 한다. 토큰 존재 여부만 `set`/`unset`으로 확인하고, 파일 내용이나
토큰 값을 로그·명령 결과·보고서에 노출하지 않는다. 예:

```bash
set -a
source envs/.env
set +a
python tests/manual/test_multi_event_scenario_versions.py prepare ...
```

soft delete가 필요한데 세 위치에서 토큰을 찾지 못하면 실행을 중단하고 사용자에게
알린다. 이 경우 `--no-delete-existing`으로 임의 전환하지 않는다. 사용자가 기존 그룹
보존을 명시적으로 요청한 경우에만 `--no-delete-existing`을 사용한다.

## 기존 전체 파이프라인

`tests/manual/test_sync_pipeline_api.py`를 사용한다. unversioned create API부터 validation, signpost, confirmation까지 기존 순서로 실행한다. v2/v3/v4 비교 실행기를 사용하지 않는다.

### 사전 확인

- Agent API 서버와 `--base-url` 연결을 확인한다.
  - local: `http://localhost:8001`
  - public demo VM: `http://40.82.137.178:8001`
- 유효한 `--user-id`를 사용한다.
- 최근 N개 실행이나 기존 group 재생성에는 `SCENARIO_GROUP_ADMIN_TOKEN` 또는 `--admin-token`을 준비한다.
- sync API가 요청 안에서 graph를 완료하므로 긴 timeout을 사용한다.
- `.claude/skills/scenario-quality-eval/test_info.local`의 `agent`, `user_id`를 공통 기본값으로 사용한다. 명령행 `--agent`, `--base-url`, `--user-id`를 우선한다.

### 실행

최근 N개를 테스트하려면 다음처럼 실행한다.

```bash
python tests/manual/test_sync_pipeline_api.py \
  --agent mi-vm \
  --user-id 10603 \
  --recent-events 20 \
  --admin-token "$SCENARIO_GROUP_ADMIN_TOKEN" \
  --timeout 1200 \
  --yes
```

`--recent-events N`은 `GET /events?sort=latest`로 선택하고 N이 100을 넘으면 paging한다. 기존 group이나 disabled 상태인 이벤트도 후보에서 제외하지 않는다. 기존 group은 먼저 soft delete한다. `scenarioSuggestYn=N`처럼 soft delete로 해소되지 않는 실패는 원인을 기록하고 다음 이벤트로 진행한다.

단일 이벤트를 테스트하려면 다음처럼 실행한다.

```bash
python tests/manual/test_sync_pipeline_api.py \
  --base-url http://localhost:8001 \
  --mi-event-id 12345 \
  --user-id 10001 \
  --yes
```

기존 Scenario Group 때문에 create가 막히면 `--delete-existing --admin-token "$SCENARIO_GROUP_ADMIN_TOKEN"`을 추가한다. create에서 중복 생성 오류가 발생하면 실행기가 group을 soft delete하고 한 번 재시도하도록 둔다.

전체 Event Type을 테스트하려면 다음처럼 실행한다.

```bash
python tests/manual/test_sync_pipeline_api.py \
  --base-url http://localhost:8001 \
  --user-id 10001 \
  --all-event-types \
  --events-per-type 1 \
  --yes
```

`--events-per-type 0`은 조회 가능한 eligible 이벤트를 모두 실행한다. 기존 group이 있는 이벤트까지 포함하려면 `--include-events-with-groups`와 admin token을 사용한다. disabled 이벤트도 포함하려면 `--include-disabled-events`를 사용한다.

### 판정과 보고

- `create_scenarios`: callback body의 `result=success`를 요구한다.
- `validate_scenarios`: `stage=scenario_validated`를 통과로 본다. invalid 결과도 warning으로 기록하고 signpost를 계속 실행한다.
- `create_signposts`: `result=success`를 요구한다.
- `confirm_generation`: common response의 `status=success`, `data.stage=completed`를 요구한다.
- SQLite/Python 계산을 성공률과 수행시간의 기준으로 사용하고 LLM으로 수치를 추정하지 않는다.

결과를 다음 위치에서 확인한다.

- JSON 및 Markdown: `local/output/sync_pipeline_api_test/<batch_id>/`
- 지표: `local/output/sync_pipeline_api_test/sync_pipeline_metrics.sqlite3`

최종 보고에 성공 건수, 실패 이벤트와 단계·원인, soft delete/retry 수, 느린 API, SQLite와 Markdown 경로를 포함한다.

## 신규 Multi-Event SSE·Presentation

`tests/manual/test_sse_scenario_group_api.py`를 사용한다. canonical
`POST /scenario-groups`의 SSE stream과
`GET /scenario-groups/{scenarioGroupId}/presentation?operationId=...`를 함께 검증한다.
validation/signpost/confirmation이나 v2/v3/v4 sync endpoint를 호출하지 않는다.

### 실행

Event 선택, 관리자 토큰 로딩, 기존 활성 Scenario Group soft delete 정책은
Multi-Event 버전 비교와 동일하다. 명시 ID 또는 최신·오래된 순·키워드 선택 중 하나만 사용한다.

```bash
python tests/manual/test_sse_scenario_group_api.py \
  --agent mi-vm \
  --event-ids 1463 1464 1433 \
  --user-id 10603 \
  --admin-token "$SCENARIO_GROUP_ADMIN_TOKEN" \
  --timeout 1200
```

```bash
python tests/manual/test_sse_scenario_group_api.py \
  --base-url http://localhost:8000 \
  --event-count 3 \
  --event-sort latest \
  --keyword 호르무즈 \
  --user-id 10603 \
  --admin-token "$SCENARIO_GROUP_ADMIN_TOKEN" \
  --timeout 1200
```

기존 그룹을 보존해야 한다고 사용자가 명시한 경우에만 `--no-delete-existing`을 사용한다.
create POST는 멱등하지 않으므로 timeout이나 stream 오류 뒤 동일 POST를 자동 재시도하지 않는다.
실행 실패 시 남은 `scenarioGroupId`, `operationId`, 마지막 sequence를 보고해 operation polling이나
`Last-Event-ID` 재연결로 서버 상태를 별도 확인할 수 있게 한다.

### SSE 판정

- HTTP 200, `Content-Type: text/event-stream`, `Cache-Control: no-cache`,
  `X-Accel-Buffering: no`를 요구한다.
- 첫 업무 event는 `accepted`, 첫 sequence는 1이어야 한다.
- SSE `id`, JSON `sequence`, `event`/`eventType` 일치와 sequence 연속 증가를 요구한다.
- 모든 event의 `scenarioGroupId`, `operationId`가 `accepted`와 같아야 한다.
- keep-alive comment는 업무 event와 sequence에서 제외한다.
- `retrying`은 실패로 처리하지 않는다.
- `completed`, `failed`, `interrupted`만 terminal로 처리하며 성공 판정은
  `completed.status=succeeded`만 허용한다.
- `section_ready`의 `snapshotRevision`이 마지막으로 조회한 Presentation revision보다 커질 때 조회한다.
- `completed`에서는 revision 중복 여부와 무관하게 최종 Presentation API를 다시 조회한다.

### Presentation 판정

- SSE 식별자와 Presentation의 `scenarioGroupId`, `operation.operationId`가 같아야 한다.
- `schemaVersion=v1`, `engineVersion=v4`와 `eventAnalysis`, `scenarioDesign`,
  `roleSelectionRationale` 세 section을 요구한다.
- 조회를 유발한 SSE보다 `operation.latestSequence`, `snapshotRevision`이 뒤처지지 않아야 한다.
- 최종 조회는 operation과 모든 하위 section이 성공/`ready`여야 한다.
- 최종 v4 결과는 Dimension 3~6개, 각 Dimension `rationale` 10~200자,
  Scenario row 3~5개를 요구한다.
- 모든 Presentation 200 응답에 `ETag`가 있어야 하고, 같은 URL과 ETag의
  conditional GET이 body 없는 HTTP 304와 동일 ETag를 반환해야 한다.

### 결과물

`local/output/sse_scenario_group_api_test/<batch_id>/`에서 다음을 확인한다.

- `selected_events.json`
- `existing_groups_soft_delete.json`
- `sse_events.json`
- `presentations/presentation_revision_<revision>_sequence_<sequence>.json`
- `presentations/presentation_final.json`
- `presentation_requests.json`
- `result.json`
- `report.md`

최종 보고에 Event IDs, Scenario Group/operation ID, terminal event, 마지막 sequence와
snapshot revision, SSE event 순서, Presentation 조회 횟수와 ETag 304 판정, 실패 원인,
JSON·Markdown 경로를 포함한다.

## Multi-Event v4 단독 실행

`tests/manual/test_multi_event_scenario_versions.py`를 `prepare --v4-only`,
`run-version --version v4`, `report` 순서로 실행한다. create API만 실행하고 validation,
signpost, confirmation은 실행하지 않는다. v2/v3를 먼저 실행하지 않으며 별도 subagent도
필요하지 않다.

중복 없는 Event 1~5개 선택, 관리자 토큰 로딩, 기존 활성 Scenario Group soft delete,
timeout 및 동일 POST 재시도 금지 정책은 Multi-Event 버전 비교와 동일하다. 기존 그룹을
보존하려면 명시적으로 `--no-delete-existing`을 사용한다.

```bash
python tests/manual/test_multi_event_scenario_versions.py prepare \
  --v4-only \
  --agent mi-vm \
  --event-ids 101 202 \
  --admin-token "$SCENARIO_GROUP_ADMIN_TOKEN" \
  --user-id 10603 \
  --timeout 1200

python tests/manual/test_multi_event_scenario_versions.py run-version \
  --manifest <manifest.json> \
  --version v4 \
  --timeout 1200

python tests/manual/test_multi_event_scenario_versions.py report \
  --manifest <manifest.json> \
  --quality-check true
```

`--v4-only` manifest는 `versions=["v4"]`, `executionMode="v4-only"`를 고정한다.
이 manifest에서는 v2/v3 실행을 거부하며 v4는 다른 version 산출물 없이 독립 실행한다.
나중에 v2/v3/v4 비교가 필요하면 기존 manifest를 재사용하지 말고 새 `prepare` batch를 만든다.
v4-only의 생성 Group은 자동 삭제하지 않는다. 버전별 생성 직후 soft delete는
v2/v3/v4 비교 manifest에만 적용한다.

`--quality-check true`는 v4 결정적 품질검사를 실행하지만 비교 대상이 없으므로 Agent Judge
순위, 우수 version, 품질·실용 추천은 만들지 않는다. `false`이면 API 결과와 실제 Scenario
보고서만 생성한다.

## Multi-Event v2/v3/v4 비교

`tests/manual/test_multi_event_scenario_versions.py`를 `prepare`, `orchestrate`, `report` 단계로 실행한다.
create API만 비교하고 validation, signpost, confirmation은 실행하지 않는다. 비교 실행은
`v2 생성 → v2 Group soft delete → v3 생성 → v3 Group soft delete → v4 생성 → v4 Group soft delete`
순서를 고정한다.

### 품질검사 여부 확인

실행 전에 사용 가능한 사용자 입력 도구로 품질검사를 포함할지 묻고 응답을 받는다. 다음 선택지를 제시한다.

- `품질검사 포함 (Recommended)`: `true`
- `API 결과만`: `false`
- 사용자가 이미 포함/제외를 명시했으면 다시 묻지 않는다.
- 입력 도구가 자동 기본값 처리를 지원하면 `true`를 기본값으로 설정한다.

`true`이면 결정적 검사와 Agent Judge를 실행하고 버전별 점수·판정·우수 버전을 보고한다. Agent Judge는 이 skill을 실행 중인 Codex 또는 Claude 모델이 직접 수행한다. 별도 LLM API, 앱 LLM connector, `codex exec`, `claude` CLI를 호출하지 않는다. `false`이면 실제 API 결과와 Scenario 비교 보고서만 만들고 Judge, 품질 점수, 버전 순위, 우수 버전 판정을 생략한다.

### 로컬 서버

로컬 서버는 기존 Gunicorn과 UvicornWorker 설정으로 실행할 수 있다.

```bash
poetry run dotenv -f envs/.env run --no-override -- \
  gunicorn main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 3 \
  --bind 127.0.0.1:8000 \
  --timeout 1200 \
  --graceful-timeout 1200
```

Docker의 기존 Gunicorn 3-worker 기본 설정은 변경하지 않는다. 기존 전체 파이프라인 순차 테스트에는 Uvicorn 로컬 실행도 허용한다.

### 이벤트 선택과 prepare

중복 없는 이벤트 1~5개를 선택한다. 다음 선택법 중 하나만 사용한다.

- 명시 ID: `--event-ids 101 202`
- 최신 또는 오래된 N개: `--event-count 3 --event-sort latest|oldest`
- 키워드 기반 N개: `--event-count 5 --keyword 호르무즈 [--event-sort latest|oldest]`

키워드 선택의 기본 정렬은 `latest`로 둔다. 이벤트 상세를 수집하고 동일한 이벤트 목록과 `userId`, 로컬 `runId`를 manifest에 고정한다. `runId`는 API나 DB에 전달하지 않고 로컬 산출물을 묶는 용도로만 사용한다. v4도 단일 `targetMarket`을 입력받지 않으며 모든 Scenario의 pressure band는 글로벌 LNG 기준이다. 지역 가격 허브 관련성이 명확한 v4 Scenario만 응답 row의 `relatedMarkets`에 시장과 근거를 선택적 보조정보로 포함한다.

선택된 이벤트에 연결된 기존 활성 Scenario Group은 버전 실행 전에 기본적으로 모두 soft delete한다. 기존 그룹을 보존해야 하는 예외적인 실행에만 `prepare --no-delete-existing`을 사용한다. 활성 그룹이 있으면 `--admin-token` 또는 `SCENARIO_GROUP_ADMIN_TOKEN`이 필요하다. 실행기는 이벤트별 `GET /scenario-groups?includeDeleted=false&miEventId=...` 결과에서 그룹 ID를 중복 제거하고, 각 그룹을 `DELETE /scenario-groups/{scenarioGroupId}`로 한 번씩 삭제한다. 사전 삭제 결과는 manifest의 `preRunCleanup`과 `existing_groups_soft_delete.json`에 기록한다.

비교 중에는 성공한 각 version 응답의 정확한 `data.scenarioGroup.scenarioGroupId`만 즉시 soft delete한다.
삭제 전에 create 응답 JSON을 먼저 저장하고, 삭제 응답은 `<version>_soft_delete.json`과
create artifact의 `postRunCleanup`에 함께 저장한다. 관리자 토큰이 없으면 비멱등 create POST를
호출하기 전에 중단한다. `prepare --no-delete-existing`은 사전 그룹 보존만 뜻하며 이번 비교가
새로 생성한 v2/v3/v4 Group의 사후 삭제를 끄지 않는다.

예:

```bash
python tests/manual/test_multi_event_scenario_versions.py prepare \
  --agent mi-vm \
  --event-count 5 \
  --keyword 호르무즈 \
  --event-sort latest \
  --admin-token "$SCENARIO_GROUP_ADMIN_TOKEN" \
  --user-id 10603 \
  --timeout 1200
```

prepare가 출력한 batch/manifest 경로를 이후 실행 단계에 동일하게 전달한다.

### 버전 실행 순서

1. v2 `run-version`으로 생성하고 성공 응답의 Group을 즉시 soft delete한다.
2. v2 삭제 성공을 확인한 뒤 v3를 생성하고 즉시 soft delete한다.
3. v3 삭제 성공을 확인한 뒤 v4를 생성하고 즉시 soft delete한다.
4. v4 삭제 성공을 확인하고 세 create 응답을 모아 `report`를 실행한다.

```bash
python tests/manual/test_multi_event_scenario_versions.py run-version \
  --manifest <manifest.json> \
  --version v2 \
  --admin-token "$SCENARIO_GROUP_ADMIN_TOKEN" \
  --timeout 1200
```

비교 manifest의 `run-version`은 성공한 create 뒤 soft delete까지 한 단계로 수행한다. 수동 실행도
반드시 v2 명령 완료와 삭제 성공을 확인한 뒤 v3, 그 뒤 v4 순으로 호출한다.

한 명령으로 실행할 때는 다음 순차 orchestration을 사용한다. 일반 create 실패는 기록하고
다음 version을 계속 실행할 수 있지만, create 결과가 불명확하거나 성공한 Group의 삭제가 실패하면
활성 서버 상태를 남길 수 있으므로 뒤 version을 실행하지 않는다.

```bash
python tests/manual/test_multi_event_scenario_versions.py orchestrate \
  --manifest <manifest.json> \
  --admin-token "$SCENARIO_GROUP_ADMIN_TOKEN" \
  --timeout 1200
```

동일 version POST를 자동 재시도하지 않는다. create API는 멱등하지 않으므로 timeout 뒤 재호출하면 중복 Scenario Group이 생길 수 있다. timeout은 결과 불명으로 기록하고 API/DB 증적 확인이 필요하다고 보고한다. 이미 완료된 version의 create·soft delete 증적은 보존한다.

### Agent Judge와 보고서 생성

품질검사 선택이 `true`이면 먼저 결정적 검사와 Agent Judge 입력을 생성한다.

```bash
python tests/manual/test_multi_event_scenario_versions.py report \
  --manifest <manifest.json> \
  --quality-check true \
  --prepare-judge-only
```

명령이 출력한 `comparison_judge_input.json`을 직접 읽고 그 안의 `constraints`, `criteria`, `outputSchema`, `evidence`만 근거로 평가한다. 현재 skill을 실행 중인 모델이 모든 성공 version과 Scenario를 직접 판정하고, `outputSchema`에 맞는 JSON을 manifest의 `artifacts.judge` 경로인 `comparison_judge.json`에 작성한다. 의미 판정을 Python 규칙으로 대체하거나 별도 모델에 위임하지 않는다.

Judge JSON을 작성한 뒤 같은 보고 명령을 다시 실행해 schema, version·criterion·Scenario 집합, 평균 최고 version을 검증하고 최종 Markdown을 만든다. (markdown 파일은 markdown 문법에 충실)

```bash
python tests/manual/test_multi_event_scenario_versions.py report \
  --manifest <manifest.json> \
  --quality-check true
```

검증에 실패하면 `comparison_judge.json`을 근거 없이 부분 수정하지 말고 오류와 입력 schema를 대조해 전체 판정을 바로잡은 뒤 다시 실행한다.

품질검사 선택이 `false`이면 Agent Judge 준비 단계 없이 한 번만 실행한다.

```bash
python tests/manual/test_multi_event_scenario_versions.py report \
  --manifest <manifest.json> \
  --quality-check false
```

`true`일 때 실제 이벤트와 API 응답만 근거로 다음을 검사한다.

- 이벤트 사실과 Scenario·dimension의 무모순성
- LNG 가격 예측 요소의 dimension 반영
- 글로벌 LNG 기준 floor/ceiling의 pressure band 및 조합 타당성
- mixed의 필요성과 상승·하락 요인 조합 타당성
- Scenario 3~5개, baseline 정확히 1개, floor/ceiling 각각 1개, mixed 선택, 조합·band 중복 없음
- dimension 수 v2/v3/v4 각각 3~6개와 전체 이벤트 lineage coverage

Agent Judge는 먼저 각 기준을 1~5점과 PASS/WARN/FAIL로 절대평가한다. 이 점수는 version별 품질 조건 충족 여부를 확인하는 용도이며 최종 상대평가 승자를 자동 결정하지 않는다. Scenario별 실제 title, narrative, cells, role, probability와 API rationale를 근거로 판단한다. 기준 단순 평균 최고 version은 `절대 점수 최고 버전`으로 별도 표시한다.

`generationDiagnostics.coverageStatus=partial|none`, `unsupportedLevers`,
`unsupportedLeverDetails`는 현재 활성 모델 파라미터 catalog의 제한을 나타내는
**비채점 capability warning**으로 취급한다. 향후 파라미터 확장을 전제로 생성한
Scenario·Dimension의 품질 결함을 뜻하지 않으므로, 이 정보만으로 절대 점수,
criterion verdict, pairwise 승자, `bestVersions`, 품질·실용 추천을 낮추지 않는다.
보고서의 version별 아쉬운 점이나 추천 tradeoff에는 현재 실행 제약으로 명시한다.
`parameterMappingReady=true`도 full coverage를 뜻한다고 해석하지 않는다.

단, 다음처럼 coverage 상태와 별개로 확인되는 실제 품질 결함은 해당 기준에서 평가한다.

- 선택 Event의 driver나 lineage가 Dimension에 반영되지 않음
- Dimension·Value·Scenario 인과가 모순되거나 중복됨
- 비활성·미지원 레버를 현재 실행 가능하다고 잘못 표기함
- coverage 관련 API 필드가 서로 모순되거나 필요한 진단 정보가 누락됨

성공한 모든 version 쌍을 직접 비교한다. v2/v3/v4가 모두 성공하면 `v2 vs v3`, `v2 vs v4`, `v3 vs v4`를 각각 한 번 평가한다. 각 pair에서 다음 기준별 승자 또는 동률, 실제 evidence, 반론, 최종 rationale를 작성한다.

- Event grounding과 사실·가정 구분
- Dimension 및 Value의 독립성·유용성
- Scenario 인과 논리와 설명 가능성
- Baseline 및 제외 Scenario의 타당성
- 사용자가 결과만 읽고 납득할 수 있는 명료성

각 version의 실제 잘한 점과 아쉬운 점을 함께 작성한다. 최종 결론은 `품질 우선 추천`과 `비용·속도 포함 실용 추천`을 분리하고, 선택 조건과 tradeoff를 명시한다. 품질 우선 추천은 pairwise evidence를 우선하며 latency/token은 품질 차이가 없을 때만 보조 판단으로 사용한다. 실용 추천은 Agent Judge 입력의 실제 elapsedMs와 totalTokens를 함께 사용한다. 성공 version이 2개 미만이면 비교 결론을 `판정 불가`로 표시한다.

`false`일 때도 이벤트와 실행 결과, Scenario Group, dimension, Scenario 실제 값, API rationale를 version별로 비교한다.

### `comparison_report.md` 고정 형식

보고서 생성기는 `tests/manual/multi_event_comparison/report.py`, 회귀 테스트는
`tests/automated/test_multi_event_scenario_comparison.py`를 사용한다. 성공한 각
version의 Scenario 비교에는 다음을 반드시 포함한다.

- Scenario Group의 제목, 요약, 설명을 구분해 표시한다.
- 기존 `Dimension | 설명 | Event lineage | Values` 표 다음에 `시나리오별 Dimension Value` 표를 만든다.
- `시나리오별 Dimension Value` 열 순서는 반드시 `Scenario ID · 레이블 | scenario_role | pressure_band | <Dimension labels...>`로 유지한다.
- `scenario_role`은 row의 `scenarioRole` 또는 `scenario_role` 값을 사용한다. `pressure_band`는 `globalPressureBand` 또는 `global_pressure_band` 값을 사용한다. 필드가 없거나 값이 `null`이면 `-`로 표시한다.
- Scenario 표의 dimension 헤더와 cell 값에는 내부 `dimensionId`/`valueId` 대신 `dimensionDefinitions[].label`과 `values[].label`을 사용한다. 같은 dimension label이 중복되면 `Event <lineage>`를 붙여 구분한다.
- 각 Scenario 아래에 `Dimension | Dimension 선택 근거 | 선택 Value | Value 선택 근거` 표를 만든다. Scenario의 narrative와 `globalPressureRationale`도 조합/가격 판단 근거로 함께 표시한다.
- version별 실제 응답 필드 차이를 보존한다. Dimension 근거는 `selectionRationale`, `rationale`, `sourceRefs[].rationale` 순으로 사용하고, Value 근거는 선택된 value의 `sourceAssignments[].rationale`, `globalPressureContribution` 순으로 사용한다. 응답에 근거가 없으면 없다고 명시하며 추정하거나 새 근거를 만들지 않는다.
- pressure band별 기존 `Cells` 열도 같은 label 변환을 적용해 내부 ID가 사용자용 비교 값으로 노출되지 않게 한다.

결정적 품질검사에 FAIL이 있으면 검사 표 바로 아래에 `FAIL 항목 상세 설명`을
추가한다. FAIL마다 다음 네 항목을 반드시 포함한다.

- 검사 목적: M-01~M-08이 무엇을 검사하는지 사용자 언어로 설명한다.
- 확인된 실제 문제: `detail`과 `offenders`를 풀어 쓰고 원문만 반복하지 않는다.
- 영향: Scenario 비교나 운영 해석에 어떤 문제가 생기는지 설명한다.
- 수정 방향: 수정할 payload/lineage/role/rationale 방향을 구체적으로 안내한다.

M-06 FAIL의 offender가 Event ID이면 해당 Event가 어떤 Dimension의
`sourceEventIds`, `sourceRefs`, `sourceAssignments`에도 연결되지 않아 그 Event의
driver가 Scenario cell 조합에 직접 반영되지 않았다는 의미를 명시한다.

보고서 형식을 수정한 뒤 다음을 검증한다.

```bash
./.venv/bin/pytest tests/automated/test_multi_event_scenario_comparison.py -q
./.venv/bin/ruff check \
  tests/manual/multi_event_comparison/report.py \
  tests/automated/test_multi_event_scenario_comparison.py
./.venv/bin/ruff format --check \
  tests/manual/multi_event_comparison/report.py \
  tests/automated/test_multi_event_scenario_comparison.py
```

기존 batch 보고서만 갱신할 때는 `run-version`을 다시 호출하지 않는다. 기존
`manifest.json`, API response artifact, Judge JSON을 재사용해 `report`만 실행하고,
생성된 Markdown에서 고정 열과 FAIL 상세 설명을 직접 확인한다.

### 결과물

`local/output/multi_event_scenario_comparison/<batch_id>/`에서 다음을 확인한다.

- `manifest.json`
- `selected_events.json`
- `existing_groups_soft_delete.json`
- `v2_create_response.json`
- `v2_soft_delete.json`
- `v3_create_response.json`
- `v3_soft_delete.json`
- `v4_create_response.json`
- `v4_soft_delete.json`
- `orchestration.json`
- `comparison_judge_input.json` (`quality-check=true`일 때)
- `comparison_judge.json` (`quality-check=true`일 때만)
- `comparison_report.md`

v4-only batch에는 v2/v3 response artifact와 Agent Judge artifact가 생성되지 않는다.

보고서에 입력 조건과 이벤트 상세, version별 성공/실패·그룹 ID·시간·token usage,
각 생성 Group의 soft delete 결과, Scenario Group 제목·요약·설명, dimension 비교,
label 기반 Scenario×dimension value 표, Scenario별 dimension/value 선택 근거, 글로벌 pressure band별
Scenario 실제 값과 API 판단 근거를 포함한다. v4 row에 `relatedMarkets`가 있으면 시장별 근거를
보조정보로 표시하되 방향·강도 tag로 해석하지 않는다. 품질검사 시 절대 점수, version별 잘한 점·아쉬운 점,
모든 version pair의 직접 비교와 반론, 품질 우선 추천, 비용·속도 포함 실용 추천을 포함한다.
