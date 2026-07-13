# model_parameter_agent 서비스 오픈 전 심층 리뷰 리포트

- 작성일: 2026-07-11 KST
- 대상: `apps/agents/model_parameter_agent/`, model parameter persistence/API, LUT/basecase 파이프라인, prompt 및 DB 주입 문구
- 대상 파라미터: `GDP`, `PMI`, `PowerMix`, `Temperature`, `LiqUtilAdjustment`
- 방식: Codex 직접 코드 리뷰 + 5개 subagent 병렬 리뷰 + Claude interactive 시도 + 자동화 테스트
- 결과: 코드 변경 없음. 본 문서는 launch readiness 판단용 리뷰 산출물이다.

## 0. 검토 방식과 한계

### 사용한 subagent persona

1. Backend/API reliability: API contract, DB transaction, callback, status transition
2. LangGraph/algorithm/performance: routing, slot/value proposal, prompt size, cap, validation
3. Data/LUT/basecase: coverage, exact join, unit/range, cache, source contract
4. Prompt/product/domain: step별 persona, DB `parameter_hint`/`mapping_comment`, rationale UX
5. Security/ops/readiness: deployment, callback config, auth, logging, secrets, observability

### Claude interactive

Claude Code CLI를 feedback mode로 실행했으나, 파일 탐색 중 세션 사용량 한도에 도달해 최종 리뷰 응답을 받지 못했다. 따라서 이 리포트의 finding 근거로 Claude 출력을 사용하지 않았다. 실행 시도 사실만 기록한다.

### 실행 테스트

```bash
poetry run pytest tests/automated/test_model_parameter_lut_domain.py \
  tests/automated/test_model_parameter_lut_pipeline.py \
  tests/automated/test_model_parameter_agent_contract.py -q
```

- 결과: `130 passed, 8 warnings in 13.47s`

```bash
poetry run pytest tests/automated/test_model_parameter_report_scope.py \
  tests/test_config_loader.py -q
```

- 결과: `30 passed, 8 warnings, 6 subtests passed in 5.56s`
- warning: Pydantic v1 `ForwardRef` deprecation, LangGraph cache `allowed_objects` pending deprecation

## 1. 결론

현재 구현은 "LLM이 만든 좌표/값을 서버가 exact catalog와 sanitize로 검증한다"는 큰 방향은 좋다. 하지만 서비스 오픈 관점에서는 다음 축이 아직 위험하다.

1. 운영 배포 설정이 검증 조건과 다르다: K8s는 LUT off, callback skip 상태다.
2. async API/백그라운드 경로에서 sync DB 호출과 상태 전이 원자성 문제가 있다.
3. callback 전달 보장이 약하고 실패 경로에서 callback 자체가 누락될 수 있다.
4. Step1.5 routing과 Step2 prompt가 "잘못된 후보/slot을 0개로 버리는" 계약을 갖지 못한다.
5. PowerMix는 full mix 합계 정합을 보장할 정보와 검증이 없다.
6. Step3 value와 confirmation value가 타입/범위 검증 없이 DB로 갈 수 있다.
7. DB basecase 설정 오류와 exact join 미스가 warning으로만 흐를 수 있다.
8. 프롬프트에 들어가는 DB `parameter_hint`/`mapping_comment`는 5개 parameter 중 PowerMix, Temperature, LiqUtilAdjustment가 특히 보강 필요하다.

오픈 전 최소 gate는 P0 항목 해결, LUT/callback 운영 설정 확정, callback receiver 포함 통합 테스트, 5개 parameter 회귀 시나리오 재실행이다.

## 2. P0 - 오픈 전 해결 권고

### P0-1. 배포 아티팩트가 model_parameter_agent 라우터를 포함하지 않을 수 있음

