# Model Parameter LUT + Basecase 구현 진행 기록

- 작업 브랜치: `design/model-param-lut-final-merge`
- 시작 HEAD: `2b49c8a`
- 시작일: 2026-07-10
- 상태: 구현·전체 매핑 이벤트타입 확장 테스트·LUT 감사 완료, Event 19 별도 확인 대기
- 재개 기준: 아래에서 가장 마지막 `DONE` 단계 다음 항목부터 진행한다.

## 사용자 소유 변경 보존

이번 작업과 무관한 아래 기존 변경은 수정하거나 커밋에 포함하지 않는다.

- 삭제: `docs/architectures/model_parameter_agent_main_merge_report.md`
- 삭제: `docs/architectures/model_parameter_agent_structure_improvement_plan.md`
- 미추적: `.claude/worktrees/`
- 미추적: `apps/agents/model_parameter_agent/docs/lut_basecase_*_20260709.md`

## 단계 현황

| 단계 | 상태 | 결과 |
|---|---|---|
| 1. 지침·최종 설계·현재 코드 분석 | DONE | D-01~D-11, 필독 문서, 기준선 구조와 공개 계약 확인 |
| 2. 비교 브랜치 선별 분석 | DONE | 두 feature commit은 merge/cherry-pick하지 않고 함수·테스트 아이디어만 선별 |
| 3. Claude 대화형 설계 리뷰 | DONE | state/source/diagnostics/streaming 위험을 교차 검토하고 최종 구현 경계 확정 |
| 4. 공통 connector stream/reasoning | DONE | 호출별 옵션, fresh-buffer retry, usage/trace 계약과 독립 테스트 완료 |
| 5. 설정·YAML·typed LUT domain | DONE | 5개 adapter, immutable catalog/index, compact leaf/period와 실제 CSV count 검증 완료 |
| 6. 단일 proposal pipeline 통합 | DONE | 공통 source 구성, compact Step2, exact resolver, 단일 기준값 Step3 연결 완료 |
| 7. 운영 projection·sync diagnostics | DONE | DB/운영 JSON 불변, sync-only provenance/cell 진단과 report 수집 완료 |
| 8. 자동화·정적·성능 검증 | DONE | 관련 전체 195개 테스트와 14 subtest, focused 29개, 정적 검사 통과 |
| 9. Claude 구현 리뷰·수정 | DONE | 독립 리뷰와 Claude 최종 리뷰 반영, 필수 미해결 항목 없음 |
| 10. 대상 파라미터 5개 실제 테스트 | DONE | 실제 LLM/DB 경로 5/5 첫 시도 성공, ERROR_COUNT=0, proposal 395~399 read-back |
| 11. 최종 문서·커밋 목록 정리 | DONE | 통합 report 품질표/Claude 판정/완료 보고서 반영, 최종 195-test gate 통과 |
| 13. 전체 매핑 이벤트타입 확장 테스트 | DONE | stream=true/LUT=true로 DB 가용 최대 18그룹·36시나리오 실행, 35 성공·1 Step2 실패 확인 |
| 14. Event 19 routing 별도 검토 | HOLD | PowerMix routing 0개 불허가 원인임을 Claude/독립 리뷰로 확인, 사용자 별도 확인 전 소스·API·DB 변경 보류 |
| 15. 실제 결과·LUT 감사·별도 report | DONE | 35개 성공 950 reference 전수 확인, 나머지 34건 우선 품질 검토와 parameter별 9개 표 작성 |

## 1. 분석 및 기준선 — DONE

### 읽은 기준 문서

- `AGENTS.md`
- `.claude/rules/python-conventions.md`
- `docs/architectures/project_directory_structure.md`
- `apps/agents/model_parameter_agent/docs/lutjoin_final/README.md`
- `apps/agents/model_parameter_agent/docs/lutjoin_final/DEVELOPMENT_AGENT_PROMPT.md`
- `claude-interactive` 및 `model-parameter-agent-test` skill 지침

### 기준선 테스트

```bash
poetry run pytest -q tests/automated/test_model_parameter_agent_contract.py
```

- 결과: `100 passed, 8 warnings in 35.16s`

### 현재 공개 계약

- 운영 proposal DB와 `proposalParameters` JSON 구조는 변경하지 않는다.
- actual basecase만 운영 `basecaseValue`에 저장한다.
- LUT provenance와 cell 진단은 테스트용 sync 응답/state에만 둔다.
- 실제 실행 엔트리포인트는 `model_param.py`이며 model-parameter router가 등록돼 있다. 공용 `main.py`의 주석 상태는 이 Agent 실행 계약과 무관하므로 변경하지 않는다.

## 2. 비교 브랜치 선별 분석 — DONE

