# Model Parameter 추가·활성화 가이드

## 1. 체크인 기준선

현재 Agent runtime 판정 기준은 Proposal Flow `v4.1.8`, proposal capability `extend17-v9`,
workbook contract `new-bc-v9`, 신규 Scenario Group catalog `v4.1` full pin이다. 기존 v4 Scenario는
저장된 pin을 그대로 읽고, v0050 적용 시 기존 v4.1 Scenario pin은 현행 checksum으로 이관된다.
DB 적용 상태는 runner preflight와 read-back으로 확인한다.

- v0050 DB master는 26행·활성 18개다. 현행 v4.1 proposal capability는 17개이며 10개는
  LUT-backed, 7개는 검증된 exact Basecase-only capability다. 나머지 활성 `CanalToll`은 v4.0 catalog 호환용이다.
- 신규 Scenario Group용 v4.1 active Lever는 Full Set 21개다. binding occurrence는 56개이며,
  이 중 41개는 근거가 없으면 0개를 선택하는 `conditional` binding이다. executable 고유 Parameter는 17개다.
- legacy dimension mapping 129행은 v4가 읽거나 변경하지 않는 보호 대상 invariant다.
- v1/v3 신규 proposal 이름 allow-list 5개: GDP, PMI, PowerMix, Temperature, LiqUtilAdjustment
- v4.1 `extend17-v9` capability 17개: 위 5개 + Population(ID 11),
  HurricaneIntensity(ID 12), LiqProdAdjustment(ID 13), PipelineAdjustment(ID 15),
  RegasAdjustment(ID 16), SupplyDisruption(ID 17), PNG Contract Volume(ID 18), ShippingCost(ID 20),
  RegionalProductionAdjustment(ID 22), ShippingFuelCost(ID 23), Suez Canal Cost(ID 25),
  Panama Canal Cost(ID 26)
- `extend17-v9`의 v4 `multi_event_model_lever_dimensions` 기준값은 하나의 `read_only_proposal` contract
  `model-parameter-workbook-contract-v9.json`을 사용한다. 이 workbook contract는 비활성
  User-Adjusted Gas Demand와 v4.0 catalog 호환용 CanalToll까지 19종 reference를 보존하지만 v4.1 proposal
  capability에는 17종만 둔다.
  ID 13·14 matrix write target은 최종 workbook의 84개월 범위 `G:CL`을 사용하며 mgmt v0044 master와
  동일해야 한다.
  packaged baseline Excel artifact는 `resources/basecase_v4/new-bc-v2/`의 digest를 사용한다. 활성 MI Base 경로는
  Object Storage의 연결 workbook을 같은 구조 계약으로 검증하며, v1/v3는 기존 `resources/basecase/` 호환 경계를 유지한다.
- LUT-backed 10개는 contract reference→same-exact-key LUT fallback→slot/evidence/value 절차를 사용한다.
  v4.1 Basecase-only 7개도 같은 `v4_workbook_then_lut` mode를 쓰지만 등록 LUT가 없으므로 검증된 workbook
  exact slot만 사용하며, v4에는 별도 legacy Basecase reference mode를 두지 않는다.
- source matching 뒤 LLM과 proposal persistence 전에 version별 capability gate를 적용한다. v4의 단일
  `deterministic` binding은 결정적으로 통과시킨다. 복수 binding 또는 단일 `conditional` binding은 Step1.5에서
  각 applicability 근거를 독립 판정한다. 복수 Parameter가 각각 근거를 만족하면 설정 상한까지 함께 유지한다.
  deterministic 빈 응답은 primary 1건으로 복구한다. conditional 응답 누락은 자동 보정하지 않으며, complete
  all-N/A는 별도 승인된 parameter별 conditional routing 정책과 물리 경로·방향·범위·기간을 모두 만족할 때만
  bounded assumption으로 제한 복구한다.
- 공개 proposal/confirmation API와 payload, confirmation 동작은 변경하지 않는다.
- DB migration 정본은 sibling mgmt repository다. v0050은 기존 master ID 1~24, v4/v4.0 catalog·pin과
  legacy mapping을 보존하면서 ID 25·26, v4.1 운하 binding 개정, v4.1 Scenario checksum pin 이관,
  logical catalog v4를 한 transaction에서 수행한다.
- 현재 mapping workbook은 `261016_시나리오가정_MI수급모델_input_매핑_model-parameter-canonical-v4.1.xlsx`다.
  DB 적용과 runtime 판정은 versioned canonical·contract·mgmt DML을 기준으로 한다.

새 파라미터의 DB/canonical/resource capability 활성화는 이름이나 `use_yn` 하나만 바꾸는 작업이 아니다. master, v4 Lever binding, Basecase/LUT capability, resource manifest, prompt 크기, proposal/confirmation 검증을 한 단위로 다룬다. legacy mapping은 신규 v4 rollout의 입력이나 fallback으로 사용하지 않는다. capability를 활성화해도 runtime proposal allow-list에 자동으로 추가되지 않으며, 신규 proposal 허용은 별도 정책 변경과 검증이 필요하다.

반복 가능한 전체 구현은 `$rollout-model-parameters`, release 전체 승인은
`$verify-model-parameter-release`, v4 multi-event proposal·Confirmation 품질 확인은
`$model-parameter-multi-event-quality`를 사용한다. 핵심 Skill은 v4
`multi_event_model_lever_dimensions` 경로만 지원한다.

현재 운하 분리 규칙은 `10_MODEL_PARAMETER_V4_1_CANAL_SPLIT.md`를 따른다. v4.1 conditional binding의
역사 계약은 `09_MODEL_PARAMETER_V4_1_CONDITIONAL_BINDING.md`에 보존한다.

## 2. 변경 전 확인

