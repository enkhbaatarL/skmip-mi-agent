# model_parameter_agent 서비스 오픈 전 통합 점검 리포트

- 작성일: 2026-07-13 KST
- 대상: `apps/agents/model_parameter_agent/`, persistence/API, callback, deployment, LUT/basecase, prompt, DB 주입 문구
- 대상 파라미터: `GDP`, `PMI`, `PowerMix`, `Temperature`, `LiqUtilAdjustment`
- 목적: 서비스 오픈 전 크리티컬 이슈, 성능/운영 리스크, DB/basecase/LUT 적합성, prompt/persona/어투/DB 값 개선사항을 하나의 문서로 정리
- 산출물 성격: 코드 변경 없는 launch readiness review

## 0. 검토 방식

### 수행한 검토

1. Codex 직접 코드 리뷰
2. 5개 subagent 관점 리뷰
   - Backend/API reliability
   - LangGraph/algorithm/performance
   - Data/LUT/basecase
   - Prompt/product/domain
   - Security/ops/readiness
3. Claude Code interactive 교차 리뷰 시도
4. 자동화 테스트 실행
5. 이후 추가 질의 기반 보강
   - 5개 파라미터 단위/basecase/LUT 스케일 확인
   - 공통 `tabular` adapter 확인
   - 정수/소수 JSON 표현 이슈 확인
   - basecase raw 추출과 `BasecaseReference` float 변환 확인

### Claude interactive 결과

Claude Code CLI를 feedback mode로 실행했으나, 파일 탐색 중 세션 사용량 한도에 도달해 최종 리뷰 응답을 받지 못했다. 따라서 본 리포트의 finding 근거로 Claude 출력을 사용하지 않았다.

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

## 1. 종합 결론

현재 구현은 "LLM이 만든 좌표/값을 서버가 exact catalog와 sanitizer로 검증한다"는 큰 방향은 적절하다. 그러나 서비스 오픈 기준으로는 운영 배포, callback 보장, 상태 전이 원자성, prompt 계약, value validation, PowerMix/LiqUtil domain invariant가 아직 위험하다.

오픈 전 최소 조건은 다음이다.

1. 배포 아티팩트가 `model_parameter_agent` route를 실제 포함하는지 컨테이너 기준 smoke test
2. 운영 K8s에서 `MODEL_PARAMETER_LUT_ENABLED=true`, `skip_callback=false` 확정
3. callback retry/outbox 또는 reconciliation 보장
4. proposal status transition 조건부 update 적용
5. Step1.5/Step2가 "선택 없음"을 표현할 수 있도록 prompt 및 sanitizer 계약 보강
6. PowerMix full vector 또는 합계 정합 정책 확정
7. value type/range validation 추가
8. DB basecase 설정 오류 hard-fail
9. 5개 parameter 단위/스케일 문구를 DB `parameter_hint`/`mapping_comment`에 반영
10. callback receiver 포함 end-to-end smoke test

## 2. P0 - 오픈 전 해결 권고

### P0-1. 배포 아티팩트가 model_parameter_agent router를 포함하지 않을 수 있음

근거:

- `model_param.py`는 model parameter router를 등록한다.
- `Dockerfile.model_param`은 `model_param.py`를 `main.py`로 복사한다.
- 일반 `main.py`에서는 model parameter router 등록이 주석 처리되어 있다.
- `devops/compose/docker-compose.yml`은 일반 `Dockerfile` 기반 `scenario-group-agent` 이미지를 빌드한다.
- `devops/k8s/deployment.yaml`은 image만 지정하고 `Dockerfile.model_param` 사용 여부를 보장하지 않는다.

영향:

- 실제 배포 컨테이너에서 `/model-parameters/...` route가 없을 수 있다.

권고:

- model parameter 전용 이미지, service, deployment manifest를 명시한다.
- CI/release gate에 컨테이너 실행 후 route smoke test를 추가한다.

