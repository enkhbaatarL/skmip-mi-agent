---
name: model-parameter-multi-event-quality
description: MI Model Parameter Agent의 Scenario API v4 multi_event_model_lever_dimensions 그룹을 동적으로 발견하고 ordered Event, catalog version/checksum, selected Lever state와 hydrated parameter binding, runtime allowlist 경계, proposal/confirmation persistence를 통합 평가한다. v4 멀티 이벤트 품질 테스트, catalog-pinned Lever 검증, active-but-blocked leakage 진단, active parameter coverage 및 동일 Scenario Before/After coverage 개선 campaign 요청에 사용한다.
---

# Model Parameter v4 Multi-Event Quality

Scenario API v4의 선택 Dimension/Lever lineage를 active impact Lever catalog와 대조하고, 운영 matcher와 runtime allowlist 경계를 거친 실제 Model Parameter proposal flow를 평가한다. 기본 실행은 DB read-only discovery다. `--execute`는 사용자가 실제 DB write를 승인한 경우에만 사용한다.

## 필수 참조

작업 전에 다음을 읽는다.

1. `references/quality-matrix.md`: v4 판정 기준과 보고서 증적 계약
2. `tests/manual/model_parameter_agent/runner_common.py`: 공유 proposal/confirmation 실행·DB read-back 계약
3. release acceptance가 범위에 있으면 `.claude/skills/verify-model-parameter-release/SKILL.md`
4. 동일 Scenario Before/After 또는 coverage 확대 campaign이면
   `references/same-cohort-coverage-campaign.md`

공통 workflow나 release 검증 절차를 이 skill에 복제하지 않는다.

## 실행 전제조건

- runner와 automated test는 같은 Python 환경을 사용한다.
- `envs/.env`와 `APP_CONFIG`가 현재 환경에 유효해야 한다.
- discovery DB에 read 권한이 있고 v4 group/scenario/group-event, active impact Lever/master, proposal schema가 적용되어 있어야 한다.
- proposal `mi_event_id`는 nullable이어야 한다.
- 적합한 실제 v4 scenario가 없으면 결함이 아니라 `COVERAGE LIMIT`이다.
- `--execute`에는 사용자의 명시적 write 승인, 고정된 Basecase/LUT release, LLM 자격, proposal/confirmation write 권한이 필요하다.
- runtime은 승인·승격된 `resources/`만 사용하며 staging 경로인 `new_resources/`를 자동 로드하지 않는다. staging LUT가 없는 것은 정상이고, 파일이 있으면 release 식별과 승격 검증 전 live execute를 금지한다.
- 이 skill은 canonical master, impact Lever catalog, Basecase/LUT, config, workbook, DB schema를 수정하지 않는다.

운영 proposal 경계는 코드의 `MODEL_PARAMETER_PROPOSAL_ALLOWLIST`를 source of truth로 사용한다. runner에 이름 목록을 복제하지 않는다. active master에 있으나 allowlist 밖인 parameter는 `active-but-blocked`로 유지하고, `PROPOSAL_SCOPE_EXCLUDED` 증적과 함께 LLM 이전에 제외한다.

## 실행 절차

### 1. Read-only discovery

```bash
poetry run python tests/manual/model_parameter_agent/evaluate_multi_event_quality.py
```

명시 범위는 둘 중 하나만 지정한다.

```bash
poetry run python tests/manual/model_parameter_agent/evaluate_multi_event_quality.py --scenario-group-id 123
poetry run python tests/manual/model_parameter_agent/evaluate_multi_event_quality.py --scenario-id 456
```

runner는 다음을 검증한다.

- 필수 테이블/컬럼과 proposal `mi_event_id` nullable 계약
- `api_version=v4`, `generation_strategy=multi_event_model_lever_dimensions` 대상만 discovery
- exact `display_order=1..N`으로 정렬된 1~5개 Event, 중복 및 Dimension `source_event_ids` membership
- scenario group에 저장된 impact catalog version/checksum과 active catalog의 정확한 일치
- 선택 Dimension의 primary Lever code/ID/flag, `lever_states` code/ID/domain과 active catalog의 hydrated `parameter_bindings` 일치
- active master 기반 운영 v4 matcher의 raw 후보와 운영 partition 함수의 `runtime-allowed | active-but-blocked` 분리
- raw/runtime/blocked key 고유성과 disjoint/union 불변식, graph v4 raw trace의 key·canonical target 일치, Step1.5 target별 단일 canonical task와 non-empty merged lineage
- active parameter별 `raw → runtime → selected → proposed → confirmed` matrix