1. parameter_name과 모델 target이 수급모델 workbook에 실제로 존재하는지 확인한다.
2. 값의 단위·절대값/증감값 의미·허용 범위를 parameter_hint로 확정한다.
3. exact key axes와 horizon 2026~2030의 기준값이 있는지 확인한다.
4. v4 Lever code와 parameter binding role(primary/alternative), applicability가 승인되었는지 확인한다. legacy direct/routing/indirect/na mapping은 변경하지 않는다.
5. 신규 proposal을 허용할 parameter인지 별도 승인하고 ID 기반 capability contract 변경 범위와 회귀 테스트를 확정한다.
6. 동일 Lever의 primary/alternative가 raw 후보가 되는 것이 의도인지 확인한다. Step1.5에는
   applicability와 Scenario/Event/Lever 맥락을 제공한다. 각 binding의 근거가 독립적으로 확인되면 복수 후보를
   설정 상한까지 유지한다. deterministic 응답 누락만 primary 한 건으로 복구한다. conditional은 0건을 허용하되,
   all-N/A 정책 복구를 추가하려면 허용 Lever/Parameter 쌍, 필요한 정성 증적, direction mapping, scope/time 필수값,
   인접 Parameter로의 추론 금지 경계를 코드·prompt·회귀 테스트에 함께 등록한다.
7. 대규모 시설 catalog가 slot·prompt byte 상한 안에 들어오는지 측정한다.
8. v4 workbook contract 대상이면 authoritative source와 write target을 분리하고, digest·sheet·header·range,
   expected record 수, exact-key 오류 차단, fallback·evidence·atomic 정책을 함께 확정한다.

자료가 부족하면 master `use_yn=N`, binding 미등록 또는 LUT `enabled=false`로 두며 과거값을 임의 이월하지 않는다. Basecase-only는 검증된 exact Basecase slot이 없으면 executable하지 않다.

### 2.1 파라미터별 정합성 매트릭스 — 활성화 전 필수 산출물

제안 범위를 확대하기 전에 신규 파라미터마다 아래 표의 한 행을 완성한다. 개수 합계나 공통 테스트 통과만으로
개별 행을 대신할 수 없다. 값은 설명 문서에서 추정하지 않고 현재 versioned artifact와 실제 원본에서 확인한다.

| 검증 축 | 파라미터별로 기록할 값 | 판정 기준 |
|---|---|---|
| DB master/canonical | ID·name·활성, `model_file/sheet/table`, `semantic_axes`, 모든 `basecase_*`, hint·unit·값 의미·범위 | mgmt DML과 Agent canonical exact match |
| v4 Lever catalog | Lever ID/code, catalog version/checksum, binding role·applicability·support | active hydrated binding과 exact match |
| proposal capability | schema/release, ID·name·target, exact axes, reference mode, evidence policy, constraints | DB/canonical과 exact match |
| 원본 Excel | workbook role/path/digest, source sheet/range/header/columns, parser, record count | sheet·header가 실제 artifact에 존재하고 파싱 수가 계약과 일치 |
| 변형 데이터/LUT | 파일/path/digest/header, adapter/formula/join, exact axes, 단위, record count | 원본→변형 계산과 same-exact-key fallback을 대표값으로 재현 |
| 최종 쓰기 대상 | workbook role, sheet/table/header, key/value columns, unit·값 의미 | 실제 최종 workbook과 플랫폼 입력 계약에 exact match |
| 배포 설정 | local/Kubernetes contract·capability path, release ID, SHA/schema | 두 설정이 동일하고 실제 파일을 가리킴 |
| runtime 출력 | `parameterName`, `modelTarget`, `slot_axes`, `proposedValue` 단위·의미 | capability와 최종 쓰기 대상 tuple이 그대로 출력됨 |

현재 0032의 대표 행은 역할 분리를 다음처럼 보여 준다.

| Parameter | authoritative reference | transformed fallback | final write target |
|---|---|---|---|
| `PipelineAdjustment` | Supply `BCPipeline` B:F | pipeline LUT, 동일 5축 exact key | Supply `PipelineAdjustment` / `table1`, B/C/D/E/F/H |
| `SupplyDisruption` | Supply `BCProduction` C:K + `SeasonalityLogic.csv` | production×seasonality LUT, 동일 3축 exact key | Supply `ProductionAdjustment` / `table2`, I/J/K/M |

`reference_source`와 `write_target`은 의도적으로 다른 계약이다. `BCProduction`을 읽는다고 결과를 그 시트에
쓰는 것이 아니며, `SupplyDisruption`이라는 파라미터명에서 시트명을 유추하지 않는다. 특히 과거
`VolumeAdjustment` 시트가 다른 workbook이나 역사 자료에 있더라도 현재 target인
`ProductionAdjustment`의 별칭이나 fallback으로 사용할 수 없다.

### 2.2 즉시 실패시키는 불일치

다음 중 하나라도 있으면 구현 완료나 release PASS로 판정하지 않고, 파라미터를 비활성 또는 proposal scope
밖에 둔다.

1. DB/canonical/capability의 ID·name·`model_file/sheet/table` 중 하나가 다르다.
2. 원본 reference sheet는 있지만 최종 write-target sheet/table/header가 실제 workbook에 없다.
3. exact axes의 이름·개수·순서·의미가 DB, contract, LUT와 runtime 출력에서 다르다.
4. 단위 또는 absolute/delta 의미가 변환 전후나 write target에서 달라지는데 명시적 변환 계약이 없다.
5. 원본이 정상적으로 없어서 LUT를 쓰는 경우가 아닌데, parser 오류·중복 충돌·잘못된 target을 LUT로 가린다.
6. local config와 Kubernetes config가 다른 contract/capability release 또는 SHA를 가리킨다.
7. 신규 파라미터별 source→fallback→runtime output focused test 없이 전체 개수 테스트만 통과했다.