### P0-2. 운영 K8s 설정이 검증 조건과 반대임

근거:

- `envs/config.yaml`은 `model_parameter_lut_enabled: true`
- `devops/k8s/configmap.yaml`은 `skip_callback: true`
- `devops/k8s/configmap.yaml`은 `model_parameter_lut_enabled: false`
- 코드 기본값도 LUT false다.

영향:

- 기존 VM/테스트 리포트는 LUT on 기준이다.
- 배포가 false면 PMI/PowerMix/Temperature/LiqUtilAdjustment의 LUT-only row가 사라진다.
- callback skip이면 비동기 완료 신호가 backend에 전달되지 않는다.

권고:

- 운영 profile에서는 `MODEL_PARAMETER_LUT_ENABLED=true`, `skip_callback=false`를 명시한다.
- callback URL/token 누락 또는 skip true이면 readiness fail 정책을 둔다.

### P0-3. callback 전달 보장이 부족하고 실패 경로가 취약함

근거:

- callback client는 단일 POST와 401 token refresh 1회 외 5xx/timeout/429 retry가 없다.
- graph 실패 후 DB fail update가 먼저 실행되고, 이 DB write가 실패하면 error callback 생성 전 중단될 수 있다.
- callback 실패 상태 업데이트도 보호되지 않는다.

영향:

- backend가 completion/failure를 영구히 모를 수 있다.
- proposal이 `PROCESSING` 또는 callback `FAILED` 상태로 방치될 수 있다.

권고:

- callback outbox 또는 retry worker를 추가한다.
- idempotency key, attempt count, next_retry_at, last_error를 저장한다.
- DB 실패와 callback 발송을 분리하고 reconciliation 대상을 남긴다.

### P0-4. async endpoint/background에서 sync DB 호출이 이벤트 루프를 막음

근거:

- async endpoint와 async background flow에서 sync DB service를 직접 호출한다.
- graph 첫 노드의 scenario context load도 sync DB 작업이다.

영향:

- DB 지연 시 동일 worker의 LLM stream, callback, API 처리가 함께 지연될 수 있다.

권고:

- 단기: `asyncio.to_thread()` 또는 bounded executor로 격리
- 중기: background worker queue 또는 async DB 전환
- launch gate: 동시 요청 부하 테스트

### P0-5. proposal 상태 전이가 원자적이지 않음

근거:

- 완료 전이는 `id + del_yn`만 보고 `PROPOSED`로 변경한다.
- 실패 전이도 `id + del_yn`만 보고 `FAILED`로 변경한다.
- confirmation도 row lock 없이 `CONFIRMED`로 변경한다.

영향:

- stale/중복 background task가 이미 `CONFIRMED`된 row를 `PROPOSED` 또는 `FAILED`로 되돌릴 수 있다.
- 중복 요청, 재시도, worker race에서 last-write-wins가 발생한다.

권고:

- `PROCESSING -> PROPOSED/FAILED`, `PROPOSED -> CONFIRMED` 조건부 update로 바꾼다.
- affected row count가 0이면 stale transition으로 기록하고 후속 처리한다.
- confirmation은 row lock 또는 version/updated_at 조건을 둔다.

### P0-6. Step1.5 routing이 "해당 없음"을 표현하지 못함

근거:

- prompt가 min 1 / max 2 selection을 강제한다.
- 단일 routing candidate면 deterministic keep된다.
- sanitizer는 max 2와 no-selection contract를 강제하지 않는다.

영향:

- 잘못 매핑된 후보가 있을 때 LLM이 반드시 하나를 골라 false positive가 된다.
- 기존 Event19 PowerMix false positive가 이 구조에서 재발할 수 있다.

권고:

- Step1.5 selection을 `0..max`로 바꾼다.
- 단일 후보도 applicability check를 거치게 한다.
- "사건이 해당 parameter의 causal mechanism을 직접 설명하지 않으면 빈 배열" 규칙을 명시한다.

