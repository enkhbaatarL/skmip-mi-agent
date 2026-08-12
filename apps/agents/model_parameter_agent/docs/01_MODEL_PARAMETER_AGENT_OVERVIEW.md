# Model Parameter Agent 개요

## 1. Parameter Agent의 목적

Model Parameter Agent는 시나리오가 수급모델에 미치는 영향을 모델 입력 파라미터의 변경안으로 제안한다.

- v1 단일 이벤트와 v3 멀티 이벤트 시나리오를 구분하고, 기존 DB mapping으로 관련 파라미터를 찾는다.
- Basecase와 LUT에 실제로 존재하는 국가·기간·시설 slot만 사용한다.
- 현재 기준값을 바탕으로 제안값과 근거를 만든다.
- 사용자가 검토·수정한 최종값을 확정 상태로 저장한다.

현재 활성 대상은 `GDP`, `PMI`, `PowerMix`, `Temperature`, `Population`, `HurricaneIntensity`, `LiqProdAdjustment`, `LiqUtilAdjustment`, `PipelineAdjustment`, `SupplyDisruption`의 10개다. Coal/Gas Futures는 2026년 이후 값이 없어 보류하고, ElectrificationRate는 승인된 Basecase·LUT·mapping이 없어 보류한다.

v1은 scenario group의 대표 event type과 scenario dimension key를 그대로 mapping에 대입한다. `generation_strategy=multi_event_composite_dimensions`인 v3는 동적 composite dimension을 master mapping에 추가하지 않는다. 대신 `dimensionDefinitions[].sourceRefs`의 template ID를 그룹 이벤트 관계에 연결해 각 원본 `(event_type_l2_id, dimKey)`를 복원하고 같은 129개 dimension mapping을 재사용한다.

기계 판정 기준은 [canonical JSON](../../../../scripts/model_parameter/model-parameter-canonical-v1.json), 사람이 읽는 설명은 [canonical mapping 문서](../resources/Model_Parameter_Base_Case_Mapping.md), 업무용 표는 [canonical mapping Excel](../resources/mapping/260807_시나리오가정_MI수급모델_input_매핑_model-parameter-canonical-v1.xlsx)이다. 이전 Excel은 `resources/mapping/archive/`의 역사·검토 자료이며 현재 실행 기준이 아니다.

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
| `tmm_mi_scenario_group_event_m`    | v3 그룹의 ordered event·event type·dimension template 관계 관리     |
| `tmm_mi_dimension_value_mapping_m` | v3 자유 value의 source projection과 승인 상태 관리                  |
| `tmm_mi_model_param_proposal_m`    | 제안 상태, 제안값, 확정값, 오류·callback 결과 저장                   |

### 2.3 Flow 문서

[Flow 문서](04_MODEL_PARAMETER_AGENT_FLOW.md)는 다음 핵심 처리 순서와 Step1.5·Step2·Step3 prompt를 설명한다.

```text
시나리오·그룹 전략 조회
→ v1 event/dimension 또는 v3 sourceRefs lineage 정규화
→ 기존 DB mapping으로 파라미터 후보 결정
→ Step1.5 routing 조건 검증·후보 선택(routing이 있는 경우)
→ Basecase/LUT slot catalog 생성
→ Step2 적용 slot 선택
→ Basecase 우선 기준값 결정
→ Step3 제안값·파라미터 근거·slot 근거 생성
→ 서버 검증 및 PROPOSED 저장
→ 사용자 확인 및 CONFIRMED 저장
```

v3의 그룹 이벤트는 `display_order` 순서로 Step1.5·Step2·Step3의 `scenario_brief.events`에 들어간다. 이벤트별 핵심 정보는 bullet 최대 5개, tag 최대 8개, detail excerpt 최대 1,200자로 제한하고 현재 후보와 관련된 composite/indirect dimension만 남긴다. `parameter_mapping_ready=false`는 실행 차단 조건이 아니다. 선택 value에 승인된 source projection이 있으면 보조 근거로 사용하고, 없거나 pending/rejected이면 경고만 남긴다.

한 composite dimension이 여러 파라미터에 연결되면 direct/routing 정책에 따라 모두 유지한다. 반대로 여러 dimension 또는 event type이 같은 모델 파라미터로 수렴하면 모든 source lineage를 보존한 하나의 task로 병합한다. 값은 서버가 dimension별 결과를 합산·평균하지 않고, LLM이 전체 근거를 종합해 slot별 최종 절대값 하나를 제안한다.

scenario `595`를 이용한 실제 prompt 입력·출력과 제안 결과도 Flow 문서에 포함되어 있다.

### 2.4 Basecase·LUT 문서

