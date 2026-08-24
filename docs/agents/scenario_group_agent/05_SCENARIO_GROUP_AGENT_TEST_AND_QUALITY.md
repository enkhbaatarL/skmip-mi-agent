# Scenario Group Agent 테스트와 품질 평가

## 두 종류의 검증

API가 성공했다고 Scenario 품질까지 좋은 것은 아니다. 테스트를 다음 두 층으로 나눈다.

```text
scenario-sync-pipeline
  → API 실행, 상태 전이, callback/SSE, 시간, JSON·SQLite 증적
  → scenario-quality-eval
      → 내용 품질, Validation 검사력, MLflow 원인 진단
```

| 목적 | 사용 Skill | 정본 |
| --- | --- | --- |
| API pipeline 실행과 증적 생성 | `scenario-sync-pipeline` | [SKILL.md](../../../.claude/skills/scenario-sync-pipeline/SKILL.md) |
| 생성 결과의 품질 평가 | `scenario-quality-eval` | [SKILL.md](../../../.claude/skills/scenario-quality-eval/SKILL.md) |

이 문서는 자주 쓰는 선택 기준만 설명한다. option, 판정, 보고서 형식이 달라지면 각 `SKILL.md`를 우선한다.

## 1. Scenario Sync Pipeline

### 실행 모드 선택

| 요청 | 실행기·모드 | 범위 |
| --- | --- | --- |
| 단일 Event 전체 흐름 | `test_sync_pipeline_api.py` | create→validation→signpost→confirmation |
| 여러 Event를 한 Group으로 전체 흐름 | SSE runner + follow-up body builder | 한 번의 multi-event create→validation→signpost→confirmation |
| canonical create 화면 계약 | `test_sse_scenario_group_api.py` | SSE create + Presentation |
| v4 create만 독립 검증 | `test_multi_event_scenario_versions.py --v4-only` | v4 sync create와 report |
| v2/v3/v4 비교 | version comparison mode | create 결과·성능·선택적 품질 비교 |

`--recent-events N`은 N개의 단일 Event pipeline이다. 여러 Event를 한 `miEventIds` 배열로 보내는 테스트와
혼동하지 않는다.

### 사전 조건

- local 또는 demo Agent API에 연결할 수 있어야 한다.
- 유효한 `userId`가 필요하다.
- 기존 Group soft delete가 필요하면 `SCENARIO_GROUP_ADMIN_TOKEN`을 준비한다.
- token은 `--admin-token`의 환경변수 참조, process 환경, `envs/.env` 순으로 찾는다.
- token 값, `.env` 내용, MLflow 비밀번호를 terminal output이나 report에 노출하지 않는다.
- soft delete에 token이 필요한데 없으면 중단한다. 임의로 `--no-delete-existing`으로 바꾸지 않는다.
- create POST는 멱등하지 않으므로 timeout·stream 오류 뒤 동일 요청을 자동 재시도하지 않는다.

### 단일 Event 전체 pipeline

```bash
python tests/manual/test_sync_pipeline_api.py \
  --base-url http://localhost:8001 \
  --mi-event-id 12345 \
  --user-id 10603 \
  --timeout 1200 \
  --yes
```

기존 Group을 정리해야 하면 `--delete-existing --admin-token "$SCENARIO_GROUP_ADMIN_TOKEN"`을 추가한다.
Event Type별 대표 1건은 `--all-event-types --events-per-type 1`, 최신 N개의 개별 실행은
`--recent-events N`을 사용한다.

단계별 기본 판정은 다음과 같다.

- create callback: `result=success`
- Validation: `stage=scenario_validated`; invalid 결과는 별도 warning
- Signpost callback: `result=success`
- Confirmation: `status=success`, `data.stage=completed`

산출물은 `local/output/sync_pipeline_api_test/<batch_id>/`, 누적 지표는
`local/output/sync_pipeline_api_test/sync_pipeline_metrics.sqlite3`에 남는다.

### Multi-Event 전체 pipeline

여러 Event를 한 Scenario Group으로 테스트할 때 create는 정확히 한 번 호출한다.