### P0-7. Step2 prompt가 slot 과선택을 유도함

근거:

- slot catalog leaf마다 min 1을 요구하는 문구가 있다.
- 동시에 "정확 좌표가 없으면 생략"이라는 반대 지시가 있어 충돌한다.
- raw selected slot cap을 exact validation 전에 적용한다.

영향:

- 관련 없는 slot/no-change proposal이 늘어난다.
- invalid slot이 cap을 먼저 소진해 valid slot이 밀릴 수 있다.

권고:

- Step2는 related exact slot만 반환하고 없으면 빈 배열을 허용한다.
- cap은 exact validation 이후 valid slot 기준으로 적용한다.

### P0-8. 후보 merge가 source dimension 역할을 섞음

근거:

- 같은 parameter/model 후보를 merge하면서 mapping comment가 결합되고 `source_dimension_key`/`mapping_method`가 흐려진다.
- 기존 review에서 scenario 280은 수입 시설 피해와 대체 LNG 공급이 LiqUtilAdjustment로 합쳐져 수입 시설 피해를 액화설비 감산으로 해석했다.

영향:

- 서로 다른 원인의 후보가 같은 parameter라는 이유로 합쳐져 잘못된 operation 방향을 만든다.

권고:

- 후보 merge 후에도 source dimension별 provenance를 유지한다.
- LiqUtilAdjustment는 수입/재기화/저장/운송 시설만 언급되면 액화 Train 감산 후보에서 제외한다.

### P0-9. PowerMix 합계/상쇄 정합이 약함

근거:

- Step3 slot payload는 단일 `reference_value`만 제공한다.
- PowerMix는 Country/Year 내 energy source vector 합계 정책이 필요한데, 현재 전체 vector context와 validator가 없다.

영향:

- 일부 energy source만 조정하면 전체 합계가 1.0을 벗어날 수 있다.

권고:

- 정책을 둘 중 하나로 명확히 정한다.
  - 독립 override 정책: 합계 1.0 검증을 요구하지 않는다고 product contract에 명시
  - full vector 정책: Country/Year 전체 energy source vector를 제공하고 합계 1.0 validator를 둠
- 어느 쪽이든 prompt/DB hint에 "value는 최종 비중, delta가 아님"을 명시한다.

### P0-10. proposed/confirmation value 타입과 범위 검증이 없음

근거:

- LLM schema의 `proposed_value`는 `Any`다.
- sanitizer는 null만 필터링한다.
- confirmation API도 required key/duplicate만 주로 검사하고 numeric range/type을 강하게 보지 않는다.

영향:

- `"10%"`, `"same"`, object/list, PowerMix 음수/1 초과, PMI 비정상값 등이 DB 저장 또는 확정될 수 있다.

권고:

- parameter별 value validator를 추가한다.
- 권장 범위:
  - GDP: 성장률 소수, 과도한 값 hard/soft guard
  - PMI: 일반적으로 0~100, 운영 추천 30~70 warning
  - PowerMix: 0~1, 정책에 따라 group sum check
  - Temperature: 물리 범위 guard
  - LiqUtilAdjustment: 0 이상, >1 허용 여부와 도메인 상한 명시

### P0-11. DB basecase 설정 오류가 hard-fail이 아님

근거:

- basecase extraction 실패가 warning/continue로 흐를 수 있다.
- explicit spec이 없으면 auto-detect fallback이 동작할 수 있다.

영향:

- 운영에서 sheet/column 설정 오류가 proposal 품질 저하로 은폐될 수 있다.

권고:

- 서비스 오픈 대상 parameter는 basecase read spec을 strict mode로 검증한다.
- 등록 parameter가 0 records면 startup/readiness fail 처리한다.

## 3. P1 - High priority 개선

