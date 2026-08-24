# Model Parameter Agent 처음 이해하기

## 이 Agent는 무엇을 하나요?

Model Parameter Agent는 Scenario에서 일어난 시장 변화를 Demand·Supply·Trade 모델이 실제로 읽을 수 있는
입력값으로 바꾸어 제안한다.

예를 들어 다음 Scenario가 확정됐다고 생각해 보자.

> 미국 LNG 액화시설이 두 달 동안 부분 가동하고 이후 정상 수준으로 회복한다.

이 문장만으로는 수급모델을 실행할 수 없다. 어느 시설의 어느 월 값을 바꿀지, 현재 값은 얼마인지, 새로운 값은
얼마가 적절한지를 정해야 한다. Agent는 Scenario 근거와 등록된 모델 정의를 함께 보아 다음과 같은 변경안을
만든다.

```text
Scenario의 액화시설 가동 차질
  → 적용 가능한 LiqUtilAdjustment 후보 확인
  → Country / LNG Plant / Train / Year / Month 위치 선택
  → 현재 Basecase 또는 LUT 기준값 확인
  → 각 위치의 최종 제안값과 근거 생성
```

Agent는 모델 Excel을 직접 수정하거나 Demand→Supply→Trade→Output 계산을 실행하지 않는다. 이 단계의 결과는
사용자가 검토하고 확정할 수 있는 Model Parameter proposal이다.

## 결과를 만드는 전체 순서

```text
1. 적용할 Scenario를 고른다
   ↓
2. Agent가 Scenario와 Event 근거를 읽는다
   ↓
3. DB mapping 또는 v4 Lever binding으로 관련 파라미터 후보를 찾는다
   ↓
4. 현재 proposal 허용 범위와 실제 Basecase/LUT 위치를 확인한다
   ↓
5. 적용 위치와 제안값, 근거를 만든다
   ↓
6. 사용자가 값을 유지·수정·추가·삭제한 뒤 확정한다
```

제안 생성과 사용자 확정은 별도 단계다. 비동기 API의 `PROCESSING`은 접수만 끝났다는 뜻이고,
`PROPOSED`가 되어야 제안 생성이 끝난다. 사용자가 확인한 뒤에만 `CONFIRMED`가 된다.

## 먼저 알아둘 용어

### Model Parameter

수급모델의 한 입력 종류다. 현재 신규 proposal에서 허용하는 예는 `GDP`, `PMI`, `PowerMix`,
`Temperature`, `LiqUtilAdjustment`다.

### Model target

값을 넣을 모델 파일, Sheet, table과 value field의 조합이다. 같은 파라미터명만 맞는 것으로는 충분하지 않으며
등록된 target과 좌표 구조가 함께 맞아야 한다.

### Slot

모델에서 값 하나가 들어갈 정확한 위치다. 예를 들어 `PMI / Japan / 2027 / 1월`과
`PMI / Japan / 2027 / 2월`은 서로 다른 slot이다. Agent는 일부 축만 비슷한 값이나 가까운 시설의 값을
대신 사용하지 않는다.

### Basecase

Demand·Supply·Trade workbook에 들어 있는 현재 모델 입력값이다. 같은 exact slot에 Basecase가 있으면
LUT보다 우선하는 기준값이 된다.

### LUT

Look-up table의 줄임말이다. CSV 원본과 파라미터별 adapter가 Basecase에 없는 exact slot의 참고값을 만든다.
LUT는 Scenario에 맞는 파라미터를 새로 정하지 않고, 이미 선정된 후보의 위치와 기준값을 보충한다.

### Proposal과 Confirmation

Proposal은 Agent가 만든 초안이고 Confirmation은 사용자가 검토한 최종 입력 묶음이다. Confirmation은 같은
proposal 행을 갱신하며 LLM을 다시 호출하지 않는다. 확정됐다는 사실이 모델 계산까지 실행됐다는 뜻은 아니다.

### Mapping과 Model Impact Lever

v1/v3는 Event Type과 Dimension을 파라미터에 연결한 legacy mapping을 사용한다. v4는 선택한 Dimension
value에 저장된 Model Impact Lever state와 현재 catalog binding을 사용한다. v4는 legacy mapping을
fallback으로 사용하지 않는다.

