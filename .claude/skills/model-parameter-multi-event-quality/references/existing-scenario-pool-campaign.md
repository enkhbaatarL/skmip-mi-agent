# Existing Scenario Pool 대표 Trio Campaign

신규 Scenario Group이나 Scenario를 만들지 않고 현재 DB의 기존 결과를 재사용해 대표 trio testset을 확장할 때
적용한다. 기본 모드는 DB read-only이며 Proposal write, confirmation, callback, LLM 실행을 포함하지 않는다.

## 1. 고정 release 계약

Group은 다음을 모두 만족해야 한다.

- `api_version=v4`
- `generation_strategy=multi_event_model_lever_dimensions`
- Scenario Lever catalog `v4.1`과 승인 checksum exact match
- Group status `created|realized`, stage `completed`, `parameter_mapping_ready=true`
- ordered Event relation 존재·ID/순서 고유
- active Scenario 3개 이상, 실행 가능 status Scenario 3개 이상
- Dimension 3~6개, baseline 정확히 1개, floor/ceiling 존재, Scenario cell 조합 고유

release 또는 구조 gate 불일치 Group을 수에 맞추려고 포함하지 않는다.

## 2. 최신 최대 50 Group 선택

1. 적합 Group을 `scenario_group.mod_dtm DESC, scenario_group_id DESC`로 정렬한다.
2. ordered Event ID tuple을 논리 입력 signature로 사용한다.
3. 같은 signature가 여러 개면 가장 최신 Group 하나만 유지한다.
4. 고유 signature 목록에서 최대 50개만 고정한다.

따라서 exact release Group이 60개라도 고유 Event signature가 40개이면 최종 대상은 40개다. 과거 중복 Group
10개를 추가해 cap을 채우면 effective coverage를 부풀리므로 금지한다.

## 3. 전체 Scenario read-only preflight와 trio 선정

선택 Group에 속한 모든 Scenario를 Proposal-only runner의 read-only 모드로 먼저 검사한다. Object Storage/MI Base
bootstrap은 write 실행이 없으므로 요구하지 않는다.

대표 trio 선정 순서는 다음과 같다.

1. runtime candidate가 있는 Scenario를 우선한다.
2. 가능한 selection pool에서 baseline·floor·ceiling을 보존한다.
3. runtime canonical Parameter 종류 집합 완전 동일, 최소/평균 pairwise Jaccard, 공통 Parameter 수를 우선한다.
4. 동률이면 pressure span, role/cell 다양성, 안정적인 Scenario ID 순으로 결정한다.
5. runtime-capable Scenario가 3개 미만이면 ID 3개는 유지하고 `coverage limit`로 표시한다.

기존 Proposal history의 `covered`는 중복 write를 막는 현재 상태일 뿐 Scenario의 runtime capability가 아니다.
재사용 fixture 선정에서는 covered Scenario를 배제하지 않고 아래 상태를 분리한다.

- `runtime_capable`: v4.1 runtime Parameter 후보 존재
- `current_write_eligible`: runtime-capable이면서 uncovered guard 통과
- `covered`: 기존 blocking Proposal로 현재 write skip
- `coverage_limit`: runtime 후보 없음

## 4. 실행 명령

```bash
python tests/manual/model_parameter_agent/collect_existing_representative_trios.py \
  --max-groups 50 \
  --inventory-output <run-dir>/inventory.json \
  --preflight-output <run-dir>/read-only-preflight.json \
  --plan-output <run-dir>/representative-trio-plan.json \
  --testset-output tests/fixtures/model_parameter_agent/<dataset>.json \
  --report-json <run-dir>/collection-report.json \
  --report-markdown <run-dir>/collection-report.md
```

각 출력은 exclusive-create한다. 같은 경로가 있으면 덮어쓰지 않고 실패한다.

## 5. Hard gate와 KPI 분모

Hard gate:

- selected Group 수 `1..50`
- ordered Event signature 고유성 100%
- signature별 최신 revision 선택률 100%
- Group당 대표 Scenario 정확히 3개
- Scenario ID 전역 고유
- inventory와 preflight Scenario scope exact match
- preflight `FAIL=0`
- Scenario Lever/API/strategy/checksum exact match
- Group/Scenario/Proposal 생성 0건

Read-only KPI:

최종 표는 아래 핵심 7개 안팎으로 압축한다.

- 대상 Group / 전체·대표 Scenario
- Scenario Lever `v4.1` / 현재 Proposal Flow release pin
- `runtime-capable` / `coverage limit`
- `current write eligible` / `covered`
- 3개 이상 write eligible Group / coverage-limit Group
- 대표 3개 runtime Parameter type consistency
- preflight `FAIL` / hard stop

`runtime-capable`은 현재 release의 runtime allowlist 안에 실행 후보 Parameter가 1개 이상 있다는 뜻이다.
`current write eligible`은 여기에 lifecycle/catalog 정합성과 uncovered guard까지 통과해 지금 새 Proposal을 쓸 수 있다는
뜻이다. `covered`는 기존 Proposal 때문에 중복 쓰기를 막은 상태이고, `coverage limit`은 runtime 후보가 없어 LLM/쓰기를
시도하지 않는 상태다. 둘 다 이번 Proposal 실행 실패를 뜻하지 않는다.

실제 Proposal 결과 KPI인 success, semantic abstention, `같은 종류 + Scenario별 다른 제안값`, exact-slot value
differentiation, token/latency는 사용자의 명시적 write 승인 후 같은 고정 fixture identity에서만 추가한다.
`같은 종류 + Scenario별 다른 제안값`은 type-consistent triple-success Group을 분모로 하며, 동일 canonical
Parameter의 value를 순서 독립으로 정규화한 전체 Proposal signature가 대표 3개 사이에서 서로 모두 다르면 변별된
것으로 판정한다. 같은 exact
model slot의 값 차이는 좌표 차이 착시를 제거하는 별도 보조 KPI로 유지한다. read-only 수집 리포트에는 두 지표를
`NOT_MEASURED_READ_ONLY`/`N/A`로 표시하고 기존 Proposal 이력에서 값을 추정하지 않는다.

## 6. Fixture와 보고서

fixture의 불변 경계는 release contract와 ordered Group/Event/Scenario identity다. context/input fingerprint는 drift
탐지용 collection snapshot이다. runtime candidate와 Proposal history 상태는 시간에 따라 달라질 수 있는 관측 baseline으로
분리한다.

Markdown은 후보군 압축, read-only KPI, Group별 trio, KPI 개선안, 고정 컬럼 설명을 표로 포함한다. KPI 개선안은 신규
지표 추가가 아니라 성공률·triple-success·종류 동일성·Scenario별 제안값 변별 등 기존 KPI 개선 방향이다. `Covered`를
실패로, `coverage limit`을 실행 오류로 집계하지 않는다.

최종 collection Markdown/JSON에는 `Read-only KPI`의 의미와 해석 방법을 항상 포함한다. 이는 Proposal을 생성하지
않고 기존 저장 데이터와 deterministic preflight로 계산한 cohort 구성·실행 전제·coverage 지표다. collection
`PASS`는 선정·release·구조·preflight 계약 통과이지 실제 Proposal 성공이나 제안값 품질 통과가 아니다. 보고서는
읽을 수 있는 범위와 실제 Proposal을 실행하지 않아 읽을 수 없는 범위, `Covered`/`coverage limit` 해석, 동일 fixture
identity·release·context fingerprint에서만 회귀 비교한다는 조건을 명시한다.