### 채택

- Codex: parameter별 business key, basecase/LUT provenance, 호출별 `stream`, 단일 LLM 기준값, LiqUtil metadata 복원 아이디어
- Claude: exact `year - 1` GDP, horizon/flag 개념, loader fixture, stream chunk/usage 결합 아이디어

### 거절

- full LUT/effective record를 LangGraph state에 저장
- global 40,000 raw cap
- nearest Year/Month/Plant/Train 치환
- PMI t1 fallback 및 Full Country List 사용
- 모든 parameter 대상 이름 기반 metadata 제외
- 누락 cell 자동 no-change 생성 또는 candidate 전체 폐기
- LUT-only 값을 운영 `basecaseValue`로 투영
- connector 내부의 전역 Settings 기반 streaming

### 실제 LUT 기대 record 수

| Parameter | 2026~2030 기대 record |
|---|---:|
| GDP | 815 |
| PMI | 5,040 |
| PowerMix | 4,200 |
| Temperature | 5,040 |
| LiqUtilAdjustment | 19,366 |

## 3. Claude 대화형 설계 리뷰 — DONE

Claude Code CLI `2.1.206`을 feedback-only로 실행했다. 파일 편집은 허용하지 않았다.

### 수용한 판단

- YAML은 flag와 무관하게 startup fail-fast 검증하고, flag=true일 때만 CSV/catalog를 preload한다.
- `LutCatalog`는 process-level immutable cache이며 state에 넣지 않는다.
- Step2는 leaf별 실제 available period를 포함한 compact catalog를 사용한다.
- Step2 이후 `BasecaseIndex ∪ LutCatalog` exact membership을 검증하고 nearest는 사용하지 않는다.
- Step3는 선택 좌표당 단일 `llm_reference_value`만 노출한다.
- partial 응답은 cell 단위로 검증해 valid cell을 유지하고 missing/invalid 수만 진단한다.
- stream iteration 중단은 SDK retry에 맡기지 않고 fresh buffer로 전체 호출을 재시도한다.

### 조정하거나 거절한 판단

- Claude가 제안한 process-level request session store는 cleanup 누락, multi-process, 전역 mutable 상태 위험 때문에 사용하지 않는다.
- request `BasecaseIndex`는 LangGraph state의 직렬화 제외 arbitrary object로 유지하고, 직렬화되는 state에는 compact catalog/selected references/diagnostics만 둔다.

## 4. 구현 전 확정 영향·리스크

- merged candidate identity와 YAML canonical axis가 어긋나지 않도록 candidate별 BasecaseIndex를 격리한다.
- LiqUtil의 `Period`, `Life Cycle Category`, `Nameplate Capacity`는 business key가 아니며 exact reference에서만 복원한다.
- LUT-only cell은 LLM 기준값으로 LUT를 사용하더라도 운영 `basecaseValue=null`이다.
- 설정 horizon은 이름에 `lut`가 들어가지만 basecase와 LUT proposal 후보 양쪽에 적용한다.
- Step2/Step3 100 cap은 요청 전체가 아니라 parameter task별로 독립 적용한다.
- 실제 A.X gateway의 `stream_options.include_usage`와 reasoning 지원 여부는 실제 시나리오 테스트에서 확인한다.

## 5. 공통 connector stream/reasoning — DONE

### 변경

- `invoke_llm_structured_output()`에 optional `stream=False`와 `reasoning_effort=None`을 추가했다.
- `None`/`default`는 request key 자체를 생략하고 `none/minimal/low/medium/high/xhigh`는 그대로 전달한다.
- stream content delta를 전부 결합하고 usage-only final chunk 및 nullable usage를 처리한다.
- stream create/consume/parse 중 중단, 빈 content, partial JSON이 발생하면 이전 buffer를 폐기하고 전체 호출을 재시도한다.
- connector는 model-parameter Settings를 직접 읽지 않는다.
- provider/model의 reasoning 미지원 오류에서 값을 제거해 default로 fallback하지 않는다.

### 검증

```bash
poetry run pytest -q \
  tests/automated/test_llm_structured_output.py \
  tests/automated/test_tracing_context.py
uvx ruff check \
  apps/connectors/llm/llm_client.py \
  tests/automated/test_llm_structured_output.py
uvx ruff format --check \
  apps/connectors/llm/llm_client.py \
  tests/automated/test_llm_structured_output.py
git diff --check -- \
  apps/connectors/llm/llm_client.py \
  tests/automated/test_llm_structured_output.py
```

- pytest: `32 passed, 8 warnings, 8 subtests passed`
- Ruff check/format: 통과
- diff check: 통과

## 6. Model Parameter 설정 — DONE

