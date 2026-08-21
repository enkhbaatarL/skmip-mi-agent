# Model Parameter Agent 개요

## 1. Parameter Agent의 목적

Model Parameter Agent는 시나리오가 수급모델에 미치는 영향을 모델 입력 파라미터의 변경안으로 제안한다.

- v1 단일 이벤트와 v3 멀티 이벤트는 기존 DB mapping으로, v4는 선택 dimension value의 Lever state와 catalog binding으로 관련 파라미터를 찾는다.
- Basecase와 LUT에 실제로 존재하는 국가·기간·시설 slot만 사용한다.
- 현재 기준값을 바탕으로 제안값과 근거를 만든다.
- 사용자가 검토·수정한 최종값을 확정 상태로 저장한다.

현재 DB/canonical master의 활성 대상은 `GDP`, `PMI`, `PowerMix`, `Temperature`, `Population`, `User-Adjusted Gas Demand`, `HurricaneIntensity`, `LiqProdAdjustment`, `LiqUtilAdjustment`, `PipelineAdjustment`, `RegasAdjustment`, `SupplyDisruption`, `PNG Contract Volume`, `RemainingUnrestrictedAmount`, `ShippingCost`, `VolumeCancelled`의 16개다. 이 중 LUT-backed는 10개, Basecase-only는 6개다. `CDD`, `HDD`, Coal/Gas Futures, `ElectrificationRate`는 비활성이다. CDD/HDD binding은 catalog capability 진단을 위해 남지만 v4 raw 후보에서는 `INACTIVE_MODEL_PARAMETER`로 제외된다.

v1은 scenario group의 대표 event type과 scenario dimension key를 mapping에 대입한다. `generation_strategy=multi_event_composite_dimensions`인 v3는 `dimensionDefinitions[].sourceRefs`로 원본 `(event_type_l2_id, dimKey)`를 복원해 공유 legacy 129개 mapping을 재사용한다. `generation_strategy=multi_event_model_lever_dimensions`인 v4는 이 mapping, Event Type, 과거 `lever_mappings` 계열을 조회하거나 fallback으로 사용하지 않는다. 선택된 value의 `lever_states`와 active Lever catalog를 엄격히 검증한 뒤 executable binding으로 raw 후보를 만든다.

모든 버전의 신규 proposal은 raw 후보 생성 후 `GDP`, `PMI`, `PowerMix`, `Temperature`, `LiqUtilAdjustment` 5개 runtime allow-list를 공통으로 적용한다. 제한은 Step1.5·LLM 호출·proposal 행 생성 전에 적용한다. DB/canonical에 활성으로 남은 나머지 11개와 그 resource capability는 삭제하지 않지만 신규 proposal로는 제안하지 않는다.

v4 master와 Lever의 기계 판정 기준은 [parameter canonical](../../../../scripts/model_parameter/model-parameter-canonical-v4.json)과 [Lever canonical](../../../../scripts/model_parameter/model-impact-lever-canonical-v4.json)이다. v1/v3 최종 mapping은 [v1 canonical](../../../../scripts/model_parameter/model-parameter-canonical-v1.json)의 `dimension_mappings` 129행이 기준이며, 해당 fixture의 master 활성 10개 정의를 현재 공용 v4 master에 덮어쓰지 않는다. 사람이 읽는 설명은 [canonical mapping 문서](../resources/Model_Parameter_Base_Case_Mapping.md), 업무용 표는 [v4 canonical workbook](../resources/mapping/260813_시나리오가정_MI수급모델_input_매핑_model-parameter-canonical-v4.xlsx)이다. workbook은 v4 master·Lever와 현재 v1/v3 mapping 129행을 함께 보여 준다. 2026-08-13 v4 적용 전 snapshot의 128행·25/2/55/46은 변경 전 증적이지 현재 mapping이 아니다.

### 1.1 v3와 v4의 제안 가능 범위

“master에서 활성”, “mapping/binding이 도달할 수 있음”, “신규 proposal에 제안할 수 있음”은 서로 다른 뜻이다. 현재 공용 master는 16개가 활성이고, v1/v3 raw mapping-reachable set은 LUT-backed 10개, v4 raw executable-binding set은 고유 활성 parameter 16개다. 실제 신규 proposal은 버전과 관계없이 runtime allow-list 5개와의 교집합만 사용한다. 개별 Scenario에서는 관련 분기·변화 state·routing 결과·exact Basecase/LUT slot 존재 여부에 따라 더 좁아진다.

