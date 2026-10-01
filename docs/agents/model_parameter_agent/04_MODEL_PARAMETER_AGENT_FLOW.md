# Model Parameter Agent Flow

> 현재 핵심 Skill과 release 판정 범위는 v4 `multi_event_model_lever_dimensions` Flow뿐이다.
> v1/v3 분기는 기존 호환 동작을 설명하며 신규 검증 경로로 사용하지 않는다.

## 범위

- 체크인 전역 합집합 기준으로 v1/v3 legacy mapping은 raw Parameter 10개, 0032 canonical v4 Lever catalog는 master
  filtering 전 raw binding 이름 16개와 effective active Parameter 14개에 도달한다. 요청 하나의 후보는 관련
  lineage와 선택 value에 해당하는 하위 집합이다.
- v1/v3는 기존 5종 이름 allow-list, v4는 ID `{4, 6, 7, 8, 14, 15, 17}` capability gate를 LLM·persistence 전에 적용한다.
- LLM 판단은 v1/v3의 조건부 Step1.5와 공통 Step2·Step3으로 나뉜다. v4 candidate는 Step1.5 없이 deterministic하게 구성한다.
- Step2는 “어디를 바꿀지”, Step3는 “얼마로 바꾸고 왜 그런지”를 판단한다.
- 최종 확인은 LLM을 다시 호출하지 않고 서버 검증 후 `CONFIRMED`로 저장한다.

이 문서는 현재 코드의 proposal graph, 비동기 background 처리, Confirmation 순서와 단계별 검증 경계를
설명한다. 개별 실행의 성공 여부는 이 문서가 아니라 실행 시 생성한 증적과 보고서로 판정한다.

## 공통 실행 원칙

- path의 `scenario_id`가 속한 Group의 `generation_strategy`로 v1·v3·v4 context loader를 선택한다.
- v1/v3 legacy mapping과 v4 Lever binding은 서로의 fallback이 아니다.
- raw 후보를 만든 직후 runtime proposal allow-list를 적용하고, 제외 후보를 LLM이나 persistence로 보내지 않는다.
- LLM은 등록되지 않은 parameter나 exact catalog 밖 slot을 새로 만들 수 없다.
- proposal graph는 candidate·slot key, 중복과 Step3 제안값의 유한 숫자를 다시 검증한 결과만 저장한다.
- 동기·비동기 proposal은 같은 graph를 사용하고, 접수·저장·callback 방식만 다르다.
- Confirmation은 LLM을 호출하지 않고 같은 proposal row를 갱신한다.

## 이 문서에서 쓰는 말

| 용어 | 의미 | 예시 |
|---|---|---|
| 시나리오 | 모델에 반영하려는 사건과 조건 | 특정 국가의 2026년 경기 둔화 |
| 파라미터 후보 | 시나리오의 영향을 받을 수 있는 모델 입력 항목 | `GDP`, `PMI` |
| slot | 값을 적용할 정확한 위치 | `Country=China`, `Year=2026` |
| 기준값 | 새 값을 제안할 때 비교하는 현재 값 | GDP 성장률 `0.042` |
| 제안값 | 시나리오를 반영해 LLM이 제안한 값 | GDP 성장률 `0.041` |
| composite dimension | v3에서 여러 event/source dimension을 조합해 만든 scenario dimension | `복합 공급 압력` |
| source lineage | composite dimension을 원본 event·template·dimension으로 연결하는 근거 | `sourceEventIds`, `sourceRefs` |
| Lever provenance | v4 선택 value를 dimension·event·Lever·binding으로 연결하는 근거 | `lever_states`, binding role/applicability |

`candidate_key`와 `slot_key`는 처리 중 항목을 안전하게 연결하는 서버 식별자다. 사용자가 직접 만들 필요는 없다.

## 1. Proposal 생성

### 실행 구조

```mermaid
flowchart TD
    A[제안 요청: scenario_id] --> B[시나리오·그룹 전략 조회]
    B --> V{generation strategy}
    V -- v1 --> C1[대표 event type과\nscenario dimension 정규화]
    V -- v3 --> C2[sourceRefs와 group relation으로\n원본 event type·dimKey 역투영]
    V -- v4 --> C3[선택 value의 Lever states와\nactive catalog 검증]
    C1 --> C[기존 DB mapping으로\nraw 후보 결정]
    C2 --> C
    C3 --> C4[executable Lever binding으로\nraw 후보 결정]
    C --> R1[legacy proposal\n5종 allow-list]
    C4 --> R4[extend10 ID/name/target\ncapability gate]
    R1 --> D{routing 후보가<br/>하나라도 있는가?}
    R4 --> G
    D -- 예 --> E[Step1.5<br/>routing 조건 검증·후보 선택]
    D -- 아니오 --> F[direct 후보 확정]
    E --> G[같은 파라미터 후보 병합]
    F --> G
    G --> H[v1/v3 기존 Basecase 또는<br/>v4 capability별 reference source 검증]
    H --> H2[Basecase 우선·exact LUT fallback<br/>slot catalog 생성]
    H2 --> I[Step2<br/>적용할 slot 선택]
    I --> J[서버 exact 검증·slot_key 발급]
    J --> P[v4 policy<br/>PowerMix atomic expansion·LiqUtil evidence gate]
    P --> K[Basecase 우선 기준값 결정]
    K --> L[Step3<br/>제안값·두 종류 근거 생성]
    L --> M[서버 key·Step3 유한 숫자·중복 검증]
    M --> N[(PROPOSED 저장)]
```

| 단계 | 실행 주체 | 핵심 입력 | 핵심 출력 |
|---|---|---|---|
| 문맥 조회 | 서버 | `scenario_id` | scenario, group strategy, ordered event, dimension과 lineage/Lever provenance |
| raw 후보 결정 | 서버 | v1/v3 legacy key 또는 v4 selected Lever state | direct/routing 또는 executable primary/alternative raw 후보 |
| runtime 범위 필터 | 서버 | raw 후보, v1/v3 이름 5종 또는 v4 ID capability 7종 | LLM·저장으로 전달할 후보 |
| Step1.5 | LLM, v1/v3 조건부 | legacy routing과 관련 시나리오 문맥 | 허용된 `candidate_key` 0개 이상 선택 |
| reference 준비 | 서버 | 확정 후보, v1/v3 Basecase 또는 v4 `new-bc-v5`, LUT | 값이 존재하고 차단되지 않은 exact slot catalog |
| Step2 | LLM | 시나리오 문맥, 파라미터별 slot catalog | `candidate_key + slot_axes` |
| 기준값 결정 | 서버 | Step2 좌표 | `slot_key + coordinates + reference_value` |
| Step3 | LLM | 확정 slot, 기준값, hint/comment | 제안값, 파라미터 근거, slot별 근거 |
| 저장 | 서버 | 검증된 Step3 결과 | `PROPOSED` proposal |

Basecase/LUT 파일 자체를 읽는 기준은 [Basecase·LUT 문서](./05_MODEL_PARAMETER_AGENT_BASECASE_LUT_PARSING.md)를 참고한다.

아래 단계는 하나의 proposal graph 안에서 순서대로 실행된다.

### 1.1 시나리오 문맥 조회와 파라미터 후보 결정

서버는 `scenario_id`로 scenario와 scenario group을 읽고 `generation_strategy`에 따라 context adapter를 선택한다.