```bash
python tests/manual/test_sse_scenario_group_api.py \
  --base-url http://localhost:8000 \
  --event-count 3 \
  --event-sort latest \
  --user-id 10603 \
  --admin-token "$SCENARIO_GROUP_ADMIN_TOKEN" \
  --timeout 1200
```

create 성공 후 같은 `scenarioGroupId`에만 다음 순서를 적용한다.

1. `tests/manual/build_request_bodies_from_group.py`로 Validation body 생성
2. `POST /scenario-groups/{id}/validation/sync`
3. `POST /scenario-groups/{id}/signposts/sync`
4. Group을 다시 조회해 Confirmation body 생성
5. `POST /scenario-groups/{id}/confirmation`
6. 최종 Group에서 모든 Event 연결과 `stage=completed` 확인

요청·응답은 create batch의 `follow_up/`에 저장한다.

### canonical SSE·Presentation

```bash
python tests/manual/test_sse_scenario_group_api.py \
  --agent mi-vm \
  --event-ids 1463 1464 1433 \
  --user-id 10603 \
  --admin-token "$SCENARIO_GROUP_ADMIN_TOKEN" \
  --timeout 1200
```

검사 항목은 다음과 같다.

- SSE headers, 첫 `accepted`, sequence 연속성과 event/data 일치
- keep-alive 제외, `retrying` non-terminal 처리
- `completed|failed|interrupted` terminal 처리
- `section_ready` revision에 따른 Presentation 조회
- 최종 v4 engine, 세 section ready, Dimension 3~6개, Scenario 3~5개
- ETag와 conditional GET 304

산출물은 `local/output/sse_scenario_group_api_test/<batch_id>/`에 있다. 핵심 파일은
`sse_events.json`, `presentations/presentation_final.json`, `result.json`, `report.md`다.

### v4-only create

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

v4-only manifest는 다른 version 실행을 거부한다. 이 모드는 Validation·Signpost·Confirmation을 실행하지 않는다.
비교가 필요하면 기존 manifest를 바꾸지 말고 새 batch를 만든다.

## 2. Scenario Quality Eval

기본 입력은 `scenario-sync-pipeline`이 만든 `local/output/sync_pipeline_api_test/<batch_id>/`의 성공 run이다.
pipeline 실패 run은 품질 실패와 섞지 않고 별도 집계한다. Event detail이 없으면 Event grounding 검사를
임의로 통과시키지 않고 `SKIP`으로 기록한다.

### 평가 순서

1. 성공 pipeline run과 JSON·SQLite 증적 확인
2. Layer 1 결정적 규칙 검사
3. Layer 2 Agent Judge
4. 필요 시 Validation mutation probe
5. 접근 가능할 때만 MLflow trace 진단
6. SQLite 저장과 `quality_report.md` 생성
7. 원인별 `violation_plan_background.md` 생성

### Layer 1

코드로 재현 가능한 구조를 검사한다.

- callback 필수 필드와 table header/cell 정합성
- baseline 정확히 1개
- 빈 cell과 Template enum 근거
- Scenario 조합 중복과 개수
- Signpost 필수값, 방향·impact 범위, 공통 label 비율
- Validation `isValid`와 stage 정합성

의미 판단을 결정적 규칙으로 억지 판정하지 않고 Agent Judge로 넘긴다.

### Agent Judge

현재 skill을 실행 중인 모델이 `quality_judge_input.json`의 evidence와 schema만 사용해 평가한다. 별도 LLM
API, 앱 connector, `codex exec`, `claude` CLI를 호출하지 않는다.

```bash
./.venv/bin/python tests/manual/eval_scenario_quality.py \
  --batch-id <batch_id> \
  --prepare-judge-only
```

입력에 따라 `quality_judge.json`을 작성한 뒤 같은 batch를 최종 처리한다.

```bash
./.venv/bin/python tests/manual/eval_scenario_quality.py \
  --batch-id <batch_id>
```