### 변경

- `model_parameter_lut_enabled=false`
- `model_parameter_lut_horizon_start_year=2026`
- `model_parameter_lut_horizon_end_year=2030`
- `model_parameter_max_parameter_slots=100`
- `model_parameter_max_value_prompt_basecase_records=100`
- `model_parameter_llm_stream_enabled=false`
- `model_parameter_llm_reasoning_effort=default`
- `start_year <= end_year` Pydantic 설정 검증
- `envs/config.yaml`과 K8s ConfigMap의 resolved 기본값 동기화

### 검증

```bash
poetry run pytest -q tests/test_config_loader.py
uvx ruff check apps/common/configs/config.py
uvx ruff format --check apps/common/configs/config.py
git diff --check -- \
  apps/common/configs/config.py envs/config.yaml \
  devops/k8s/configmap.yaml tests/test_config_loader.py
```

- pytest: `13 passed, 6 subtests passed`
- Settings Ruff check/format: 통과
- diff check: 통과
- `tests/test_config_loader.py` 전체 Ruff에는 이번 변경과 무관한 기존 unittest/subprocess 규칙 위반이 남아 있어 파일 전체 lint gate에는 사용하지 않았다.

### 현재 DB 기반 실 테스트 후보 사전 확인

dotenv를 수동 테스트 스크립트와 동일하게 선행 로드한 뒤 읽기 전용으로 확인했다.

| 대상 parameter | scenario_id | event_type_l2_id | 현재 DB 후보 |
|---|---:|---:|---|
| GDP | 305 | 21 | GDP, PMI |
| PMI | 306 | 21 | GDP, PMI |
| PowerMix | 287 | 5 | PowerMix |
| Temperature | 289 | 6 | PowerMix, Temperature |
| LiqUtilAdjustment | 105 | 2 | LiqUtilAdjustment |

- 다섯 시나리오 모두 현재 DB에서 조회됐고 mapping warning은 0건이었다.
- GDP/PMI 및 Temperature 시나리오는 같은 graph 실행에서 다른 mapping 후보도 함께 나올 수 있으므로 최종 품질 평가는 대상 parameter별로 필터링한다.

## 7. Typed LUT domain과 실제 resource 검증 — DONE

### 변경

- `resources/lut/config/lut_parameters.yaml`에 파일, adapter/layout, CSV column, canonical key와 LiqUtil metadata 축만 선언했다.
- 공통 `tabular` adapter의 `row`/`year_columns`와 GDP growth, Temperature degree-days, LiqUtil 전용 adapter를 구현했다.
- YAML은 extra field/path escape/key-metadata 중복을 거부하고, enabled 상태의 CSV는 header/type/finite/Month 범위/exact duplicate를 검증한다.
- GDP는 exact `year - 1`만 사용하고 2025는 2026 계산용 lookback으로만 읽는다.
- PMI는 t2의 84개국만 사용하며 t1, General, Full Country List는 registry path에 포함하지 않는다.
- process-level immutable `LutCatalog`, request `BasecaseIndex`, 값 없는 leaf별 period `SlotCatalog`, exact `EffectiveReference` resolver를 구현했다.
- compact catalog는 full exact-key set을 별도로 복제하지 않고 leaf/period 구조 자체로 membership을 확인한다.

### 검증

```bash
poetry run pytest -q tests/automated/test_model_parameter_lut_domain.py
uvx ruff check \
  apps/agents/model_parameter_agent/utils/lut \
  tests/automated/test_model_parameter_lut_domain.py
uvx ruff format --check \
  apps/agents/model_parameter_agent/utils/lut \
  tests/automated/test_model_parameter_lut_domain.py
git diff --check -- \
  apps/agents/model_parameter_agent/resources/lut/config \
  apps/agents/model_parameter_agent/utils/lut \
  tests/automated/test_model_parameter_lut_domain.py
```

- pytest: `21 passed`
- 실제 2026~2030 record: GDP 815, PMI 5,040, PowerMix 4,200, Temperature 5,040, LiqUtilAdjustment 19,366
- Ruff check/format 및 diff check: 통과
- 실제 catalog cold load는 로컬 기준 약 1.6초였고, 같은 hash/horizon warm/concurrent 호출은 동일 immutable instance를 재사용했다.

### 실제 basecase 호환성 사전 검증

LLM 호출 전 읽기 전용으로 다섯 대상 scenario의 workbook record를 exact index로 변환했다.