v3 `sourceRefs`, legacy `(event_type_l2_id, dimKey)` mapping, projection 상태는 v4 판정 근거로 사용하지 않는다.

### 2. Discovery gate

- schema, ordered Event, catalog pin, selected Lever/binding lineage 오류는 `FAIL`이며 실행을 막는다.
- 명시한 scenario/group이 v4 대상이 아니거나 없으면 `FAIL`이다.
- 자동 discovery에서 대상이 없으면 `COVERAGE LIMIT`이다.
- `runtime-allowed` raw 후보가 없는 scenario는 정상적으로 실행을 건너뛰고 coverage 한계로 기록한다.
- `active-but-blocked` 후보 자체는 오류가 아니다. runtime/selected/proposed/confirmed 누출 또는 exact reason 누락이 오류다.

### 3. Write 실행

```bash
poetry run python tests/manual/model_parameter_agent/evaluate_multi_event_quality.py \
  --scenario-group-id 123 \
  --execute
```

`--execute`는 먼저 다음 DB/LLM 독립 smoke gate를 실행한다.

```bash
python -m pytest -q -m model_parameter_core \
  tests/automated/test_model_parameter_agent_contract.py \
  tests/automated/test_model_parameter_multi_event_quality.py \
  tests/automated/test_model_parameter_runner_common.py
```

`--execute`는 반드시 `--scenario-id` 또는 `--scenario-group-id`로 write 범위를 명시해야 하며, 미지정 시 DB preflight 전에 `FAIL`한다. smoke 실패 시 proposal/confirmation을 하나도 실행하지 않고 `FAIL`한다. 통과하면 `runner_common.execute_proposal_and_confirmation()`을 scenario마다 정확히 한 번 호출한다. 자동 retry 옵션은 제공하지 않는다. 실패 후 재실행이 필요하면 기존 proposal ID와 실패 증적을 먼저 보존하고 사용자가 별도 실행한다.

v4 persistence의 authoritative link는 `scenario_group_id`이며 API `eventId=null`, DB `mi_event_id=NULL`이어야 한다. empty payload rollback, valid confirmation, reconfirmation, payload 보존은 공유 workflow 결과를 그대로 판정한다.

### 4. 보고서와 CLI 결과

기본 보고서는 `tests/reports/model_parameter_agent/model_parameter_v4_multi_event_quality_<timestamp_microseconds>.md`에 생성된다. `--report-path`를 지정할 수 있다. runner는 DB 작업 전에 보고서 파일을 exclusive-create하며, 같은 경로가 이미 있으면 기존 파일을 덮어쓰지 않고 중단한다.

보고서 필수 항목:

- schema와 `model_parameter_core` gate
- ordered Event와 stored→active catalog version/checksum
- selected Dimension별 source Event, Lever code/ID/direction/domain, hydrated binding
- active parameter boundary matrix와 blocked exact reason
- proposal/API/DB/confirmation 연결, partial proposal ID/failed stage, elapsed/token/retry 관측성
- execution error와 review/coverage limit

CLI exit는 mandatory `FAIL`만 1이다. `PASS`, `REVIEW`, `COVERAGE LIMIT`는 0이다.

### 5. Proposal-only uncovered campaign

Confirmation 없이 proposal row만 제한 실행해야 하면 quality runner의 `--execute`를 사용하지 않고 별도
uncovered-only runner를 사용한다. 기본은 read-only이며 capability release와 Group 또는 Scenario 범위를
명시한다.

```bash
python tests/manual/model_parameter_agent/run_proposal_only.py \
  --scenario-group-id 123 \
  --capability-release v4-proposal-capability-v1
```