### Raw 후보와 runtime allow-list

DB에서 활성인 파라미터, mapping 또는 binding으로 도달할 수 있는 파라미터, 지금 신규 proposal에 허용되는
파라미터는 서로 다른 집합이다. 현재 모든 version의 신규 proposal은 raw 후보를 만든 뒤 5개 runtime
allow-list와 교집합을 취한다.

## 현재 구현 범위

Model Parameter Agent는 시나리오가 수급모델에 미치는 영향을 모델 입력 파라미터의 변경안으로 제안한다.

- v1 단일 이벤트와 v3 멀티 이벤트는 기존 DB mapping으로, v4는 선택 dimension value의 Lever state와 catalog binding으로 관련 파라미터를 찾는다.
- Basecase와 LUT에 실제로 존재하는 국가·기간·시설 slot만 사용한다.
- 현재 기준값을 바탕으로 제안값과 근거를 만든다.
- 사용자가 검토·수정한 최종값을 확정 상태로 저장한다.

체크인된 v4 canonical 기준선의 활성 대상은 `GDP`, `PMI`, `PowerMix`, `Temperature`, `Population`, `User-Adjusted Gas Demand`, `HurricaneIntensity`, `LiqProdAdjustment`, `LiqUtilAdjustment`, `PipelineAdjustment`, `RegasAdjustment`, `SupplyDisruption`, `PNG Contract Volume`, `RemainingUnrestrictedAmount`, `ShippingCost`, `VolumeCancelled`의 16개다. 이 중 LUT-backed는 10개, Basecase-only는 6개다. `CDD`, `HDD`, Coal/Gas Futures, `ElectrificationRate`는 비활성이다. CDD/HDD binding은 catalog capability 진단을 위해 남지만 v4 raw 후보에서는 `INACTIVE_MODEL_PARAMETER`로 제외된다. 이 수치는 저장소 기준선이며 live DB 상태를 뜻하지 않는다. 배포·검증 때는 DB read-back으로 실제 적용값을 확인해야 한다.

v1은 scenario group의 대표 event type과 scenario dimension key를 mapping에 대입한다. `generation_strategy=multi_event_composite_dimensions`인 v3는 `dimensionDefinitions[].sourceRefs`로 원본 `(event_type_l2_id, dimKey)`를 복원해 공유 legacy 129개 mapping을 재사용한다. `generation_strategy=multi_event_model_lever_dimensions`인 v4는 이 mapping, Event Type, 과거 `lever_mappings` 계열을 조회하거나 fallback으로 사용하지 않는다. 선택된 value의 `lever_states`와 active Lever catalog를 엄격히 검증한 뒤 executable binding으로 raw 후보를 만든다.

모든 버전의 신규 proposal은 raw 후보 생성 후 `GDP`, `PMI`, `PowerMix`, `Temperature`, `LiqUtilAdjustment` 5개 runtime allow-list를 공통으로 적용한다. 제한은 Step1.5·LLM 호출·proposal 행 생성 전에 적용한다. 체크인 canonical에 활성으로 남은 나머지 11개와 그 resource capability는 삭제하지 않지만 신규 proposal로는 제안하지 않는다.

v4 master와 Lever의 저장소 판정 기준은 [parameter canonical](../../../scripts/model_parameter/model-parameter-canonical-v4.json)과 [Lever canonical](../../../scripts/model_parameter/model-impact-lever-canonical-v4.json)이다. v1/v3 체크인 목표 mapping은 [v1 canonical](../../../scripts/model_parameter/model-parameter-canonical-v1.json)의 `dimension_mappings` 129행이 기준이며, 해당 fixture의 master 활성 10개 정의를 v4 master 기준선에 덮어쓰지 않는다. 사람이 읽는 설명은 [canonical mapping 문서](../../../apps/agents/model_parameter_agent/resources/Model_Parameter_Base_Case_Mapping.md), 업무용 표는 [v4 canonical workbook](../../../apps/agents/model_parameter_agent/resources/mapping/260813_시나리오가정_MI수급모델_input_매핑_model-parameter-canonical-v4.xlsx)이다. workbook은 v4 master·Lever와 v1/v3 mapping 129행의 체크인 기준선을 함께 보여 준다. 2026-08-13 v4 적용 전 snapshot의 128행·25/2/55/46은 변경 전 증적이며, 어느 수치도 live DB를 조회한 결과로 간주하지 않는다.