1. `/proposals/sync` 테스트 route가 DB row를 만들 수 있으므로 운영 노출 여부를 분리한다.
2. confirmation payload가 원 proposal universe와 비교되지 않아 임의 slot/value 확정 가능성이 있다.
3. invalid slot이 cap을 먼저 소비하는 구조를 valid-after-validation cap으로 바꾼다.
4. prompt payload 크기와 latency budget을 parameter별로 계측한다.
5. `date.today()` 직접 사용 구간은 timezone/test clock 주입으로 바꾼다.
6. exact join canonicalization은 공백/표기 차이만 처리하므로 alias/country mapping 오류 가능성이 있다.
7. operational callback에는 `lutValue`가 빠져 provenance 확인이 어렵다.
8. LLM model/version/temperature/usage/prompt hash를 proposal metadata로 남긴다.
9. DEBUG body logging, callback body logging, config secret placeholder 노출을 운영 profile에서 제한한다.
10. K8s readiness/liveness probe, resource request/limit, graceful shutdown이 필요하다.

## 4. 5개 파라미터 단위, basecase, LUT, adapter 점검

### 요약

adapter 적용 후 최종 reference 스케일은 5개 모두 basecase와 LUT가 대체로 같은 단위/스케일로 맞는다. 다만 원본 LUT 단위가 다른데 adapter가 변환하는 케이스는 `GDP`, `Temperature`이고, `PowerMix`, `LiqUtilAdjustment`는 원본 LUT 값이 이미 소수라고 전제한다.

| Parameter | Basecase 실제값/단위 | LUT 원본 | Adapter 처리 | 최종 판단 |
|---|---|---|---|---|
| GDP | 성장률 소수. 예: `0.019` | GDP absolute `BUSD` | `current / previous - 1.0`로 성장률 변환 | 원본 단위는 다르지만 adapter가 맞춤 |
| PMI | index. 예: `49~54` | index. 대부분 `50.0` | 숫자화만 함 | 단위 동일 |
| PowerMix | `%` 표기지만 실제값은 소수 share. 예: `0.036`, `0.3` | Power Mix 소수 share `0~1` | 숫자화만 함 | 스케일 동일, 변환 없음 |
| Temperature | `℃`. 예: `-2.2~11.3` | HDD/CDD degree-days | `18 ± degree_days / divisor`로 ℃ 변환 | 원본 단위는 다르지만 adapter가 맞춤 |
| LiqUtilAdjustment | `%` 표기지만 실제값은 utilization coefficient. `0`, `0.244`, `1`, `>1` 존재 | `LNG plant utilisation %`, 값은 소수 | 숫자화만 함 | 스케일 동일, 변환 없음 |

### adapter 현황

| Parameter | Adapter | Layout | 설명 |
|---|---|---|---|
| GDP | `gdp_growth` | custom | GDP 금액을 성장률로 변환 |
| PMI | `tabular` | `year_columns` | 연도별 컬럼을 row로 펼침 |
| PowerMix | `tabular` | `row` | 행 단위 값을 그대로 읽음 |
| Temperature | `temperature_degree_days` | custom | HDD/CDD를 ℃로 변환 |
| LiqUtilAdjustment | `liq_util` | custom | Plant/Train metadata 복원, capacity 변환 |

공통 adapter는 `tabular` 하나이며 현재 `PMI`, `PowerMix`가 사용한다.

### PowerMix/LiqUtil percent scale 주의

`PowerMix`, `LiqUtilAdjustment`는 컬럼명이나 문서 단위가 `%`지만 adapter에서 `/100` 변환을 하지 않는다. 현재 원본 값이 이미 `0.30 = 30%` 형식이라 맞는 것이다. 만약 향후 source가 `30`을 "30%" 의미로 제공하면 현재 코드는 `30.0`으로 그대로 사용한다.

권고:

- DB hint/comment에 "0.30 = 30%" 스케일을 명시한다.
- PowerMix는 `0 <= value <= 1` guard를 둔다.
- LiqUtil은 `0 이상` guard와 `>1` 허용/상한 정책을 별도로 둔다.