| scenario_id | 관련 후보 | raw basecase | horizon exact index | compact leaf |
|---:|---|---:|---:|---:|
| 305 | GDP, PMI | 141 | 96 | 247 |
| 306 | GDP, PMI | 141 | 96 | 247 |
| 287 | PowerMix 2개 mapping 후보 | 114 | 110 | 1,680 (Step1.5 merge 전) |
| 289 | Temperature, PowerMix | 207 | 205 | 924 |
| 105 | LiqUtilAdjustment | 21,656 | 14,411 | 347 (LUT enabled union 기준) |

- exact duplicate/conflict나 metadata schema 오류는 발생하지 않았다.
- LiqUtil 요청의 serialized compact payload는 full raw 21,656행을 넣지 않고 약 124KB였다(LUT disabled basecase-only 사전 측정).

### 실행 엔트리포인트 정정

- 구현 중 공용 `main.py`를 startup 연결 지점으로 잘못 판단했으나 사용자 확인으로 실제 엔트리포인트가 `model_param.py`임을 바로잡았다.
- `main.py` 변경은 완전히 제거했으며, YAML 상시 검증과 enabled 시 catalog preload는 `model_param.py` lifespan에 연결했다.
- `Dockerfile.model_param`이 배포 이미지에서 `model_param.py`를 `main.py`로 복사하는 실행 계약과 router 등록을 확인했다.
- `MODEL_PARAMETER_AGENT_FLOW.md`와 project directory architecture의 엔트리포인트·LUT resource 흐름도 함께 갱신했다.

## 8. 단일 proposal pipeline·운영 projection — DONE

### 변경

- `load_basecase_samples`가 flag와 무관하게 동일한 2026~2030 horizon의 request `BasecaseIndex`와 값 없는 compact `SlotCatalog`를 만든다.
- flag=true일 때만 process `LutCatalog`를 source union에 넣고, false 또는 YAML 미등록 parameter는 basecase-only로 같은 pipeline을 계속 사용한다.
- Step2 task에는 전체 leaf/leaf별 actual period catalog와 parameter별 독립 100 hard cap을 제공한다.
- Step2 결과는 canonical business-key axis set과 exact membership을 검사하며 nearest/부분 key/중복 exact slot은 제외한다.
- 선택된 exact key만 `EffectiveReference`로 state에 넣고 Step3에는 좌표당 `llm_reference_value` 숫자 하나만 제공한다.
- Step3 reference 100 cap도 parameter task별로 적용하며, selected exact reference가 cap을 넘으면 조용히 자르지 않고 요청 오류로 실패한다.
- Step3는 명시적 valid cell만 유지한다. 누락 cell을 생성하지 않고, 일부 누락/invalid 때문에 같은 candidate의 다른 valid cell을 폐기하지 않는다.
- actual basecase가 있는 cell만 운영 `basecaseValue`에 값을 넣고 LUT-only는 `null`로 유지한다.
- LiqUtil의 Period/Life Cycle/Nameplate Capacity는 exact reference metadata에서 서버가 복원하며 LLM business key에는 노출하지 않는다.
- PowerMix는 source별 독립 cell로 유지하고 전체 vector 보완·합계 검증·정규화를 하지 않는다.
- sync 테스트 응답의 optional `diagnostics`에 source/provenance/selected-valid-missing-invalid count를 제공하되 callback과 proposal DB JSON에는 넣지 않는다.

### 자동화 검증

```bash
poetry run pytest -q \
  tests/automated/test_model_parameter_lut_domain.py \
  tests/automated/test_model_parameter_lut_pipeline.py \
  tests/automated/test_model_parameter_report_scope.py
poetry run pytest -q tests/automated/test_model_parameter_agent_contract.py
```

- 신규 domain/pipeline/report: `45 passed`
- 기존 contract: `100 passed, 8 warnings`
- 검증된 정책: source matrix, exact miss/no-nearest, basecase override/basecase-only/LUT-only, 독립 cap, single reference, partial/no-change, Liq metadata, PowerMix, state 직렬화, sync/callback 분리

## 9. 5-parameter 명시 시나리오 report runner — DONE

### 변경

- 수동 evaluator에 `--parameter-scenarios PARAMETER=SCENARIO_ID`를 추가했다.
- `--target-parameters`와 parameter 집합이 정확히 일치해야 하며 형식, 중복 parameter, 중복 scenario, 누락·삭제 scenario를 실행 전에 거부한다.
- 같은 group을 공유하는 GDP=305와 PMI=306도 target identity로 분리해 parameter당 정확히 한 번, 총 5회만 실행한다.
- 대상 parameter가 mapping 후보와 selected adjustment 양쪽에 실제 존재해야 해당 parameter-scenario를 PASS로 판단한다.
- raw state의 resolved config, LUT version, selected provenance와 cell diagnostics를 scenario 및 최종 요약에 기록한다.
- 기존 event-type discovery/report mode는 유지한다.

### 검증

