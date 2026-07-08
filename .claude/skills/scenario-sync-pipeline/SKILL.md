---
name: scenario-sync-pipeline
description: MI Scenario Group Agent sync 파이프라인 테스트를 실행하고 분석한다. sync API를 순차 호출하거나, eventTypeL2Id별 GET /events 조회로 대상 miEventId를 수집하거나, 기존 scenario group을 soft delete 후 재시도하거나, SQLite 기반 성공/실패/수행시간 리포트를 만들어야 할 때 사용한다.
---

# Scenario Sync Pipeline

`tests/manual/test_sync_pipeline_api.py`를 표준 실행기로 사용한다. 이 스크립트는 sync 테스트 API를 순서대로 호출하고, 각 API 호출 시간을 SQLite에 저장한다. 성공률과 평균 수행시간 같은 통계는 LLM 추정이 아니라 SQLite/Python 계산 결과를 기준으로 보고한다.

권장 기본 실행은 `GET /events sort=latest` 기준 최근 N개 이벤트를 가져와 실행하는 방식이다. 최근 N개 실행에서는 이미 scenario group이 있거나 `scenarioActionState.type=disabled`여도 후보에서 제외하지 않는다. 기존 group이 있으면 먼저 soft delete하고, create 단계에서 중복 생성 오류가 나도 group을 다시 찾아 soft delete 후 1회 재시도한다.

## 사전 확인

- Agent API 서버가 실행 중이고 `--base-url`로 접근 가능한지 확인한다.
- 유효한 `--user-id`를 사용한다.
- 최근 N개 실행이나 기존 group 재시도가 필요한 실행에서는 `scenario_group_admin_bearer_tokens`에 등록된 bearer token을 `--admin-token`으로 전달한다.
- create/validation/signpost sync API는 HTTP 요청 안에서 graph를 끝까지 실행하므로 timeout을 길게 잡는다.

## 최근 N개 이벤트 실행

전체 이벤트 중 최신 N개를 선택해 create, validation, signpost, confirmation을 순서대로 실행한다. 이미 scenario group이 있는 이벤트는 soft delete 후 재생성한다. `scenarioActionState.type=disabled` 이벤트도 실행을 시도하지만, `scenarioSuggestYn=N`처럼 soft delete로 해결할 수 없는 경우에는 실패 reason으로 기록하고 다음 이벤트로 진행한다.

```bash
python tests/manual/test_sync_pipeline_api.py \
  --base-url http://localhost:8000 \
  --user-id 10001 \
  --recent-events 10 \
  --admin-token "$SCENARIO_GROUP_ADMIN_TOKEN" \
  --yes
```

`--recent-events N`은 `GET /events?sort=latest` 기준이며, N이 100을 넘으면 paging으로 수집한다. 선택된 이벤트 메타데이터는 `selected_events.json`으로 저장한다.

## 단건 실행

하나의 `miEventId`에 대해 create, validation, signpost, confirmation을 순서대로 실행한다.

```bash
python tests/manual/test_sync_pipeline_api.py \
  --base-url http://localhost:8000 \
  --mi-event-id 12345 \
  --user-id 10001 \
  --yes
```

`--yes`를 빼면 각 단계가 끝난 뒤 다음 API로 진행할지 사용자 입력을 받는다.

기존 scenario group이 생성되어 있어 create가 막힐 수 있으면 다음 옵션을 추가한다.

```bash
--delete-existing --admin-token "$SCENARIO_GROUP_ADMIN_TOKEN"
```

단건 실행에서도 create 단계에서 `SCENARIO_GROUP_ALREADY_CREATED` 또는 "이미" 계열 오류가 발생하면 group을 조회해 soft delete 후 1회 재시도한다.

## Event Type 전체 실행

`eventTypeL2Id` 1부터 21까지 순회한다. 기본값은 각 event type마다 related scenario group이 없고 disabled가 아닌 이벤트 1개를 선택한다.

```bash
python tests/manual/test_sync_pipeline_api.py \
  --base-url http://localhost:8000 \
  --user-id 10001 \
  --all-event-types \
  --events-per-type 1 \
  --yes
```

`--events-per-type 0`을 사용하면 `GET /events` paging으로 찾을 수 있는 eligible 이벤트를 전부 실행한다.

이미 scenario group이 있는 이벤트까지 의도적으로 재테스트할 때는 `--include-events-with-groups --admin-token "$SCENARIO_GROUP_ADMIN_TOKEN"`을 함께 사용한다. 선택된 이벤트에 related group이 있으면 실행기가 자동으로 soft delete 후 진행한다.

disabled 이벤트까지 포함하려면 `--include-disabled-events`를 추가한다. 단, disabled reason이 `scenarioSuggestYn=N`이면 create가 실패로 끝날 수 있다.

## 성공/실패 판정

- `create_scenarios`는 callback body의 `result=success`여야 한다. 이후 단계에서 `scenarioGroup`, `table`이 필요하므로 실패 시 해당 run은 실패로 기록한다.
- `validate_scenarios`는 `stage=scenario_validated`이면 통과로 본다.
- validation 결과가 `stage=scenario_created`, `isValid=false`, 또는 `result=failure`이면 reason을 warning으로 출력하고 signpost 단계로 계속 진행한다.
- `create_signposts`는 `result=success`여야 한다.
- `confirm_generation`은 common response의 `status=success`이고 `data.stage=completed`여야 한다.

## 결과물

실행기는 다음 결과를 남긴다.

- JSON 증적: `local/output/sync_pipeline_api_test/<batch_id>/`
  - 선택 이벤트 목록: `selected_events.json`
- SQLite 지표: 기본값 `local/output/sync_pipeline_api_test/sync_pipeline_metrics.sqlite3`
- 콘솔 요약: 전체 성공 건수, 실패 원인, soft delete/retry 건수, run별 수행시간, API별 평균/min/max 수행시간

사용자에게 결과를 보고할 때는 다음을 포함한다.

- 전체 시도 건수 대비 전체 파이프라인 성공 건수
- 실패한 `miEventId`, `eventTypeL2Id`, initial `actionState`, 실패 step, 실패 reason
- soft delete 수행 건수와 create retry 건수
- 눈에 띄게 느린 API 또는 특이한 수행시간
- 재현 가능한 후속 조회를 위한 SQLite 파일 경로