시트명 대소문자·공백·복수형을 비롯한 식별자는 fuzzy match하지 않는다. 불일치를 발견했을 때 과거 fixture,
archive workbook, legacy mapping 또는 설명 문구를 근거로 자동 보정하지 않는다.

### 2.3 최종 행 매핑 게이트 — 모든 파라미터 확대 시 필수

시트·table·header가 존재한다는 검사만으로는 충분하지 않다. write target의 layout에 따라 아래 정책을 계약에
명시하고, Agent가 반환할 모든 exact slot에 적용한다.

| write target 정책 | 적용 기준 | 필수 검증 |
|---|---|---|
| `appendable` | `fixed_columns`처럼 플랫폼이 새 행을 추가할 수 있는 대상 | key/value header, exact axes, 단위와 값 의미가 일치해야 한다. 기존 행 개수는 source whitelist가 아니다. |
| `existing_exact` | `matrix_time_columns`처럼 이미 존재하는 행과 월 열을 찾아 쓰는 대상 | 제안 key가 실제 대상 행·기간에 정확히 하나 존재해야 한다. 반환 식별자와 metadata는 대상 행 표기를 정본으로 사용한다. |

`existing_exact`에서는 authoritative source와 LUT의 합집합을 그대로 후보로 만들지 않는다. 최종 target과
교집합을 먼저 취하고 다음을 모두 지킨다.

1. source key가 target에 없으면 release를 실패시킨다. 유사명·부분 축·용량 일치로 자동 연결하지 않는다.
2. LUT key가 target에 없으면 runtime 후보에서 제외한다. LUT-only 값을 target 부재의 우회로로 사용하지 않는다.
3. source에 값이 없고 target과 LUT에는 같은 exact key가 있으면 target의 식별자·metadata와 LUT의 값만 결합한다.
4. row identity에 쓰이는 metadata는 source 계산값보다 target cell을 우선한다. 단위 변환으로 target 식별값을
   역산하지 않는다.
5. 각 parameter마다 “모든 selectable slot이 target에서 1건에 매핑되는가”를 전수 검사하고, 과거 명칭이 남은
   대표 LUT-only key가 제외되는 회귀 테스트를 추가한다.

`LiqUtilAdjustment`의 재발 방지 기준은 다음과 같다. 현재 target의 정식 식별자인
실제 target의 식별자만 반환할 수 있다. 근거 텍스트의 별칭은 로드된 전체 Basecase 좌표에서 자동 생성한
collision-safe alias index가 정확히 한 target에만 연결할 때 사용한다. 예를 들어 실제 좌표가
`Cove Point Export / Cove Point Export`이면 근거의 `Cove Point LNG / Cove Point LNG T1`을 정규화할 수 있지만,
Agent 출력은 항상 원래 target 좌표여야 한다. Country·Lifecycle·Capacity만 같거나 같은 alias가 둘 이상의 target에
걸리면 연결하지 않는다.

### 2.3.1 근거 좌표명 완화와 다중 slot 확장 경계

근거 문구와 Basecase 좌표의 표기 차이는 조건부로 완화한다. Step2 LLM이 실제 slot hierarchy와 연결된
Scenario/Event/Lever 원문을 비교하고, 원문에서 그대로 복사한 Plant·Train·기간 근거 문구와 좌표 일치 이유를
구조화한다. 서버는 Plant·Train 두 문구의 원문 존재·서로 다른 span·exact target과 기간 문구의 exact Year/Month
포함 여부를 검증한다. 설비 공통어
(`LNG/Export/Plant/Terminal`), 유일 약칭, `Stage↔단계`, `Train/T↔호기`, 단일 Train의 `T1`처럼 실제 좌표에서
자동 생성한 deterministic alias는 보조 안전망으로만 사용한다. 이 추론과 정규화는 근거 판정에만 사용하고 반환
좌표는 slot catalog의 exact 값을 유지한다. LLM 좌표 추론, alias 또는 상대기간 해석을 사용한 경우
`parameterSelectionRationale`의 참고 문구로 사용자에게 알린다.

완화가 근거 없는 다중 선택으로 이어져서는 안 된다.

1. LiqUtilAdjustment는 하나의 coherent Lever provenance 안에 Plant와 Train 수준 근거가 모두 있어야 한다.
   Plant만 언급된 경우 후보 slot이 하나여도 Train을 추론하지 않는다.
2. 복수 Train은 각 Train이 직접 명시되거나 `1~6호기`처럼 닫힌 범위가 있을 때만 선택한다. 범위 밖 Train은 제외한다.
3. 명시 월은 그 월 한 건만 선택한다. `단기`는 분석 기준일이 속한 월 한 건으로 보수적으로 해석한다.
   `재가동 지연`, `10월 하순 이후` 같은 표현만으로 이후 여러 월을 자동 확장하지 않는다.
4. 실제 좌표의 Plant와 Train이 같은 단일-Train 설비에 자동 생성된 `T1` alias를 쓰려면 Plant 문구와 Train 문구가
   서로 다른 span으로 모두 있어야 한다. `... LNG T1` 한 번만 쓴 문구를 Plant+Train 두 근거로 중복 계산하지 않는다.
5. 자동 alias가 둘 이상의 실제 좌표와 충돌하면 전부 거절한다. target별 예외 코드나 설비별 한·영 dictionary를
   추가하지 말고 LLM의 구조화 근거와 exact-slot 검증으로 처리한다.
6. 동일한 Plant·Train evidence 조합을 서로 다른 exact target에 반환하면 해당 LLM 승인은 전부 거절한다.
   같은 target의 여러 기간은 허용하되, 명시 연월·분기·닫힌 범위로 직접 판정되지 않는 복수 slot은 각
   `period_evidence_text`가 해당 exact Year/Month를 포함해야 한다.