### 정수/소수 JSON 표현

현재 공통 adapter와 LUT/basecase index는 값을 `strict_float()`로 통일한다.

- `30` -> `30.0`
- `50` -> `50.0`
- `0.3` -> `0.3`

basecase도 처음 raw 추출 단계에서는 Excel cell type을 보존하지만, `BasecaseReference.value` 생성 시 `strict_float()`를 거쳐 최종 prompt/reference 값은 float가 된다.

권고:

- 내부 계산 타입은 float 유지
- prompt/response/DB 저장 직전 JSON 숫자 정규화 helper 적용
- 정규화 정책:
  - finite float이고 `value.is_integer()`이면 `int(value)`
  - 소수부가 있으면 float 유지
  - bool은 변환하지 않음

예상 효과:

- PMI `50.0` -> `50`
- PowerMix `0.3` 유지
- GDP `0.019` 유지
- Temperature `5.0`은 `5`가 되므로, 온도에서 `5.0` 표시가 필요하면 parameter별 예외 정책을 둔다.

## 5. DB basecase/LUT 개선 권고

1. **LUT 운영 설정 hard gate**
   - 오픈 profile에서 LUT false이면 startup/readiness fail
   - 5개 parameter record count를 startup log와 health diagnostics에 기록

2. **basecase strict validation**
   - service-open 대상 parameter는 read mode, sheet, column role, value column, time descriptor를 startup에서 검증
   - auto-detect fallback은 개발 profile에만 허용

3. **source contract 문서화**
   - GDP: LUT source는 GDP absolute, service value는 growth decimal
   - PMI: index
   - PowerMix: decimal share, percent number 금지
   - Temperature: LUT source는 HDD/CDD, service value는 ℃
   - LiqUtilAdjustment: utilization coefficient, percent number 금지, capacity는 MTPM에서 MTPA로 변환

4. **range/sanity validator**
   - source load 시점과 final value 저장 시점 모두 검증
   - hard fail과 warning threshold를 분리

5. **provenance 노출**
   - callback에는 운영 정책상 `lutValue`를 숨기더라도, 내부 DB/diagnostic에는 effective source, basecase reference id, LUT reference id를 추적 가능하게 남긴다.

## 6. Prompt 및 persona 개선

### 공통 방향

- LLM에게 "반드시 하나 선택"을 시키지 말고, causal mechanism이 부족하면 빈 배열을 허용한다.
- `reference_value`는 최종값 스케일의 기준값이며 delta가 아니라고 반복 명시한다.
- `proposed_value`는 최종 입력값이지 변화분/변화율/보정률이 아니다.
- 각 step은 역할을 분리한다.
  - Step1.5: applicability judge
  - Step2: exact slot selector
  - Step3: conservative value proposer

### Step1.5 routing 문구 초안

```text
역할: 수급모델 parameter applicability judge.
각 후보가 scenario/event/dimension의 직접 인과 메커니즘으로 설명되는 경우에만 선택한다.
후보가 하나뿐이어도 자동 선택하지 않는다.
직접 인과가 부족하거나 운송/가격/수입시설 이슈가 parameter의 물리적 조정 축으로 이어지지 않으면 빈 배열을 반환한다.
선택 개수는 0개 이상, 최대 {maxRoutingCandidates}개다.
```

### Step2 slot 문구 초안

```text
역할: exact slot selector.
catalog에 존재하는 좌표 중 scenario가 직접 영향을 주는 slot만 반환한다.
관련 slot이 없으면 빈 배열을 반환한다.
leaf마다 최소 1개를 선택할 필요는 없다.
추정 좌표, 근접 좌표, 과거 시점, 단순 no-change slot은 반환하지 않는다.
```

### Step3 value 문구 초안

