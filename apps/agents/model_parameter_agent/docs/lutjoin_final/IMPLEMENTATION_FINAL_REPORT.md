# Model Parameter LUT + Basecase 구현 완료 보고서

- 작업 브랜치: `design/model-param-lut-final-merge`
- 기준 HEAD: `2b49c8a`
- 구현 기간: 2026-07-10
- 상태: 구현 및 실제 5-parameter 검증, 최종 자동화 gate 완료
- 상세 단계 기록: `IMPLEMENTATION_PROGRESS.md`
- 구현 기준: `DEVELOPMENT_AGENT_PROMPT.md`, `README.md` D-01~D-11
- 실제 실행 report: `tests/reports/model_parameter_agent/model_parameter_proposal_evaluation_parameters_GDP_PMI_PowerMix_Temperature_LiqUtilAdjustment_20260710_180134.md`

## 1. 변경 목적

기존 basecase-only model parameter proposal pipeline에 GDP, PMI, PowerMix, Temperature, LiqUtilAdjustment LUT를 안전하게 결합한다. full LUT state 적재, raw cap, nearest 좌표 치환, LUT 값을 운영 basecase로 오인하는 문제 없이 compact catalog와 exact reference를 사용하고, 기존 운영 API/DB 계약은 유지한다.

실행 엔트리포인트는 공용 `main.py`가 아니라 `model_param.py`다. YAML startup validation과 LUT preload는 `model_param.py` lifespan에 연결했으며 `Dockerfile.model_param`의 배포 복사 계약도 확인했다.

## 2. 주요 구현 결과

### LLM connector

- 호출별 `stream`과 `reasoning_effort` 옵션을 추가했다.
- stream delta/usage chunk를 결합하고, 중단·빈 content·partial JSON에서는 이전 buffer를 버린 뒤 전체 호출을 재시도한다.
- connector는 model-parameter settings를 직접 읽지 않으며 미지원 reasoning 오류를 묵시적으로 default로 재호출하지 않는다.

### 설정과 startup

- 기본값: LUT false, horizon 2026~2030, task별 Step2/Step3 cap 100/100, stream false, reasoning default.
- YAML processing schema는 flag와 무관하게 검증한다.
- flag=true인 `model_param.py` startup에서 실제 CSV/catalog를 fail-fast preload한다.

### LUT domain

- 최소 YAML registry와 allowlist adapter 구조를 추가했다.
- process-level immutable `LutCatalog`, request-local `BasecaseIndex`, 값 없는 compact `SlotCatalog`, selected-key `EffectiveReference`를 구현했다.
- malformed header/value/type, path escape, key/metadata 축 중복, exact duplicate conflict를 거부한다.
- 2026~2030 실제 record 수를 검증했다.

| Parameter | record |
|---|---:|
| GDP | 815 |
| PMI | 5,040 |
| PowerMix | 4,200 |
| Temperature | 5,040 |
| LiqUtilAdjustment | 19,366 |

### 단일 proposal pipeline

- flag는 reference source만 결정하며 이후 Step2/Step3 pipeline은 하나다.
- Step2는 parameter별 compact catalog와 독립 100 cap을 사용한다.
- selected 좌표는 `BasecaseIndex ∪ LutCatalog` exact membership만 허용하며 nearest/fuzzy 보정은 없다.
- Step3는 좌표별 단일 `llm_reference_value`를 받고, valid partial cell만 보존한다.
- LLM 응답의 좌표/metadata 대신 서버의 authoritative `EffectiveReference`를 운영 결과에 투영한다.
- 같은 candidate의 중복 Step3 adjustment는 응답 순서와 값 동일 여부에 무관하게 전부 거부한다.
- actual basecase가 있을 때만 운영 `basecaseValue`를 채우며 LUT-only는 null이다.
- LiqUtil Period/Lifecycle/MTPA는 exact reference에서 복원한다. Closed만 객관 규칙으로 제외한다.
- PowerMix는 source별 cell을 보존하며 임의 전체 vector 보완·정규화를 하지 않는다.

### state/API/DB와 diagnostics

- request runtime object와 serializable output state를 분리하고 graph `output_schema`에서 runtime object를 제외했다.
- 운영 proposal/callback JSON은 기존 계약을 유지했다.
- sync/test state에만 resolved config, LUT version, provenance, selected/valid/missing/invalid diagnostics를 제공한다.
- 현재 graph에는 checkpointer가 없다. 향후 checkpointer 도입 시 runtime index 재수화 또는 별도 runtime store 설계가 필요하다.

### 실제 report runner

- `--parameter-scenarios PARAMETER=SCENARIO_ID`를 추가했다.
- target parameter 집합과 scenario mapping을 실행 전에 엄격히 검증한다.
- 대상 parameter가 현재 DB mapping 후보와 final selected result에 모두 존재해야 PASS다.
- report가 `effective_references`와 parameter별 cap을 기준으로 Step3를 판정하도록 수정했다.

## 3. 리뷰와 판단

Claude Code CLI를 구현 전 설계 리뷰, 구현 후 diff 리뷰, 실제 결과 품질 리뷰에 read-only로 사용했다.