7. Scenario narrative를 evidence corpus에 포함할 수 있지만 연결된 source Event와 coherent Lever lineage 요건은
   그대로 유지한다. Scenario text만으로 source provenance를 새로 만들지 않는다.

### 2.4 역사 v4.1 extend16 신규 3개 정합성 매트릭스

> 이 절은 v4.1 호환 계약을 설명하는 역사 자료다. 현행 v4.1 운하 파라미터 정본은 다음 절을 사용한다.

`extend16-v8`에서 proposal scope에 들어오는 세 Parameter는 mgmt 0033 master와 0034 v4.0 catalog의 직접
binding을 그대로 보존하고, v4.1 conditional binding에서도 재사용하는 Basecase-only capability다. 아래 tuple을
하나의 release 계약으로 고정한다.

| Parameter | DB master/current canonical | v4 Lever | authoritative source → final write target | exact axes·단위 | runtime 계약 |
|---|---|---|---|---|---|
| `RegionalProductionAdjustment` | ID 22, active; Supply / `ProductionAdjustment` / `table1` | ID 53 `regional_upstream_production`, primary executable | Supply `BCProduction` C:K의 Identifier·Year별 Mt 합계 × `1/0.735` → Supply `ProductionAdjustment` / `table1`, B/C/E | Year, Province/Country; Bcm annual final absolute, 2,187 records | `regional_production_annual`, appendable, minimum 0 |
| `ShippingFuelCost` | ID 23, active; Trade / `ShippingCostInput` / `table3` | ID 54 `lng_vessel_fuel_cost`, primary executable | Trade `ShippingCostInput` B:C rows 28~35 → 동일 sheet B/F | Year; $/tonne absolute, 5 records | `exact_rows`, existing exact, `C3=Absolute`, minimum 0 |
| `CanalToll` | ID 24, active; Trade / `ShippingCostInput` / `table4` | ID 55 `canal_toll`, primary executable | Trade `ShippingCostInput` A:C의 Suez/Panama 두 block → 동일 sheet A/B/F | Canal, Year; $/crossing absolute, 10 records | `exact_rows`, existing exact, `C3=Absolute`, minimum 0 |

세 Parameter 모두 proposal capability는 공통 `v4_workbook_then_lut` reference mode를 사용하되 등록된 LUT가
없으므로 실제 fallback은 발생하지 않는다. ShippingFuelCost와 CanalToll은 `existing_exact`,
RegionalProductionAdjustment는 `appendable` 계약이다. 빈 값, non-finite, 중복 exact key, horizon 밖 좌표는
제안 slot이 아니며, RegionalProductionAdjustment 원천 K열의 개별 음수 component는 Identifier·Year 합산 결과가
음수가 아닐 때만 유효하다.

제안 허용여부와 Event 적용성은 별도 gate다. `ShippingFuelCost`는 LNG 선박 IFO380
연료비의 연도별 `$/tonne` 절대값 변화가 있을 때만 `lng_vessel_fuel_cost`로 선택하고,
LNG bunker–VLSFO 상대 spread나 LNG 현물가 상승만으로 추론하지 않는다. `CanalToll`은
Suez·Panama 운하별 `$/crossing` 통항료 금액 변화에만 적용하며, Hormuz 해협의 수수료
논의나 봉쇄·우회·지연은 `route_disruption`이다. 이 적용성 증적이 없어 abstain한 것은
capability 누락이 아니므로 release 실패와 분리해 보고한다.

### 2.5 v4.1 Suez/Panama 분리 정합성 매트릭스

| Parameter | DB master/current canonical | v4.1 Lever | authoritative source → final write target | exact axes·단위 | runtime 계약 |
|---|---|---|---|---|---|
| `Suez Canal Cost` | ID 25, active; Trade / `ShippingCostInput` / `table4` | v4.1 `canal_toll` primary 및 `route_disruption`·`regional_price_spread` conditional | Trade `ShippingCostInput` A:C Suez rows 39~46 → 동일 sheet A/B/F `table4` | Canal=Suez, Year; $/crossing absolute, 5 records | `exact_rows`, existing exact, `C3=Absolute`, minimum 0 |
| `Panama Canal Cost` | ID 26, active; Trade / `ShippingCostInput` / `table5` | v4.1 `canal_toll` primary 및 `route_disruption`·`regional_price_spread` conditional | Trade `ShippingCostInput` A:C Panama rows 50~57 → 동일 sheet A/B/F `table5` | Canal=Panama, Year; $/crossing absolute, 5 records | `exact_rows`, existing exact, `C3=Absolute`, minimum 0 |

두 Parameter는 같은 sheet를 사용하지만 `parameterName`, `modelTable`, source block과 exact Canal 축이 모두
다르다. Suez 근거로 Panama를, Panama 근거로 Suez를 선택하지 않는다. ID 24 `CanalToll`과 v4
binding은 기존 v4 Scenario 호환을 위해 보존하지만 v4.1 capability에는 포함하지 않는다. PowerMix의 연간/월간
표는 이번처럼 `parameterName`을 분리하지 않고 하나의 Parameter 안에서 table별 atomic formatting을 유지한다.

### 2.6 이번 누락의 원인과 재발 방지 게이트

기존 누락은 DB master와 v4.0 Lever catalog에는 ID 22·23·24가 있었지만 Agent의 proposal capability와 workbook
contract가 이전 `extend14-v6/new-bc-v6`에 머물러 발생했다. Lever가 executable이라는 사실만으로 runtime
allow-list와 기준값 contract가 자동 확장되지 않으므로, 다음 검사를 릴리스 필수 조건으로 둔다.

