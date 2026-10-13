# Model Parameter Agent v4 핵심 이해도 퀴즈

## 1. 목적과 범위

이 퀴즈는 [개요](01_MODEL_PARAMETER_AGENT_OVERVIEW.md), [API](02_MODEL_PARAMETER_AGENT_API_SPEC.md), [DB](03_MODEL_PARAMETER_AGENT_DB_SPEC.md), [Flow](04_MODEL_PARAMETER_AGENT_FLOW.md), [Basecase·LUT](05_MODEL_PARAMETER_AGENT_BASECASE_LUT_PARSING.md), [추가 가이드](06_MODEL_PARAMETER_AGENT_PARAMETER_ADDITION_GUIDE.md)의 v4 계약을 확인하는 10문항이다. 문항당 1점이며 복수 선택은 정답을 모두 골라야 한다.

## 2. 문제

### 문제 1. 버전별 후보 소스

맞는 설명을 모두 고르시오.

1. v1/v3는 live DB의 dimension mapping을 사용하며 체크인 목표 기준선은 129행이다.
2. v4는 `tmm_mi_model_param_dimension_map`에 후보가 없으면 Event Type mapping으로 fallback한다.
3. v4는 선택 value의 `lever_states`와 active Lever catalog binding을 사용한다.
4. v4는 미선택 value의 Lever state도 합쳐 후보 누락을 방지한다.

### 문제 2. API 호환성

맞는 설명을 모두 고르시오.

1. v4 전용 proposal endpoint와 request version 필드가 추가된다.
2. 기존 동기·비동기 proposal과 confirmation endpoint를 그대로 쓴다.
3. v4 응답의 `eventId`는 `null`이고 `scenarioGroupId`가 authoritative link다.
4. Lever provenance를 public proposal JSON의 필수 필드로 추가한다.

### 문제 3. Active set, raw reachability와 runtime allow-list

체크인 기준선 수치를 쓰고 다음 집합을 서로 구분하시오. 이 수치와 live DB 상태, 요청 하나의 후보 수가
어떻게 다른지도 설명하시오.

- DB/canonical master 전체/활성 수
- v1/v3 legacy mapping 행 수와 method count
- resource capability의 LUT-backed/Basecase-only parameter 수
- v1/v3 raw direct/routing reachability와 v4 raw active binding 수
- 실제 proposal runtime allow-list 수와 이름, allow-list 밖 raw active 후보의 처리

### 문제 4. v4 strict validation

다음 중 proposal을 LLM 호출 전에 차단해야 하는 것을 모두 고르시오.

1. group catalog checksum과 현재 active catalog checksum 불일치
2. 선택 dimension value의 primary Lever state 누락
3. `source_event_ids`가 group event 집합 밖 ID를 포함
4. Lever code와 ID가 active catalog에서 일치하지 않음
5. `direction=unchanged` state가 supporting context에 존재

### 문제 5. Candidate routing

v4의 단일 deterministic binding, 복수 primary/alternative, conditional binding을 각각 어떻게 처리하는지 설명하시오. `price_only`, binding 없음, 비활성 parameter, `unchanged` state와 raw candidate가 runtime allow-list 밖인 경우도 함께 설명하시오.

### 문제 6. Step1.5·Step2·Step3

세 단계가 받거나 만들 수 있는 정보를 연결하시오.

1. Step1.5
2. Step2
3. Step3

- A. exact 좌표, 단일 effective reference와 전체 Lever provenance를 바탕으로 최종 절대값·근거 생성
- B. Scenario 요약, ordered Event, 선택 value/Lever provenance, parameter hint·semantic axes·applicability로 후보 routing
- C. 같은 문맥과 압축 exact slot catalog만 받고 값·기준값 없이 slot 선택

### 문제 7. 숫자 방향

Lever의 `direction`, `pressure_contribution`, domain을 숫자 부호로 직접 변환하면 안 되는 이유와, 반대 방향 Lever가 같은 parameter로 병합될 때의 처리 원칙을 설명하시오.

### 문제 8. Basecase와 LUT

다음 slot의 effective reference와 저장 `basecaseValue`를 쓰시오.

| capability | Basecase | LUT |
|---|---:|---:|
| LUT-backed | `49.5` | `50` |
| LUT-backed | 없음 | `50` |
| Basecase-only | 없음 | 없음 |

부분 key나 인접 시설 값으로 fallback할 수 있는지도 답하시오.