```bash
poetry run pytest -q tests/automated/test_model_parameter_report_scope.py
poetry run python tests/manual/model_parameter_agent/evaluate_event_type_proposals.py --help
```

- report scope 자동화: `16 passed, 8 warnings`
- 실제 DB read-only scope 확인: GDP=305, PMI=306, PowerMix=287, Temperature=289, LiqUtilAdjustment=105, execution count 5
- py_compile, 신규 test Ruff/format, manual script `F,E9,I` Ruff, diff check: 통과
- 실제 LLM/DB proposal 실행은 Claude 구현 리뷰 및 전체 자동화 gate 이후 단계 10에서 수행한다.

## 10. 최종 자동화 gate 및 Claude 구현 리뷰 — DONE

### 독립 코드 리뷰와 반영

- canonical exact key를 찾은 뒤 LLM이 되돌린 axis/metadata가 운영 결과를 오염시킬 수 있던 경로를 수정했다. 최종 cell 좌표와 metadata는 항상 서버가 보관한 `EffectiveReference`를 기준으로 materialize한다.
- 같은 candidate key의 Step3 adjustment가 중복되면 순서에 따라 첫 응답이 채택될 수 있던 경로를 수정했다. 동일값/상이값과 입력 순서에 무관하게 해당 candidate의 모든 adjustment를 거부하고 진단을 남긴다.
- request runtime object가 graph 최종 출력에 노출되지 않도록 직렬화 output state와 runtime state를 분리하고 graph `output_schema`를 지정했다.
- 수동 report가 runtime `effective_references` 대신 legacy basecase만 읽어 LUT-only 실행을 0건으로 오판하던 경로를 수정했다. parameter task별 100 cap도 report에서 동일하게 판정한다.
- P0 finding은 없었다.

### Claude Code CLI 최종 리뷰와 판단

Claude Code CLI를 read-only feedback mode로 다시 실행해 수정 diff와 테스트를 검토했다.

1. `effective_references=[]`를 legacy payload와 구분하지 못하는 truthiness fallback — 수용 후 key 존재 여부로 수정했다.
2. duplicate adjustment 거부 분기에서 slot-axis warning이 누락됨 — 수용 후 동일 진단을 추가했다.
3. metadata가 axes와 충돌할 수 있다는 정보성 의견 — registry validator가 key/metadata 중복을 이미 거부하므로 추가 변경하지 않았다.
4. unknown candidate 중복의 별도 진단 의견 — 기존 unknown-candidate 정책과 동일하게 처리되는 정보성 항목이므로 변경하지 않았다.

Claude의 최종 결론은 실제 테스트 전에 필수로 고칠 항목이 없다는 것이었다. 현재 graph는 checkpointer를 사용하지 않으므로 runtime object checkpoint 직렬화는 현 계약의 문제가 아니다. 향후 checkpointer를 도입한다면 runtime object 재수화 전략이나 별도 runtime store가 필요하다는 제약을 남긴다.

### 자동화·정적 검증

```bash
poetry run pytest -q \
  tests/automated/test_llm_structured_output.py \
  tests/automated/test_tracing_context.py \
  tests/test_config_loader.py \
  tests/automated/test_model_parameter_lut_domain.py \
  tests/automated/test_model_parameter_lut_pipeline.py \
  tests/automated/test_model_parameter_report_scope.py \
  tests/automated/test_model_parameter_agent_contract.py
```

- 전체 관련 범위: `195 passed, 8 warnings, 14 subtests passed in 41.98s`
- Claude 지적 2건 반영 후 focused 재검증: `29 passed, 8 warnings in 1.15s`
- `compileall`, 변경 파일 Ruff `F,E9`, 신규 테스트/state 전체 Ruff, format check, `git diff --check`: 통과
- 기존 대형 pipeline/manual 파일의 이번 변경과 무관한 formatting debt는 관련 없는 대량 변경을 피하기 위해 그대로 유지했다.

## 11. 5-parameter 실제 테스트 — DONE

### 확정 대상

| Parameter | scenario_id | event_type_l2_id | scenario_group_id |
|---|---:|---:|---:|
| GDP | 305 | 21 | 60 |
| PMI | 306 | 21 | 60 |
| PowerMix | 287 | 5 | 51 |
| Temperature | 289 | 6 | 52 |
| LiqUtilAdjustment | 105 | 2 | 18 |

### 재개 시 실행 명령

API server를 시작하지 않고 `model_param.py`와 동일한 proposal graph를 직접 실행한다.