1. v4.1 hydrated catalog의 executable binding이 가리키는 활성 Parameter ID/name/target 집합과 proposal
   capability 집합을 **set equality**로 비교한다. 개수만 같거나 일부 표본만 성공하는 것으로 대체하지 않는다.
2. 각 행에 대해 `ID + name + model_file/sheet/table + exact axes + unit`을 full outer diff하고 하나라도 빠지거나
   더 있으면 startup/release를 실패시킨다. 비활성 ID 9는 workbook reference를 보존해도 proposal contract에는 넣지 않는다.
3. 신규 capability마다 workbook contract의 source·write target·record count와 실제 materialization 1건 이상을
   검증한다. `existing_exact`은 source key가 target slot에 모두 존재해야 하고 `appendable`은 target header와 단위를 고정한다.
4. local config와 Kubernetes ConfigMap의 capability release/SHA 및 workbook path를 동시에 갱신하고 equality test를 실행한다.
5. 신규 Parameter별 focused regression과 대표값 검증 없이 전체 allow-list 개수 테스트만 통과시켜서는 안 된다.
6. 실제 v4.1 proposal campaign에서 세 Lever의 candidate provenance와 성공·abstain 사유를 별도 행으로 보고한다.

## 3. DB canonical 변경

tmm_mi_model_param_m에는 다음을 모두 명시한다.

- use_yn, parameter_name, parameter_hint
- model_file, model_sheet, model_table, semantic_axes
- basecase_read_mode와 모든 basecase_* 컬럼
- 수정 감사 컬럼과 del_yn

sibling mgmt에는 새 versioned migration으로 최종 DML을 두고, 이 저장소의 canonical과 같은 tuple인지 정적
검증한다. DML 준비만 요청된 경우에는 DML/canonical diff까지가 증적이며 DB 적용을 주장하지 않는다. target DB
적용이 승인된 경우에만 transaction·read-back으로 최종 행과 hydrated catalog checksum을 확인한다.

기본키와 생성 감사 컬럼은 변경하지 않는다. v4 binding은 active Impact Lever catalog가 parameter name, role과 applicability를 소유한다. legacy mapping 전체는 transaction 전후 digest가 같은지 확인하는 invariant로만 취급한다. Flow/node에서 직접 SQL을 작성하지 않고 persistence service를 사용한다.

다음 명령은 128행 snapshot을 사용한 **역사적 v4 canonical rollout 예시**다. 현재 runtime allow-list-only
v0.2.4 작업이나 129행 기준선이 적용된 DB에서는 실행하지 않는다. 이후 DB/canonical 변경이 별도로 승인되고 새
snapshot-compatible versioned runner가 준비된 경우에만 그 runner로 dry-run과 apply를 수행한다.

    poetry run python scripts/model_parameter/apply_model_parameter_v4.py

역사적 release에서 검증된 변경을 commit한 명령은 다음과 같다.

    poetry run python scripts/model_parameter/apply_model_parameter_v4.py --apply

위 v4 runner는 기존 snapshot과 함께 보존하는 역사적 release replay다. 현재 live baseline과 다르면 실행하지 않으며, 이후 master/Lever 변경에는 새 snapshot과 versioned runner가 필요하다. allow-list-only 변경에서는 어떤 DB runner도 실행하지 않고 SELECT-only fingerprint 또는 repository diff로 DB 비변경을 확인한다.

workbook은 다음 명령으로 v4 canonical·config·archive와 보호 대상 legacy mapping의 비변경 상태를 확인한다. 이 검사는 v4 Lever canonical 검증을 대신하지 않는다.

    poetry run python scripts/model_parameter/sync_mapping_workbook.py --check-only

## 4. LUT와 v4 workbook resource 변경

`apps/agents/model_parameter_agent/new_resources/`는 신규 Basecase/LUT를 받는 staging 경로다. 현재처럼
`new_resources/lut/`가 없거나 LUT가 아직 들어오지 않은 상태는 정상이다. runtime과 manifest는 이 경로를
직접 읽지 않는다. 신규 LUT가 도착하면 `.DS_Store`, `~$*` 같은 임시 파일을 제외하고 파일명·크기·digest와
기존 `resources/lut/` 충돌을 먼저 확인한다. 검증·승인이 끝난 파일만 canonical `resources/lut/`로 승격하고
adapter, manifest, config/ConfigMap, canonical/workbook/docs/tests를 함께 갱신한다. staging 원본은 사용자가
별도로 요청하지 않는 한 이동·삭제·덮어쓰기하지 않는다.

`envs/config.yaml`과 외부에서 관리하는 Neuro Model Parameter 설정을 같이 수정한다. 검토용 Neuro 사본을
`devops/k8s/model-parameter-configmap.yaml`에 둘 수 있지만 Git에는 커밋하지 않는다. 공용
`devops/k8s/configmap.yaml`은 전용 설정의 source of truth가 아니다.

- 활성 parameter: enabled=true, adapter, files, required_columns, key_axes, 필요 시 metadata_axes
- 보류 parameter: enabled=false로 다운로드·구조 검증만 수행
- 보조 파일: references에 등록하고 독립 parameter catalog를 만들지 않음
- object key: fundamental_model_artifact/LUT/demand/... 또는 supply/supply_bc/...
- adapter 동작 변경: ADAPTER_SCHEMA_VERSION을 올려 runtime cache 분리

adapter는 필수 header, horizon, 숫자 형식, 빈 값, exact-key 충돌, join 누락, 시설 상태와 정밀도 정책을 검증해야 한다. 모든 packaged CSV가 활성·보류·reference 중 하나로 분류되어야 한다.