### v1·v3와 v4의 제안 가능 범위

“master에서 활성”, “mapping/binding이 도달할 수 있음”, “신규 proposal에 제안할 수 있음”은 서로 다른 뜻이다. 체크인 canonical의 전역 합집합 기준으로 master 활성은 16개, v1/v3 raw mapping-reachable set은 LUT-backed 10개, v4 raw executable-binding set은 고유 활성 parameter 16개다. 이 수는 요청 하나에서 동시에 나오는 후보 수가 아니다. 실제 신규 proposal은 요청별 raw 후보와 runtime allow-list 5개의 교집합만 사용하고, 관련 분기·변화 state·routing 결과·exact Basecase/LUT slot 존재 여부에 따라 더 좁아진다.

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

## 사용자는 단계별로 무엇을 보나요?

### 1. 제안 요청

사용자는 Scenario ID를 기준으로 제안을 요청한다. 동기 API는 완료 결과를 한 응답에서 확인하는 테스트용
경로이고, 운영 비동기 API는 proposal ID와 `PROCESSING` 상태를 먼저 반환한다.

### 2. 제안 완료

성공 결과에는 적용 파라미터와 model target, exact slot, 기준값, 제안값과 근거가 들어 있다. v3/v4 결과는
여러 Event를 하나로 묶은 `scenarioGroupId`가 authoritative link이고 `eventId`는 `null`이다.

### 3. 사용자 검토와 확정

사용자는 제안값을 그대로 사용하거나 수정하고, 필요하면 항목을 추가·삭제한 전체 목록을 Confirmation API로
보낸다. 동기 제안 응답에만 있는 `lutValue`는 Confirmation payload에서 제거한다.

## 처리 상태를 읽는 법

| 상태 | 의미 | 다음 확인 |
| --- | --- | --- |
| `PROCESSING` | 비동기 제안 접수 후 background 처리 중 | callback과 proposal DB 상태 |
| `PROPOSED` | 제안 생성과 저장 완료 | 사용자의 검토·Confirmation |
| `CONFIRMED` | 사용자가 보낸 최종 목록 저장 완료 | 후속 모델 입력 export 또는 모델 실행 |
| `FAILED` | background 제안 처리 실패 | `error_code`, `error_message`와 callback |

callback 상태인 `PENDING | SUCCEEDED | FAILED | SKIPPED`는 proposal 내용 상태와 별개다. 예를 들어 proposal은
`PROPOSED`지만 callback 전송만 `FAILED`일 수 있다.

## 개발 문서에서 자주 나오는 기술 용어

| 용어 | 쉬운 설명 |
| --- | --- |
| exact key | 국가·기간·시설 등 모든 축이 일치하는 slot 식별 기준 |
| candidate | mapping/binding과 허용 범위를 통과해 검토 중인 파라미터 |
| Step1.5 | 조건부 후보가 여러 개일 때 적용할 후보를 고르는 단계 |
| Step2 | 값은 보지 않고 적용할 exact slot을 고르는 단계 |
| Step3 | 검증된 slot과 기준값으로 최종 절대값과 근거를 만드는 단계 |
| provenance | v3 source lineage 또는 v4 Lever처럼 후보가 나온 경로 |
| canonical | DB·LUT·workbook 등 여러 표현을 맞출 때 기계 판정 기준이 되는 자료 |
| callback | 비동기 작업이 끝났음을 연동 시스템에 알리는 요청 |

## 더 자세히 알고 싶다면