```bash
MODEL_PARAMETER_LUT_ENABLED=true poetry run python \
  tests/manual/model_parameter_agent/evaluate_event_type_proposals.py \
  --target-parameters GDP PMI PowerMix Temperature LiqUtilAdjustment \
  --parameter-scenarios \
    GDP=305 PMI=306 PowerMix=287 Temperature=289 LiqUtilAdjustment=105 \
  --concurrency 2 --retries 1
```

### 완료 판정

- `ERROR_COUNT=0`, `SCENARIO_EXECUTION_COUNT=5`
- 다섯 parameter-scenario 모두 `status=passed`
- 각 대상 parameter가 현재 DB mapping candidate와 실제 selected result에 모두 존재
- `mapping_candidate_coverage`와 `selected_result`가 PASS
- 빈 recommendation 0건
- resolved config가 LUT enabled, 2026~2030, task별 cap 100/100, 확정 stream/reasoning 값을 표시
- 다섯 실행이 동일한 non-empty LUT version을 표시
- 최종 proposal DB row를 read-back하고 저장 JSON에 대상 parameter/value가 존재
- 생성된 단일 markdown report에 skill의 9개 `Parameter Quality Evaluation` 기준을 parameter별 실제 근거로 추가

실행 중 agent logic/report 문제가 확인되면 최소 범위로 수정하고 focused/전체 자동화 검증과 해당 실제 시나리오를 다시 실행한다. DB mapping 데이터는 변경하지 않는다.

### 실제 실행 결과

- 실행 시각: 2026-07-10 18:01:34~18:03:48 KST
- 총 소요시간: 133.374초
- concurrency=2, retries=1
- 실제 결과: `ERROR_COUNT=0`, `SCENARIO_EXECUTION_COUNT=5`, 5건 모두 attempt 1
- 통합 report: `tests/reports/model_parameter_agent/model_parameter_proposal_evaluation_parameters_GDP_PMI_PowerMix_Temperature_LiqUtilAdjustment_20260710_180134.md`

| Parameter | scenario_id | proposal_id | elapsed | mapping | selected | exact cell | 결과 |
|---|---:|---:|---:|---|---|---|---|
| GDP | 305 | 395 | 40.562s | PASS | PASS | 4/4 valid | PASS |
| PMI | 306 | 397 | 78.006s | PASS | PASS | 24/24 valid | PASS |
| PowerMix | 287 | 396 | 26.060s | PASS | PASS | 1/1 valid | PASS |
| Temperature | 289 | 399 | 66.735s | PASS | PASS | 1/1 target valid | PASS |
| LiqUtilAdjustment | 105 | 398 | 33.604s | PASS | PASS | 5/5 valid | PASS |

- 다섯 실행 모두 동일 LUT version `e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809`을 사용했다.
- resolved config는 LUT enabled, horizon 2026~2030, cap 100/100, stream false, reasoning default로 일치했다.
- 모든 target에서 invalid/missing/rejected exact cell이 0이고 빈 recommendation도 0이었다.
- 최종 DB proposal row 395~399를 read-back했으며 status는 모두 `PROPOSED`, 대상 parameter와 value가 저장됐다.
- callback은 raw graph 수동 검증 계약에 따라 `SKIPPED`였고 외부 callback은 보내지 않았다.

### 실제 결과 Claude 교차 리뷰

Claude Code CLI session `fc23336b-5578-4f90-876f-0f96cba0ae6e`에서 최종 명세와 4,511줄 report를 read-only로 대조했다.

- 필수 코드 수정 또는 재실행이 필요한 finding은 없었다.
- Temperature 2027-03은 과거의 2026-03 이벤트 월을 실행일 이후 가장 가까운 같은 월로 이월한 정책상 exact 결과지만, “차기 동절기 재발” 가정이 rationale에 명시되지 않아 품질 `REVIEW`로 남겼다.
- PowerMix LUT-only 0.36505 no-change는 `basecaseValue=null`이라는 D-03 운영 투영 때문에 `null -> 값`으로 오독할 수 있어 품질 `REVIEW`로 남겼다. 운영 schema를 바꾸거나 LUT를 basecase로 투영하지 않는다.
- LiqUtil T4 Planned/T5 Speculative `0 -> 0`은 exact/Closed 제외/no-change 계약상 유효하지만 현재 운영 Train 감산에는 불필요한 리뷰 노이즈라 품질 `REVIEW`로 남겼다.
- LiqUtil 결과를 서버에서 lifecycle/no-change로 후처리 제외하면 D-05의 LLM 명시 cell 보존을 위반할 수 있어 변경하지 않았다. 현재 Step2 prompt도 약한/neutral direct mapping은 slot을 선택하고 Step3에서 no-change를 판단하도록 명시하므로, 이번 한 건만으로 정책을 역전하지 않았다.
- 같은 report에 parameter별 9개 고정 품질 기준, 구체 근거, REVIEW 개선 방향을 추가했다.