runtime proposal 범위를 제한하기 위해 DB, canonical JSON/SQL, config, LUT, Basecase workbook을 축소하지 않는다.
v4 runtime은 active parameter definition과 catalog binding에 필요한 resource를 사용한다. 기존 v1/v3 Basecase
preload의 누락·파싱 오류·0건은 warning으로 남기며, 현행 v4.1 17개 capability 전체는 자동화·release
acceptance에서 별도로 검증한다. v4 `new-bc-v9` startup은 contract schema/path와 contract에 고정된
Workbook path/digest만 경량 검증한다. sheet·header·range·변환·고정 record count는 최초 exact v4 materialization에서
fail closed하고 성공 결과를 process cache한다.

### versioned workbook 계약을 변경하거나 확장할 때

현재 `extend17-v9`의 v4-only reference는 `resources/contracts/model-parameter-workbook-contract-v9.json`이 소유한다.
각 release는 검증용 불변 packaged artifact 디렉터리와 digest를 고정하며, 현재 v9은 `resources/basecase_v4/new-bc-v2/`를 사용한다.
활성 MI Base의 Object Storage workbook은 이 계약의 구조를 적용하되 요청별 실제 digest로 별도 고정한다.
계약 coverage·parser·hash 또는 workbook digest가 바뀌면 새 release ID와 새 contract 파일·artifact 디렉터리를 만든다. 기존 `resources/basecase/` 파일을 덮어쓰거나
`new_resources/`를 runtime path로 연결하지 않는다.

향후 proposal 범위를 확대할 때는 기존 5개가 사용하는 방식을 기본 불변 조건으로 삼는다.

1. 새 Parameter를 현재 versioned workbook contract에 선언하고 authoritative source, write target, exact axes,
   변환, record count, constraints를 고정한다.
2. capability `reference_mode`는 공통 `v4_workbook_then_lut`를 사용한다. 새 Parameter만 legacy Basecase parser로
   우회하는 mode를 추가하지 않는다.
3. 공통 candidate→contract reference→same-exact-key LUT fallback→Step2 exact slot→evidence→Step3 value→persistence
   순서를 그대로 사용한다. 파라미터별 차이는 contract parser·축·제약에만 둔다.
4. authoritative source가 현재 workbook에 없으면 먼저 versioned workbook/auxiliary source 계약을 준비한다.
   이를 생략하고 LUT-only 또는 legacy-only로 활성화하려면 별도 설계 승인과 문서화가 필요하다.
5. 기존 5개와 새 Parameter를 함께 parameterized regression으로 검증하며 public API와 proposal JSON은 유지한다.

- 계약 capability는 writer/engine 승인 전까지 `read_only_proposal`로 유지한다.
- authoritative source와 기존 DB write target, key/metadata axes, 단위·absolute-value 의미를 분리해 선언한다.
- write target이 `appendable`인지 `existing_exact`인지 선언하고, `existing_exact`이면 target-backed slot 전수
  검증과 target-owned metadata 회귀 테스트를 추가한다.
- 신규 source가 정상적으로 없는 exact key에만 기존 LUT fallback을 허용한다. non-finite·cached error·상충
  duplicate key는 명시적으로 차단해 LUT로 복구하지 않는다.
- PowerMix는 authoritative raw source fraction의 원본 정밀도를 보존하고 재정규화하지 않는다. Country/Year별
  승인된 10-member 완전성·중복·유한성·0~1·합 1로 atomic 검증하며, Basecase/LUT 결합 effective vector와
  Step3 proposed vector에도 합 1과 `1e-6` 허용오차를 다시 적용한다. 검증 뒤 proposal 출력은 table1의
  Year+Country 또는 table2의 Year+Month+Country별로 largest-remainder 보정해 0.01 단위·합계 1.00으로 만든다.
- LiqUtilAdjustment는 한 Lever provenance 안에서 Plant와 Train 둘 모두, slot과 일치하는 Year/Month,
  Group에 실제로 연결된 source Event와 직접 운영 근거가 있어야 한다. 승인된 한국어/영문·Stage·Train
  표기 정규화는 허용하지만 출력은 exact catalog 좌표를 사용한다. 단일 후보라는 이유로 Plant·Train·기간
  근거를 생략하지 않는다. 음수만 차단하고 1 초과값을 보존하며, lifecycle 공란은 exact record를 제외하지
  않고 metadata/applicability에서만 생략한다.
- contract schema/hash 또는 workbook digest가 달라지면 같은 release ID를 재사용하지 않고 version을 올린다.

현재 고정 source 회귀 수는 GDP 815, PMI 5,040, PowerMix 4,200, Temperature 5,040,
Population 845, HurricaneIntensity 60, LiqProdAdjustment 23,820, LiqUtilAdjustment 23,820,
PipelineAdjustment 420, SupplyDisruption 4,908, User-Adjusted Gas Demand 12, RegasAdjustment 22,320,
PNG Contract Volume 684, ShippingCost 5, RegionalProductionAdjustment 2,187, ShippingFuelCost 5,
CanalToll 10이다. 변경 release에서는 새 digest와 실제 count를 함께 검토하되, count를 맞추기 위해
invalid key를 임의 보간하거나 nearest/fuzzy fallback하지 않는다.

## 5. LiqProdAdjustment 적용 사례

LiqProdAdjustment는 체크인 canonical/resource capability와 v4.1 `extend17-v9` proposal allow-list에서 활성이다.

- master ID 13, use_yn=Y
- adapter liq_prod
- source BCLiquefaction.csv
- key Country, LNG Plant, LNG Plant Train, Year, Month
- value 월 생산능력 × LNG plant utilisation
- Closed 시설 제외
- v4 `liquefaction_production_override` Lever의 primary binding으로 capability를 보존

v4에서는 `liquefaction_utilization`과 `liquefaction_production_override`를 분리한다. 단기·부분 차질은
LiqUtilAdjustment, 생산량 직접 override·대폭/영구 손실·신규 Train ramp-up은 LiqProdAdjustment를 사용한다.
legacy mapping은 후보 source나 fallback으로 사용하지 않는다.