### 문제 9. Canonical rollout과 runtime-only 변경

master와 Lever catalog를 어떻게 적용해야 하는지, checksum이 바뀐 기존 v4 Scenario를 어떻게 처리해야 하는지 설명하시오. 이번 extend14 변경에서 불변인 DB·canonical·workbook artifact·confirmation 범위와 새 contract/capability를 가리키도록 함께 바뀌는 config 범위도 포함하시오.

### 문제 10. 실패와 저장 호환성

raw active/executable candidate가 있어도 모두 runtime allow-list 밖인 경우와, 최종 허용 candidate가 0개일 때 proposal row 처리·오류를 설명하시오. v4 provenance·제외 reason code가 공개 API/저장 JSON에 들어가는지도 답하시오. Confirmation이 원래 proposal과 같은 항목·값만 허용하는지, `proposedValue=null`을 허용하는지도 설명하시오.

## 3. 정답과 해설

### 정답 1

**1번, 3번.** v1/v3는 live DB의 legacy mapping을 사용하며 체크인 canonical 목표 기준선은 129행이다. `generation_strategy=multi_event_model_lever_dimensions`인 v4는 선택 value의 state와 active catalog만 사용하고 Event Type, dimension mapping, 과거 `lever_mappings` 계열을 fallback으로 쓰지 않는다.

### 정답 2

**2번, 3번.** public endpoint, request/response, callback, confirmation 동작과 저장 JSON shape은 그대로다. v3/v4의 `eventId`는 `null`이며 Lever provenance는 내부 state·trace·validation warning·실패 detail에만 둔다.

### 정답 3

- 외부개발 v4.1 master 24행·활성 16개
- 체크인 legacy mapping 129행: direct 35, routing 6, indirect 55, na 33
- active resource LUT-backed 10개
- Basecase-only 활성 6개: `RegasAdjustment`, `PNG Contract Volume`, `ShippingCost`,
  `RegionalProductionAdjustment`, `ShippingFuelCost`, `CanalToll`
- inactive 3개: `User-Adjusted Gas Demand`, `RemainingUnrestrictedAmount`, `VolumeCancelled`
- v1/v3 raw direct/routing reachability 10개
- v4.1 active Lever 21개, binding occurrence 56개(conditional 37개), effective executable 고유 Parameter 16개
- v1/v3 proposal 이름 allow-list 5개: `GDP`, `PMI`, `PowerMix`, `Temperature`, `LiqUtilAdjustment`
- v4 extend16 ID capability 16개: LUT-backed 10개 + `RegasAdjustment`, `PNG Contract Volume`,
  `ShippingCost`, `RegionalProductionAdjustment`, `ShippingFuelCost`, `CanalToll`

이 수는 live DB 조회 결과가 아니라 체크인 runtime fixture의 전역 합집합이다. v1/v3 raw reachability
합집합은 `GDP`, `PMI`, `PowerMix`, `Temperature`, `Population`, `HurricaneIntensity`,
`LiqProdAdjustment`, `LiqUtilAdjustment`, `PipelineAdjustment`, `SupplyDisruption` 10개다. Basecase-only
활성 6개에는 legacy direct/routing row를 추가하지 않았다. v4의 effective executable 16개는 Lever-native
경로이며 shared mapping을 조회하지 않는다. 요청 하나에서는 관련 lineage·선택 value에 해당하는 하위 집합만
후보가 된다. 외부개발 DB의 v4.1 executable 고유 16개와 extend16 capability는 ID/name/target set equality로
일치해야 한다. 하나라도 capability에서 빠지면 release 실패이며 LLM·proposal 입력으로 진행하지 않는다.
v1/v3는 raw 10개 중 5개만 허용한다.

### 정답 4

**1번, 2번, 3번, 4번.** checksum/code/ID/primary/source-event 무결성은 strict validation이다.
`unchanged`는 오류가 아니라 supporting context이며, unchanged-only라서 변화 후보가 0개가 되면
`ABSTAINED_NO_CHANGE`로 정상 미제안 이력을 저장한다. 비동기 요청은 기존 `PROCESSING` 행을
`ABSTAINED`로 전환하고, 동기 요청도 빈 `PROPOSED` 대신 `ABSTAINED` 행과 결과를 반환한다.

### 정답 5