- 근거:
  - `model_param.py:170`은 model parameter router를 등록한다.
  - `Dockerfile.model_param:33`은 `model_param.py`를 `main.py`로 복사한다.
  - 일반 `main.py:87-91`은 model parameter router 등록이 주석 처리되어 있다.
  - `devops/compose/docker-compose.yml:6-10`은 일반 `Dockerfile` 기반 `scenario-group-agent` 이미지를 빌드한다.
  - `devops/k8s/deployment.yaml:18-20`은 이미지명만 있고 `Dockerfile.model_param` 사용 여부를 보장하지 않는다.
- 영향: 실제 배포 컨테이너에서 `/model-parameters/...` route가 없을 수 있다.
- 권고:
  - model_parameter 전용 이미지/서비스/매니페스트를 명시한다.
  - 빌드된 컨테이너 기준 route smoke test를 CI/release gate에 추가한다.

### P0-2. 운영 K8s 설정이 검증 조건과 반대임

- 근거:
  - `envs/config.yaml:47`은 `model_parameter_lut_enabled: true`
  - `devops/k8s/configmap.yaml:70`은 `skip_callback: true`
  - `devops/k8s/configmap.yaml:74`는 `model_parameter_lut_enabled: false`
  - `apps/common/configs/config.py:134`의 코드 기본값도 LUT false
- 영향:
  - 기존 VM/리포트 검증은 LUT on 기준이다.
  - 배포가 false면 PMI/PowerMix/Temperature/LiqUtilAdjustment의 LUT-only row가 사라진다.
  - callback skip이면 비동기 완료 신호가 backend에 전달되지 않는다.
- 권고:
  - 운영/개발 환경별 의도값을 명시한다.
  - `MODEL_PARAMETER_LUT_ENABLED=true`, `skip_callback=false` 조건으로 startup smoke와 `/proposals/sync` 5-parameter fixture를 release gate로 둔다.
  - callback이 필수인 profile에서 `skip_callback=true` 또는 callback URL/token 누락이면 startup/readiness fail로 막는다.

### P0-3. callback 전달 보장이 부족하고 실패 경로가 취약함

- 근거:
  - `callback_client.py:39-56`은 단일 POST, 401 refresh 1회 외 5xx/timeout/429 재시도가 없다.
  - `flow.py:273`에서 graph 실패 후 `fail_proposal_result()`가 먼저 실행되고, 이 DB write가 실패하면 error callback payload 생성 전 함수가 중단될 수 있다.
  - `flow.py:308`의 callback 실패 상태 업데이트도 보호되지 않는다.
- 영향: backend가 completion/failure를 영구히 모를 수 있고, proposal이 `PROCESSING` 또는 callback `FAILED` 상태로 방치될 수 있다.
- 권고:
  - callback outbox 또는 retry worker를 추가한다.
  - callback 요청에 idempotency key, attempt count, next_retry_at을 둔다.
  - DB 실패와 callback 발송을 분리하고, 어떤 경우에도 실패 callback 또는 reconciliation 대상이 남도록 한다.

### P0-4. async endpoint/background에서 sync DB 호출이 이벤트 루프를 막음

- 근거:
  - `api.py:70-79` async endpoint가 `prepare_propose_parameters_callback()` sync DB 작업을 직접 호출한다.
  - `flow.py:245`, `flow.py:273`, `flow.py:289`, `flow.py:308`에서 async background 함수가 sync DB service를 직접 호출한다.
  - `nodes.py:275`의 graph 첫 노드 `load_scenario_context()`도 sync DB load를 수행한다.
- 영향: DB 지연 시 동일 worker의 LLM stream/callback/API 처리까지 지연될 수 있다.
- 권고:
  - 최소 수정은 `asyncio.to_thread()` 래핑과 bounded worker다.
  - 장기적으로 async DB 또는 background worker queue로 분리한다.
  - 동시 요청 부하 테스트를 launch gate에 포함한다.

### P0-5. proposal 상태 전이가 원자적이지 않고 stale background task가 덮어쓸 수 있음

- 근거:
  - `repository.py:185-193` 완료 전이는 `id + del_yn`만 보고 `PROPOSED`로 변경한다.
  - `repository.py:205-216` 실패 전이도 `id + del_yn`만 보고 `FAILED`로 변경한다.
  - `repository.py:166-174` confirmation도 row lock 없이 `CONFIRMED`로 변경한다.
  - row가 없으면 repository가 조용히 return한다.