## 6. v4.1 raw Lever binding과 extend17 proposal 범위의 핵심 규칙

| Lever | Parameter binding |
|---|---|
| `weather_demand` | Temperature primary |
| `power_generation_mix` | PowerMix primary |
| `population_demographics` | Population primary |
| `economic_activity` | GDP primary; PMI alternative |
| `direct_gas_demand` | binding 없음; proposal 제외 |
| `upstream_production` | SupplyDisruption primary |
| `liquefaction_utilization` | LiqUtilAdjustment primary |
| `liquefaction_production_override` | LiqProdAdjustment primary |
| `regasification_capacity` | RegasAdjustment primary |
| `us_gom_hurricane_disruption` | HurricaneIntensity primary |
| `pipeline_capacity` | PipelineAdjustment primary |
| `lng_charter_rate` | ShippingCost primary |
| `png_contract_volume` | PNG Contract Volume primary |
| `regional_upstream_production` | RegionalProductionAdjustment primary |
| `lng_vessel_fuel_cost` | ShippingFuelCost primary |
| `canal_toll` | Suez Canal Cost, Panama Canal Cost primary |
| `route_disruption` | ShippingCost, ShippingFuelCost, Suez Canal Cost, Panama Canal Cost conditional |
| `trade_restriction` | 공급·시설 6종과 PNG Contract Volume conditional |
| `inventory_condition` | 수요 4종·공급 6종·PNG Contract Volume conditional |
| `regional_price_spread` | 수요·공급·PNG와 ShippingCost, ShippingFuelCost, Suez Canal Cost, Panama Canal Cost conditional |
| `financial_market_sentiment` | GDP, PMI conditional |

`price_only` Lever도 상태의 명시된 원인·직접 영향이 실제 model input과 연결되면 conditional 후보가 된다.
가격·재고·심리 방향 자체를 model input 방향으로 바꾸지 않으며, 근거가 없으면 0건을 유지한다. CDD/HDD와
User-Adjusted Gas Demand의 역사 binding은 v4.1 catalog에 복제하지 않는다.

현재 v4 신규 proposal에서는 capability gate를 통과한 GDP, PMI, PowerMix, Temperature, Population,
HurricaneIntensity, LiqProdAdjustment, LiqUtilAdjustment, PipelineAdjustment, SupplyDisruption,
RegasAdjustment, PNG Contract Volume, ShippingCost, RegionalProductionAdjustment, ShippingFuelCost,
Suez Canal Cost, Panama Canal Cost만 이후 단계로 전달한다. v4.1 executable Parameter가 capability에서 빠지면 release 오류다.

### 현행 v4.1 Basecase-only 7개

| Parameter | 기준값 | v4 Lever binding |
|---|---|---|
| RegasAdjustment | 검증된 Basecase exact slot | `regasification_capacity` primary |
| PNG Contract Volume | 검증된 Basecase exact slot | `png_contract_volume` primary |
| ShippingCost | 검증된 Basecase exact slot | `lng_charter_rate` primary |
| RegionalProductionAdjustment | 검증된 Basecase aggregate/appendable slot | `regional_upstream_production` primary |
| ShippingFuelCost | 검증된 Basecase exact slot | `lng_vessel_fuel_cost` primary |
| Suez Canal Cost | 검증된 Suez Basecase exact slot / `table4` | `canal_toll` primary |
| Panama Canal Cost | 검증된 Panama Basecase exact slot / `table5` | `canal_toll` primary |

별도 LUT fallback을 추가하지 않는다. 검증된 Basecase exact slot이 없는 좌표는 제외한다. 이 7개는
`extend17-v9` runtime proposal allow-list 안에 있으며, direct evidence와 exact 좌표가 없으면 abstain한다.
`RemainingUnrestrictedAmount`와 `VolumeCancelled`는 0032 canonical에서 inactive/unbound이므로 새 contract와
forward canonical release 없이 후보화하지 않는다.

## 7. prompt·token 보호

resource release에서 준비된 LUT record는 서버 cache/index에 보관한다. v4 runtime은 지정 version의 active catalog
binding으로 도달 가능한 definition을 사용하며, 현행 v4.1 17개 capability 전체 검증은 자동화·release acceptance의
책임이다. runtime allow-list gate는 source matching 직후, 조건부 Step1.5·Step2·Step3 LLM과 proposal
persistence 전에 적용한다. v4 Step1.5는 동일 Lever state의 복수 binding과 모든 conditional binding에 적용한다.
각 applicability가 독립적으로 근거 있으면 설정 상한까지 복수 Parameter를 유지한다.

conditional binding 수가 많은 Lever는 Event/Dimension/Lever 공통 provenance를 후보별로 반복하지 않는다.
Step1.5의 `lever_context`에 공통 근거를 한 번만 싣고, 각 후보의 Parameter hint·semantic axes·mapping comment·
applicability는 보존한다. 대표 worst-case prompt를 직렬화해 설정 byte 상한 아래인지 확인하며, 단순히 상한을
늘려 해결하지 않는다. Step2 exact-slot 선택 뒤 proposal 품질 검증은 v4의 post-slot 후보 집합을 기준으로 하여,
근거가 없어 안전하게 탈락한 conditional 후보가 다른 유효 후보의 persistence를 막지 않게 한다.

- 파라미터별 반환 상한: model_parameter_max_parameter_slots=100
- 요청 전체 선택 slot 상한: model_parameter_max_total_selected_slots
- 직렬화 상한: model_parameter_max_step2_prompt_bytes, model_parameter_max_step3_prompt_bytes
- proposal Flow release: model_parameter_proposal_flow_release=v4.1.8
- transient LLM 호출: model_parameter_transient_retry_max_attempts=2,
  base delay 0.5초, max jitter 0.25초; timeout·transport·retryable HTTP와
  `EOF while parsing`으로 확인된 불완전 JSON만 retry하고 완결 JSON의 schema·semantic/좌표/DB 오류는 retry 금지