| 궁금한 것 | 다음 문서 |
| --- | --- |
| 화면이나 다른 시스템이 무엇을 보내고 받는지 | [API Spec](02_MODEL_PARAMETER_AGENT_API_SPEC.md) |
| 어떤 DB table이 기준과 결과를 소유하는지 | [DB Spec](03_MODEL_PARAMETER_AGENT_DB_SPEC.md) |
| 후보·slot·값 제안과 확정이 어떤 순서로 실행되는지 | [기능 Flow](04_MODEL_PARAMETER_AGENT_FLOW.md) |
| Basecase와 LUT를 어떻게 준비하고 결합하는지 | [Basecase·LUT](05_MODEL_PARAMETER_AGENT_BASECASE_LUT_PARSING.md) |
| 새 파라미터를 안전하게 추가·활성화하는 방법 | [파라미터 추가 가이드](06_MODEL_PARAMETER_AGENT_PARAMETER_ADDITION_GUIDE.md) |
| 핵심 계약을 제대로 이해했는지 확인하는 방법 | [이해도 퀴즈](07_MODEL_PARAMETER_AGENT_COMPREHENSION_QUIZ.md) |
| 자연어로 테스트하고 품질 보고서를 읽는 방법 | [테스트와 품질 평가](08_MODEL_PARAMETER_AGENT_TEST_AND_QUALITY.md) |
| 공통 프로젝트 폴더와 코드 배치 원칙 | [Project Directory Structure](../../architectures/project_directory_structure.md) |

## 코드를 맡은 사람이 처음 볼 위치

[루트 README](../../../README.md)의 구조 설명 방식과 현재 파일 배치를 기준으로 핵심 경로만 나타내면 다음과 같다.

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
│   ├── connectors/object_storage/         # S3 호환 Object Storage 연결
│   └── persistence/
│       ├── model_parameter/               # 공용 parameter ORM·repository·DTO
│       └── model_impact_lever/             # 공용 Lever catalog service·repository·DTO
├── docs/agents/model_parameter_agent/      # 공식 Agent 문서
├── envs/config.yaml                       # 로컬 실행·resource 설정
├── devops/k8s/configmap.yaml              # 배포 환경 설정
└── tests/
    ├── automated/test_model_parameter_*.py
    ├── manual/model_parameter_agent/
    └── reports/model_parameter_agent/     # 시나리오 테스트 리포트
```

API는 `api.py`에서 시작해 `flows/`로 들어간다. 제안 Flow는 전략에 따라 v1/v3 legacy mapping adapter 또는 v4 Lever-native context loader로 raw 후보를 만든 뒤, 공통 runtime allow-list를 Step1.5·LLM·저장보다 먼저 적용한다. 허용 후보만 Basecase/LUT, prompt와 저장 service로 전달한다. v1 proposal은 대표 event ID를 저장하지만 v3/v4 proposal은 `mi_event_id=NULL`로 저장하고 `scenario_group_id`를 authoritative link로 사용한다. 외부 API의 기존 optional `eventId`도 v3/v4에서는 `null`이며 새 필드는 추가하지 않는다. DB query는 flow/node가 직접 작성하지 않고 Agent service와 `apps/persistence/`의 domain service/repository를 통해 실행한다.

확정 단계의 custom parameter 허용 동작, 기존 저장 데이터와 JSON shape은 그대로 유지한다. proposal 생성의 Step3는 `proposedValue`를 유한 숫자로 검증한다. Confirmation은 각 value 객체에 `proposedValue` key가 있어야 하지만 값은 `null`일 수 있고, `null`이 아닌 값만 persistence 경계에서 엄격한 유한 숫자로 정규화한다. 원래 proposal과 동일한 항목·값인지 비교하지 않으므로 사용자는 구조 계약과 알려진 정의 검증 범위 안에서 항목을 수정·추가·삭제할 수 있으며, custom parameter도 공통 구조 검증을 통과하면 저장할 수 있다. 어느 경로도 설정 기반 소수 자릿수 round/trunc/ceil을 적용하지 않는다. Basecase/LUT 기준값의 기존 정밀도 정책은 유지한다. runtime allow-list는 신규 proposal 생성에만 적용하며 confirmation을 추가로 제한하지 않는다. v4 provenance와 미지원 진단은 request state, trace, validation warning 또는 실패 detail에만 둔다. DB DDL·master·mapping, Lever catalog/checksum, config, canonical JSON/SQL/workbook은 이 runtime 제한의 변경 대상이 아니다.

코드를 변경하기 전에는 [AGENTS.md](../../../AGENTS.md),
[Python conventions](../../../.claude/rules/python-conventions.md)와
[Project Directory Structure](../../architectures/project_directory_structure.md)를 함께 확인한다.
자연어로 테스트를 요청하는 방법은 [테스트와 품질 평가](08_MODEL_PARAMETER_AGENT_TEST_AND_QUALITY.md)에서
이어진다.