| Parameter | v1/v3 raw mapping | v4 raw binding | 신규 proposal | 기준값 | 판정 근거와 용도 |
|---|---|---|---|---|---|
| `GDP` | direct 1건 | `economic_activity` primary | 허용 | LUT-backed | 연간 경기 변화를 직접 표현한다. |
| `PMI` | direct 1건 | `economic_activity` alternative | 허용 | LUT-backed | 월 단위 산업 경기를 GDP보다 세밀하게 표현한다. |
| `PowerMix` | direct 12건 + routing 1건 | `power_generation_mix` primary | 허용 | LUT-backed | 발전소·연료전환 Event를 가스 발전 비중으로 연결한다. |
| `Temperature` | direct 2건 | `weather_demand` primary | 허용 | LUT-backed | 한파·폭염을 중복 degree-day 입력 대신 최종 기온 입력으로 표현한다. |
| `LiqUtilAdjustment` | direct 9건 + routing 1건 | `liquefaction_availability` primary | 허용 | LUT-backed | 기존 Train의 단기·부분 차질과 회복을 월별 가동률로 표현한다. |
| `Population` | routing 1건 | `economic_activity` alternative | runtime 제외 | LUT-backed | 인구·이민·인구전망 변화용 capability는 보존한다. |
| `HurricaneIntensity` | routing 1건 | `natural_disaster_disruption` primary | runtime 제외 | LUT-backed | 미국 GoM 허리케인·승인 시설·Year/Month capability를 보존한다. |
| `LiqProdAdjustment` | direct 4건 + routing 1건 | `liquefaction_availability` alternative | runtime 제외 | LUT-backed | 대폭·영구 생산손실·신규 Train ramp-up capability를 보존한다. |
| `PipelineAdjustment` | direct 2건 | `pipeline_capacity` primary | runtime 제외 | LUT-backed | 파이프라인 송출능력 exact-slot capability를 보존한다. |
| `SupplyDisruption` | direct 4건 + routing 1건 | `upstream_production` primary | runtime 제외 | LUT-backed | upstream 생산·자연재해·지정학 공급량 capability를 보존한다. |
| `User-Adjusted Gas Demand` | direct/routing 없음 | `direct_gas_demand` primary | runtime 제외 | Basecase-only | 검증된 workbook exact 좌표 capability를 보존한다. |
| `RegasAdjustment` | direct/routing 없음 | `regasification_capacity` primary | runtime 제외 | Basecase-only | 재기화 workbook exact-slot capability를 보존한다. |
| `PNG Contract Volume` | direct/routing 없음 | `contract_volume` alternative | runtime 제외 | Basecase-only | 계약량 변화의 exact-slot capability를 보존한다. |
| `RemainingUnrestrictedAmount` | direct/routing 없음 | `trade_restriction` primary | runtime 제외 | Basecase-only | 제재 후 거래 가능 잔여 물량 capability를 보존한다. |
| `ShippingCost` | direct/routing 없음 | `shipping_cost`, `route_disruption` primary | runtime 제외 | Basecase-only | 운임·항로 우회의 Trade exact-slot capability를 보존한다. |
| `VolumeCancelled` | direct/routing 없음 | `contract_volume` primary, `trade_restriction` alternative | runtime 제외 | Basecase-only | 계약 취소·무역 제한 capability를 보존한다. |
| `CDD` | 불가 | raw alternative binding만 보존 | 비활성 | 독립 LUT 없음 | Temperature adapter 입력 원재료이며 `INACTIVE_MODEL_PARAMETER` 진단만 남긴다. |
| `HDD` | 불가 | raw alternative binding만 보존 | 비활성 | 독립 LUT 없음 | CDD와 같이 Temperature adapter의 입력 원재료다. |
| `Coal Futures Price` | 불가 | binding 없음 | 비활성 | disabled LUT | 2026년 이후 유효 strip이 없어 과거값을 이월하지 않는다. |
| `Gas Futures Price` | 불가 | binding 없음 | 비활성 | disabled LUT | Coal Futures와 같은 이유로 보류한다. |
| `ElectrificationRate` | 불가 | binding 없음 | 비활성 | LUT spec 없음 | 유효 Basecase/LUT/legacy 연결이 없어 capability가 미완성이다. |

여기서 과거 개발자의 주관적 의도는 코드만으로 단정할 수 없다. 확인 가능한 사실은 v4 적용 전
2026-08-13 v4 적용 전 snapshot의 활성 5개가 당시 legacy direct/routing의 고유 후보 5개와 정확히 일치했다는
점이다. 당시 13개 dimension 행은 `mapping_method=na`, `model_param_id=NULL`이었고 Population routing 행은 없었다. 기존 v1/v3 mapping rollout은 해당 13행을 승인된 direct/routing으로 복구하고 Population routing 1행을 추가해 raw mapping-reachable set을 10개로 늘렸다. 이번 runtime allow-list 변경은 이 DB mapping 범위와 별도이며, DB master·mapping, v4 Lever catalog/checksum·Scenario/proposal 데이터를 바꾸지 않는다.