- 영향:
  - stale/중복 background task가 이미 `CONFIRMED`된 row를 `PROPOSED`/`FAILED`로 되돌릴 수 있다.
  - 중복 요청, 재시도, worker race에서 last-write-wins가 발생한다.
- 권고:
  - 완료/실패 update는 `WHERE id=? AND status='PROCESSING' AND del_yn='N'` 조건부 update로 바꾸고 affected row를 검사한다.
  - confirmation은 `SELECT ... FOR UPDATE` 또는 조건부 update로 원자화한다.
  - 동일 scenario active `PROCESSING` 재요청은 재사용 또는 409로 거부한다.

### P0-6. Step1.5 routing이 "해당 없음"을 표현하지 못함

- 근거:
  - `model_parameter_proposal.py:23-36`은 routing task당 최소 1개, 최대 2개를 강제한다.
  - `nodes.py:1277-1306`은 routing 후보가 1개면 LLM 판단 없이 deterministic 통과시킨다.
  - `nodes.py:2187-2242` sanitizer는 max 2를 강제하지 않고, 빈 선택을 명확한 no-selection으로 처리하지 않는다.
- 영향:
  - 의미상 맞지 않는 단일 routing 후보가 사실상 direct처럼 통과한다.
  - 기존 Event19 PowerMix false positive가 이 구조에서 재발할 수 있다.
- 권고:
  - routing 선택 계약을 `0..max`로 바꾼다.
  - 단일 routing 후보도 Step1.5 applicability judge로 보낸다.
  - 0개 선택 시 API 결과를 `NO_APPLICABLE_PARAMETER`, empty success, 또는 INVALID_REQUEST 중 하나로 명확히 정한다.
  - `model_parameter_max_routing_candidates_per_dimension`을 prompt와 sanitizer 양쪽에서 실제 사용한다.

### P0-7. Step2 prompt가 slot 과선택을 유도함

- 근거:
  - `model_parameter_proposal.py:65-75`는 catalog leaf가 있으면 최소 1개를 강제하면서, 연관성이 없으면 생략하라는 문장도 함께 둔다.
  - `nodes.py:840-940`은 모든 candidate task를 한 번에 Step2로 보낸다.
- 영향:
  - Step1.5에서 잘못 통과한 후보가 Step2에서 억지로 살아날 수 있다.
  - broad scenario에서 LUT universe가 proposal universe처럼 사용된다.
- 권고:
  - "관련 exact slot이 있을 때만 최소 1개, 없으면 0개 허용"으로 문구를 단일화한다.
  - no-change 검토용 slot과 실제 변경 proposal slot을 분리한다.
  - `change_intent` 또는 `selection_reason_type`을 추가해 no-change/no-impact noise를 줄인다.

### P0-8. 후보 merge가 source dimension의 역할을 섞음

- 근거:
  - `nodes.py:1204-1259`는 같은 parameter/model target 후보를 하나로 merge하며 `dimension_key=None`, `mapping_method=merged`, `mapping_comment` join으로 만든다.
  - 기존 full review에서 scenario 280은 `affected_facility_type=수입 시설`과 `alt_lng_supply_availability`가 LiqUtilAdjustment로 합쳐져 수입 시설 피해를 액화설비 감산으로 해석했다.
- 영향: direct/routing/indirect 역할과 방향성이 섞여 잘못된 slot/value를 만들 수 있다.
- 권고:
  - merge 전 routing applicability를 확정한다.
  - Step2/3 prompt에는 source dimension별 역할, direction, activation condition을 구조화해 전달한다.
  - 특히 LiqUtilAdjustment는 `affected_facility_type`이 수입/재기화/저장/운송 시설이면 액화 Train 감산 후보에서 제외해야 한다.

### P0-9. PowerMix 합계/상쇄 정합을 Step3가 보장할 수 없음