- v1 `single_event_template_dimensions`는 group의 대표 event, event type L2와 scenario dimension template을 읽는다. 현재 scenario dimension key를 기존 `(event_type_l2_id, dimension_key)` DB mapping에 직접 대입한다.
- v3 `multi_event_composite_dimensions`는 2~5개 group-event relation을 `display_order` 순서로 읽고 모든 event의 핵심 정보를 로드한다. 각 `dimensionDefinitions[].sourceRefs[]`의 `scenarioDimensionTemplateId`를 relation template ID에 연결하고, definition의 `sourceEventIds`와 교집합인 relation에서 `event_type_l2_id`를 복원한다. source ref의 `dimKey`와 합친 `(event_type_l2_id, dimKey)`를 같은 DB mapping에 대입한다. 선택 dimension lineage에서 참조되지 않은 group event가 있으면 LLM 호출 전에 실패한다.
- v4 `multi_event_model_lever_dimensions`는 Scenario, Group, ordered Group–Event 관계, active Lever catalog와 active parameter definition만 조회한다. `dimension_values`가 선택한 value 하나의 `lever_states`만 추출하고 legacy dimension mapping, Event Type, `lever_mappings`·`lever_refs`·`impact_lever_refs`를 후보 source나 fallback으로 사용하지 않는다.

v4 loader는 group API version/strategy와 catalog checksum, dimension/value/primary Lever 존재, `source_event_ids`의 group event 부분집합, Lever code/ID 일치와 primary state 포함 여부를 strict 검증한다. checksum 불일치, 미등록 code, ID 불일치, primary 누락은 LLM 호출 전에 `INVALID_REQUEST`로 실패한다. catalog checksum이 바뀐 기존 v4 Scenario는 재해석하지 않고 현재 catalog로 다시 생성해야 한다.

v4 selector는 executable binding만 raw 후보화한다. `price_only`, binding 없음, 비활성 parameter와 catalog unsupported는 제외 reason을 내부 state/trace에 보존한다. `direction=unchanged`는 변화 후보가 아니라 supporting context다. parameter별 중복 raw 후보는 dimension, 선택 value, ordered Event, Lever state와 binding provenance를 모두 보존해 하나로 병합한다.

전략별 raw matching 직후 서버는 version별 scope gate를 적용한다. v1/v3 이름 allow-list 또는 v4 capability
contract 밖의 active parameter는 `PROPOSAL_SCOPE_EXCLUDED` 진단 근거와 warning으로 분리하고 LLM prompt에
보내지 않는다. v4 contract 안의 후보도 DB ID/name/model target 중 하나가 다르면 fail closed한다. 허용 후보가
하나도 없으면 오류가 아니라 `ABSTAINED_OUT_OF_PROPOSAL_SCOPE` 보류로 종결한다. 비동기 요청은 먼저
`PROCESSING` row를 만든 뒤 background에서 `ABSTAINED`로 전환한다.

v3 adapter는 composite `scenario_dimension_key`·label·선택 value와 원본 `mapping_dimension_key`·`event_type_l2_id`를 분리한다. 또한 `source_event_ids`, `source_refs`, 선택 value의 description·derivation rationale·pressure contribution, 승인 projection과 mapping readiness를 lineage에 보존한다. 선택 value가 definition의 `valueId` 또는 label과 일치하면 해당 metadata를 사용하고, 정의에 없는 자유 value이면 raw composite value를 유지한다.

모든 `sourceEventId`는 group relation에 존재해야 하며 각 source ref template은 해당 source event relation과 연결되어야 한다. group 밖 event나 relation 없는 template은 LLM 호출 전에 `INVALID_REQUEST`로 실패한다. relation은 유효하지만 복원한 key에 DB mapping이 없으면 전체 요청을 실패시키지 않고 그 source만 제외하고 warning을 남긴다.

같은 composite dimension/value의 `status=approved` source projection이 있으면 LLM의 보조 근거로 사용한다. projection이 없거나 pending/rejected여도 proposal은 계속하며 warning과 trace에 기록한다. `parameter_mapping_ready=false`는 승인 projection 가용성 표시일 뿐 실행 gate가 아니다.

| mapping 방식 | 서버 처리 |
|---|---|
| `direct` | 연결된 활성 파라미터를 raw 후보로 만든 뒤 allow-list에 있으면 확정 |
| `routing` 1개 이상 | raw 후보에 allow-list를 적용한 뒤 남은 항목만 Step1.5 LLM 조건 검증으로 전달 |
| `indirect` | 파라미터 후보로 만들지 않고 Step2·Step3의 보조 dimension으로 유지 |
| `na` | 파라미터·slot·값 판단 prompt에서 제외 |

이 단계에서는 Basecase 값이나 LUT 값으로 파라미터 필요성을 판단하지 않는다. v1/v3는 활성 mapping 밖, v4는 catalog binding 밖의 파라미터를 새로 만들지 않으며, 두 경로 모두 runtime allow-list 밖의 항목을 downstream으로 전달하지 않는다.

다음 후보 확장·수렴 정책은 v1/v3 legacy 경로에서 같다.

- 한 scenario/composite dimension이 여러 direct/routing 파라미터에 매핑되면 raw 후보를 모두 유지한 뒤 runtime allow-list를 적용한다.
- 여러 dimension 또는 서로 다른 event type이 동일한 model file·sheet·parameter로 수렴하면 하나의 parameter task로 병합하고 모든 source dimension과 event lineage를 보존한다.
- 같은 v3 source ref가 여러 event relation에 반복되면 후보는 중복 생성하지 않지만 관련 event ID는 모두 보존한다.
- allow-list를 통과한 direct 후보는 Step1.5를 거치지 않고 자동 통과한다. routing만 composite scenario dimension 단위로 검증하며 dimension당 최대 2개를 유지한다.

v1의 기존 candidate key 형식은 유지한다. 병합된 v3/v4 parameter task는 단일 event ID에 의존하지 않는 안정적인 key를 사용한다.

#### Step1.5·Step2·Step3의 `scenario_brief`

세 LLM 단계는 같은 버전별 brief 원칙을 사용하되 현재 candidate와 관련된 composite/direct/routing dimension, 그리고 필요한 indirect dimension만 남긴다. `na`와 무관한 scenario dimension은 제외한다.

| 구분 | event 문맥 | dimension 문맥 |
|---|---|---|
| v1 | 기존 단일 `event` | 관련 scenario value와 dimension template |
| v3 | group relation `display_order` 순서의 `events` 배열 | composite dimension, 원본 mapping dimension, source event/ref lineage와 승인 projection |
| v4 | group relation `display_order` 순서의 `events` 배열 | 선택 value와 전체 Lever state·binding provenance, parameter hint·semantic axes |

v3/v4 event 항목에는 event ID, `display_order`, title, one-line summary, 앞 5개 key bullet, 앞 8개 tag와
`detail_analysis` 앞부분을 넣는다. detail 상한은 기존 v3는 event당 1,200자, 현재 운영 v4는 event당
6,000자다. 최대 5개 event의 확장된 본문도 Step1.5·Step2·Step3 compact JSON byte guard를 그대로
적용하며, 상한을 넘으면 LLM 호출 전에 실패한다. Event 자연어는 선택된 v4 dimension/value를 설명하는
데이터일 뿐 prompt 지시를 바꾸거나 선택되지 않은 Scenario branch를 활성화하지 않는다. Step2의 slot
catalog에는 값·기준값이 없고, v4에서만 hierarchy terminal의 적용성 판단에 필요한
`Life Cycle Category`를 `applicability_attributes`로 보존한다. Step3에는 exact 좌표별 단일
`reference_value`와 병합된 전체 Lever provenance가 들어간다.

### 1.2 Step1.5: v1/v3 routing 조건 검증·후보 선택

