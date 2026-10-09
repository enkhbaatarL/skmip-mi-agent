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

### v4.1.1 proposal Flow release

`v4.1.1`은 새 Impact Lever catalog가 아니라 v4.1 catalog를 그대로 사용하는 Model Parameter proposal Flow
release다. 따라서 catalog version/checksum, 21개 Lever, 56개 binding, Parameter master/capability와 기존
v4.1 Scenario Group/Scenario ID는 변경하지 않는다. 비교 코호트가 고정된 작업에서는 Scenario를 재생성하지 않고
동일한 20 Event·20 Group·82 Scenario를 재사용한다. 배포 설정은
`model_parameter_proposal_flow_release=v4.1.1`로 식별한다.

### v4.1.2 proposal Flow release

`v4.1.2`는 v4.1.1의 catalog·binding·workbook 계약을 바꾸지 않고, 요청 접수 시점의 활성
MI Base `case_id`를 proposal에 고정한다. `SCNRCASE` Demand·Supply·Trade 입력 3종만
기준값 계산에 사용하고, 최신 `run_seq`에 연결된 `SCNRCASEH/HI/HTF`는 metadata만
조회한다. 선택된 활성 Base의 Object Storage를 확인할 수 없을 때는 동일 case/run/file identity와
workbook hash/contract를 검증한 cache만 허용하며, 없으면 다른 Basecase로 바꾸지 않고 실패한다.
활성 Base 부재 시 기존 설정 resource 사용은 명시적 운영 설정에서만 허용하고 기본은 fail closed다.
이 변경은 public API JSON을 늘리지 않으며 sibling mgmt v0037의 nullable
`tmm_mi_model_param_proposal_m.mi_base_case_id`로 요청별 선택을 저장한다.

### v4.1.3 proposal Flow release

`v4.1.3`은 Scenario Lever catalog `v4.1`, checksum, 21개 Lever·56개 binding, Parameter master,
workbook/LUT와 공개 API/DB schema를 그대로 둔다. 변경 범위는 proposal 내부 의사결정과 설명 가능성이다.

- Step1.5가 모든 conditional 후보를 `DIRECT`, `ASSUMPTION_ELIGIBLE`, `NOT_APPLICABLE`로 분류하고
  causal path·대상·방향·기간·confidence를 구조화한다.
- Step1.5 complete all-N/A는 그대로 성공 처리하지 않는다. 다만 parameter별 conditional routing 정책이 허용하고
  선택 branch의 물리 경로·방향·범위·기간이 모두 확인되는 후보만 `BOUNDED_ASSUMPTION`으로 제한 복구한다.
  현재 허용 쌍은 `route_disruption → ShippingCost` 하나다. 이는 항차 시간·선복 가용성에서 전역 LNG charter
  rate로 이어지는 추론을 명시하며, `ShippingFuelCost`와 `CanalToll`은 직접 근거 없이는 복구하지 않는다.
- 기본 `balanced` mode는 medium 이상 근거의 bounded assumption과 weak/medium 값 variation을 허용한다.
  `strict`는 assumption을 막고, `exploratory`는 low confidence/strong까지 허용하되 catalog·slot 경계는 동일하다.
- 선택 상한은 dimension별 3개, Scenario 전체 conditional Parameter 4개다. 선택된 Scenario value에서 도달 가능한
  active binding만 검토하며 다른 Lever나 legacy mapping을 scan하지 않는다.
- Step2는 parent 전체 영향이 명시된 경우에만 child를 확장한다. 대상이 유일하고 기간만 모호하면 가장 이른 exact
  현재·미래 기간 한 건을 복구하며, 과거 월·PowerMix·LNG Plant/Train 증적 대상에는 적용하지 않는다.
- Step2/Step3 schema·semantic·좌표 오류는 재호출하지 않는다. transient 오류만 호출 단위 retry 대상이며 Scenario
  전체 outer retry는 없다.
- Step3은 active 16종별 variation policy를 prompt와 서버 계산에 함께 적용하고, 모든 slot의 대상·기간·근거 유형·
  인과 경로·기준값·계산·가정·불확실성을 rationale에 명시한다. 구조화 근거가 없거나 선언 방향과 실제 값 방향이
  모순인 cell은 저장하지 않는다.
- 같은 Group의 sibling Scenario는 동일 Parameter·slot·causal mechanism의 soft comparison에만 사용하며 현재
  Scenario 후보 또는 slot을 활성화하지 않는다.

배포 식별자는 `model_parameter_proposal_flow_release=v4.1.3`이며, catalog version은 계속 `v4.1`이다.