## 2. 다섯 가이드와 이해도 퀴즈 요약

### 2.1 API 문서

[API 문서](02_MODEL_PARAMETER_AGENT_API_SPEC.md)는 제안 요청과 사용자 확정 방법을 설명한다.

| API                                                                    | 목적                                |
| ---------------------------------------------------------------------- | ----------------------------------- |
| `POST /model-parameters/scenarios/{scenario_id}/proposals/sync`        | 제안 결과를 동기 방식으로 바로 확인 |
| `POST /model-parameters/scenarios/{scenario_id}/proposals`             | 운영에서 비동기 제안 작업 접수      |
| `POST /model-parameters/proposals/{modelParamProposalId}/confirmation` | 사용자가 검토·수정한 값을 최종 확정 |

### 2.2 DB 문서

[DB 문서](03_MODEL_PARAMETER_AGENT_DB_SPEC.md)는 파라미터 기준, 시나리오 연결 규칙, 제안·확정 결과의 저장 구조를 설명한다.

| 테이블                             | 역할                                                                 |
| ---------------------------------- | -------------------------------------------------------------------- |
| `tmm_mi_model_param_m`             | 파라미터명, 모델 대상, Basecase 읽기 기준, prompt hint 관리          |
| `tmm_mi_model_param_dimension_map` | 원본 event type·dimension과 파라미터의 연결 방법 관리                |
| `tmm_mi_model_impact_lever_m`      | v4 Lever 정의, binding, catalog version과 활성 상태 관리             |
| `tmm_mi_scenario_group_event_m`    | v3/v4 그룹의 ordered event 관계 관리                                |
| `tmm_mi_dimension_value_mapping_m` | v3 자유 value의 source projection과 승인 상태 관리                  |
| `tmm_mi_model_param_proposal_m`    | 제안 상태, 제안값, 확정값, 오류·callback 결과 저장                   |

### 2.3 Flow 문서

[Flow 문서](04_MODEL_PARAMETER_AGENT_FLOW.md)는 다음 핵심 처리 순서와 Step1.5·Step2·Step3 prompt를 설명한다.

```text
시나리오·그룹 전략 조회
→ v1/v3 legacy lineage 또는 v4 선택 value·Lever provenance 정규화
→ legacy mapping 또는 v4 executable Lever binding으로 raw 후보 결정
→ runtime proposal allow-list 5개로 필터
→ Step1.5 legacy routing 또는 v4 primary/alternative 후보 선택(필요한 경우)
→ Basecase/LUT slot catalog 생성
→ Step2 적용 slot 선택
→ Basecase 우선 기준값 결정
→ Step3 제안값·파라미터 근거·slot 근거 생성
→ 서버 검증 및 PROPOSED 저장
→ 사용자 확인 및 CONFIRMED 저장
```

v3/v4의 그룹 이벤트는 `display_order` 순서로 Step1.5·Step2·Step3의 `scenario_brief.events`에 들어간다. v4는 선택한 value의 state만 사용하며 dimension/value/primary Lever, `source_event_ids` 부분집합, Lever code/ID, catalog checksum을 strict 검증한다. checksum이 다르거나 catalog에 없는 code·ID가 있으면 proposal을 중단하고 해당 Scenario를 현재 catalog로 재생성해야 한다.

v1/v3에서 한 composite dimension이 여러 파라미터에 연결되면 direct/routing 정책에 따라 모두 유지한다. v4에서 여러 dimension/value/Lever가 같은 파라미터로 수렴하면 전체 Lever provenance를 보존한 하나의 task로 병합한다. 값은 서버가 source별 결과를 합산·평균하거나 Lever 방향을 숫자 부호로 변환하지 않고, LLM이 전체 근거를 종합해 slot별 최종 절대값 하나를 제안한다.

scenario `595`를 이용한 실제 prompt 입력·출력과 제안 결과도 Flow 문서에 포함되어 있다.

### 2.4 Basecase·LUT 문서

[Basecase·LUT 문서](05_MODEL_PARAMETER_AGENT_BASECASE_LUT_PARSING.md)는 파일 준비, 파싱 설정, exact slot 결합과 기준값 선택 방법을 설명한다.

