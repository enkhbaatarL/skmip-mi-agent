# Model Parameter LUT + Basecase 구현 진행 기록

- 작업 브랜치: `design/model-param-lut-final-merge`
- 시작 HEAD: `2b49c8a`
- 시작일: 2026-07-10
- 상태: 구현 진행 중
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
| 6. 단일 proposal pipeline 통합 | IN_PROGRESS | Step2 exact membership, EffectiveReference, Step3 partial 정책 연결 및 회귀 조정 중 |
| 7. 운영 projection·sync diagnostics | PENDING | DB/운영 JSON 불변, sync-only 진단 노출 |
| 8. 자동화·정적·성능 검증 | PENDING | 관련 pytest, contract, compile, ruff, diff check |
| 9. Claude 구현 리뷰·수정 | PENDING | diff/test 결과 교차 리뷰 후 최소 수정 |
| 10. 대상 파라미터 5개 실제 테스트 | PENDING | 파라미터별 시나리오 1개, 통합 리포트, 실패 시 반복 수정 |
| 11. 최종 문서·커밋 목록 정리 | PENDING | 최종 README와 본 진행 기록 동기화 |

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
- model-parameter router가 현재 `main.py`에서 주석 처리된 상태는 이번 작업에서 임의로 바꾸지 않는다.

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

## 다음 재개 지점

1. proposal graph/state/prompt/presentation의 신규 exact pipeline 테스트와 기존 contract assertion을 최종 D-policy에 맞춘다.
2. sync diagnostics와 수동 5-scenario report runner를 검증하고 단계별 커밋을 만든다.
3. 전체 정적/자동화 검증 후 Claude에게 구현 diff와 테스트 결과를 다시 리뷰받는다.