Live Proposal campaign 뒤에는 최종 평가 대상 Proposal row에 `proposal_parameters`가 포함되어야 한다. 새 Proposal
Flow release를 같은 고정 cohort에 전건 재실행하도록 승인받은 경우 `run_proposal_only.py --execute
--replay-covered`를 사용한다. 이는 기존 행을 보존하는 append-only 실행이며 `CONFIRMED`/`PROCESSING`을 우회하지
않는다. 이때 최종 품질은 과거 covered 행이 아니라 `final_campaign_readback`의 신규 Proposal ID만 사용한다.
공식 비교는 매번 같은 고정 cohort의 live clean 전건 replay로 수행하며, 과거 campaign에서 성공했던 개별 Scenario의
재현 여부는 진단용 transition으로만 남긴다. 과거 성공 건을 골라 재실행·복구하거나 이전 결과와 같게 만들도록
강제하지 않는다. 부분 post-fix 결과는 공식 live clean KPI에 합산하지 않는다.
최종 고정 cohort 품질은 다음 명령으로 별도 산출한다.

```bash
python tests/manual/model_parameter_agent/evaluate_representative_trios.py final-cohort \
  --testset-input tests/fixtures/model_parameter_agent/<dataset>.json \
  --final-history-evidence <run-dir>/final-full-cohort-read-only.json \
  --output-json <run-dir>/final-cohort-trio-quality-report.json \
  --output-markdown <run-dir>/final-cohort-trio-quality-report.md
```

이 Report의 `최종 DB 기준 Trio Parameter·값 변별` 섹션은 전체 고정 Scenario 성공률, full-trio, 동일 Parameter
종류, 세 Scenario의 전체 proposed-value signature 변별, scalar exact common slot 변별, PowerMix atomic-vector
변별, slot rationale 명시 완전성을 항상 포함한다. evidence schema v6 이상은 secret을 제외한 전체
`model_parameter_*` 로컬·Neuro 선언 및 runtime effective config snapshot과 선언 차이도 포함한다.
또한 미제안·실패를 Group/Event, Step1.5·Step2·Step3, reason code, 확정 가능한 Parameter별로 자동 집계하고
관측 건수 기반 개선안과 fail-closed 안전 경계를 함께 표시한다. semantic abstention, 기술 실패, capability limit은
분리하며 Step1.5 미결정 routing을 모든 후보 Parameter의 실패로 중복 계산하지 않는다.
triple-success가 아닌 Group은 type/value/exact-slot을 `N/A`로 남긴다. 이 섹션이나 payload/config snapshot이
없으면 live campaign Report는 완료로 처리하지 않는다. 일반 `evaluate` 명령에서도 `--testset-input`과
`--final-history-evidence`를 함께 지정하면 동일 섹션이 자동 부착된다.
여기서 full-trio는 대표 Scenario 3개가 모두 이번 campaign의 신규 Proposal과 하나 이상의 유효 value cell을
DB read-back에서 가진 Group이다. Parameter 종류 동일·값 변별은 이 성공 조건에 포함하지 않고 후속 KPI로 분리한다.

## 7. 기존 Event 풀로 Scenario부터 재생성

기존 Scenario를 그대로 수집하는 대신 reference fixture의 Event 40개로 Scenario를 다시 만들라는 요청은
`existing_event_pool/add-only-regenerated-scenarios` 정책으로 분리한다. 원본 Group/Scenario를 삭제·수정하지 않고
Event별 신규 v4 Group을 생성한 뒤 validation/confirmation을 수행한다. ordered Event ID 40개 exact 일치, Event
고유성, 원본 Group 40개 보존, 신규 Group 40개 순증, Scenario Lever `v4.1`/현재 Proposal Flow release를 hard gate로
둔다. 전체 신규 Scenario preflight 뒤 대표 3개/Group plan을 만들고 Proposal 실행 전에
`evaluate_representative_trios.py freeze`로 fixture를 1회 고정한다. 이후 Proposal-only 실행은 해당 SHA-256과
identity를 사용하며 confirmation/callback을 호출하지 않는다. Object Storage가 없는 로컬 환경에서는 승인된
`configured_fallback`을 process-local로만 적용하고, 이 결과를 active MI Base/Object Storage 연동 검증으로 해석하지
않는다.