- 근거:
  - `nodes.py:1734-1743`의 Step3 slot payload는 slot별 `reference_value` 하나만 제공한다.
  - `model_parameter_proposal.py:115-117`도 single source reference만 설명한다.
  - PowerMix는 Country/Year 내 10개 Energy Source 합계가 1.0이어야 하지만 전체 mix context와 validator가 없다.
- 영향:
  - Gas 비중을 올리거나 내릴 때 상쇄 source 없이 합계가 깨질 수 있다.
  - 일부 source만 값이 바뀌어 모델 입력 전체 정합이 깨질 수 있다.
- 권고:
  - PowerMix Step3에는 같은 Country/Year의 전체 Energy Source vector를 제공한다.
  - full vector 변경 시 합계 1.0 검증을 서버에서 수행한다.
  - 상쇄 source가 선택되지 않았으면 reference 유지 또는 explicit review로 보내는 정책을 둔다.

### P0-10. proposed value와 confirmation value의 타입/범위 검증이 없음

- 근거:
  - `schemas/model_parameter_proposal.py:116`의 `LLMValueCell.proposed_value`는 `Any`
  - `nodes.py:2498-2505` sanitizer는 null만 제외한다.
  - `schemas/api/parameters.py:18-22` API value도 `dict[str, Any]`
  - `confirm_parameters/validation.py:254-287`은 required key/slot 중복 중심이며 numeric/range 검증이 없다.
- 영향: `"10%"`, `"same"`, object/list, PowerMix 음수/1 초과, PMI 비정상값 등이 DB 저장/확정될 수 있다.
- 권고:
  - parameter별 value policy를 둔다.
  - 공통 finite numeric 변환을 수행한다.
  - 권장 range: GDP 성장률 band, PMI 30~70, PowerMix 0~1 및 group sum, Temperature 물리 범위, LiqUtilAdjustment 도메인 상한.

### P0-11. DB basecase 설정 오류가 hard-fail이 아니라 잘못된 추출/누락으로 흐를 수 있음

- 근거:
  - `models.py:143-145`는 `basecase_read_mode` 값만 제한한다.
  - `parameter_mapping.py:947-965`에서 명시 spec이 없으면 auto-detect fallback으로 넘어간다.
  - `parameter_mapping.py:681-693`은 Excel 추출 예외를 warning 후 계속 진행한다.
- 영향: basecase 설정/엑셀 schema가 깨졌는데 LUT-only 또는 empty catalog 기반 proposal이 만들어질 수 있다.
- 권고:
  - active `tmm_mi_model_param_m` 전체 startup strict validation을 추가한다.
  - 명시 `read_mode` row는 auto-detect fallback을 금지한다.
  - "정상적으로 basecase 없음"과 "읽기 실패"를 분리한다.

## 3. P1 - High Priority 개선

### P1-1. `/proposals/sync`가 운영 router에 있고 실제 DB row를 저장함

- 근거: `api.py:28-43`, `flow.py:142-146`
- 영향: 테스트용 호출이 운영 DB에 `PROPOSED` row를 만들고 callback은 `SKIPPED`가 되어 latest proposal 판단을 오염시킬 수 있다.
- 권고: dev/test에서만 route 등록하거나 dry-run API로 분리한다.

### P1-2. confirmation이 원 proposal universe와 대조하지 않음

- 근거: `confirm_parameters/nodes.py:18-26`은 전역 parameter definition만 로드해 검증한다.
- 영향: 다른 proposal/scenario payload나 임의 target이 `CONFIRMED`로 저장될 수 있다.
- 권고: proposal row를 lock으로 읽고 기존 proposal의 parameter/target/slot universe와 비교한다. 사용자 추가를 허용한다면 별도 flag/권한/감사 이력을 둔다.

### P1-3. invalid slot이 cap을 먼저 소모해 valid slot을 떨어뜨릴 수 있음