평가 rubric은 Event grounding, baseline, Scenario spectrum, Dimension quality, 내부·시장 정합성,
Signpost 관련성·변별성·관측 가능성·인과 방향, 설명 명료성을 다룬다. 외부 사실이 필요한 항목은 hard fail이
아니라 `NEEDS_FACT`로 분리한다.

Layer 1과 성능만 필요하면 `--no-judge`를 사용한다. stability 검증은 `--stability-runs 2`로 두 번 평가하고
rubric verdict 일치율 80% 이상을 수용 기준으로 삼는다.

### Validation mutation probe

Validation 검사 자체의 유효성을 보려면 성공 create table에 결함을 하나씩 넣어 `/validation/sync`를 반복한다.

```bash
./.venv/bin/python tests/manual/eval_scenario_quality.py \
  --batch-id <batch_id> \
  --probe \
  --agent local \
  --user-id 10603 \
  --probe-mutations V-00,V-01,V-04,V-05,V-06,V-07,V-08,V-09
```

- V-00은 clean unchanged fast-path다.
- V-01·V-08은 조합·제목 중복 탐지를 본다.
- V-04는 narrative와 cell의 의미 모순을 본다.
- V-05는 optional/Additional Dimension autofill을 본다.
- V-06은 필수 입력 차단을 본다.
- V-07·V-09는 의미 보존 변경과 유사 제목의 false positive·warning을 본다.

### MLflow와 Golden Case

MLflow URI를 명시했을 때만 trace를 수집한다. trace 없음이나 접근 실패는 품질 FAIL이 아니라
infra/SKIP이다. trace에서 확인한 사실과 증적만 보고 추정한 책임 stage를 보고서에서 구분한다.

전문가 피드백은 `tests/manual/golden_cases/gc_<miEventId>_<slug>.md`에 등록하고 `--golden`으로 judge recall을
검토한다. 자동 키워드가 아니라 검토자가 matched/missed/extra를 기록한다.

### 결과물

| 파일·저장소 | 역할 |
| --- | --- |
| `quality_judge_input.json` | rubric, evidence, 출력 schema |
| `quality_judge.json` | Agent Judge 판정 |
| `quality_report.md` | 품질·성능·probe·trace 결과 |
| `violation_plan_background.md` | 원인과 수정 방향을 묶은 후속 plan 배경 |
| `sync_pipeline_metrics.sqlite3` | pipeline·quality·probe·golden 지표 |

평균 점수보다 violation의 대상, evidence, reason, suggested fix를 우선해서 읽는다.

## 3. 자동 테스트

변경 범위에 맞는 묶음을 선택한다.

```bash
./.venv/bin/pytest \
  tests/automated/test_scenario_group_agent_contract.py \
  tests/automated/test_scenario_group_pipeline_contract.py \
  tests/automated/test_v4_multi_event_model_lever_scenarios.py -q
```

| 변경 영역 | 주요 테스트 |
| --- | --- |
| SSE·operation·heartbeat | `test_scenario_group_operation_api.py`, `test_v4_operation_heartbeat.py` |
| Presentation | `test_scenario_group_presentation_api.py`, `test_sse_scenario_group_manual_runner.py` |
| Validation | `test_scenario_group_validation_review.py`, `test_v4_scenario_validation_change_set.py` |
| Additional Dimension | `test_additional_dimension_*` |
| Signpost | `test_v4_signpost_context.py`, `test_signpost_generation_subgraph.py` |
| Event relation·중복 | `test_scenario_group_event_relation_contract.py`, `test_scenario_group_event_set_conflict.py` |
| version 비교 report | `test_multi_event_scenario_comparison.py` |

## 최종 보고 체크리스트

- 어떤 실행 모드를 사용했는지 기록한다.
- 성공 건수와 실패 Event·단계·원인을 분리한다.
- soft delete, retry, timeout, 불명확한 create 상태를 기록한다.
- Markdown·JSON·SQLite 경로를 남긴다.
- 품질 평가를 생략했다면 API 성공이 품질 PASS를 뜻하지 않음을 명시한다.
- Layer 1, Judge, probe, trace, golden 중 실행하지 못한 계층과 사유를 기록한다.
- 비밀값을 보고서에 포함하지 않는다.