[Basecase·LUT 문서](05_MODEL_PARAMETER_AGENT_BASECASE_LUT_PARSING.md)는 파일 준비, 파싱 설정, exact slot 결합과 기준값 선택 방법을 설명한다.

| 구분      | 활용 내용                                                               |
| --------- | ----------------------------------------------------------------------- |
| Basecase  | Demand·Supply·Trade 모델 Excel에 현재 입력된 기준값                     |
| LUT       | 활성 10개 파라미터의 기본 참고값 CSV와 계산 adapter                    |
| 선택 기준 | 같은 exact slot에 Basecase 값이 있으면 우선 사용하고, 없으면 LUT 사용   |
| 파일 준비 | 애플리케이션 시작 시 S3 호환 Object Storage 또는 packaged 파일에서 준비 |

Basecase와 LUT는 파라미터 후보를 새로 결정하지 않는다. DB mapping으로 확정된 파라미터의 실제 선택 가능 slot과 기준값을 제공한다.

### 2.5 파라미터 추가 가이드

[파라미터 추가 가이드](06_MODEL_PARAMETER_AGENT_PARAMETER_ADDITION_GUIDE.md)는 canonical 10개를 기준으로 master, 승인된 dimension mapping, LUT adapter·manifest와 prompt 크기 보호를 함께 변경하고 검증하는 순서를 설명한다.

`LiqProdAdjustment`는 이제 활성 상태이며 `BCLiquefaction.csv`의 월 생산능력 × 이용률로 LUT 값을 만든다. 같은 event·dimension의 기존 `LiqUtilAdjustment` direct mapping과 함께 후보가 될 수 있고, 단기·부분 가동률은 LiqUtil, 대폭·영구 생산량 override는 LiqProd라는 hint/comment로 의미를 구분한다.

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
│   └── persistence/model_parameter/       # 공용 ORM·repository·DTO
├── envs/config.yaml                       # 로컬 실행·resource 설정
├── devops/k8s/configmap.yaml              # 배포 환경 설정
└── tests/
    ├── automated/test_model_parameter_*.py
    ├── manual/model_parameter_agent/
    └── reports/model_parameter_agent/     # 시나리오 테스트 리포트
```

API는 `api.py`에서 시작해 `flows/`로 들어간다. 제안 Flow는 v1/v3 context adapter, DB mapping, Basecase/LUT, prompt와 저장 service를 사용하고, 확정 Flow는 사용자가 보낸 전체 값을 검증해 기존 proposal을 갱신한다. v1 proposal은 대표 event ID를 저장하지만 v3 proposal은 `mi_event_id=NULL`로 저장하고 `scenario_group_id`를 authoritative link로 사용한다. 외부 API의 기존 optional `eventId`도 v3에서는 `null`이며 새 필드는 추가하지 않는다. DB query는 Agent Flow가 직접 작성하지 않고 service와 `apps/persistence/model_parameter/`를 통해 실행한다.

확정 단계의 custom parameter 허용 동작과 proposal/confirmation의 기존 유한 숫자·정밀도 정규화는 그대로 유지한다. 이번 v3 연계는 parameter별 min/max·정수·단위 validator를 추가하지 않으며, canonical master·129개 dimension mapping·Basecase/LUT·mapping workbook이나 DB DDL을 변경하지 않는다. 배포 대상 DB에는 v3 scenario group/event relation·dimension value mapping schema와 proposal `mi_event_id` nullable 변경이 먼저 적용되어 있어야 한다.

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

> `현재 활성 전체 파라미터별로, 각 파라미터에 매핑된 모든 이벤트타입을 대상으로 시나리오그룹 2개씩, 각 그룹의 시나리오 2개씩 proposal과 confirmation까지 테스트하고 통합 레포트를 작성해줘.`

실행 시점의 DB에서 활성 Parameter와 `direct`·`routing` mapping을 조회해 테스트 대상을 정한다. API 서버 없이 raw graph로 proposal을 실행하고, 성공 건은 confirmation과 DB read-back까지 확인한 뒤 하나의 통합 Markdown 리포트를 `tests/reports/model_parameter_agent/`에 작성한다. 리포트에는 파라미터·slot 선정, Basecase/LUT 기준값, 제안값과 근거, token, 실행시간·retry, confirmation 결과와 같은 그룹 내 scenario 비교가 포함된다.

### 다른 요청 프롬프트

> `GDP 파라미터에 매핑된 모든 이벤트타입에서 시나리오그룹 2개씩, 각 그룹의 시나리오 2개씩 테스트하고 레포트를 작성해줘.`

> `event_type_l2_id=7 여름 폭염 이벤트타입에서 시나리오그룹 2개와 각 그룹의 시나리오 2개를 테스트하고 레포트를 작성해줘.`

> `scenario_id=595를 proposal과 confirmation까지 테스트하고 레포트를 작성해줘.`