```text
역할: conservative final value proposer.
reference_value는 해당 exact 좌표의 현재 기준 최종값이다.
proposed_value는 reference_value 대비 delta가 아니라 모델에 입력할 최종값이다.
parameter_hint와 mapping_comment에 정의된 단위, 스케일, 범위를 반드시 따른다.
근거가 약하면 reference_value에 가까운 보수적 값을 제안한다.
문자열 percent, "same", object/list 값은 금지한다.
```

## 7. 5개 parameter DB 주입 문구 개선안

### GDP

`parameter_hint`:

```text
국가·연도별 real GDP growth rate의 최종 입력값이다. value는 성장률 소수다(0.03=+3%). BUSD 절대 GDP 금액이나 성장률 변화폭이 아니다. proposedValue는 해당 Country/Year의 최종 성장률로 입력한다.
```

`mapping_comment`:

```text
GDP 성장률, 경기침체, 경기부양, 생산 차질이 국가 경제성장률을 직접 바꾸는 경우에만 선택한다. 단순 LNG 가격 변동이나 특정 설비 차질은 GDP 영향이 명시된 경우에만 선택한다.
```

### PMI

`parameter_hint`:

```text
국가·연월별 제조업 PMI index의 최종 입력값이다. 50은 중립, 50 초과는 확장, 50 미만은 위축을 의미한다. proposedValue는 index level이며 변화폭이나 percent가 아니다.
```

`mapping_comment`:

```text
제조업 활동, 산업 생산, 공장 가동, 수출 주문, 공급망 충격이 특정 국가의 제조업 심리를 직접 변화시키는 경우 선택한다. 에너지 가격만 언급되고 제조업 활동 영향이 명시되지 않으면 선택하지 않는다.
```

### PowerMix

`parameter_hint`:

```text
국가·연도·에너지원별 발전량 비중의 최종 입력값이다. value는 소수 비중이다(0.30=30%). proposedValue는 증감폭이 아니라 해당 Country/Year/Energy Source의 최종 비중이다. percent number 30은 금지한다. 전체 vector 정책을 사용하는 경우 같은 Country/Year의 에너지원 합계는 1.0이어야 한다.
```

`mapping_comment`:

```text
전원믹스, 발전설비, 원전/석탄/재생에너지 정책, fuel switching처럼 발전원 비중이 구조적으로 바뀌는 경우에만 선택한다. LNG 운송 규제, 항로 제약, 운송비 상승, 수입 터미널 병목처럼 발전원 비중 변화가 명시되지 않은 사건은 선택하지 않는다.
```

### Temperature

`parameter_hint`:

```text
국가·연월별 평균 기온의 최종 입력값이다. value 단위는 섭씨(℃)다. proposedValue는 temperature anomaly나 HDD/CDD가 아니라 해당 Country/Year/Month의 최종 온도다.
```

`mapping_comment`:

```text
폭염, 한파, 계절 이상기온처럼 특정 국가·월의 온도 자체가 달라지는 사건에서 선택한다. 과거 월을 가리키면 과거 slot을 선택하지 말고, 지속 중인 현상이 명시된 경우에만 현재 이후 잔존 영향 월을 선택한다. 그렇지 않으면 다음 해당 계절의 미래 월로 이월한다.
```

### LiqUtilAdjustment

`parameter_hint`:

```text
LNG 액화 Plant Train의 월별 utilization coefficient 최종 입력값이다. 0.80=80% 가동률이며 percent number 80은 금지한다. 일반적으로 0~1이지만 기준 데이터에 1을 초과하는 Train/월이 있을 수 있으므로 근거 없이 1.0으로 cap하지 않는다.
```

`mapping_comment`:

```text
수출 시설, 액화 시설, LNG Plant, Train, upstream-to-liquefaction 운영 제약이 명시된 경우에만 선택한다. 수입 터미널, 재기화 시설, 저장 시설, 항만·운송·항로 제약만 언급된 경우 기존 LNG Plant Train 가동률을 직접 낮추지 않는다.
```

`alt_lng_supply_availability` 보강:

```text
대체 LNG 공급이 실제 수출국/액화 Plant Train의 추가 공급으로 설명되는 경우에만 대체 공급국 Train의 가동률 상향을 검토한다. 잔여 여력은 max(0, 1.0 - reference_value)를 기준으로 보수적으로 배분하고, 이미 고가동인 Train 또는 비운영 설비는 제외한다.
```

## 8. 성능/운영/보안 점검

### 성능

- sync DB 호출이 async path에 섞여 있어 event loop blocking 가능성이 있다.
- Step2/Step3 prompt payload가 LiqUtil 등에서 커질 수 있다.
- max slot cap은 exact validation 이후 적용해야 한다.
- LLM call latency, token usage, retry count를 parameter/step별로 계측해야 한다.

### 운영

- callback outbox/retry 부재가 가장 큰 운영 리스크다.
- stale `PROCESSING` 복구 job이 필요하다.
- deployment route smoke와 callback receiver smoke가 release gate에 있어야 한다.
- K8s probes/resources/graceful shutdown 설정이 필요하다.

### 보안

- 운영 profile에서 request/callback body DEBUG logging 금지
- config/secret placeholder와 실제 credential 혼재 점검
- callback token refresh 실패, 401 반복, 5xx retry 정책 필요
- sync/test endpoint 운영 노출 여부 확인

## 9. 권장 오픈 전 작업 순서

1. 배포 아티팩트와 K8s config 확정: model parameter image, route, LUT on, callback skip false
2. callback retry/outbox 및 실패 reconciliation 설계
3. proposal 상태 전이 조건부 update와 confirmation row lock/versioning
4. Step1.5 routing `0..max` 계약 변경
5. Step2 no-change/0-slot 계약 정리 및 valid-after-validation cap 적용
6. PowerMix 정책 확정: independent override 또는 full vector sum validation
7. proposed/confirmation value numeric/range validator 추가
8. DB basecase strict startup validation 및 auto-detect fallback 제한
9. 5개 parameter DB hint/comment 업데이트
10. 정수/소수 JSON 표현 정규화 여부 결정 및 적용
11. callback receiver 포함 end-to-end smoke
12. Event19, Scenario280, Temperature rollover, PowerMix, LiqUtil 회귀 테스트
13. 동시 요청/장시간 LLM/callback 장애 부하 테스트

## 10. Launch go/no-go checklist

| 항목 | 기준 | 상태 |
|---|---|---|
| route smoke | 배포 컨테이너에서 `/model-parameters/...` route 확인 | 필요 |
| LUT config | 운영 profile `MODEL_PARAMETER_LUT_ENABLED=true` | 필요 |
| callback | `skip_callback=false`, retry 또는 outbox | 필요 |
| status transition | stale task가 confirmed row 덮어쓰지 않음 | 필요 |
| Step1.5 | 후보 0개 반환 가능 | 필요 |
| Step2 | exact valid slot만 cap 적용 | 필요 |
| value validation | parameter별 type/range guard | 필요 |
| PowerMix | 합계 정책 문서화 및 validator/예외 정책 | 필요 |
| LiqUtil | 수입/재기화/운송 이슈 제외 규칙 | 필요 |
| numeric representation | 정수/소수 JSON 표현 정책 | 권장 |
| observability | LLM usage, callback attempt, proposal lifecycle metric | 필요 |
| tests | 5개 parameter 회귀 + callback receiver E2E | 필요 |

## 11. 미검증/제약

- 외부/테스트 DB를 직접 조회하지 않았다. DB 문구 개선안은 repo 문서, local basecase extract, LUT source, adapter code 기준이다.
- 실제 container build/run smoke는 수행하지 않았다.
- callback receiver 통합 테스트와 부하 테스트는 수행하지 않았다.
- Claude interactive는 실행했으나 사용량 한도로 최종 결과를 받지 못했다.
- 코드 변경은 하지 않았다.