## 12. 최종 문서 및 재검증 — DONE

- `IMPLEMENTATION_FINAL_REPORT.md`에 변경 목적, 구조, 리뷰, 실제 5건, 영향/리스크와 구현 커밋을 정리했다.
- 최종 실제 report는 기본 gitignore 대상이므로 이번 실행 파일 하나만 명시적으로 추적했다.
- report에서 API key, authorization, password, secret, access token 등 민감정보 패턴이 없음을 확인했다.
- 사용자 소유 dirty 변경은 stage/commit 대상에서 계속 제외했다.

최종 관련 자동화 gate:

```bash
poetry run pytest -q \
  tests/automated/test_llm_structured_output.py \
  tests/automated/test_tracing_context.py \
  tests/test_config_loader.py \
  tests/automated/test_model_parameter_lut_domain.py \
  tests/automated/test_model_parameter_lut_pipeline.py \
  tests/automated/test_model_parameter_report_scope.py \
  tests/automated/test_model_parameter_agent_contract.py
```

- 결과: `195 passed, 8 warnings, 14 subtests passed in 42.55s`
- warning: 기존 Pydantic ForwardRef deprecation 7건, LangGraph cache `allowed_objects` pending deprecation 1건
- 실패: 0

## 13. 전체 매핑 이벤트타입 확장 테스트 — DONE

### DB 가용 범위

- 5개 대상 parameter의 현재 매핑 합집합은 event_type_l2_id `1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 17, 18, 19, 21`이다.
- 요청한 이벤트별 2그룹 × 그룹별 2시나리오를 모두 충족하는 이벤트는 `2, 6, 7, 18` 4개다.
- 나머지 10개 이벤트는 활성 시나리오 2개 이상인 그룹이 1개뿐이다. DB mapping/scenario 데이터를 변경하지 않는 조건에서 가용 최대 범위는 18그룹 × 2 = 36시나리오다.

### 올바른 실행 설정

첫 실행은 `MODEL_PARAMETER_LLM_STREAM_ENABLED`를 누락해 `resolved_config.stream=false`임을 확인한 즉시 중단했다. 해당 부분 report는 최종 판정에서 제외한다.

- 제외 report: `tests/reports/model_parameter_agent/model_parameter_proposal_evaluation_parameters_GDP_PMI_PowerMix_Temperature_LiqUtilAdjustment_20260710_182047.md`
- 최종 원본 report: `tests/reports/model_parameter_agent/model_parameter_proposal_evaluation_parameters_GDP_PMI_PowerMix_Temperature_LiqUtilAdjustment_20260710_182853.md`

```bash
MODEL_PARAMETER_LUT_ENABLED=true \
MODEL_PARAMETER_LLM_STREAM_ENABLED=true \
poetry run python \
  tests/manual/model_parameter_agent/evaluate_event_type_proposals.py \
  --target-parameters GDP PMI PowerMix Temperature LiqUtilAdjustment \
  --groups-per-event 2 --scenarios-per-group 2 \
  --concurrency 4 --retries 1
```

- 전 36회에서 resolved config의 `lut_enabled=true`, `stream=true`, reasoning=`default`를 확인했다.
- 35건은 proposal 저장까지 성공했다. scenario 281 한 건은 두 attempt 모두 Step2 selected slot 0개로 실패했다.
- scenario 282는 첫 Step2 streaming 지연/실패 후 시나리오 retry에서 22개 slot을 선택해 성공했다.

## 14. Event 19 routing 별도 검토 — HOLD

### 최초 실패 격리

- 대상: event 19, group 48, scenario 281 `IMO 운송 규제 보통 강도`
- Step1.5를 통과한 candidate: `19|impactintensity|powermix|demand|powermixadjustment`
- basecase/LUT source와 compact catalog — 정상
- Step2 — `slot_count=1`, `selected_count=0`, `selected=false`
- Step3 value 산정 — selected slot이 없어 미실행

단독 `stream=true`, LUT=true 실행을 retries=2로 추가해 3회 모두 같은 결과를 얻었다. 본 배치 2회와 합쳐 5/5 재현이다.

- 단독 실패 report: `tests/reports/model_parameter_agent/model_parameter_proposal_evaluation_parameters_PowerMix_20260710_184926.md`

### 사용자 지적 후 DB·scenario 재대조