- 근거:
  - `nodes.py:2276-2286`에서 Step2 raw response 개수 기준으로 cap을 먼저 적용한다.
  - exact membership 검증은 `nodes.py:584-633` 이후 단계에서 수행한다.
- 영향: 앞쪽 100개가 exact miss이고 101번째가 valid인 경우 valid slot이 먼저 버려진다.
- 권고: raw response cap은 방어용 큰 hard limit로만 두고, per-parameter cap은 exact reference 성공 후 valid slot 기준으로 적용한다.

### P1-4. prompt/token/latency budget이 부족함

- 근거:
  - Step2/Step3는 모든 candidate task를 단일 LLM call로 보낸다 (`nodes.py:840`, `nodes.py:741`).
  - cap은 parameter별이라 후보가 N개면 단일 호출에 최대 N*100 slot/value가 들어갈 수 있다.
  - 기존 리포트는 LiqUtil 99 cells 280초, Step2 prompt 109k tokens 사례를 기록한다.
- 권고:
  - prompt byte/token estimate를 호출 전 기록한다.
  - hard budget 초과 시 candidate별 chunking + bounded concurrency로 나눈다.
  - parameter별 production cap을 20~40 수준으로 낮추고 예외는 review로 보낸다.

### P1-5. 시간 해석이 wall-clock 의존이고 검증과 연결되지 않음

- 근거:
  - `nodes.py:2561-2569`는 `date.today()`를 직접 사용한다.
  - `_is_current_or_future_year_month()`는 정의되어 있지만 Step2 sanitizer에는 연결되어 있지 않다.
  - `nodes.py:2650-2663` helper는 명시 과거 연월을 그대로 반환할 수 있다.
- 영향: 같은 scenario가 실행일/서버 timezone에 따라 다른 slot을 고를 수 있고, 과거 월 exact slot이 통과할 수 있다.
- 권고:
  - `reference_date`를 state/request/config로 주입한다.
  - Asia/Seoul 기준을 명시하고 테스트에서 freeze 가능하게 한다.
  - Year/Month sanitizer에서 current/future 정책 위반을 warning/reject한다.

### P1-6. exact join 기준인데 문자열 축 정규화가 약함

- 근거:
  - `utils/lut/keys.py:18-34`는 문자열 축을 `strip()`만 한다.
  - `domain.py:261-274`에서 exact key miss는 `None`이 된다.
  - `nodes.py:625-633`은 missing reference를 warning 후 제외한다.
- 영향: 대소문자, 내부 공백, Unicode 차이로 valid source가 조용히 탈락할 수 있다.
- 권고:
  - axis별 canonicalizer를 도입한다: `casefold`, Unicode normalize, whitespace collapse, alias map.
  - 표시 원문은 metadata로 보존한다.
  - startup에서 "정규화하면 같은데 현재 exact mismatch" 목록을 리포트한다.

### P1-7. LUT/basecase provenance가 운영 payload에서 숨겨짐

- 근거:
  - `presentation.py:204-209`는 `include_lut_value=False`가 기본이다.
  - `nodes.py:1734-1743` Step3 payload도 `effective_source`, `lut_version`, `actual_basecase_value`, `lut_default_value`를 주지 않는다.
- 영향:
  - `basecaseValue=null -> proposedValue=...`가 신규 제안처럼 보일 수 있다.
  - PMI LUT 50 같은 "중립 default" 의미가 rationale에서 설명되지 않는다.
- 권고:
  - API 계약을 바꾸기 어렵다면 DB/debug/audit에 provenance를 보존한다.
  - UI/운영 문서에 `basecaseValue=null`은 "basecase override 없음"임을 명시한다.
  - Step3에는 사용자용 source label 정도는 제공한다.

### P1-8. LLM 재현성/관측성 부족

- 근거:
  - `nodes.py:1026-1034`는 `temperature=0.0`을 전달하지만 `llm_client.py:156-176`의 structured request kwargs에 temperature가 포함되지 않는다.
  - `nodes.py:418`, `nodes.py:800`, `nodes.py:900`은 LLM 예외를 warning 후 bare raise한다.
  - `llm_usage`는 단계별로 덮어써지고 누적 비용 필드가 없다.