DB/mgmt migration은 필수가 아니다. 최종 proposal은 기존 `proposal_parameters` JSON과 slot `rationale` 문자열에
저장하고 상태도 기존 `PROPOSED`/`ABSTAINED`/`FAILED` 계약을 사용한다. candidate assessment와 variation policy
trace는 request-local 실행 증적이며 공개 JSON이나 신규 컬럼으로 영속화하지 않는다. 향후 운영 화면에서 근거 유형,
policy release, confidence를 구조화 검색해야 할 때만 mgmt 레포에서 별도 audit JSON 컬럼/테이블을 신규 버전으로
검토하며, 이는 v4.1.3 실행의 선행 조건이 아니다.

### v4.1.5 proposal Flow release

`v4.1.5`는 v4.1.4의 Scenario Lever catalog `v4.1`, checksum, 21개 Lever·56개 binding, Parameter master,
workbook/LUT 및 공개 API/DB schema를 그대로 유지한다. 변경 범위는 Proposal 성공률과 value cell coverage를
높이는 내부 Step1.5/Step2/Step3 및 평가 증적이다.

- Step1.5 complete all-N/A는 `route_disruption → ShippingCost`와 물리 cargo 배분·재정거래·운송 경로가 명시된
  `regional_price_spread → ShippingCost`만 policy recovery한다. 가격 spread만으로는 복구하지 않고 다른
  Parameter로 확장하지 않는다.
- Step2가 현재 Scenario/Event/Lever 원문과 실제 slot catalog의 alias·기간을 대조해 대상이 하나로 확정될 때만
  누락 slot을 복구하고, 이미 하나가 선택됐어도 명시 범위의 나머지 exact 기간을 확장한다. global time-only
  Parameter도 명시 기간이 있으면 허용한다. Pipeline은 pipeline명 또는 From+To, 액화 설비는 Plant+Train이 모두
  필요하며, ambiguous target·과거 기간·PowerMix는 복구하지 않는다.
- Step3의 `bounded-expert-v3`는 기존 parameter별 weak/medium/strong cap을 유지하면서 duration, scope,
  offset, confidence, sibling position을 severity band 내부 위치로 변환한다. 계산은 deterministic이고
  `OBSERVED`/`DERIVED` 값에는 적용하지 않는다. sibling은 비교 정보일 뿐 후보·slot·방향의 근거가 될 수 없다.
- 불완전 응답 또는 모든 slot의 `DERIVED` no-change에는 exact slot과 routing 방향이 모두 확정된 경우만 weak
  deterministic fallback을 적용한다. PowerMix·unknown/unchanged·상충 방향은 실패를 유지한다. semantic 오류를
  고치기 위한 LLM 추가 호출은 없다.
- 내부 trace에는 variation factor와 판단 이유, fallback 여부를 명시하고 공개 slot rationale에는 업무 근거와
  불확실성만 설명한다.
- 동일 고정 cohort의 release 재평가는 기존 Proposal을 보존한 append-only `release-replay-v1`으로 수행하며,
  새 Proposal ID만 최종 KPI에 사용한다.
- 실행 evidence/report에는 secret을 제외한 전체 `model_parameter_*` 로컬·Neuro 선언값과 runtime effective
  snapshot, 파일 SHA와 선언 차이를 포함한다.

### v4.1.6 사용자 rationale 표현

`v4.1.6`은 v4.1.5의 후보·slot·값 계산과 안전 경계를 그대로 유지하고, 플랫폼에 저장·노출되는 rationale만
현업 사용자 관점으로 정리한다. 내부 trace에는 evidence enum, variation policy release/mode, severity,
variation factor, fallback 여부를 계속 남긴다.

- Parameter rationale은 제안 이유, 시나리오 영향, 적용 범위·기간을 설명한다.
- Slot rationale은 `적용 대상`, `시나리오 영향`, `조정 내용`, `산정 근거`, `계산 방법`, `주요 가정`,
  `확인 필요`를 명시한다.
- `candidate_key`, `slot_key`, Step, catalog/binding/routing, 정책 버전·mode, enum,
  weak/medium/strong, trio/sibling 같은 내부 용어는 공개 문자열에 넣지 않는다.
- 직접 전망 수치가 없는 값은 “정성 정보를 보수적으로 수치화한 초기 제안”임을 밝히고 사용자 검토를 요청한다.
- 공개 API/DB JSON shape와 rationale field 이름은 바꾸지 않는다.

배포 식별자는 `model_parameter_proposal_flow_release=v4.1.6`이고 catalog version은 계속 `v4.1`이다.
신규 테이블·컬럼 또는 mgmt migration은 필요하지 않다.

