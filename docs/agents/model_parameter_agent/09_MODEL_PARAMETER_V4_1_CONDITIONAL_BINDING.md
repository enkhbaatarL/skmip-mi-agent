# Model Parameter v4.1 Conditional Binding

## 1. Release contract

| 항목 | v4.0 보존값 | v4.1 신규값 |
|---|---:|---:|
| Impact Lever Full Set | 21 | 21, 추가·삭제 없음 |
| binding occurrence | 19 | 56 |
| conditional binding | 0 | 37 |
| 활성 proposal Parameter | 16 | 16, model input 변경 없음 |
| catalog checksum | `416017351f2b9539370963a3ca413914876da55a1db3f41e3dacd34bd466c763` | `7f4ef0b7aa60efb550b9175654fd82350f0c293debf880a9180e7e935db54d69` |
| proposal capability | `extend16-v7` 당시 기준 | `extend16-v8` |
| workbook contract | `new-bc-v7` | `new-bc-v7`, 변경 없음 |

v4.1은 기존 v4.0 행을 수정하지 않고 `tmm_mi_model_impact_lever_m`에 같은 21개 Lever의 새 version 행을
side-by-side로 추가한다. 신규 Scenario Group만 설정의 `scenario_group_v4_impact_catalog_version=v4.1`을 사용한다.
기존 Group은 저장된 v4.0 version/checksum으로 계속 hydrate한다. migration 정본은 sibling mgmt의 0036이다.
Lever Full Set, code·domain·label·description·parent는 v4.0과 동일하다. 조건부 후보가 실제 모델
대상·좌표·기간을 남기도록 5개 고빈도 Lever의 `applicability_hint`만 binding과 함께 보강한다.

## 2. 확장 binding

모든 추가 binding은 `role=alternative`, `selection_mode=conditional`, `support_status=executable`이다.

| Lever | 추가 Parameter | 수 |
|---|---|---:|
| `route_disruption` | ShippingCost, ShippingFuelCost, CanalToll | 3 |
| `trade_restriction` | SupplyDisruption, RegionalProductionAdjustment, LiqUtilAdjustment, LiqProdAdjustment, PipelineAdjustment, RegasAdjustment, PNG Contract Volume | 7 |
| `inventory_condition` | GDP, PMI, PowerMix, Temperature, SupplyDisruption, RegionalProductionAdjustment, LiqUtilAdjustment, LiqProdAdjustment, PipelineAdjustment, RegasAdjustment, PNG Contract Volume | 11 |
| `regional_price_spread` | 위 수요·공급·PNG 11종 + ShippingCost, ShippingFuelCost, CanalToll | 14 |
| `financial_market_sentiment` | GDP, PMI | 2 |

재고·가격·심리 상태 자체를 writable input으로 바꾸지 않는다. Event/Scenario에 그 상태의 원인 또는 직접 영향이
실제 model input 대상·좌표·기간으로 명시된 경우에만 연결한다. 가격 상승을 공급 감소로 바꾸는 식의 proxy 추론은
금지한다.

## 3. runtime 선택 규칙

| binding 유형 | Step1.5 | 빈 응답 | 복수 응답 |
|---|---|---|---|
| 단일 deterministic | 생략 | 해당 없음 | 해당 없음 |
| 복수 deterministic primary/alternative | 실행 | primary 1건으로 복구 | 각 applicability가 독립적으로 근거 있으면 설정 상한까지 유지 |
| 단일·복수 conditional | 실행 | 0건 유지 | 각 applicability가 독립적으로 근거 있으면 설정 상한까지 유지 |

`price_only`는 더 이상 domain 이름만으로 탈락하지 않는다. conditional binding이 있으면 `partial` support로 후보화하며,
binding이 없는 기존 catalog만 `PRICE_ONLY`로 분류한다. 후보 확대 뒤에도 capability ID/name/target, exact slot,
reference와 유한 숫자 검증은 그대로 적용한다.

## 4. 설비 좌표 추론

Step2 LLM이 실제 slot hierarchy와 연결된 Event/Lever 문맥을 비교해 exact Basecase 좌표를 선택한다. 표기 차이로
선택했다면 다음 세 필드를 구조화해 반환한다.

- `plantEvidenceText`: 입력 원문에서 그대로 복사한 Plant 근거
- `trainEvidenceText`: 입력 원문에서 그대로 복사한 Train 근거
- `coordinateMatchNoteKo`: 실제 좌표와 같은 실체로 판단한 이유

서버는 선택 좌표가 실제 catalog exact slot인지, 두 근거 문구가 연결된 Event/Lever 원문에 실제 존재하는지,
두 문구가 서로 다른 span인지 검증한다. 통과한 경우에도 output 좌표는 LLM 표현이 아니라 Basecase canonical
좌표다. 일반 표기 정규화와 실제 좌표에서 자동 생성한 alias는 안전 보조 수단일 뿐이며, target별 hard-coded
mapping을 추가하지 않는다. 자동 alias가 둘 이상 target에 충돌하면 사용하지 않는다.

단일-Train 설비에서 모델의 Plant/Train 문자열이 같은 경우에도 `... T1` 한 문구를 Plant와 Train 두 근거로
중복 계산하지 않는다. Plant와 Train 근거가 각각 있어야 한다. 기간도 명시 월 또는 보수적으로 해석 가능한 단일
bounded period만 허용하며, `재가동 지연`, `10월 하순 이후`만으로 여러 월을 확장하지 않는다.