| 구분      | 활용 내용                                                               |
| --------- | ----------------------------------------------------------------------- |
| Basecase  | Demand·Supply·Trade 모델 Excel에 현재 입력된 기준값                     |
| LUT       | LUT-backed 활성 10개 파라미터의 기본 참고값 CSV와 계산 adapter          |
| Basecase-only | 신규 활성 6개 파라미터는 검증된 Basecase exact slot에서만 실행      |
| 선택 기준 | 같은 exact slot에 Basecase 값이 있으면 우선 사용하고, 없으면 LUT 사용. Basecase-only에는 LUT fallback 없음 |
| 파일 준비 | 애플리케이션 시작 시 S3 호환 Object Storage 또는 packaged 파일에서 준비 |

Basecase와 LUT는 파라미터 후보를 새로 결정하지 않는다. canonical resource capability 10+6은 그대로 준비·검증하되, 신규 proposal Flow에서는 runtime allow-list를 통과한 5개에 대해서만 실제 선택 가능 exact slot과 기준값을 사용한다. Basecase와 LUT가 모두 없는 slot은 제외한다.

### 2.5 파라미터 추가 가이드

[파라미터 추가 가이드](06_MODEL_PARAMETER_AGENT_PARAMETER_ADDITION_GUIDE.md)는 canonical master, v4 Lever binding, legacy mapping 분리, Basecase/LUT capability와 prompt 크기 보호를 함께 변경하고 검증하는 순서를 설명한다.

`LiqProdAdjustment`는 DB/canonical에서 활성이고 `BCLiquefaction.csv`의 월 생산능력 × 이용률로 LUT 값을 만든다. legacy mapping과 v4 alternative binding capability는 보존하지만 현재 runtime allow-list 밖이므로 신규 proposal에서는 제외된다. 같은 액화 가용성 경로에서는 allow-list에 포함된 `LiqUtilAdjustment`만 proposal 처리로 진입한다.

### 2.6 핵심 이해도 퀴즈

[핵심 이해도 퀴즈](07_MODEL_PARAMETER_AGENT_COMPREHENSION_QUIZ.md)는 API·DB·전체 Flow·Basecase/LUT·prompt와 token 절감·파라미터 추가 절차를 고르게 다루는 10문항과 정답·해설로 구성한다.

## 3. Parameter Agent 디렉토리 구조

[루트 README](../../../../README.md)의 구조 설명 방식과 현재 파일 배치를 기준으로 핵심 경로만 나타내면 다음과 같다.

```text
skmip-mi-agent/
├── model_param.py                         # 전용 FastAPI 실행 진입점
├── Dockerfile.model_param                 # Model Parameter Agent 이미지 빌드
├── apps/
│   ├── agents/model_parameter_agent/
│   │   ├── api.py                         # 제안·확정 API
│   │   ├── presentation.py                # API 응답 조립
│   │   ├── flows/
│   │   │   ├── propose_parameters/        # 후보·slot·값 제안 Flow
│   │   │   └── confirm_parameters/        # 사용자 확정 Flow
│   │   ├── prompts/                       # Step1.5·Step2·Step3 prompt
│   │   ├── schemas/                       # API·제안 데이터 구조
│   │   ├── persistence/                   # Agent 업무 단위 DB service
│   │   ├── utils/
│   │   │   ├── basecase.py                # Basecase 읽기
│   │   │   ├── lut/                       # LUT adapter·catalog·결합
│   │   │   └── resource_*.py              # 파일 준비·runtime 경로
│   │   ├── resources/
│   │   │   ├── basecase/                  # packaged Basecase
│   │   │   ├── lut/                       # packaged LUT
│   │   │   └── mapping/                   # canonical Excel과 이전본 archive
│   │   └── docs/                          # 현재 설명 문서
│   ├── connectors/object_storage/         # S3 호환 Object Storage 연결
│   └── persistence/
│       ├── model_parameter/               # 공용 parameter ORM·repository·DTO
│       └── model_impact_lever/             # 공용 Lever catalog service·repository·DTO
├── envs/config.yaml                       # 로컬 실행·resource 설정
├── devops/k8s/configmap.yaml              # 배포 환경 설정
└── tests/
    ├── automated/test_model_parameter_*.py
    ├── manual/model_parameter_agent/
    └── reports/model_parameter_agent/     # 시나리오 테스트 리포트
```