명시적인 proposal write 승인 후에만 같은 명령에 `--execute`를 추가한다. 이 runner는 비삭제 proposal 전체
이력에서 `PROPOSED`/`CONFIRMED` Scenario를 skip하고, `PROCESSING`이 하나라도 있으면 campaign 전체를
hard-stop한다. lifecycle/capability skip Scenario도 history guard 범위에서 제외하지 않는다. `FAILED` 이력만
있거나 이력이 없는 실행 가능 Scenario만 대상으로 하며 write 직전에 resource/context/catalog/input fingerprint와
proposal history를 다시 판정한다. `v4-proposal-capability-v1`은 0030 full checksum, 기존 5종 allow-list와
`new-bc-v1` contract SHA, semantic schema와 실제 resource content fingerprint를 묶은 고정 계약이다. 각 write
직전에는 현재 Scenario뿐 아니라 명시 cohort 전체의 in-flight 상태를 다시 확인한다. Confirmation, callback,
outer retry와 uncovered guard 우회는 제공하지 않는다.

read-only는 resource runtime을 bootstrap하지 않는다. `--execute`는 Scenario DB 조회 전에 resource runtime을
고정하고 실제 파일 hash와 등록된 source/schema/fingerprint를 증적한 뒤 0030 proposal schema를 검사한다. graph가
사용한 context는 persistence 직전에 frozen preflight context와 다시 비교한다. execute 증적의 runtime/schema가
미등록이거나 승인된 release contract와 다르면 fail-closed한다. DB uniqueness가 도입되기 전 write pilot은 같은
cohort에 대한 다른 runner/public proposal 요청이 없도록 운영 singleton을 별도로 보장한다.

### 6. 동일 Scenario Before/After coverage campaign

동일 cohort에서 proposal 결과만 비교하거나, Event 유형을 늘려 proposal count·coverage를 개선하는 작업은
`references/same-cohort-coverage-campaign.md` 절차를 따른다. 핵심 불변 조건은 다음과 같다.

- Before/After의 catalog pin, Group IDs, Scenario IDs, runtime candidate IDs가 동일해야 한다.
- 유효 model input과 Lever Full set을 coverage를 위해 변경하지 않는다.
- 표기 alias와 기간 해석은 완화할 수 있지만 출력은 exact model coordinate이며 다중 slot은 명시 근거를 요구한다.
- After는 Before uncovered 후보만 Scenario별 1회 실행하고 DB 전체 read-back으로 KPI를 다시 계산한다.
- 비교에는 `scripts/compare_same_cohort.py`를 사용하고 전체 coverage와 후보 성공률을 분리해 보고한다.
- logic/config 변경은 `rollout-model-parameters`, release 검증은 `verify-model-parameter-release`, 배포는
  `mi-vm-deploy`에 handoff한다. 이 quality mode 자체가 DB binding/config를 임의 수정하지 않는다.

## Release gate

release acceptance까지 요청받으면 이 보고서의 mandatory `FAIL`이 0인지 먼저 확인한 뒤 `verify-model-parameter-release`를 사용한다. canonical fixture, LUT startup/guard, YAML/Kubernetes parity, Excel/archive, 전체 regressions, transactional DB 및 static SQL idempotency/rollback은 release skill 범위다.

## 안전 규칙

- 기본 모드에서 graph, callback, confirmation을 호출하지 않는다.
- `--execute` 전 preflight 또는 automated gate 실패가 하나라도 있으면 모든 live write를 막는다.
- unscoped read-only discovery만 허용하고 unscoped `--execute`는 DB 접속 전에 차단한다.
- 기존 보고서 경로는 덮어쓰지 않으며 보고서 예약 실패도 DB 접속 전에 차단한다.
- write-producing workflow를 자동 retry하지 않는다.
- catalog checksum, Lever ID/binding, group Event membership 오류를 경고로 낮추지 않는다.
- valid but unmapped/non-executable catalog state는 reason code와 함께 coverage 증적으로 보존한다.
- 보고서에 비밀값, DB 자격증명, 전체 prompt 원문을 기록하지 않는다.
- 이 품질 실행에서 production config, catalog, master, Basecase/LUT, workbook, schema, confirmation workflow를 변경하지 않는다.
- `new_resources/`의 user-owned staging 파일을 수정하거나 runtime source로 간주하지 않는다.