allow-list 적용 전 executable deterministic binding이 하나뿐이면 `direct`로 분류되어, 그 후보가 allow-list를
통과할 때 결정적으로 선택한다. 복수 primary/alternative와 단일을 포함한 conditional binding은 Step1.5가
applicability를 독립 판정한다. 각각 근거가 있으면 설정 상한까지 복수 선택하고, deterministic 빈 응답은 primary
1건으로 복구하지만 conditional 빈 응답은 0건을 유지한다. binding 없는 `price_only`는 제외하지만 v4.1의
conditional binding이 있는 `price_only`는 후보 판정으로 진행한다. binding 없음, 비활성·unsupported parameter는
제외하며 reason code를 내부 증적에 보존한다. raw candidate가
active/executable이어도 runtime allow-list 밖이면 `PROPOSAL_SCOPE_EXCLUDED`로 분류해 Step1.5 LLM 전에
제외한다. `unchanged`는 변화 candidate가 아니다.

### 정답 6

**1-B, 2-C, 3-A.** Step1.5는 후보 routing, Step2는 값 없는 exact slot 선택, Step3는 단일 reference를 사용한 최종 절대값과 두 종류의 근거 생성을 담당한다.

### 정답 7

Lever 방향은 시장·운영 문맥이지 각 모델 입력 필드의 수학적 부호 계약이 아니다. `parameter_hint`, 단위, binding applicability, Scenario/Event 문맥과 기준값을 함께 해석해야 한다. 반대 방향 Lever가 같은 parameter로 수렴하면 양쪽 provenance를 잃지 않고 상쇄 관계를 rationale에 설명하며, 서버가 임의 합산·평균하지 않고 exact slot마다 최종 절대값 하나를 만든다.

### 정답 8

- LUT-backed, Basecase `49.5`: effective reference와 `basecaseValue` 모두 `49.5`
- LUT-backed, LUT만 `50`: effective reference `50`, 저장 `basecaseValue=null`
- Basecase-only, Basecase 없음: slot 제외

모든 key axis가 같은 exact slot만 쓸 수 있다. 부분 key, nearest 값, 다른 시설 축의 조합은 금지한다.

### 정답 9

일반 v4 master·Lever rollout은 mgmt migration을 정본으로 하나의 transaction에서 precondition,
cross-table active binding, checksum/read-back과 함께 검증·적용한다. checksum이 바뀌면 기존 v4 Scenario를
새 catalog로 재해석하지 않고 신규 Scenario를 생성한다. v4.1은 master와 legacy mapping을 바꾸지 않고 기존
v4.0 옆에 같은 Lever Full Set 21행과 conditional binding을 추가한다. versioned capability는 `extend16-v8`,
workbook contract는 model input이 같아 `new-bc-v8`을 유지하며 local/Kubernetes config의
catalog version·capability release·hash를 함께 갱신한다. public API payload와 confirmation workflow도 변경하지 않는다.

### 정답 10

raw active/executable candidate라도 allow-list 밖이면 `active-but-blocked`로 제외하며 LLM이나 제안값 생성으로
진행하지 않는다. 이 필터 뒤 허용 candidate가 0개면 `ABSTAINED_OUT_OF_PROPOSAL_SCOPE`로 정상 미제안 이력을
저장한다. Lever provenance와 `PROPOSAL_SCOPE_EXCLUDED` 같은 내부 제외 reason code는 public
proposal/confirmation JSON shape에 새 필드로 추가하지 않고 non-input state, trace와 validation warning에 남긴다.
callback과 결과 행에는 내부 제외 코드 대신 공개 `ABSTAINED_*` 코드와 사용자 문구를 기록한다. Confirmation은
원래 proposal과 항목·값을 비교하지 않아 수정·추가·삭제와 구조상 유효한 custom parameter를 허용한다. 각 value에는
`proposedValue` key가 필요하지만 값은 `null`일 수 있고, non-null 값만 persistence에서 유한 숫자로 검증한다.

## 4. 점수 해석

| 점수 | 이해 수준 |
|---:|---|
| 9~10 | v4 후보·reference·rollout 경계를 설명할 수 있음 |
| 7~8 | 전체 흐름은 이해했으나 일부 strict validation 경계 재확인 필요 |
| 5~6 | legacy/v4 또는 LUT/Basecase-only 구분 보완 필요 |
| 0~4 | 개요 → DB → Flow → Basecase/LUT 순서로 다시 확인 권장 |