- 권고:
  - structured output request에 temperature 적용 여부를 결정한다.
  - failed `llm_call` trace를 남긴다.
  - `llm_calls[].usage` 합산 필드를 추가한다.

### P1-9. auth/logging/secrets 운영 위험

- 근거:
  - `api.py:28` 이후 router에 FastAPI `Depends`/`Security`가 없다.
  - `request_logging.py:26-32`는 request body를 DEBUG로 출력한다.
  - `callback_client.py:26-30`, `flow.py:64-77`도 callback/proposal payload를 DEBUG로 출력한다.
  - `envs/config.yaml:68-70`, `devops/k8s/secret.yaml:7-12`에 credential-like 값 또는 placeholder가 있다.
- 권고:
  - gateway/mTLS/JWT 등 실제 ingress 보안 계약을 문서화하고 smoke test에 포함한다.
  - 운영 log level은 INFO 이상으로 두고 body/payload log는 redaction하거나 비활성화한다.
  - repo에 들어간 credential-like 값은 rotate하고 ExternalSecret/CI secret store로 이동한다.

### P1-10. observability/readiness 부족

- 근거:
  - `model_param.py` startup은 schema/LUT/basecase/token preload를 수행하지만 별도 readiness endpoint/probe가 없다.
  - `devops/k8s/deployment.yaml:17-41`에는 readiness/liveness/startup probe와 resource requests/limits가 없다.
  - `model_param.py`에는 일반 `main.py`의 MLflow tracing setup 흐름이 없다.
- 권고:
  - `/healthz`, `/readyz`를 분리한다.
  - LUT/basecase/token 상태를 readiness에 반영한다.
  - proposal_id/scenario_id 기반 trace context를 LLM 호출까지 전달한다.

## 4. DB/Basecase/LUT 평가

### 좋은 점

- `basecase override > LUT default` 정책은 적합하다.
- exact key union + server-side reference projection은 LLM 환각 방지에 효과적이다.
- LUT catalog는 duplicate conflicting key를 fail-fast 처리한다.
- 최신 count summary 기준 81개 scenario의 value row 2,131건은 current LUT lookup 2,131/2,131 매칭이었다.

### 보강 필요

1. **LUT enabled 운영값 확정**
   - 검증은 LUT on 기준이다. K8s false면 결과 품질과 coverage가 달라진다.

2. **coverage 기준 문서 정리**
   - 과거 문서에는 PMI t1 fallback/General full country list가 남아 있고, 최종 구현은 자체 LUT distinct 기준이다.
   - outdated 문서는 superseded 표시가 필요하다.

3. **custom adapter source contract 문서화**
   - GDP/Temperature/LiqUtil adapter는 헤더와 변환 상수를 코드에 갖고 있다 (`adapters.py:218`, `adapters.py:279`, `adapters.py:360`).
   - CSV source version/checksum/생성일/owner를 startup summary에 남긴다.

4. **parameter별 sanity validator**
   - GDP: growth band, horizon-1 year source 존재
   - PMI: 30~70 band, LUT 50은 neutral baseline
   - PowerMix: 0~1, Country/Year group sum 1.0
   - Temperature: 물리 범위, HDD/CDD 동시 양수 처리
   - LiqUtilAdjustment: percent 표기 금지, >1 기준값 처리 정책, 도메인 상한

5. **runtime cache 정책**
   - 정적 자산은 재배포/재기동만 허용한다고 운영 절차에 명시하거나, hot replace가 필요하면 cache key를 sha256 기반으로 통일한다.

## 5. Prompt 및 DB 주입값 개선

### 5.1 Step1.5 Candidate Validation

현재 persona는 "routing 후보 선택 agent"이며 반드시 1개 이상 선택하도록 되어 있다. 서비스 오픈 전에는 "applicability judge"로 바꿔야 한다.

권장 방향:

```text
당신은 routing 후보의 적용 가능성을 판정하는 수급모델 input parameter applicability judge입니다.
각 task에서 선택 가능한 candidate_key는 0개 이상, 최대 {max_candidates}개입니다.
mapping_comment의 적용 조건이 scenario/dimension에서 명시적으로 충족되지 않으면 0개를 반환합니다.
단순 가능성, 간접 관련성, basecase slot 존재 여부만으로 후보를 선택하지 않습니다.
```

### 5.2 Step2 Slot Proposal

현재 Step2는 no-change/minimal-change도 slot을 고르게 한다. 운영 proposal에서는 불필요한 no-change row와 과선택 비용이 커진다.

권장 방향:

```text
관련 exact slot이 있을 때만 slot을 반환합니다.
조정 필요성이 없거나 scenario/event와 연결할 exact 좌표가 없으면 0개를 반환할 수 있습니다.
no-change 확인 목적의 slot은 실제 변경 proposal과 구분하고 rationale에 "기준값 유지" 근거를 명시합니다.
```

### 5.3 Step3 Value Proposal

현재 Step3는 모든 slot에 값을 반환하게 하지만 numeric/type/range와 parameter-specific rule이 약하다.

권장 방향:

- proposed_value는 JSON number만 허용
- parameter별 허용 범위와 단위를 prompt와 서버 validator에 모두 반영
- reference source를 사용자용 용어로 설명
- uncertainty는 모호한 표현 대신 "정량 근거 없음", "보수 조정", "기준값 유지"로 작성

### 5.4 5개 파라미터별 DB 문구 보강안

#### GDP

현재 문구는 대체로 양호하다. 단기/장기 역할 분리를 더 강하게 한다.

```text
국가·연도별 실질 GDP 전년 대비 성장률의 최종 입력값이다. value는 증감폭이 아니라 해당 Country/Year에 적용할 성장률 자체이며 소수로 입력한다(0.042=4.2%). 통상 범위는 -0.10~+0.10이다. 1년 미만의 단기 수요·가격·심리 충격은 연간 GDP 경로를 직접 바꾸지 않는 것이 원칙이며, 산업활동 단기 변화는 PMI를 우선 검토한다. LNG 수요 변화율이나 가격 변화율을 GDP multiplier로 사용하지 않는다.
```

#### PMI

PMI는 절대 index, neutral 50, 타국 앵커링 금지를 명확히 한다.

```text
국가·연월별 PMI 지수 절대값이다(예: 49.5). 50은 중립, 50 초과는 확장, 50 미만은 위축을 의미한다. 통상 범위는 35~65이며 proposedValue는 basecase 대비 차이가 아니라 최종 PMI 값이다. PMI는 단기 산업활동·제조업·서비스업 경기 민감도 변수로 사용하고, 국가별 절대 수준이 다르므로 다른 국가의 PMI 값을 기준값으로 삼지 않는다.
```

#### PowerMix

PowerMix는 가장 위험하다. full mix, 합계 1.0, 운송/항로 제외 조건이 필요하다.

```text
국가·연도·에너지원별 전체 발전량 비중의 최종 입력값이다. value는 소수 비중이다(0.30=30%). proposedValue는 증감폭이 아니라 해당 Country/Year/Energy Source의 최종 비중이다. 전체 에너지원 벡터를 함께 조정하는 경우 합계는 1.0이어야 한다. 일부 에너지원만 조정할 때는 상쇄되는 에너지원과 합계 정합성을 rationale에 설명한다. LNG 운송비·항로·수입 터미널 문제만으로는 PowerMix를 선택하지 않는다.
```

Event19 routing comment 보강:

```text
전원믹스·탄소규제·발전설비·연료전환 정책처럼 Gas/Coal/Nuclear/Renewable 비중이 구조적으로 바뀌는 경우에만 PowerMix를 선택한다. LNG 운송 규제, 항로 제약, 운송비 상승, 수입 터미널 병목처럼 발전원 비중 변화가 명시되지 않은 사건은 PowerMix를 선택하지 않는다.
```

#### Temperature