## 5. 적용·검증 순서

1. 외부개발 DB를 read-only transaction으로 snapshot하고 무조건 rollback한다.
2. snapshot에서 v4.0 Full Set을 복제하고 승인 conditional binding만 추가해 canonical JSON을 생성한다.
3. canonical/snapshot 자체 digest, active master target, Full Set 21, binding count와 checksum을 검증한다.
4. DB dry-run에서 master, legacy mapping, v4.0·기타 Lever, Scenario template의 snapshot digest를 lock/read 비교한다.
5. 승인 후 v4.1 21행만 insert하고 hydrated v4.0/v4.1 checksum을 모두 read-back한다.
6. local YAML과 Kubernetes ConfigMap의 catalog version, capability release/SHA가 같은지 확인한다.
7. 같은 Event cohort로 신규 v4.1 Group을 만들고 signpost가 proposal 필수 입력이 아니면 생략한다.
8. 동일 Scenario 내용의 v4.0/v4.1 matcher 비교와 실제 v4.1 proposal campaign을 구분해 보고한다.

재현 파일:

- `scripts/model_parameter/capture_model_impact_lever_v4_1_external_snapshot.py`
- `scripts/model_parameter/prepare_model_impact_lever_v4_1.py`
- `scripts/model_parameter/model-impact-lever-canonical-v4.1-0036.json`
- `scripts/model_parameter/apply_model_impact_lever_v4_1.py`

## 6. 실수하기 쉬운 지점

- Pydantic에 default 필드를 추가하면 과거 checksum이 바뀔 수 있다. `selection_mode=deterministic`은 checksum
  payload에서 생략해 v4.0 pin을 보존하고, `conditional`만 v4.1 checksum에 포함한다.
- conditional binding이 한 건뿐이어도 direct로 우회시키지 말고 Step1.5를 거쳐야 한다.
- conditional LLM 응답 누락을 primary default로 채우면 사실상 deterministic binding이 되므로 금지한다.
- Scenario support status, Model Parameter context loader, matcher의 `price_only` 판정 세 곳을 함께 변경한다.
- proposal capability의 Parameter set은 그대로여도 catalog version/checksum이 바뀌므로 release ID/SHA와
  local/Kubernetes 설정을 함께 갱신한다. workbook input·좌표·원본이 같으면 workbook release는 올리지 않는다.
- 기존 pinned Scenario를 v4.1로 덮어쓰지 않는다. 같은 논리 입력 비교는 read-only matcher에서 수행하고,
  실제 end-to-end는 같은 Event cohort로 새 v4.1 Group을 생성한다.
- `.env`에 shell 문법이 아닌 값이 있을 수 있으므로 직접 `source`하지 말고 애플리케이션의 dotenv/config loader를 쓴다.
- 한 Lever state에 conditional binding이 11~14개면 동일한 Event/Dimension/Lever provenance를 후보마다
  반복 직렬화하지 않는다. Step1.5 prompt에는 공통 근거를 `lever_context`에 한 번만 두고, 후보별로는
  Parameter hint·axes·applicability를 유지한다. 압축 후에도 byte guard는 그대로 적용한다.
- Step1.5를 통과했어도 Step2에서 exact slot 근거가 없는 conditional 후보는 안전하게 abstain할 수 있다.
  proposal 직전 품질 gate는 v4에 한해 `slot_candidate_mappings`에 남은 후보를 검증해야 하며, 탈락 후보 하나가
  독립적으로 근거를 확보한 다른 Parameter까지 전체 실패시키면 안 된다.
- API JSON과 DB decimal 왕복에서 최하위 부동소수점 표현만 달라질 수 있다. evidence runner는 `1e-12`
  절대·상대 허용오차로 숫자를 비교하되, 좌표·Parameter·구조 차이와 의미 있는 값 차이는 계속 실패시킨다.
- Git commit author와 DB audit principal을 혼동하지 않는다. Git author는 작업자 설정을 따르되,
  v4.1 DB audit은 비개인 식별자 `model-impact-lever-v4.1-v0036`으로 고정한다.
- `impact_lever_id`는 56~76을 canonical에 명시한다. MySQL은 transaction rollback 뒤에도
  AUTO_INCREMENT 소비값을 되돌리지 않으므로, dry-run에서 자동 할당된 ID를 release 기준으로 삼지 않는다.
  apply 전 snapshot drift, ID 충돌 또는 부분 v4.1 행이 있으면 fail closed한다.

## 7. proposal campaign 재실행 원칙

Group runner가 앞 Scenario 실패에서 중단되어 뒤 Scenario가 graph를 한 번도 실행하지 못한 경우, 그 뒤 후보를
Scenario별로 격리해 최초 1회 실행하는 것은 **보충 실행(test orchestration)** 이다. Parameter Agent 운영 Flow의
retry가 아니며, 이미 실패한 동일 Scenario를 다시 호출하지 않는다. 확정적 코드 수정의 효과를 검증하려고 같은
Scenario를 다시 실행할 때만 최초 실패 증적, 수정 항목, 새 code revision을 함께 남겨 `post-fix re-test`로 구분한다.

운영 Flow 고도화 시에는 Scenario별 실패 격리와 제한된 transient retry를 별도 설계할 수 있다. timeout·일시적
transport 오류만 횟수 제한을 두고 재시도하며, semantic empty, exact 좌표 불일치, basecase 동일값은 자동
재시도하지 않는다. catalog/schema/checksum/integrity 오류는 항상 fail closed한다.