- candidate key 문자열과 달리 실제 DB row의 `mapping_method`는 `routing`이다.
- routing comment는 전원믹스·발전설비·연료전환으로 발전 비중이 구조적으로 바뀌는 정책일 때만 PowerMix를 선택하도록 한다.
- scenario 281은 `3개월 / 보통 / 시행 확정 / 단발적·한시`이며 narrative는 LNG 운송비 프리미엄이다.
- scenario 282는 `1년 / 큼 / 시행 확정 / 구조적·영구`지만 narrative 핵심은 LNG 운송비와 항로 제약이다. 구조적 규제가 곧 발전 믹스 구조 변화라는 근거는 아니다.
- scenario group 자체도 ShippingCost 계열 선택 검증용이다. ShippingCost는 현재 지원 대상 5개 parameter에 없다.
- 따라서 281의 Step2 미선택은 타당할 가능성이 높고, 282의 11개국 Gas × 2년 = 22 slot은 routing over-selection 가능성이 높다.
- 진짜 원인 후보는 `CANDIDATE_VALIDATION_SYSTEM`이 routing 후보가 있으면 dimension별 최소 1개를 강제하여, 유일한 지원 후보 PowerMix를 의미 불일치에도 Step1.5에서 통과시킨 정책이다.

### 폐기한 접근과 현재 상태

- 초기에 direct 후보로 잘못 해석해 조건부 Step2 LLM 재호출 prototype을 작성했으나, 사용자 지적과 실제 DB 확인 후 전부 제거했다.
- 사용자는 추가 LLM 재호출을 명시적으로 금지했다. 이후 fix는 기존 Step1.5/Step2 각 1회 호출 구조를 유지한다.
- Claude와 독립 리뷰에서 routing 0개 허용 정책, API의 후보 0개 계약, 수동 report의 N/A 판정을 검토했다.
- 공통 결론은 281/282 모두 현재 서술로 PowerMix 조건을 충족하지 않고, Step1.5의 routing 최소 1개 강제가 PowerMix를 사실상 direct로 만든다는 것이다.
- 281은 Step2가 잘못 통과한 후보를 뒤늦게 거절했으며, 282의 11개국 Gas × 2년은 정상 성공이 아니라 false positive/over-selection으로 판단했다.
- 사용자가 이 이슈를 별도로 확인하기로 했으므로 소스·DB·API 계약을 수정하거나 전체 배치를 재실행하지 않았다.
- 상세 report: `tests/reports/model_parameter_agent/model_parameter_event19_routing_review_20260710.md`

## 15. 전체 결과 및 LUT 감사 — DONE

### 나머지 34개 시나리오

- Event 19의 281/282를 제외한 34개는 모두 첫 attempt에 proposal 저장까지 성공했다.
- selected/returned/valid reference는 928/928/928, missing/invalid/rejected는 0/0/0이다.
- actual basecase 우선 reference 683개, LUT-only reference 245개다.
- 의미 품질 우선 finding은 scenario 280의 수입 시설→Wheatstone 감산, scenario 317의 `6월 Peak`→2026-07 시간 선택이다.
- scenario 289의 미래 이월 설명, 287/267/105의 no-change/provenance 노이즈, 93/130/136의 대량 slot·성능을 REVIEW로 남겼다.

### 성공 35건 LUT 전수 감사

- 같은 catalog hash `e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809`를 사용했다.
- selected reference 950개가 모두 current catalog exact row와 일치했다.
- actual basecase 우선 705개, LUT-only 245개이며 final DB axis/value도 950/950 일치했다.
- LUT-only 245개 모두 운영 `basecaseValue=null`을 유지했다.
- scenario 267, 268, 280을 CSV 원행으로 역검증해 axes/metadata/value exact 일치를 확인했다.
- Event 19와 scenario 280의 문제는 LUT 데이터 오류가 아니라 의미 routing/selection 문제다.

### 최종 문서

- 메인 report: `tests/reports/model_parameter_agent/model_parameter_full_event_stream_lut_review_20260710.md`
- Event 19 별도 report: `tests/reports/model_parameter_agent/model_parameter_event19_routing_review_20260710.md`
- 메인 report에도 Event 19의 dimension 비교, slot/value 단계, 원인, LUT 무관성, HOLD 상태를 유지했다.
- parameter 5개 각각 동일한 9개 `Parameter Quality Evaluation` 기준으로 결과를 작성했다.

## 다음 재개 지점

1. 사용자가 Event 19 별도 report를 확인해 routing 0개 처리와 운영 API empty 계약을 결정한다.
2. 승인되면 추가 LLM 재호출 없이 기존 Step1.5 한 번에서 routing 0개를 허용하는 최소 수정과 자동화 테스트를 적용한다.
3. scenario 281·282, 명시적 PowerMix 양성 fixture, scenario 280을 `stream=true`/LUT=true로 재검증한다.
4. 전체 36개 회귀에서 기존 정상 후보와 950-cell exact/LUT 불변식이 유지되는지 확인한다.