- 상한 초과: LLM 호출 전 actual/limit과 parameter별 크기를 포함해 실패

proposal Step3의 `proposedValue`는 유한 숫자여야 한다. Confirmation은 `proposedValue` key가 필수지만 값은 `null`일 수 있고, non-null 값만 persistence 경계에서 엄격한 유한 숫자로 정규화한다. 원래 proposal과 같아야 한다는 비교는 없다. 설정 기반 소수 자릿수 round/trunc/ceil은 적용하지 않되 PowerMix proposal 최종 출력만 그룹별 0.01 단위·합계 1.00으로 보정하며 Confirmation 수정값에는 재적용하지 않는다. Basecase/LUT 기준값의 adapter 정밀도 정책은 이와 별개로 유지하되 v4 PowerMix source fraction은 atomic sum을 보존하도록 정밀도 변환에서 제외한다. 기존 proposed precision 설정 키는 배포 설정 호환용이며 runtime 제안값을 변환하지 않는다.

proposal-only evidence runner가 API 응답과 DB JSON을 비교할 때는 JSON/DB 왕복으로 생기는 최하위
floating-point noise에만 `1e-12` 절대·상대 허용오차를 적용한다. Parameter명, slot 좌표, payload 구조 또는
의미 있는 값 차이는 허용하지 않는다.

## 8. 완료 판정

1. canonical consistency와 resource release·LUT adapter 자동화 테스트가 통과한다.
2. config.yaml과 ConfigMap manifest가 같다.
3. 적용 대상 DB의 master 26행·활성 18개와 v4.1 active Lever 21개·binding occurrence 56개를 확인한다.
   v4.1 checksum `467749ea59c3af7e875669be23da00c0fd8ef7c226256f9518a5945e36e4d7c4`를 read-back하고,
   기존 v4/v4.0 catalog·pin이 보존되고 기존 v4.1 Scenario pin은 같은 version의 위 checksum으로 이관됐는지 확인한다.
4. v4.1 canonical JSON·mgmt SQL, LUT manifest, workbook/archive와 legacy mapping 비변경 digest를 확인한다.
5. resource capability 기준으로 LUT-backed 활성 10개의 selectable LUT slot과 현행 v4.1 Basecase-only 7개의
   Basecase slot을 확인한다. v4.1 proposal capability가 executable 17개와 정확히 일치하는지 검증한다.
6. v4 `new-bc-v9` contract의 세 workbook·auxiliary digest/header와
   815/5,040/4,200/5,040/845/60/23,820/23,820/420/4,908/12/22,320/684/5/2,187/5/10/5/5 record를 확인하고,
   invalid exact-key LUT 차단, PowerMix atomic vector, HurricaneIntensity 0~4 정수,
   LiqProd/LiqUtil target·evidence 회귀를 통과한다.
7. v4 multi-event quality runner로 실제 선택 value에서 도달한 allow-list parameter를 proposal하고, 빈 confirmation rollback, 정상 confirmation, reconfirmation, DB read-back을 수행한다.
8. 실제 리포트에 parameter, candidate, slot, effective reference, proposal, token, 시간·retry와 confirmation ID를 남긴다.
9. logic-only release는 Impact Lever catalog version/checksum과 Scenario ID를 변경하지 않는다. 같은 고정 cohort로
   Before/After를 비교하고, catalog/binding 변경 release와 명확히 구분한다.

DB seed의 Git 작성자와 audit principal은 분리한다. Git author는 작업자 계정을 사용하더라도
`crt_usr_logn_id`/`mod_usr_logn_id`에는 개인명을 넣지 말고 release 식별자(예:
`model-impact-lever-v4.1-v0050`)를 사용한다. 또한 dry-run INSERT를 AUTO_INCREMENT에 맡기면 MySQL은
rollback 뒤에도 번호를 소비한다. release canonical과 migration/seed에는 검증된 ID를 명시하고,
dry-run에서 우연히 할당된 ID를 기준값으로 채택하지 않는다.

신규 파라미터마다 아래 결과를 별도 행으로 남긴다. 모든 칸이 PASS이거나 승인된 N/A 사유가 있어야 하며,
기존 파라미터를 포함한 총 개수만 맞는 것으로 완료 처리하지 않는다.

| Parameter | DB/canonical | Lever | capability | source Excel | transformed/LUT | write target | config | runtime output |
|---|---|---|---|---|---|---|---|---|
| `<new parameter>` | PASS/FAIL | PASS/FAIL | PASS/FAIL | PASS/FAIL | PASS/FAIL/N/A | PASS/FAIL | PASS/FAIL | PASS/FAIL |

검증 전후 DB·canonical·catalog와 기존 v1/v3 Basecase·업무용 mapping workbook fingerprint가 같아야 한다. 별도로 추가한 v4 contract/config path와 `new-bc-v2` packaged baseline artifact는 선언된 digest·header·record count와 일치해야 하며, 활성 MI Base의 Object Storage workbook도 같은 구조 계약을 통과해야 한다. workbook `SUMMARY`의 파일·시트·표 이름·화면 표시 여부도 logical table catalog와 일치해야 한다.

catalog checksum이 바뀌면 master와 Lever catalog를 원자적으로 적용한 뒤 신규 v4 Scenario를 생성한다. 기존 v4 Scenario를 새 catalog로 조용히 재해석하지 않는다. Coal/Gas Futures는 실제 2026년 이후 strip이 제공될 때, ElectrificationRate는 국가·연·Drive Train LUT와 승인 binding·capability가 준비될 때 같은 절차로 활성화한다.
