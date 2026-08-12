---
name: model-parameter-multi-event-quality
description: MI Model Parameter Agent의 Scenario API v3 multi_event_composite_dimensions 그룹을 동적으로 발견하고 sourceRef lineage, DB mapping 후보, parameter 병합·확장, proposal/confirmation persistence, token·시간 증적을 통합 평가한다. 사용자가 v3 멀티 이벤트 모델 파라미터 품질 테스트, multi-event proposal/confirmation 검증, active parameter coverage 보고서, sourceRef mapping 품질 진단을 요청할 때 사용한다. 단일 이벤트 scenario-only 테스트에는 model-parameter-agent-test를 사용한다.
---

# Model Parameter Multi-Event Quality

Scenario API v3 composite dimension을 기존 event type/dimension mapping에 역투영한 결과와 실제 Model Parameter proposal flow를 독립적으로 비교한다. 기본 실행은 DB read-only discovery이며, 명시적 승인 뒤에만 실제 LLM·proposal·confirmation write를 수행한다.

## 필수 참조

작업을 시작하기 전에 다음을 읽는다.

1. `references/quality-matrix.md`: v3 판정 기준과 보고서 증적 계약
2. `.claude/skills/model-parameter-agent-test/SKILL.md`: 공통 proposal/confirmation 실행 및 rollback 계약
3. release acceptance까지 요청받은 경우 `.claude/skills/verify-model-parameter-release/SKILL.md`: workbook, 전체 회귀, DB 안전 검증 절차

이 skill에서 기존 두 skill의 명령과 절차를 복제하지 않는다.

## 실행 전제조건

- repository root에서 Poetry와 runner가 같은 Python interpreter 및 설치된 `pytest`를 사용해야 한다.
- `envs/.env`와 `APP_CONFIG`가 현재 환경에 유효해야 한다. 설정 placeholder가 남아 있으면 automated contract collection도 `FAIL`이다.
- discovery DB에 대한 read 권한과 연결이 있어야 하며, v3 group-event/dimension 관계 schema와 proposal `mi_event_id` nullable migration이 먼저 적용되어 있어야 한다.
- 실제 적합한 v3 scenario가 없으면 결함으로 간주하지 않고 `COVERAGE LIMIT`으로 보고한다.
- `--execute`에는 사용자의 명시적 write 승인, 고정된 Basecase/LUT resource release, LLM 연결·자격, proposal/confirmation DB write 권한이 모두 필요하다.
- isolated automated contract hook은 mock/unit fixture만 사용하고 외부 DB·LLM을 호출하지 않는다. 이 결과는 반드시 `UNIT PASS/FAIL`로 표시하며 live DB confirmation 증적을 대체하지 않는다.
- 이 skill은 canonical master, 129개 dimension mapping, Basecase/LUT, workbook 또는 DB schema를 수정하지 않는다.

## 실행 절차

### 1. Read-only discovery

먼저 실제 DB를 변경하지 않는 discovery를 실행한다.

```bash
poetry run python tests/manual/model_parameter_agent/evaluate_multi_event_quality.py
```

범위를 고정할 때는 둘 중 하나만 사용한다.

```bash
poetry run python tests/manual/model_parameter_agent/evaluate_multi_event_quality.py --scenario-group-id 123
poetry run python tests/manual/model_parameter_agent/evaluate_multi_event_quality.py --scenario-id 456
```

runner는 다음을 수행한다.

- 필수 v3 테이블·컬럼과 proposal `mi_event_id` nullable 계약 preflight
- `api_version=v3`, `generation_strategy=multi_event_composite_dimensions` group 동적 발견
- 2~5개 group-event relation의 display order 및 source event membership 검사
- 선택 dimension의 `sourceRefs`를 relation template과 연결하고 event type 복원
- active master와 `(event_type_l2_id, dimKey)` mapping으로 독립 eligible 후보 산출
- active parameter별 `eligible → candidate → selected → proposed → confirmed` matrix 생성

`parameter_mapping_ready=false`를 제외 조건으로 사용하지 않는다. 승인 projection은 보조 근거이고, pending/rejected/미존재 projection은 경고로 기록한다.

### 2. Discovery 결과 판정

- schema 또는 lineage 오류가 있으면 LLM 호출 전에 중단하고 `FAIL`로 보고한다.
- 실제 적합 v3 scenario가 없으면 `COVERAGE LIMIT`으로 보고한다.
- 자동 discovery는 active parameter와 convergence/expansion coverage가 늘어나는 scenario를 우선 선택한다.
- 모든 scenario에서 active parameter 전부를 요구하지 않는다. 해당 scenario의 sourceRef로 eligible인 parameter만 필수다.

### 3. Write 실행 승인

실제 proposal/confirmation은 DB row를 생성·변경하므로 사용자에게 실행 승인을 받은 경우에만 `--execute`를 사용한다.

```bash
poetry run python tests/manual/model_parameter_agent/evaluate_multi_event_quality.py \
  --scenario-group-id 123 \
  --execute
```

`--execute`는 기존 Model Parameter raw graph와 기존 confirmation workflow를 재사용한다. v3 proposal은 `mi_event_id=NULL`, `scenario_group_id` authoritative link여야 한다. empty confirmation rollback, valid confirmation, reconfirmation은 `model-parameter-agent-test`의 계약대로 판정한다.

필요할 때만 `--retries N`을 사용한다. retry가 발생하면 성공하더라도 `REVIEW` 증적으로 남기며, 각 attempt의 trace·token·시간을 보존한다.

### 4. 통합 보고서 검토

기본 보고서는 `tests/reports/model_parameter_agent/model_parameter_multi_event_quality_<timestamp>.md`에 생성된다. `--report-path`로 위치를 지정할 수 있다.

반드시 다음을 확인한다.

- execution error 0
- lineage/mapping/persistence `FAIL` 0
- Step1 expected candidate와 실제 candidate의 source occurrence 일치
- direct 후보 생존, routing 최대 2개 정책, convergence/expansion source union
- proposal 및 confirmation DB read-back의 `mi_event_id=NULL`
- prompt bytes, Step1.5/2/3 token·시간·retry; 미수집 항목은 `REVIEW`
- Step1.5/2/3 실제 prompt packet의 ordered event, 관련 composite/indirect dimension, source lineage, 승인 projection; 필수 packet/context 누락은 `FAIL`
- rationale이 연결 event와 dimension의 방향·강도·기간·대상 충돌을 설명하는지 수동 검토

## Release gate

사용자가 release acceptance도 요청하면 먼저 이 skill의 v3 보고서에서 필수 `FAIL`이 0인지 확인한 뒤 `verify-model-parameter-release`를 사용한다. mapping workbook, canonical fixture, 전체 `tests/automated`, MySQL idempotency/rollback 등은 release verification skill의 절차를 그대로 따른다.

## 안전 규칙

- 기본 discovery 단계에서 graph, callback, confirmation 함수를 호출하지 않는다.
- 잘못된 source event, orphan template, malformed sourceRef를 mapping 부재 경고로 낮추지 않는다.
- mapping이 없는 유효 sourceRef 하나 때문에 전체 discovery를 실패시키지 않는다.
- 실제 scenario 부재를 품질 실패로 만들지 않고 `COVERAGE LIMIT`으로 분리한다.
- 보고서에는 비밀값, DB 자격증명, 전체 prompt 원문을 기록하지 않는다.
- canonical master, dimension mapping, Basecase/LUT, workbook 또는 DB schema를 이 품질 실행에서 수정하지 않는다.