### v4.1.7 간결한 사용자 설명

`v4.1.7`은 v4.1.6의 계산·저장 계약을 유지하면서 공개 rationale의 길이와 문체를 정리한다.

- 모든 문장형 설명은 `~합니다/~했습니다` 존댓말로 통일한다.
- Parameter 설명은 핵심 인과관계와 적용 범위·기간만 2~3문장으로 요약한다.
- Slot 설명은 기존 7개 항목을 유지하되 인과관계·근거·가정을 각각 짧게 요약하고 반복 설명을 제거한다.
- 서버 정책이 LLM 초안값을 재계산한 경우 초안의 숫자 설명은 공개하지 않고 최종 제안값과 서버 계산만 설명한다.
- 여러 적용 위치에 반복되는 설비명·기간 보정 참고사항은 한 문장으로 합친다.

현재 배포 식별자는 `model_parameter_proposal_flow_release=v4.1.7`이며 catalog version은 계속 `v4.1`이다.
DB/API JSON shape와 mgmt migration 변경은 없다.

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
| 단일·복수 conditional | 실행 | 응답 누락은 0건 유지. complete all-N/A는 승인된 parameter별 정책을 만족할 때만 제한 복구 | 각 applicability가 독립적으로 근거 있으면 설정 상한까지 유지 |

`price_only`는 더 이상 domain 이름만으로 탈락하지 않는다. conditional binding이 있으면 `partial` support로 후보화하며,
binding이 없는 기존 catalog만 `PRICE_ONLY`로 분류한다. 후보 확대 뒤에도 capability ID/name/target, exact slot,
reference와 유한 숫자 검증은 그대로 적용한다.

## 4. 설비 좌표 추론

Step2 LLM이 실제 slot hierarchy와 연결된 Event/Lever 문맥을 비교해 exact Basecase 좌표를 선택한다. 표기 차이로
선택했다면 다음 다섯 필드를 구조화해 반환한다.

- `plantEvidenceText`: 입력 원문에서 그대로 복사한 Plant 근거
- `trainEvidenceText`: 입력 원문에서 그대로 복사한 Train 근거
- `coordinateMatchNoteKo`: 실제 좌표와 같은 실체로 판단한 이유
- `periodEvidenceText`: 입력 원문에서 그대로 복사한 기간 근거
- `periodMatchNoteKo`: exact Year/Month를 포함한다고 판단한 이유

서버는 선택 좌표가 실제 catalog exact slot인지, 두 근거 문구가 연결된 Event/Lever 원문에 실제 존재하는지,
두 문구가 서로 다른 span인지 검증한다. Scenario narrative도 근거 corpus에 포함하되 source Event·Lever lineage는
필수다. 동일 Plant·Train evidence가 서로 다른 exact target을 승인하면 LLM 승인을 거절하고, 복수 slot은 각
기간 근거가 exact Year/Month를 포함해야 한다. 단, Lever lineage의 명시 연월·분기·닫힌 범위가 exact slot을
직접 포함하면 그 근거를 인정한다. 통과한 경우에도 output 좌표는 LLM 표현이 아니라 Basecase canonical
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
- conditional LLM 응답 누락을 primary default로 채우면 사실상 deterministic binding이 되므로 금지한다. complete
  all-N/A 정책 복구도 등록된 Lever/Parameter 쌍, non-strict mode, direction/scope/time_window와 요구 물리 경로를
  모두 만족해야 하며 일반 primary fallback으로 확대하지 않는다.
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

v4.1.1부터 proposal-only runner는 Scenario `FAIL`을 격리해 같은 명시 cohort의 뒤 후보까지 각각 최초 1회 실행한다.
resource/context/catalog/input fingerprint, in-flight proposal 또는 persistence integrity 변경은 `BLOCKED`로 분류해
campaign 전체를 즉시 중단한다. Scenario 전체 proposal/DB write의 outer retry는 없다.

Step1.5·Step2·Step3 내부 LLM 호출만 timeout·transport·HTTP 408/425/429/5xx에 대해 기본 최대 2회 시도한다.
semantic empty, schema invalid, exact 좌표 불일치, basecase 동일값은 자동 재시도하지 않는다. 이는 Parameter Agent
운영 Flow의 validation & transient retry 개선이며, 실패한 Scenario를 다시 실행하는 보충 실행과 다르다.
확정적 코드 수정 효과로 이미 실패한 동일 Scenario를 다시 호출하면 최초 증적·수정 항목·새 revision을 남긴
`post-fix re-test`로 구분한다.
