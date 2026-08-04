---
name: scenario-sync-pipeline
description: MI Scenario Group Agent API 파이프라인을 실행하고 증적과 보고서를 생성한다. 사용자가 v1·기존·단일 이벤트 create→validation→signpost→confirmation 테스트, eventTypeL2Id별 또는 최근 이벤트 sync 테스트, v2/v3/v4 비교, multi-event·멀티 이벤트·멀티 시나리오 테스트, 이벤트 ID·최신/오래된 순·키워드 기반 이벤트 선택, 버전별 Scenario 품질 비교를 요청할 때 사용한다.
---

# Scenario Sync Pipeline

요청을 먼저 `v1 기존 파이프라인`과 `Multi-Event 버전 비교` 중 하나로 분류한다. 두 흐름을 섞지 않는다.

## 요청 라우팅

- 사용자가 `v1`, 기존 API, 단일 이벤트, 최근 이벤트 sync, event type별 테스트를 요청하면 **v1 기존 파이프라인**을 실행한다.
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

## v1 기존 파이프라인

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

## Multi-Event v2/v3/v4 비교

`tests/manual/test_multi_event_scenario_versions.py`를 `prepare`, `run-version`, `report` 단계로 실행한다. create API만 비교하고 validation, signpost, confirmation을 실행하지 않는다.

### 품질검사 여부 확인

실행 전에 사용 가능한 사용자 입력 도구로 품질검사를 포함할지 묻고 응답을 받는다. 다음 선택지를 제시한다.

- `품질검사 포함 (Recommended)`: `true`
- `API 결과만`: `false`
- 사용자가 이미 포함/제외를 명시했으면 다시 묻지 않는다.
- 입력 도구가 자동 기본값 처리를 지원하면 `true`를 기본값으로 설정한다.

`true`이면 결정적 검사와 Agent Judge를 실행하고 버전별 점수·판정·우수 버전을 보고한다. Agent Judge는 이 skill을 실행 중인 Codex 또는 Claude 모델이 직접 수행한다. 별도 LLM API, 앱 LLM connector, `codex exec`, `claude` CLI를 호출하지 않는다. `false`이면 실제 API 결과와 Scenario 비교 보고서만 만들고 Judge, 품질 점수, 버전 순위, 우수 버전 판정을 생략한다.

### 로컬 서버

병렬 요청을 처리하도록 로컬 서버를 Gunicorn과 UvicornWorker 3개로 실행한다.

```bash
poetry run dotenv -f envs/.env run --no-override -- \
  gunicorn main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 3 \
  --bind 127.0.0.1:8000 \
  --timeout 1200 \
  --graceful-timeout 1200
```

Docker의 기존 Gunicorn 3-worker 기본 설정은 변경하지 않는다. v1 순차 테스트에는 기존 Uvicorn 로컬 실행도 허용한다.

### 이벤트 선택과 prepare

중복 없는 이벤트 2~5개를 선택한다. 다음 선택법 중 하나만 사용한다.

- 명시 ID: `--event-ids 101 202`
- 최신 또는 오래된 N개: `--event-count 3 --event-sort latest|oldest`
- 키워드 기반 N개: `--event-count 5 --keyword 호르무즈 [--event-sort latest|oldest]`

키워드 선택의 기본 정렬은 `latest`로 둔다. 이벤트 상세를 수집하고 동일한 이벤트 목록, `userId`, 고유 `comparisonRunId`를 manifest에 고정한다. v4도 단일 `targetMarket`을 입력받지 않으며 모든 Scenario의 pressure band는 글로벌 LNG 기준이다. 지역 가격 허브 관련성이 명확한 v4 Scenario만 응답 row의 `relatedMarkets`에 시장과 근거를 선택적 보조정보로 포함한다.

선택된 이벤트에 연결된 기존 활성 Scenario Group은 버전 실행 전에 기본적으로 모두 soft delete한다. 기존 그룹을 보존해야 하는 예외적인 실행에만 `prepare --no-delete-existing`을 사용한다. 활성 그룹이 있으면 `--admin-token` 또는 `SCENARIO_GROUP_ADMIN_TOKEN`이 필요하다. 실행기는 이벤트별 `GET /scenario-groups?includeDeleted=false&miEventId=...` 결과에서 그룹 ID를 중복 제거하고, 각 그룹을 `DELETE /scenario-groups/{scenarioGroupId}`로 한 번씩 삭제한다. 삭제는 v2/v3/v4 실행 전에 한 번만 수행하며, v2나 v3가 이번 비교에서 새로 만든 그룹을 뒤 버전 실행 전에 삭제하지 않는다. 삭제 결과는 manifest의 `preRunCleanup`과 `existing_groups_soft_delete.json`에 기록한다.

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