과거 월 금지와 계절/peak 해석이 핵심이다.

```text
국가·연월별 평균 기온의 최종 입력값이다. value는 섭씨 절대값이며 편차가 아니다. 한파는 basecase 대비 하향, 폭염은 basecase 대비 상향으로 조정한다. 국가별 기후 차이가 크므로 다른 국가의 기온을 기준값으로 삼지 않는다. 과거 월은 입력하지 않고 현재 이후 예측 대상 기간의 해당 계절 월에 적용한다. 한파는 보통 11~3월, 폭염은 보통 6~9월을 우선 검토한다.
```

Cold/heat comment 보강:

```text
peak_timing_pattern이 과거 월을 가리키면 과거 slot을 선택하지 말고, 시나리오가 지속 중임을 명시한 경우에만 현재 이후 잔존 영향 월을 선택한다. 그렇지 않으면 다음 해당 계절의 미래 월로 이월한다.
```

#### LiqUtilAdjustment

현재 "Base Case에 존재하는 Train만" 문구는 LUT-only effective slot과 충돌한다. 또한 >1 reference를 임의 cap하지 말아야 한다.

```text
활성 기준카탈로그(Basecase override 또는 BCLiquefaction LUT)에 존재하는 LNG Plant Train만 수정한다. value는 월별 가동률 계수이며 100 같은 percent 표기는 금지한다. 일반적으로 0~1이지만 기준값이 1을 초과하는 Train/월은 모델 기준값을 인정하고, 명확한 감산/증산 근거 없이 1.0으로 강제 cap하지 않는다. Closed 설비는 제외하며, Planned/Speculative 설비는 시나리오가 해당 설비의 가동 개시·지연을 명시한 경우에만 선택한다.
```

`affected_facility_type` routing comment 보강:

```text
affected_facility_type이 수출 시설, 액화 시설, LNG Plant, Train, upstream-to-liquefaction 운영 제약을 명시할 때만 LiqUtilAdjustment를 선택한다. 수입 터미널, 재기화 시설, 저장 시설, 항만·운송·항로 제약만 언급된 경우에는 기존 LNG Plant Train 가동률을 직접 낮추지 않는다.
```

`alt_lng_supply_availability` comment 보강:

```text
대체 LNG 공급이 실제 수출국/액화 Plant Train의 추가 공급으로 설명되는 경우에만 대체 공급국 Train의 가동률 상향을 검토한다. 잔여 여력은 max(0, 1.0 - reference_value)를 기준으로 보수적으로 배분하고, 이미 고가동인 Train 또는 비운영 설비는 제외한다. 수입 시설 피해만 있는 경우 피해 시설을 액화 Train 감산으로 해석하지 않는다.
```

## 6. 권장 오픈 전 작업 순서

1. 배포 아티팩트와 K8s config 확정: model_param image, LUT on/off, callback skip false
2. callback retry/outbox 및 실패 reconciliation 설계
3. proposal 상태 전이 조건부 update와 confirmation row lock
4. Step1.5 routing `0..max` 계약 변경 및 단일 routing도 LLM/규칙 판단
5. Step2 no-change/0-slot 계약 정리
6. PowerMix full vector context 및 합계 validator 추가
7. proposed/confirmation value numeric/range validator 추가
8. DB basecase strict startup validation 및 auto-detect fallback 제한
9. 5개 parameter DB hint/comment 업데이트
10. callback receiver 포함 end-to-end smoke, stale PROCESSING 복구, Event19/Scenario280/Temperature rollover 회귀 테스트

## 7. 미검증/제약

- 외부/테스트 DB를 직접 조회하지 않았다. DB 문구는 레포 문서와 실행 리포트에 노출된 값 기준이다.
- Claude interactive는 실행했으나 사용량 한도로 최종 결과를 받지 못했다.
- 실제 컨테이너 이미지 build/run smoke, callback receiver 통합 테스트, 부하 테스트는 이번 작업에서 수행하지 않았다.
- 코드 변경은 하지 않았다.