API는 `api.py`에서 시작해 `flows/`로 들어간다. 제안 Flow는 전략에 따라 v1/v3 legacy mapping adapter 또는 v4 Lever-native context loader로 raw 후보를 만든 뒤, 공통 runtime allow-list를 Step1.5·LLM·저장보다 먼저 적용한다. 허용 후보만 Basecase/LUT, prompt와 저장 service로 전달한다. v1 proposal은 대표 event ID를 저장하지만 v3/v4 proposal은 `mi_event_id=NULL`로 저장하고 `scenario_group_id`를 authoritative link로 사용한다. 외부 API의 기존 optional `eventId`도 v3/v4에서는 `null`이며 새 필드는 추가하지 않는다. DB query는 flow/node가 직접 작성하지 않고 Agent service와 `apps/persistence/`의 domain service/repository를 통해 실행한다.

확정 단계의 custom parameter 허용 동작, 기존 저장 데이터와 JSON shape은 그대로 유지한다. `proposedValue`는 proposal과 confirmation 모두 유한 숫자인지만 검사하고 Step3 또는 persistence에서 설정 기반 소수 자릿수 round/trunc/ceil을 적용하지 않는다. JSON numeric scalar는 별도 소수 자릿수 양자화 없이 전달하며 numeric string은 검증 경계에서 number로 변환될 수 있다. Basecase/LUT 기준값의 기존 정밀도 정책은 유지한다. runtime allow-list는 신규 proposal 생성에만 적용하며 confirmation을 추가로 제한하지 않는다. v4 provenance와 미지원 진단은 request state, trace, validation warning 또는 실패 detail에만 둔다. DB DDL·master·mapping, Lever catalog/checksum, config, canonical JSON/SQL/workbook은 이 runtime 제한의 변경 대상이 아니다.

## 4. 자연어 프롬프트로 배포하기

VM 배포와 내부망 소스 반입은 목적과 기준 소스가 다르므로 구분해서 요청한다.

### 4.1 외부 데모 VM 배포

> `Model Parameter Agent v0.3.0을 외부 데모 VM에 배포해줘.`

[`mi-vm-deploy`](../../../../.claude/skills/mi-vm-deploy/SKILL.md)가 현재 로컬 작업트리를 Model Parameter Agent image로 빌드해 ACR에 push한다. Push가 성공한 경우에만 외부 VM의 image 설정을 변경하고 container를 재생성한 뒤 상태와 시작 로그를 확인한다. `v0.3.0`은 image tag이며 Git tag checkout을 뜻하지 않고, 로컬 미커밋 변경도 image에 포함될 수 있다.

### 4.2 내부망 소스 반입

> `v0.3.0 기준으로 소스 반입 파일 만들어줘.`

[`mi-source-banib`](../../../../.claude/skills/mi-source-banib/SKILL.md)가 `origin/main`의 merge 결과를 기준으로 release tag와 release note를 준비하고, 해당 tag 기준의 저장소 Git 이력과 내부 반입 script를 하나의 bundle로 만든다. 로컬 미커밋 변경은 포함되지 않으며, 자동 수행 범위는 외부 환경의 bundle 생성까지다.

## 5. 자연어 프롬프트로 테스트하기

실제 scenario 테스트는 [`model-parameter-agent-test`](../../../../.claude/skills/model-parameter-agent-test/SKILL.md)를 사용한다.

### 대표 동작 예시

> `현재 proposal 허용 5개 파라미터별로, 각 파라미터에 매핑된 모든 이벤트타입을 대상으로 시나리오그룹 2개씩, 각 그룹의 시나리오 2개씩 proposal과 confirmation까지 테스트하고 통합 레포트를 작성해줘.`

테스트 대상은 group 전략에 따라 v1/v3 direct/routing 또는 v4 selected Lever executable binding으로 만든 raw 후보와 runtime allow-list 5개의 교집합으로 정한다. 승인된 환경에서 proposal과 confirmation, DB read-back을 확인한 뒤 통합 Markdown 리포트를 `tests/reports/model_parameter_agent/`에 작성한다. 리포트에는 파라미터·slot 선정, Basecase/LUT 기준값, Lever provenance·제안값과 근거, token, 실행시간·retry와 confirmation 결과가 포함된다.

### 다른 요청 프롬프트

> `GDP 파라미터에 매핑된 모든 이벤트타입에서 시나리오그룹 2개씩, 각 그룹의 시나리오 2개씩 테스트하고 레포트를 작성해줘.`

> `event_type_l2_id=7 여름 폭염 이벤트타입에서 시나리오그룹 2개와 각 그룹의 시나리오 2개를 테스트하고 레포트를 작성해줘.`

> `scenario_id=595를 proposal과 confirmation까지 테스트하고 레포트를 작성해줘.`