Step1.5는 legacy routing 후보에만 호출한다. v4 executable binding은 primary/alternative 여부와 무관하게
deterministic candidate로 보존하고 binding applicability, Scenario branch, Event scope, 전체 lineage를 Step2의
slot/evidence 판단으로 넘긴다. v4 후보는 exact slot이 하나로 좁혀지지 않거나 scope가 모순되면 후속 단계에서
abstain한다. v1/v3 `CANDIDATE_VALIDATION_SYSTEM`의 핵심 역할은 다음과 같다.

- scenario, ordered events, 현재 dimension/value와 source 또는 Lever provenance를 비교해 허용 후보 중 적합한 파라미터만 선택한다.
- `parameter_hint`로 후보의 의미와 적용 제약을 이해한다.
- v1/v3는 `mapping_comment`를 필수 조건으로 판단하고, 명시적 근거가 없으면 해당 후보를 제외한다.
- dimension task별로 0개부터 설정된 최대 개수까지 선택할 수 있다.
- 후보 밖의 파라미터나 key를 만들지 않고 Basecase 존재 여부를 선택 근거로 쓰지 않는다.

v4 task에는 Step2부터 `parameter_hint`, semantic axes, binding role/applicability와 선택 value의 모든 Lever state가 들어간다. Lever `direction`, `pressure_contribution` 또는 domain을 숫자 부호로 직접 변환하지 않는다.

실제 user message prefix는 다음과 같다.

```text
아래 JSON만 근거로 Step1.5 수급모델 routing 후보를 선택하십시오.
```

현재 prompt 입력 계약은 다음 모양이다.

```json
{
  "scenario_brief": {
    "scenario_id": "<scenario_id>",
    "selected_dimensions": [
      {"dimension_key": "<routing dimension>", "dimension_value": "<현재 값>"}
    ]
  },
  "routing_tasks": [
    {
      "dimension_key": "<routing dimension>",
      "dimension_label": "<표시명>",
      "dimension_value": "<현재 값>",
      "candidates": [
        {
          "candidate_key": "<허용 candidate_key>",
          "parameter_name": "<파라미터명>",
          "parameter_hint": "<의미·제약>",
          "semantic_axes": "<좌표 의미>",
          "scenario_dimension_key": "<composite dimension>",
          "mapping_dimension_key": "<원본 dimKey>",
          "event_type_l2_id": "<원본 event type>",
          "source_event_ids": ["<source event ID>"],
          "source_refs": [{"scenario_dimension_template_id": "<template ID>", "dim_key": "<원본 dimKey>"}],
          "mapping_comment": "<연결 판단 기준>"
        }
      ]
    }
  ]
}
```

응답은 선택 key만 받는다.

```json
{
  "routing_decisions": [
    {
      "dimension_key": "<입력 dimension_key>",
      "selected_candidate_keys": ["<입력에 있던 candidate_key>"]
    }
  ]
}
```

system prompt는 dimension별 선택 개수를 0개부터 최대 2개 사이로 제한한다. 조건을 충족하는 후보가 없으면 `selected_candidate_keys=[]`를 반환한다. 응답 후 서버는 입력 task에 없던 dimension·candidate key, 누락·중복된 routing task, dimension별 선택 상한 초과를 검사하고 위반 후보를 제외한다. Step1.5 이후 같은 모델 파라미터가 여러 dimension이나 event type에서 중복 선택됐으면 모든 source lineage를 보존한 하나의 후속 task로 병합한다. 승인 projection은 보조 근거지만 readiness 또는 projection 부재만으로 routing 후보를 탈락시키지 않는다. Step1.5 compact JSON도 LLM 호출 전에 byte 상한을 검사하고 trace에 prompt 크기를 기록한다.

### 1.3 Basecase·LUT reference와 slot catalog 준비

이 단계는 LLM을 호출하지 않는다.

1. v1/v3는 기존 DB `basecase_*` 설정으로 `resources/basecase/`를 읽는다.
2. 정확히 v4 `multi_event_model_lever_dimensions`이면 `read_only_proposal` contract가 고정한
   `new-bc-v5` contract가 고정한 authoritative source를 읽고 DB model target과 일치하는지 검증한다.
   변경되지 않은 Excel artifact는 `resources/basecase_v4/new-bc-v1/`의 고정 digest를 재사용한다.
   최초 materialization은 sheet/header/range/변환/고정 record count를 전체 검증한 뒤 contract
   hash와 실제 파일 signature를 key로 process cache한다.
3. LUT-backed parameter이면 같은 파라미터의 기존 LUT를 읽는다. Basecase-only 활성 4개에는 LUT fallback을 만들지 않는다.
4. 설정 기간 안에서 값이 존재하는 Basecase와 LUT exact 좌표의 합집합을 만든다. 신규 source가 정상적으로
   비어 있을 때만 동일 exact LUT key를 허용하고, cached-value 오류·non-finite·상충 duplicate로 차단된 key는
   LUT가 있어도 합집합에 넣지 않는다.
5. 같은 좌표가 양쪽에 있어도 Step2 선택 좌표는 하나로 만든다.
6. Step2에는 값과 출처를 빼고 선택 가능한 좌표 catalog만 전달한다. v4는 상위 범위 확장 시 child의
   운영 상태를 구별하도록 값이 있는 `Life Cycle Category`만 판단용 `applicability_attributes`로 함께
   전달하며, 공란 metadata는 exact slot을 제외하지 않고 이 속성에서만 생략한다.