prepare가 출력한 batch/manifest 경로를 이후 모든 subagent에 동일하게 전달한다.

### 버전 실행 순서

1. v2 `run-version`과 v3 `run-version`을 서로 다른 subagent 두 개에서 동시에 실행한다.
2. 두 subagent가 모두 종료될 때까지 기다린다.
3. v4 `run-version`을 subagent에서 실행한다.
4. 세 결과를 모아 `report`를 실행한다.

각 subagent는 manifest를 읽고 지정된 version 하나만 실행한다.

```bash
python tests/manual/test_multi_event_scenario_versions.py run-version \
  --manifest <manifest.json> \
  --version v2
```

v4까지 완전 병렬로 실행하지 않는다. v4가 먼저 저장되면 Template checksum이 없는 v4 lineage를 v2/v3가 읽어 동일 `comparisonRunId` 검증과 충돌할 수 있다. v2와 v3는 동일 Event·Template revision을 사용하므로 둘만 병렬 실행한다.

subagent 기능을 사용할 수 없을 때만 다음 fallback을 사용한다. 실행기는
`asyncio.gather(v2, v3)` 완료 후 v4를 호출하고 fallback 사용 사실을 보고서에 기록한다.

```bash
python tests/manual/test_multi_event_scenario_versions.py orchestrate \
  --manifest <manifest.json> \
  --timeout 1200
```

동일 version POST를 자동 재시도하지 않는다. DB에 `(comparisonRunId, apiVersion)` unique 제약이 없으므로 timeout 뒤 재호출하면 중복 Scenario Group이 생길 수 있다. timeout은 결과 불명으로 기록하고 API/DB 증적 확인이 필요하다고 보고한다. 한 version이 실패해도 나머지 version의 결과를 보존한다.

### Agent Judge와 보고서 생성

품질검사 선택이 `true`이면 먼저 결정적 검사와 Agent Judge 입력을 생성한다.

```bash
python tests/manual/test_multi_event_scenario_versions.py report \
  --manifest <manifest.json> \
  --quality-check true \
  --prepare-judge-only
```

명령이 출력한 `comparison_judge_input.json`을 직접 읽고 그 안의 `constraints`, `criteria`, `outputSchema`, `evidence`만 근거로 평가한다. 현재 skill을 실행 중인 모델이 모든 성공 version과 Scenario를 직접 판정하고, `outputSchema`에 맞는 JSON을 manifest의 `artifacts.judge` 경로인 `comparison_judge.json`에 작성한다. 의미 판정을 Python 규칙으로 대체하거나 별도 모델에 위임하지 않는다.

Judge JSON을 작성한 뒤 같은 보고 명령을 다시 실행해 schema, version·criterion·Scenario 집합, 평균 최고 version을 검증하고 최종 Markdown을 만든다.

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
- Scenario 3~5개, baseline 정확히 1개, floor/ceiling 각각 1개, mixed 최소 1개, 조합·band 중복 없음
- dimension 수 v2/v3/v4 각각 3~6개와 전체 이벤트 lineage coverage

Agent Judge는 각 기준을 1~5점과 PASS/WARN/FAIL로 평가한다. Scenario별 실제 title, narrative, cells, role, probability와 API rationale를 근거로 판단한다. 기준 단순 평균 최고 version을 우수 버전으로 정하고 동점은 공동 우수로 표시한다. 성공 version이 2개 미만이면 비교 결론을 `판정 불가`로 표시한다.

`false`일 때도 이벤트와 실행 결과, Scenario Group, dimension, Scenario 실제 값, API rationale를 version별로 비교한다.

### 결과물

`local/output/multi_event_scenario_comparison/<batch_id>/`에서 다음을 확인한다.

- `manifest.json`
- `selected_events.json`
- `existing_groups_soft_delete.json`
- `v2_create_response.json`
- `v3_create_response.json`
- `v4_create_response.json`
- `comparison_judge_input.json` (`quality-check=true`일 때)
- `comparison_judge.json` (`quality-check=true`일 때만)
- `comparison_report.md`

보고서에 입력 조건과 이벤트 상세, version별 성공/실패·그룹 ID·시간·token usage, Scenario Group/dimension 비교, 글로벌 pressure band별 Scenario 실제 값과 API 판단 근거를 포함한다. v4 row에 `relatedMarkets`가 있으면 시장별 근거를 보조정보로 표시하되 방향·강도 tag로 해석하지 않는다. 품질검사 시 Agent Judge 근거·점수·위반 사항·우수 version과 선정 이유도 포함한다.