구현 리뷰에서 반영한 핵심 사항:

- canonical reference axes/metadata의 authoritative 투영
- duplicate candidate adjustment의 deterministic 전체 거부
- graph output에서 runtime object 제외
- report의 effective reference 우선과 parameter별 cap 판정
- explicit empty effective-reference payload와 legacy fallback 구분
- duplicate 거부 분기의 slot-axis 진단 유지

실제 결과 리뷰 결론:

- 필수 코드 수정 또는 재실행 finding 없음
- Temperature 2027-03 이월 가정 미명시: 품질 REVIEW
- PowerMix LUT-only no-change의 `basecaseValue=null` 오독 가능성: 품질 REVIEW
- LiqUtil Planned/Speculative 0→0 no-change: 계약상 유효하지만 리뷰 노이즈로 REVIEW

마지막 LiqUtil cell을 서버에서 lifecycle/no-change 기준으로 삭제하면 LLM이 명시한 valid cell 보존 정책과 충돌할 수 있어 변경하지 않았다. 세 항목은 실제 report의 9개 품질표에 근거와 후속 개선 방향을 기록했다.

## 4. 실제 5-parameter 테스트

API server를 시작하지 않고 `model_param.py`와 같은 raw proposal graph 및 `to_output()` DB 저장 경로를 실행했다.

```bash
MODEL_PARAMETER_LUT_ENABLED=true poetry run python \
  tests/manual/model_parameter_agent/evaluate_event_type_proposals.py \
  --target-parameters GDP PMI PowerMix Temperature LiqUtilAdjustment \
  --parameter-scenarios \
    GDP=305 PMI=306 PowerMix=287 Temperature=289 LiqUtilAdjustment=105 \
  --concurrency 2 --retries 1
```

결과:

- 실행: 2026-07-10 18:01:34~18:03:48 KST, 133.374초
- `ERROR_COUNT=0`
- `SCENARIO_EXECUTION_COUNT=5`
- 5건 모두 first attempt, parameter status PASS, group status PASS
- 빈 recommendation 0
- 동일 LUT version: `e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809`
- resolved config: LUT true, 2026~2030, cap 100/100, stream false, reasoning default

| Parameter | scenario | group | proposal | target cell | 결과 |
|---|---:|---:|---:|---:|---|
| GDP | 305 | 60 | 395 | 4 | PASS |
| PMI | 306 | 60 | 397 | 24 | PASS |
| PowerMix | 287 | 51 | 396 | 1 | PASS |
| Temperature | 289 | 52 | 399 | 1 | PASS |
| LiqUtilAdjustment | 105 | 18 | 398 | 5 | PASS |

모든 대상 target cell은 exact valid였고 missing/invalid/rejected가 0이었다. proposal DB row 395~399를 read-back해 status `PROPOSED`, target parameter/value 저장을 확인했다. raw graph 수동 실행이므로 callback은 `SKIPPED`였다.

## 5. 자동화 및 정적 검증

구현 완료 시점 검증:

- 관련 전체: `195 passed, 8 warnings, 14 subtests passed in 41.98s`
- 최종 리뷰 보완 focused: `29 passed, 8 warnings in 1.15s`
- compileall, 변경 파일 Ruff `F,E9`, 신규 test/state 전체 Ruff, format check, `git diff --check`: PASS

최종 문서와 실제 report 반영 후 동일 범위를 다시 실행했다.

- 최종 gate: `195 passed, 8 warnings, 14 subtests passed in 42.55s`
- warning: 기존 Pydantic ForwardRef deprecation 7건, LangGraph cache `allowed_objects` pending deprecation 1건
- 실패: 0

## 6. 영향 범위와 잔여 리스크

- 기본 LUT flag는 false이므로 배포 설정에서 true로 켜기 전까지 reference source는 basecase-only다. pipeline 정책은 동일하다.
- 실제 테스트는 설정된 로컬/개발 DB에 proposal row 395~399를 생성했다. DB mapping 데이터는 수정하지 않았다.
- LLM 결과는 비결정적이다. 이번 품질 REVIEW 세 항목은 계약 위반이 아니며 자동화 회귀와 report 근거로 추적한다.
- checkpointer를 새로 도입할 때는 request runtime object 직렬화 전략을 별도로 설계해야 한다.
- 배포, callback 실전송, K8s runtime 검증은 이번 구현 요청 범위가 아니어서 수행하지 않았다.

## 7. 구현 커밋

| Commit | 내용 |
|---|---|
| `2e70363` | structured output stream/reasoning 옵션 |
| `cd6be15` | LUT runtime settings |
| `783c88d` | typed LUT catalog/domain |
| `acd5012` | exact LUT proposal pipeline 통합 |
| `74ade4a` | 5-parameter 명시 scenario report runner |
| `baeceee` | authoritative projection, duplicate/state/report 리뷰 보완 |

사용자가 작업 전 보유한 architecture 문서 삭제 2건, `.claude/worktrees/`, `lut_basecase_*_20260709.md` 4건은 수정하거나 커밋하지 않았다.