`new-bc-v5`의 2026~2030 authoritative record 수는 GDP 815, PMI 5,040, PowerMix 4,200,
Temperature 5,040, Population 845, HurricaneIntensity 60, LiqProdAdjustment 23,820,
LiqUtilAdjustment 23,820, PipelineAdjustment 420, SupplyDisruption 4,908이다. source mapping과 변환은
[Basecase·LUT 문서](./05_MODEL_PARAMETER_AGENT_BASECASE_LUT_PARSING.md#11-v4-new-bc-v5-read-only-proposal-계약)를
따른다.
기존 adjustment write target에서 관찰된 93/48/57/150/33,348은 같은 순서의
authoritative count가 아니며, 신규 source slot을 제한하는 whitelist로 사용하지 않는다.

PowerMix materialization은 월별로 반복된 annual row가 일치할 때만 dedupe한다. 각
`(Country, Year)`의 승인된 10-member raw source vector에 누락·중복·비유한·범위·합계
오류가 있으면 해당 group 전체를 exact slot catalog에서 제외한다. raw fraction에는 기존 Basecase 5자리
정밀도 변환이나 재정규화를 적용하지 않으며, Basecase/LUT를 결합한 effective vector도 합 `1±1e-6`을
다시 통과해야 한다.

좌표를 compact하게 묶는 상세 방식은 뒤의 [compact slot catalog](#33-compact-slot-catalog)에 설명한다.

LUT-backed 활성 10개와 Basecase-only 활성 4개는 0032 canonical fixture와 release 검증의 capability 기준선이다.
runtime startup은 v4 contract schema/path와 contract에 고정된 Workbook path/digest만 경량 검증한다.
sheet/header/range/고정 record count와 source atomic 검증은 최초 exact v4 materialization에서
fail closed하고, 성공 결과를 해당 process에 cache한다. 기존 v1/v3 Basecase preload의
누락·파싱 오류·0건은 warning을 남기고 계속한다. 현재 v4 신규 proposal Flow의 이 단계에는 기존
`new-bc-v5`에 선언된 extend10 10종이 동일한 contract reference→exact LUT fallback 경로로 도달한다.

### 1.4 Step2: 적용할 exact slot 선택

system prompt `SLOT_PROPOSAL_SYSTEM`은 “값을 판단하지 말고 실제 catalog 안에서 적용 좌표만 고른다”는 역할이다.

- 이전 단계에서 확정된 파라미터의 필요성을 다시 판단하지 않는다.
- v1/v3 lineage 또는 v4 ordered events·선택 value·Lever provenance에 관련된 exact slot만 선택한다.
- `parameter_hint`와 `mapping_comment`는 국가·시설·기간·route 같은 좌표 의미를 해석하는 데 쓴다.
- 승인 projection은 좌표 해석의 보조 근거로만 쓰고 readiness가 false라는 이유로 task를 생략하지 않는다.
- catalog에 없는 값, nearest 좌표, 서로 다른 hierarchy branch를 섞은 좌표를 만들지 않는다.
- 관련성이 약한 slot로 최대 개수를 채우지 않는다.
- v4는 exact 좌표가 catalog에 존재한다는 사실과 현재 Scenario 적용성을 구분한다. 상위 branch를 확장하기
  전에 각 child의 `applicability_attributes`, parameter·binding applicability, 선택 dimension/value와
  Event의 대상·상태·기간을 대조한다.
- 기존 운영 설비의 outage·maintenance·feedgas/shipment 차질·회복은 명시적인 신규 Train·FID·착공·COD·
  startup·commissioning·ramp-up 근거가 없으면 `Operational`/`Operating` child만 선택한다.
  `FID`·`Planned`·`Under Construction`은 해당 신규 설비 근거가 있을 때만, `Closed`는 재가동 근거가
  있을 때만 선택한다. 신규 프로젝트 근거도 같은 parent의 다른 계획 설비나 operational sibling 전체로 확대하지 않는다.
- v4는 정량 변화폭이 없어도 대상·기간을 설명할 수 있는 exact slot을 선택한다. Event가 Plant·국가·지역
  전체 영향을 명시하면 applicability 필터를 통과한 해당 catalog branch의 관련 하위 좌표를 상한 안에서
  선택할 수 있지만, 전체 범위 근거가 없으면 임의의 대표 시설이나 하위 branch로 확대하지 않는다.
- v4의 명시 연월이 없더라도 scenario narrative, selected dimension, Lever `time_window`와 기간 해석 정책이
  하나의 현재 이후 기간을 뒷받침하면 해당 exact 기간을 사용할 수 있다.
- v4 PowerMix가 한 `(Country, Year)` member를 선택하면 서버가 contract의 10개 Energy Source 전체를 같은
  atomic group으로 확장한다. 확장 전 seed는 `Country, Year, Energy Source` 3축의 중복·누락·추가 축,
  정수 Year와 승인 member를 검증하며, member 하나라도 유효한 exact reference가 없으면 group 전체를 제외한다.

실제 user message prefix는 다음과 같다.

```text
아래 JSON만 근거로 Step2 수급모델 parameter slot 축을 제안하십시오.
```

| 입력 최상위 항목 | 기능 |
|---|---|
| `scenario_brief` | 관련 scenario group·scenario·dimension과 v1 event 또는 ordered v3/v4 events 문맥 |
| `period_resolution_policy` | “3개월” 같은 표현을 현재 연월 이후 기간으로 해석하는 규칙 |
| `slot_selection_limits` | 파라미터별 반환 slot 상한과 우선순위 |
| `parameter_slot_tasks` | 파라미터, 선택·보조 dimension, 실제 slot catalog와 v4 terminal의 판단 전용 `applicability_attributes` |

응답은 각 선택 좌표의 `candidate_key`와 `slot_axes`만 받는다.

```json
{
  "parameter_slots": [
    {
      "candidate_key": "<입력 candidate_key>",
      "slot_axes": [
        {"axis_name": "Country", "axis_value": "China"},
        {"axis_name": "Year", "axis_value": 2026}
      ]
    }
  ]
}
```

서버는 모든 축이 빠짐없이 있는지, catalog의 exact 좌표인지, 중복·모호한 값·상한 초과가 없는지 검사한다.
이 검사는 구조적 존재를 보장하지만 자연어 Scenario와의 의미상 applicability를 대신 판정하지는 않으므로,
Step2가 위 lifecycle 계약으로 child를 고른다. 유효한 좌표에만 다음 단계에서 `slot_key`를 발급한다.

### 1.5 exact 기준값 결정

이 단계도 LLM을 호출하지 않는다. Step2에서 선택된 정확한 좌표마다 다음 규칙을 적용한다.

| Basecase | LUT | Step3 `reference_value` |
|---|---|---|
| 값 있음 | 값 있음 또는 없음 | Basecase 값 |
| 값 없음 | 값 있음 | LUT 값 |
| 값 없음 | 값 없음 | 해당 slot 제외 |

Basecase-only parameter는 두 번째 행의 LUT fallback 대상이 아니므로 Basecase가 없으면 제외한다.
v4 `new-bc-v5` source가 오류·non-finite·상충 duplicate로 exact key를 명시적으로 차단한 경우는 “값 없음”이
아니며, 두 번째 행으로 내려가지 않고 해당 slot을 제외한다.

서버는 각 유효 slot에 현재 요청의 파라미터 task 안에서만 사용하는 `slot_key`를 발급하고, Step3에 `slot_key + coordinates + reference_value`를 전달한다. Basecase와 LUT의 두 값이나 source 이름을 동시에 보내지 않는다. v4 PowerMix는 10개 effective reference가 모두 존재하고 각 값 0~1, 합 `1±1e-6`을 만족해야 이 단계에서 전체 group을 유지한다.

### 1.6 Step3: 제안값과 근거 생성

system prompt `VALUE_PROPOSAL_SYSTEM`은 “확정된 slot과 기준값을 바꾸지 말고 실제 모델 입력값과 근거를 만든다”는 역할이다.

- `parameter_hint`로 값의 의미·단위·스케일·산정 제약을 해석한다.
- legacy `mapping_comment` 또는 v4 binding applicability와 모든 dimension·event·Lever provenance로 적용 방향을 판단한다.
- indirect dimension은 기간·강도·대상 해석에만 쓰고 후보나 slot을 확장하지 않는다.
- 여러 dimension/event의 방향·강도·기간·대상이 다르면 그 관계와 충돌을 하나의 최종값과 근거로 종합한다.
- 서버가 dimension별 결과를 합산·평균하는 공식을 적용하지 않으며, LLM이 parameter task 전체를 보고 slot별 최종 절대값 하나를 반환한다.
- 서로 반대 방향의 Lever가 같은 parameter로 병합되면 양쪽 provenance를 보존하고 상쇄 관계를 설명하되 slot별 최종값은 하나만 반환한다. Lever direction·pressure/domain을 숫자 부호로 직접 변환하지 않고 parameter hint, 단위, applicability와 기준값으로 산정한다.
- 모든 입력 slot에 유효한 숫자 하나와 slot별 근거 하나를 반환한다.
- 입력에 없던 `candidate_key`나 `slot_key`를 만들지 않는다.

v4의 정량 근거가 부족할 때는 일반적으로 제안을 포기하지 않고 다음 증거 우선순위를 사용한다.

1. selected Scenario branch의 적용 결과로 명시된 최종 절대값을 parameter 단위·스케일에 맞춰 사용한다.
   Event의 과거·현재 관측값은 Scenario 적용값으로 오인하지 않는다.
2. 명시된 증감량·증감률·승수를 `reference_value`에 적용해 최종 절대값으로 바꾼다.
3. 방향·강도·기간만 있으면 parameter hint의 범위 안에서 reference 기준의 보수적인 비영 변화를 제안한다.
4. 방향이 불명확하거나 상반된 영향이 완전히 상쇄되면 reference를 중립 초기값으로 사용하고 가정을 설명한다.

고정 비율을 모든 parameter에 공통 적용하거나 Event의 무관한 가격·물량 숫자를 다른 단위의 parameter 값으로
전용하지 않는다. 불확실성은 값 누락이나 제안 거절이 아니라 rationale의 모델링 가정과 사용자 검토 필요성으로
표현한다. 서버는 여전히 exact slot과 유한 숫자를 검증하며 누락값을 임의로 보정하지 않는다.

v4 `LiqUtilAdjustment`는 selected Lever·Scenario/Event scope와 applicability 필터 뒤 exact 후보가 하나면
시설·기간 문구 일부가 생략돼도 `UNIQUE_INFERRED`로 허용한다. exact 후보가 여러 개거나 명시 대상·기간이
slot과 모순되면 `ABSTAINED_INSUFFICIENT_EVIDENCE`로 제외한다. 같은 원칙을 Pipeline/Supply slot에도 적용하며,
정량 변화폭 없이 방향만 유효하면 reference 대비 작은 비영 최종값과 가정·사용자 검토 필요성을 rationale에 남긴다.
절대 연월·분기·반기와 교차연도 범위는 연속 월 구간으로 해석하고, `N개월`·올해/내년·이번달/다음달은
요청 처리 시점의 현재 연월을 기준으로 유한 범위만 인정한다. 올해/내년과 결합된 분기·반기도 해당 월만
인정하며, 연도 없는 절대 분기·반기, 범위 밖 token, 역전 범위, 음수·소수 개월은 일치 근거가 아니다.

실제 user message prefix는 다음과 같다.

```text
아래 JSON만 근거로 Step3 수급모델 parameter slot 값을 제안하십시오.
```

| 입력 항목 | 기능 |
|---|---|
| `scenario_brief` | 값의 방향·강도·기간을 판단할 관련 문맥 |
| `parameter_value_tasks[].parameter` | 파라미터명, hint, semantic axes |
| `selection_dimensions` | legacy selection source 또는 v4 dimension/value/Event/Lever/binding provenance 전체 |
| `supporting_dimensions` | 값 산정을 보조하는 indirect dimension과 reason |
| `slots` | 서버가 확정한 `slot_key`, 좌표, 단일 기준값 |

현재 응답 계약은 다음과 같다.

```json
{
  "parameter_adjustments": [
    {
      "candidate_key": "<입력 candidate_key>",
      "rationale_ko": "<파라미터 전체 근거>",
      "slot_values": [
        {
          "slot_key": "<입력 slot_key>",
          "proposed_value": 0.041,
          "rationale_ko": "<해당 slot의 기준값과 제안값 근거>"
        }
      ]
    }
  ]
}
```

Step3는 같은 호출에서 두 종류의 근거를 만든다.

| 구분 | 파라미터 근거 | slot별 value 근거 |
|---|---|---|
| 답하는 질문 | 왜 이 파라미터를 이 시나리오에 적용했는가? | 왜 이 정확한 좌표의 기준값을 이 값으로 바꿨는가? |
| 생성 개수 | 파라미터당 1개 | 입력 slot당 1개 |
| 작성 범위 | 전체 적용 기간·대상·배분 원칙·제약 | 좌표, 기준값→제안값 해석 |
| 피해야 할 내용 | 개별 slot 계산 나열 | 파라미터 전체 근거 반복 |
| LLM 응답 필드 | `parameter_adjustments[].rationale_ko` | `slot_values[].rationale_ko` |

prompt는 파라미터 근거에 개별 slot 값을 나열하지 말고, slot 근거에는 `reference_value`와 hint/comment/dimension을 어떻게 해석했는지 짧게 설명하도록 요구한다. 여러 source가 수렴한 task의 파라미터 근거에는 event·dimension 간 상호작용과 방향·강도·기간·대상 충돌을 어떻게 종합했는지 설명한다. 두 근거 모두 내부 key나 구현 용어를 사용자 설명에 노출하지 않는다.

### 1.7 서버 검증과 proposal 저장

서버는 Step3 응답을 그대로 저장하지 않는다.

- 입력에 없거나 중복된 `candidate_key`와 `slot_key`를 제외한다.
- 요청한 slot 누락, `null`, 무한대, 숫자가 아닌 제안값을 검사한다.
- 제안값이 유한 숫자인지 검사하되 설정 기반 소수 자릿수 round/trunc/ceil은 적용하지 않는다.
- v4 PowerMix는 `(Country, Year)`별 `Liquids/Hydro/Solar/Wind/Bioenergy/Gas/Coal/Nuclear/Geothermal/Other`
  10개 응답이 모두 있고 각 값이 0~1이며 합이 절대오차 `1e-6` 이내에서 1인지 검사한다. 일부 member만
  성공시키지 않고 실패한 atomic group 전체를 제외한다.
- v4 LiqUtilAdjustment는 음수만 제외하고 1 초과의 관측·제안값은 clamp하거나 거부하지 않는다.
- 서버가 보관한 좌표, Basecase/LUT reference, 모델 대상을 key로 다시 결합한다.
- 유효한 slot이 남은 결과만 proposal JSON으로 만든다.

의미 검증에 실패한 개별 항목은 제외하되 다른 유효 항목은 유지한다. 하나 이상의 유효값이 남으면 전체 결과는
`PROPOSED`다. 최종 유효값이 0개이면서 정상적인 판단 결과이면 `ABSTAINED`로 저장하고, 제안 범위 밖·근거
부족·입력 위치 미확정·값 미생성·허용 범위 이탈·변경 없음 중 하나의 `ABSTAINED_*` 사유를 남긴다. LLM 호출,
LLM 응답 형식, DB 접근, 계약 무결성 등 실행 오류만 `FAILED`로 저장한다. 동기 요청도 빈 `PROPOSED` 대신
`ABSTAINED` 행과 구조화된 결과를 반환한다.

v4 Step2가 빈 결과로 끝나면 내부 `slot_selection_diagnostics`에 catalog 후보 수, LLM 원본 slot 수, 형식
검증 통과 수, exact 검증 통과 수와 제외 수를 남긴다. 오류 문구는 이 구조화된 수치로 `catalog 위치 없음`,
`시나리오 근거만으로 선택하지 못함`, `위치 형식 불일치`, `exact 좌표 불일치`를 구분한다. 선택 자체가
0건이면 구조화된 Lever `scope`와 `timeWindow`의 구체성을 함께 확인해, 대상 범위는 있으나 연도·월이
모호한 경우처럼 사용자가 보완할 정보를 안내한다. 확인되지 않은 특정 Plant·기간·lifecycle을 실패 원인으로
단정하지 않으며, 진단 객체는 API·callback·proposal JSON에 노출하지 않는다.

proposal Step3의 `proposedValue`는 유한 숫자여야 한다. Confirmation은 `proposedValue` key를 요구하지만 값은
`null`일 수 있고, `null`이 아닌 값만 persistence 경계에서 엄격한 유한 숫자로 정규화한다. 두 경로 모두
설정 기반 소수 자릿수 정밀도 변환은 하지 않는다. Basecase/LUT 기준값의 기존 정밀도 정책은 유지하되,
v4 PowerMix authoritative fraction은 atomic sum을 훼손하지 않도록 원본 정밀도를 보존한다.
`new-bc-v5`의 파라미터별 validator와 진단은 server-side에만 두며 public JSON 필드를 추가하지 않는다.

동기 요청은 처리가 끝난 `PROPOSED` 또는 `ABSTAINED` 결과를 바로 반환한다. 비동기 요청은 먼저 HTTP `200`과
`PROCESSING`을 반환하고 백그라운드에서 `PROPOSED`, `ABSTAINED`, `FAILED` 중 하나로 갱신한 뒤 callback을
보낸다. resource runtime 미등록은 `RUNTIME_REGISTRY_NOT_READY` 실패로 기록한다. 동기 요청은 같은 오류를
graph 실행 중 즉시 HTTP `503`으로 반환한다. 두 방식의 후보·slot·값 판단 규칙은 같다.

저장 식별자는 버전에 따라 다르다. v1은 proposal의 `mi_event_id`에 대표 event ID를 저장한다. v3/v4는 여러 event 중 하나를 대표값으로 선택하지 않고 `mi_event_id=NULL`로 저장하며 `scenario_group_id`를 authoritative link로 사용한다. 기존 API와 callback의 optional `eventId`도 v3/v4에서 `null`로 반환한다.

## 2. Confirmation

### 실행 구조

```mermaid
flowchart LR
    A[저장된 PROPOSED 제안] --> B[사용자 검토·수정]
    B --> C[필수 key·모델 대상·좌표·non-null 숫자 검증]
    C -->|정상| D[(CONFIRMED 저장)]
    C -->|오류| E[수정할 내용 안내]
```

확인 단계에서는 LLM을 호출하지 않는다. 사용자가 보낸 파라미터명, 모델 대상, slot 축, 기준값, 제안값과 근거의 구조를 확인한 뒤 같은 proposal 행을 `CONFIRMED`로 갱신한다. 각 value 객체에는 `basecaseValue`, `proposedValue`, `rationale` key가 필요하지만 `proposedValue` 값은 `null`일 수 있다. 원래 proposal과 항목·값을 비교하지 않으므로 사용자는 유효한 전체 payload에서 항목을 수정·추가·삭제할 수 있다. 이미 확정된 건도 다시 확정할 수 있다. runtime allow-list는 신규 proposal 생성에만 적용하며 기존 저장 행이나 confirmation을 추가로 제한하지 않는다. canonical master에 없는 custom parameter도 기존 공통 구조 검증을 통과하면 확정할 수 있다.

## 3. 구현 경계와 prompt 크기 보호

### 3.1 token과 prompt 크기를 줄이는 방식

| 구간 | 현재 구현 방식 |
|---|---|
| Step1.5 | v1/v3 legacy routing applicability 판단이 필요할 때만 호출; v4는 호출하지 않음 |
| 관련 문맥 | 각 단계와 현재 후보에 필요한 dimension/value/Event/Lever만 남기고 무관 정보와 상태·감사 컬럼 제외 |
| 후보 task | 같은 파라미터의 여러 source를 한 task로 병합하고 legacy lineage 또는 v4 Lever provenance 보존 |
| Step2 입력 | Basecase/LUT 원본 행·값·출처·일반 metadata를 제외한 compact 좌표 catalog. v4만 terminal별 값이 있는 `Life Cycle Category`를 판단 전용 `applicability_attributes`로 포함 |
| Step2 응답 | `candidate_key + slot_axes`만 수신 |
| Step3 입력 | Step2 exact 검증을 통과한 slot만 `slot_key + coordinates + reference_value`로 전달 |
| Step3 응답 | 좌표·기준값·출처를 다시 받지 않고 `slot_key + proposed_value + rationale`만 수신 |
| JSON 표현 | prompt JSON을 들여쓰기와 불필요한 공백이 없는 한 줄로 직렬화 |
| 크기 보호 | 요청 전체 slot 수와 Step1.5·Step2·Step3 compact JSON byte 상한을 넘으면 LLM 호출 전에 task별 크기를 포함해 실패 |

### 3.2 DB 활용 컬럼과 prompt 위치

Agent가 업무 문맥을 조회하는 핵심 키는 `scenario_id`다. DB 행 전체를 LLM에 보내지 않고 아래 정보 중 필요한 항목만 prompt JSON으로 다시 구성한다.

```mermaid
flowchart LR
    A[(scenario)] --> G[scenario_brief]
    B[(scenario_group)] --> G
    C[(v1 event / v3·v4 events)] --> G
    D[(v1 template /\nv3·v4 dimension definitions)] --> G
    R[(ordered group-event relation)] --> G
    E[(legacy mapping / v4 Lever catalog)] --> H[parameter task]
    F[(model parameter)] --> H
    G --> I[Step1.5 / Step2 / Step3]
    H --> I
```

| DB 테이블 | 읽는 주요 컬럼 | prompt 또는 서버 사용 위치 |
|---|---|---|
| `tmm_mi_scenario_m` | `scenario_id`, `title`, `narrative`, `dimension_values`, `impact_jkm`, `impact_ttf`, `impact_hh` | `scenario_brief` |
| `tmm_mi_scenario_group_m` | `title`, `summary`, `description`, `dimension_selected`, `api_version`, `generation_strategy`, `dimension_definitions`, catalog checksum | adapter 분기, v3 lineage 또는 v4 selected value·Lever 검증 |
| `tmm_mi_scenario_group_event_m` | `mi_event_id`, `event_type_l2_id`, `scenario_dimension_template_id`, `display_order` | v3는 source ref 역투영, v4는 `mi_event_id`·`display_order` 관계만 사용 |
| `tmm_mi_scenario_dimension_template_m` | `scenario_dimension_template_id`, `template_json` | v1 관련 dimension과 v3 source ref relation 검증 |
| `tmm_mi_dimension_value_mapping_m` | `dimension_id`, `display_value`, `source_projections`, `status`, `mapping_version` | 같은 v3 자유 value의 approved projection 보조 근거와 warning |
| `tmm_mi_mievent_m` | `mi_event_id`, `event_type_l2_id`, `event_title`, `one_line_summary`, `key_bullets_json`, `detail_analysis`, `tags_json` | v1 `scenario_brief.event` 또는 제한된 v3 `scenario_brief.events[]` |
| `tmm_mi_model_param_dimension_map` | `event_type_l2_id`, `dimension_key`, `dimension_label`, `mapping_method`, `model_param_id`, `comment` | v1/v3 후보 선정, selection/supporting dimension. v4는 조회하지 않음 |
| `tmm_mi_model_impact_lever_m` | Lever code/ID, domain, binding, applicability, active/catalog version | v4 catalog checksum·code/ID 검증과 executable 후보 선정 |
| `tmm_mi_model_param_m` | `parameter_name`, `parameter_hint`, `semantic_axes`, `model_file`, `model_sheet`, `model_table`, `basecase_*` | parameter task, 모델 대상, 서버 Basecase·slot catalog 생성 |
| `tmm_mi_event_type_l1_m` | `event_type_l1_id`, `level_1_code`, `level_1_label` | event type 문맥 조회 |
| `tmm_mi_event_type_l2_m` | `event_type_l2_id`, `event_type_l1_id`, `level_2_code`, `level_2_label` | v1/v3 legacy mapping 문맥. v4 후보 선정에는 사용하지 않음 |

prompt에 넣지 않는 대표 정보는 scenario의 상태·확률·baseline 여부, group의 상태·단계·사용자 정보, event의 일자·감사 컬럼, model parameter의 Excel 행·열 설정 원문이다. v3에서는 lineage grounding을 위해 event ID/type을 예외적으로 `events[]`에 포함한다.

<a id="hint-and-mapping-comment"></a>

#### parameter hint와 mapping comment

| DB 컬럼 | prompt에서의 의미 |
|---|---|
| `tmm_mi_model_param_m.parameter_hint` | 파라미터 값의 의미·단위·스케일·산정 제약 |
| `tmm_mi_model_param_dimension_map.comment` | 현재 dimension과 파라미터가 연결되는 이유와 우선 판단 근거 |
| `tmm_mi_model_impact_lever_m` binding applicability | v4 Lever와 primary/alternative parameter를 연결하는 적용 조건 |

| 단계 | `parameter_hint` 위치 | mapping `comment` 위치 |
|---|---|---|
| Step1.5 | `routing_tasks[].candidates[].parameter_hint` | legacy `mapping_comment` |
| Step2 | `parameter_slot_tasks[].parameter.parameter_hint` | selection provenance의 legacy comment 또는 v4 applicability |
| Step3 | `parameter_value_tasks[].parameter.parameter_hint` | 전체 selection/Lever provenance와 applicability |

`indirect` comment는 `supporting_dimensions[].reason`으로 들어가고, `na` comment는 prompt에 넣지 않는다.

GDP task에는 다음 의미의 정보가 주입된다.

```json
{
  "parameter": {
    "parameter_name": "GDP",
    "parameter_hint": "국가·연도별 실질 GDP 전년 대비 성장률의 최종 입력값이다. 0.042는 4.2%이며 증감폭이 아니라 적용할 성장률 자체를 제안한다."
  },
  "selection_dimensions": [
    {
      "dimension_key": "economic_intensity",
      "dimension_value": "보통",
      "mapping_method": "direct",
      "mapping_comment": "event의 국가별 GDP 성장률 전망과 전망치 수정폭을 우선 사용해 최종 성장률을 산정한다."
    }
  ],
  "supporting_dimensions": [
    {
      "dimension_key": "period",
      "dimension_value": "3개월",
      "mapping_method": "indirect",
      "usage_policy": "parameter_value_hint",
      "reason": "파라미터의 시간축으로 사용될 수 있다(PMI:Year/Month, GDP:Year)."
    }
  ]
}
```

### 3.3 compact slot catalog

Step2는 설정 기간 안에서 값이 존재하는 Basecase와 LUT exact 좌표의 합집합을 보내되, 전체 record는 서버 cache/index에만 유지한다. 각 좌표를 행처럼 반복하지 않고 다음 규칙으로 압축한다.

1. `key_axes`를 `Year`·`Month`와 Country·시설 같은 고정축으로 나눈다.
2. 동일한 기간 목록을 공유하는 leaf는 `period_groups` 하나를 참조한다. 반복되는 2026~2030 연·월 목록은 group별 한 번만 직렬화한다.
3. Country→Plant→Train 같은 고정축은 `fixed_axis_hierarchy`에 level 순서대로 중첩해 상위 값을 한 번만 적는다.
4. hierarchy terminal의 `period_group_id`와 해당 group의 `available_periods`를 결합해야만 exact 좌표가 된다.
5. `Year + Month`이면 같은 연도의 월을 `Months` 배열 하나로 묶는다.
6. 값, 원본 행, reference ID, source와 일반 metadata는 Step2 catalog에서 제외한다. v4는 의미상 과확장을
   막기 위해 non-time branch별 값이 있는 `Life Cycle Category`만 `applicability_attributes`로 남기며, 이는
   business key나 반환 `slot_axes`가 아니다. v1/v3 catalog에는 이 필드를 넣지 않는다.

PMI catalog의 국가·연도별 월 좌표는 다음과 같은 계층으로 표현된다.

```json
{
  "parameter_name": "PMI",
  "key_axes": ["Country", "Year", "Month"],
  "fixed_axis_names": ["Country"],
  "time_axis_names": ["Year", "Month"],
  "period_groups": [
    {
      "period_group_id": "period-group-1",
      "available_periods": [
        {"Year": 2026, "Months": [1,2,3,4,5,6,7,8,9,10,11,12]}
      ]
    }
  ],
  "fixed_axis_hierarchy": [
    {"axis_value": "China", "period_group_id": "period-group-1"}
  ]
}
```

서로 다른 hierarchy branch의 축과 period group을 섞어 새 좌표를 만들 수 없다. `maxParameterSlots`는 입력 catalog를 자르는 값이 아니라 LLM이 파라미터별로 반환할 slot 수의 상한이다. 요청 전체 선택 slot은 `model_parameter_max_total_selected_slots`로 제한한다. Step1.5와 Step2 prompt는 `model_parameter_max_step2_prompt_bytes`, Step3 prompt는 `model_parameter_max_step3_prompt_bytes`를 사용해 LLM 호출 전에 제한한다.

예를 들어 v4 `LiqUtilAdjustment`에서 같은 Freeport LNG parent 아래 T1 terminal이
`{"Life Cycle Category":["Operational"]}`, T4가 `{"Life Cycle Category":["Planned"]}`이면 기존 설비
회복 Scenario는 T1을 검토할 수 있지만 신규 Train 가동 근거 없이 T4까지 확장하지 않는다. 두 속성은 좌표
선택 판단에만 쓰며 응답 `slot_axes`에는 포함하지 않는다.

원본 record를 평면 전송하지 않도록 period group과 hierarchy를 사용한다. 실제 실행 보고서에는 provider가 반환한 input/output/total token과 prompt byte를 기록한다.

### 3.4 dimension 필터와 key 기반 재조합

| 단계 | prompt에 남기는 dimension |
|---|---|
| v1/v3 Step1.5 | routing 조건 검증에 필요한 composite scenario dimension과 원본 source lineage |
| v1/v3 Step2·Step3 | 후보를 만든 direct·routing composite/source dimension과 값 산정에 필요한 indirect dimension |
| v4 모든 단계 | 선택 value의 dimension/Event/Lever/binding provenance와 unchanged supporting context |
| 모든 단계 | 현재 후보에 무관한 dimension은 제외 |

v1은 같은 allow-list를 scenario의 `dimension_values`, group의 `dimension_selected`, dimension template에 적용한다. v3는 scenario composite value, group `dimension_definitions`, source refs/event IDs와 승인 projection을 함께 필터링하되 선택된 source lineage는 잘라내지 않는다.

v4는 scenario `dimension_values`가 선택한 value만 찾고 그 value의 `lever_states` 전체를 보존한다. 미선택 value의 state 합집합, legacy `lever_mappings` 계열, Event Type/dimension mapping fallback은 포함하지 않는다. unchanged state는 supporting context에만 남긴다.

LLM 응답은 서버 key로 원본과 다시 조합한다.

```mermaid
flowchart LR
    A[Step2 응답<br/>candidate_key + slot_axes] --> B[서버 exact 검증]
    B --> C[slot_key 발급]
    C --> D[Step3 입력<br/>slot_key + 좌표 + 기준값]
    D --> E[Step3 응답<br/>slot_key + 제안값 + 근거]
    E --> F[서버가 모델 대상·좌표·reference 재조합]
```

GDP slot 처리 예시에서 Step2는 `candidate_key + Country + Year`를 반환한다. 서버가 이를 검증해 `slot-1`을 발급하고, Step3는 좌표를 다시 반환하지 않고 다음 정보만 돌려준다.

```json
{
  "candidate_key": "21|economicintensity|gdp|demand|gdppopulationadjustment",
  "slot_values": [
    {
      "slot_key": "slot-1",
      "proposed_value": 0.041,
      "rationale_ko": "2026년 중국의 기준 성장률 4.2%를 단기 수요 둔화에 맞춰 4.1%로 소폭 조정했습니다."
    }
  ]
}
```

서버는 `candidate_key`로 파라미터와 모델 대상을, `slot_key`로 좌표와 reference를 찾아 최종 API/DB 결과를 조립한다.

### 3.5 `uncovered_only` proposal-only campaign

`tests/manual/model_parameter_agent/run_proposal_only.py`는 public proposal endpoint를 대체하지 않는 bounded
운영 runner다. 기본 모드는 DB read-only discovery이며, `--execute`를 명시한 경우에만 uncovered Scenario의
proposal graph를 순차 실행한다. Confirmation과 callback은 호출하지 않는다.

```bash
# Group 단위 read-only discovery
python tests/manual/model_parameter_agent/run_proposal_only.py \
  --scenario-group-id 282 \
  --capability-release extend10-v5

# 명시 Scenario 단위 proposal-only write; 별도 write 승인이 있을 때만 실행
python tests/manual/model_parameter_agent/run_proposal_only.py \
  --scenario-id 1374 \
  --scenario-id 1375 \
  --capability-release extend10-v5 \
  --execute
```

초기 `uncovered-only-v1` 정책은 우회 옵션을 제공하지 않는다.

- Group 또는 Scenario ID 중 한 종류의 명시 범위가 필수다.
- `extend10-v5`는 임의 label이 아니라 catalog `v4.0` / checksum
  `416017351f2b9539370963a3ca413914876da55a1db3f41e3dacd34bd466c763`, extend10 capability와
  `new-bc-v5` contract SHA, resource semantic schema와 실제 Basecase/LUT content fingerprint를 묶은 고정
  계약이다. 어느 하나라도 drift하면 Scenario DB 조회 또는 LLM 실행 전에 차단한다.
- v4 `multi_event_model_lever_dimensions`, completed Group, created/realized Group·Scenario만 실행 후보가 된다.
- Group에 저장된 catalog full pin, selected Lever lineage와 raw/runtime allow-list 경계는 기존 v4 quality oracle로
  write 전에 검증한다.
- lifecycle/capability skip을 포함한 명시 범위 전체에서 비삭제 proposal 이력을 조회한다. `CONFIRMED` 또는
  `PROPOSED`가 하나라도 있으면 해당 Scenario를 skip한다.
- stale 기준을 신뢰할 heartbeat/공통 threshold가 아직 없으므로 `PROCESSING`이 하나라도 있으면 stale 여부를
  추정하지 않고 campaign 전체를 hard-stop해 수동 조사를 요구한다.
- `ABSTAINED`/`FAILED` 이력만 있거나 이력이 없으면 uncovered다.
- read-only는 DB write와 resource bootstrap을 실행하지 않고 체크인된 contract를 검증한다. `--execute`는
  Scenario DB 조회 전에 runtime resource를 고정하고 실제 파일을 다시 hash한 source/schema/resource fingerprint를
  manifest에 먼저 저장한다. 이어 proposal 전체 mapped column과 v4 `mi_event_id nullable`을 schema preflight한다.
- 전체 cohort를 먼저 판정한 뒤, 각 write 직전에 runtime resource, Scenario/Group lifecycle, catalog pin,
  prompt 입력 전체와 candidate digest를 다시 읽어 최초 input fingerprint와 비교하고, 명시 campaign 범위 전체의
  proposal 이력을 다시 조회한다. graph가 실제로 사용한 context도 persistence 직전에 frozen context와 대조한다.
  하나라도 바뀌면 proposal row를 쓰지 않고 남은 campaign을 중단한다.
- Scenario당 최대 한 번, sequential single worker, outer retry 없음으로 실행하며 proposal ID 전후 snapshot과
  정확히 한 행의 delta, 완료 시각, v4 response identity, runtime Parameter 경계와 API/DB proposal payload 일치를
  검증한다. DB payload의 `lutValue` 저장은 실패로 판정한다.
- evidence JSON에는 capability release, 실제 코드 allow-list, catalog pin, resource contract/fingerprint,
  `uncovered-only-v1`, Scenario input fingerprint, 기존 proposal 상태와 skip/hard-stop 사유를 기록한다.

이 가드는 단일 worker pilot의 best-effort 안전장치다. DB unique claim이나 logical run이 없으므로 여러 process가
동시에 같은 Scenario를 실행하는 exactly-once 보장은 하지 않는다. multi-worker 확대 전에는 logical-run
fingerprint와 DB uniqueness를 별도 도입해야 한다. 그 전의 `--execute` 운영에서는 다른 runner와 public proposal
요청이 같은 cohort를 동시에 처리하지 않도록 운영 singleton을 별도로 보장해야 한다.

### 3.6 호환성 경계와 배포 전제

- public proposal/confirmation request·response·callback와 저장 JSON shape은 바뀌지 않는다. v3/v4는 기존 optional `eventId`를 `null`로 반환하고 `scenarioGroupId`를 authoritative 식별자로 사용한다.
- `new-bc-v5`는 v4 `multi_event_model_lever_dimensions`의 read-only proposal에만 적용한다. 기존
  `resources/basecase/`와 v1/v3 파싱은 유지하며 workbook write, Formula/Query 재계산과
  Demand/Supply/Trade engine 실행은 하지 않는다. read-only는 Workbook/reference 경계이며 기존 proposal
  persistence를 비활성화한다는 뜻이 아니다.
- 체크인 v1/v3 129행 mapping의 direct/routing 전역 합집합은 raw 10개, 0032 canonical v4 Lever-native executable binding
  전역 합집합은 raw 14개에 도달할 수 있다. 요청 하나에서는 관련 하위 집합만 후보가 되며, v1/v3는 5종,
  v4는 extend10 10종 scope gate를 적용한 뒤에만 Basecase 우선/LUT fallback과 LLM 단계로 진입한다.
- 0032 canonical 기준선은 master 21행·활성 14개, v4 active Lever 18개, raw/effective binding 16/14다. runtime은
  Scenario 생성 시 `catalog_version=v4`를 명시하고, Model Parameter context에서는 Group에 저장된 version으로
  catalog를 조회한 뒤 checksum을 검증한다. v4는 shared mapping을 조회하지 않는다.
- 이 resource overlay는 DB schema와 master/catalog/mapping data, parameter master, Lever binding·catalog checksum과 legacy mapping을
  변경하지 않는다. 별도의 catalog 변경 release에서는 master와 Lever catalog를 한 transaction으로 적용하고,
  checksum이 바뀌면 신규 v4 Scenario를 생성한다. Agent runtime은 DDL이나 canonical DML을 실행하지 않는다.
- 시작 시 schema validation이 필수 테이블·컬럼과 nullable 계약을 검사한다. 누락된 schema를 임의로 우회하지 않고 startup 또는 context load에서 명확히 실패시킨다.
- confirmation의 custom parameter와 항목 추가·삭제 허용, 기존 저장 데이터는 유지한다. `proposedValue` key는 필수지만 Confirmation 값은 `null`일 수 있고, non-null 값만 persistence에서 유한 숫자로 검증한다. proposal Step3 값은 유한 숫자여야 한다. 설정 기반 소수 자릿수 정밀도 변환은 적용하지 않으며 Basecase/LUT 기준값 정밀도 정책은 유지하되 v4 PowerMix source fraction은 원본 정밀도를 보존한다. v4 `new-bc-v5`의 PowerMix atomic 범위·합계, HurricaneIntensity 0~4 정수, 파라미터별 제약/evidence 검증은 proposal 내부 정책이며 Confirmation의 공통 공개 계약을 바꾸지 않는다.

## 관련 문서

- API 호출 방법과 응답: [API 문서](./02_MODEL_PARAMETER_AGENT_API_SPEC.md)
- DB 관계와 저장 구조: [DB 문서](./03_MODEL_PARAMETER_AGENT_DB_SPEC.md)
- Basecase/LUT와 Object Storage 구조: [Basecase·LUT 문서](./05_MODEL_PARAMETER_AGENT_BASECASE_LUT_PARSING.md)
- 신규 파라미터 추가·활성화 정합성 게이트: [파라미터 추가 가이드](./06_MODEL_PARAMETER_AGENT_PARAMETER_ADDITION_GUIDE.md)
