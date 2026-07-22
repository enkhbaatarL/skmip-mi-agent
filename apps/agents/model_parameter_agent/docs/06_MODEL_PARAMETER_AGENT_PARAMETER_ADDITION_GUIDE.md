# Model Parameter Agent 파라미터 추가 가이드

이 문서는 현재 미사용 파라미터인 `LiqProdAdjustment`를 예로 들어 Parameter master, dimension mapping, Basecase/LUT, 전용 adapter와 `config.yaml`을 어떤 순서로 준비하는지 설명한다.

> 기준일: 2026-07-22. 현재 DB, Notion, mapping Excel, 실제 `Supply Model_Input.xlsm`, `BCLiquefaction.csv`와 Agent 코드를 읽기 전용으로 대조했다. 현재 `liq_prod` adapter는 아직 없으며, 이 문서는 추가할 때 필요한 기능과 검증 기준을 설명한다.

## 1. 먼저 보는 전체 순서

`LiqProdAdjustment`는 LNG Plant Train의 **월별 최종 생산량 절대값**을 `Mt LNG/month` 단위로 제안하는 파라미터다. 현재 값이 있는 Basecase record는 0건이므로, 실제 추가의 핵심은 기존 `BCLiquefaction.csv`를 LiqProd 의미로 읽는 전용 adapter와 승인된 DB mapping을 준비하는 것이다.

```text
1. Notion에서 대상 event type·dimension·mapping method를 확인한다. direct는 유지하고 동시 후보 동작을 확인한다.
2. Parameter master의 현재 값과 Basecase parsing 설정을 확인한다.
3. parameter_hint와 mapping comment 5건의 적용·산정 원칙을 보강하고 승인한다.
4. BCLiquefaction.csv의 실제 header·기간·값을 확인한다.
5. liq_prod adapter를 추가해 월 생산능력 × 이용률을 LiqProd value로 만든다.
6. 기존 BCLiquefaction.csv를 공유하도록 config.yaml을 등록한다.
7. Object Storage download와 LUT startup validation을 통과시킨다.
8. Dimension mapping을 비활성 상태로 등록하고 비운영 환경에서 검증한다.
9. Parameter master와 승인된 mapping을 함께 활성화한다.
```

중요한 순서는 **adapter와 LUT 검증이 먼저, DB 활성화가 나중**이다. 현재 코드는 `liq_prod`를 지원하지 않으므로 DB만 먼저 활성화하면 올바른 `Mt LNG/month` 기준값을 만들 수 없다.

## 2. 어떤 자료를 기준으로 하나

| 결정할 내용 | 기준 자료 | 사용하는 항목 |
|---|---|---|
| Event type·dimension·mapping method·comment | [Notion Event Dimension Parameter Mapping](https://app.notion.com/p/cfcee86c3fac4763963d960c9d0851a7?v=357bca8c30074d4c843b552846e9f58c&source=copy_link) | `이벤트타입LV2`, `dimension`, `맵핑방식`, `comment(맵핑방식)`, `파라미터사용유무` |
| 모델 위치·단위·Basecase/LUT 의미 | [mapping Excel의 모델파트 Sheet](../resources/mapping/260702_시나리오가정_MI수급모델_input_매핑_모델파트수정_v0.4.xlsx) | `Parameter Excel Mapping (모델파트)` 8행 |
| 실제 LUT header·값·기간 | packaged `apps/agents/model_parameter_agent/resources/lut/BCLiquefaction.csv`와 조사 원본 `~/수급모델파라미터/data/LUT/supply/supply_bc/BCLiquefaction.csv` | Train, Year, Month, 생산능력, 이용률 |
| 현재 활성 상태와 runtime 제약 | 현재 DB, `config.yaml`, Agent 코드 | `use_yn`, 실제 mapping, 지원 adapter, horizon, Object Storage manifest |

mapping Excel의 `enabled=true`는 기준 행을 사용한다는 표시다. 운영 DB의 `use_yn`이나 Notion의 `파라미터사용유무`를 자동으로 활성화하지 않는다.

### 2.1 현재 상태와 먼저 내린 판단

| 구분 | 현재 확인 결과 | 추가 전에 할 일 |
|---|---|---|
| Parameter master | `model_param_id=13`, `use_yn=N`, `del_yn=N` | 대상 환경에서 이름으로 ID 재조회, hint 보강 |
| Notion mapping | 관련 5건 모두 `미대상` | 실제 대상 전환 승인, 비어 있는 comment 4건 보강 |
| DB dimension mapping | LiqProd master를 가리키는 행 0건 | 승인된 Notion mapping을 DB에 등록 |
| Basecase | 생산량 값이 있는 `LiqProdAdjustment` record 0건 | 별도 Basecase 복구 없이 LUT-only 기준값 검증 |
| LUT 원본 | 기존 LiqUtil과 같은 `BCLiquefaction.csv` 사용 가능 | 별도 원본 파일 생성 불필요 |
| LUT 데이터 | 2026-07-22 파일 기준 전체 41,103행, 2026~2030 exact key 19,366건 | 현재 기간·필수 열·중복 검증 통과 |
| Runtime adapter | `liq_util`은 있으나 `liq_prod`는 없음 | 전용 adapter 추가 필요 |
| Runtime config | `LiqUtilAdjustment`만 등록 | adapter 구현 후 LiqProd 항목 추가 |

판단 결과는 다음과 같다.

- 파일과 slot 구조는 기존 `LiqUtilAdjustment`와 공유할 수 있다.
- `liq_util` adapter를 이름만 바꿔 재사용하면 값이 **이용률**로 생성되므로 사용할 수 없다.
- `LiqProdAdjustment` value는 `월 생산능력 × 이용률`로 계산해야 한다.
- 따라서 raw CSV를 그대로 공유하되 계산만 다르게 하는 `liq_prod` adapter가 필요하다.

## 3. Parameter master에서 확인하고 보강할 값

대상 테이블은 `tmm_mi_model_param_m`이다. `LiqProdAdjustment`는 이미 존재하므로 중복 INSERT하지 않고 기존 행을 보강한다.

| 컬럼 | 현재 DB 값 | 확인·보강 기준 |
|---|---|---|
| `parameter_name` | `LiqProdAdjustment` | API 이름이자 `config.yaml` LUT key다. 철자와 대소문자를 같게 유지한다. |
| `parameter_hint` | `Train/month LNG production absolute value (Mt LNG/month; >= 0)` | 단위뿐 아니라 최종 생산량, 허용 범위, LiqUtil과의 차이를 보강한다. |
| `model_file` | `Supply` | 최종 적용 모델 구분 |
| `model_sheet` | `LiqProdAdjustment` | mapping Excel·Notion의 모델 위치와 일치 |
| `model_table` | `table1` | 제안 응답과 confirmation의 대상 table |
| `semantic_axes` | `액화시설 생산량 override — Country>Plant>Train·연·월` | Train별 월 단위 절대 생산량이라는 의미 |
| `basecase_read_mode` | `matrix_time_columns` | 행의 Train 정보와 열의 Year·Month를 조합해 읽음 |
| `basecase_header_row` | `10` | 값 이름과 행 축 header 위치 |
| `basecase_data_start_row` | `11` | 첫 Train 행 |
| `basecase_column_roles` | `B:Country,C:LNG Plant,D:LNG Plant Train,E:Life Cycle Category,F:Nameplate Capacity (MTPA)` | Basecase 열 추출과 최종 허용 축 이름을 정한다. LUT의 `key_axes`·`metadata_axes`와 같은 이름으로 맞춰야 한다. |
| `basecase_year_row` | `7` | G:DA 열별 Year |
| `basecase_month_row` | `8` | G:DA 열별 Month |
| `basecase_period_row` | `9` | G:DA 열별 Period |
| `basecase_value_start_col` / `end_col` | `G` / `DA` | 현재 DB가 읽는 첫 월별 production override 영역. 뒤쪽 별도 matrix는 현재 parser 범위 밖이다. |
| `basecase_stop_rule` | `stop_when_all_key_columns_empty` | key 열이 모두 비면 scan 종료 |
| `use_yn` | `N` | adapter·LUT·mapping 검증 완료 전까지 유지 |
| `del_yn` | `N` | 사용 가능한 정의는 `N`이어야 함 |

현재 DB의 `model_param_id=13`은 이 환경의 값일 뿐이다. 다른 환경에서는 반드시 `parameter_name='LiqProdAdjustment'`로 다시 조회한다.

mapping Excel 모델파트 행은 모델이 직접 사용하는 D:DA 영역을 중심으로 설명한다. 실제 Agent DB와 workbook에는 B열 Country, C열 LNG Plant도 있으며, LUT의 exact key가 `Country + Plant + Train + Year + Month`이므로 현재 DB의 B:C:D 축을 제거하지 않는다.

### 3.1 `parameter_hint` 보강 기준

현재 hint는 단위와 0 이상 조건만 알려 준다. 다음 내용이 prompt에서 함께 보이도록 보강해야 한다.

- 값은 차질량, 증감률, 이용률이 아니라 **월별 최종 생산량 절대값**이다.
- 단위는 `Mt LNG/month`이고 0 이상이다.
- 원칙적으로 해당 Train의 월 생산능력을 넘기지 않는다. 예외가 필요하면 근거를 남긴다.
- 같은 Train·월에 두 파라미터가 모두 입력되면 수급모델 계산에서는 `LiqProdAdjustment`가 우선한다. 이는 Agent 후보 선택 우선순위가 아니다.

보강 예시는 다음과 같다. 실제 반영 문구는 업무 담당자의 승인을 받아 확정한다.

```text
Existing LNG Plant Train의 월별 최종 LNG 생산량 절대값(Mt LNG/month).
차질량·증감률·가동률이 아니며 0 이상이고, 원칙적으로 해당 Train의 월 생산능력 이하로 제안한다.
LiqUtilAdjustment와 함께 제안될 수 있으며, 동일 Train·월의 모델 계산에서는 LiqProdAdjustment 입력이 우선 적용된다.
```

마지막 문장은 mapping Excel에 적힌 **수급모델 계산 우선순위**를 설명한다. Agent가 LiqUtil 후보를 자동으로 제외한다는 뜻은 아니다. LUT 파일·곱셈·slot 존재 조건은 여러 prompt에 반복되는 hint를 길게 만들지 않고 뒤의 adapter 절에서 관리한다.

## 4. Notion 기준 Dimension mapping과 comment 보강

대상 테이블은 `tmm_mi_model_param_dimension_map`이다. Notion에서 확인한 LiqProd 관련 행은 5건이며 모두 현재 `미대상`이다.

| Event Type L2 | Dimension | 필수 | Mapping | 현재 Comment |
|---|---|---|---|---|
| [2 / terminal_utilization_change / 터미널 Utilization 변동](https://app.notion.com/p/392263ff004c81948757c3ec43fab4e1) | `utilization_change_amount` / Utilization 변화량 | 필수 | 직접 | 비어 있음 |
| [3 / new_terminal_cod_rampup_change / 신규 터미널 COD·Ramp-up](https://app.notion.com/p/392263ff004c81dfa0c1df38ce006920) | `target_utilization_at_ramp_up` / Ramp-up 완료 시 도달 가동률 | 선택 | 직접 | 신규 Plant > Train 생산량 추가, FID 무산=0, COD·Ramp-up 반영 |
| [11 / natural_disaster / 자연재해](https://app.notion.com/p/392263ff004c81b5b377e6285347fd45) | `affected_facility_type` / 영향 시설 유형 | 필수 | 라우팅 | 비어 있음 |
| [17 / geopolitical_tension_war / 지정학적 긴장 및 전쟁·군사분쟁](https://app.notion.com/p/392263ff004c8183bf31dad1b27efa34) | `supply_disruption_intensity` / 공급 차질 강도 | 선택 | 직접 | 비어 있음 |
| [18 / economic_sanctions_trade_restrictions / 경제 제재 및 무역 제한](https://app.notion.com/p/392263ff004c8168ad72f691e0fc35c2) | `supply_disruption_intensity` / 공급 차질 강도 | 필수 | 직접 | 비어 있음 |

Notion의 `파라미터사용유무=미대상`을 업무 승인 없이 DB에서 임의로 활성화하지 않는다. 또한 현재 5건 중 4건의 comment가 비어 있으므로, `대상` 전환 전에 comment부터 보강해야 한다.

### 4.1 Parameter hint와 mapping comment의 차이

| 필드 | 적용 범위 | Prompt에서 하는 일 |
|---|---|---|
| `tmm_mi_model_param_m.parameter_hint` | LiqProd 전체 | 값의 의미, 단위, 범위, 계산 기준, LiqUtil과의 차이를 설명 |
| `tmm_mi_model_param_dimension_map.comment` | 특정 event type·dimension 연결 | direct에서는 적용 목적·값 해석을, routing에서는 후보 선택 조건을 설명 |

`parameter_hint`만 길게 써도 mapping별 선택 기준은 생기지 않는다. 반대로 mapping comment만 있어도 값의 공통 단위와 제약이 안정적으로 전달되지 않는다. 두 필드를 각각 보강해야 한다.

`direct`와 `routing` mapping의 comment는 `mapping_comment`로 slot/value 제안 context에 전달된다. 다만 `direct` candidate는 comment를 비교해 하나만 고르는 것이 아니라 조건 없이 다음 단계로 통과한다. 후보 간 선택에 comment를 실제로 사용하는 단계는 `routing`이다.

### 4.2 Mapping comment 보강 방향

아래는 mapping Excel 설명과 모델 동작을 바탕으로 한 보강 방향이다. 먼저 Notion에서 승인된 최종 문구를 확정한 뒤, 그 원문을 DB `comment`에 복사한다.

| Event L2 | Comment에 보강할 적용 목적·값 해석 |
|---|---|
| `2` | 대폭·장기 또는 최종 생산량을 직접 정해야 하는 변화에 LiqProd를 연결하며, dimension 값을 월 생산량 산정에 어떻게 참고하는지 설명 |
| `3` | `BCLiquefaction.csv`에 이미 존재하는 계획 Train에 한해 COD 지연·Ramp-up 월별 생산량 반영. 원본에 없는 신규 Train이면 Basecase/LUT 기준정보를 먼저 추가. FID 무산은 생산량 0 |
| `11` | `affected_facility_type`이 수출·액화 시설이고 월 생산량 직접 override가 필요한 경우 LiqProd를 routing으로 선택. 단기·부분 차질은 LiqUtil |
| `17` | 전쟁·군사분쟁으로 액화 Train 생산량이 대폭 또는 장기 감소해 월 생산량 절대값 입력이 필요한 경우 사용 |
| `18` | 제재·무역 제한으로 액화 Train 생산량을 직접 감소·중단시켜야 하는 경우 사용 |

### 4.3 Direct mapping은 그대로 유지한다

현재 DB에는 event 2·17·18의 같은 dimension에 `LiqUtilAdjustment` direct mapping이 이미 활성화되어 있다. Notion 원문대로 LiqProd도 `direct`로 추가하면 Agent는 둘 중 하나를 고르지 않고 **LiqUtil과 LiqProd를 모두 다음 단계로 보낸다**. comment에 “대폭이면 LiqProd, 단기면 LiqUtil”이라고 써도 이 동작은 바뀌지 않는다.

이 가이드에서는 사용자 결정에 따라 event 2·3·17·18의 LiqProd mapping을 `direct`로 유지한다. 따라서 event 2·17·18 테스트에서는 같은 scenario에 LiqUtil과 LiqProd 후보가 함께 생성되는지, 두 결과가 모두 제안될 때 값과 근거가 각 파라미터 의미에 맞는지 확인한다. 동일 slot에 두 입력이 생기면 수급모델 계산에서 LiqProd가 우선 적용되는지도 함께 검증한다.

event 11만 Notion 원문대로 `routing`을 유지하며, 보강된 comment로 LiqUtil/LiqProd 선택을 검증한다.

### 4.4 Dimension 값을 생산량으로 바꾸는 원칙도 보강한다

현재 Agent에는 dimension 값을 LiqProd 절대 생산량으로 바꾸는 고정 수식이 없다. LLM이 LUT 기준값, hint, mapping comment와 scenario를 함께 보고 제안한다. 따라서 comment 승인 때 다음 산정 원칙도 함께 확정해야 한다.

| Event L2 | 승인할 산정 원칙 |
|---|---|
| `2` | `utilization_change_amount`가 percentage point인지 상대 변화율인지, LUT 생산량에 어떻게 적용할지 |
| `3` | `월 생산능력 × target utilization`을 사용할지, COD 지연·Ramp-up 월별 경로와 FID 무산 0을 어떻게 적용할지 |
| `11` | 시설 유형으로 parameter를 고른 뒤 차질 강도·기간·회복 pattern을 생산량에 어떻게 반영할지 |
| `17`, `18` | 강도 단계별 감소율 또는 중단값과 적용 기간을 어떻게 정할지 |

승인된 원칙은 mapping comment에 간단히 넣거나 별도 업무 기준을 comment가 가리키게 한다. 근거 없이 임의 수식을 가이드에 확정값으로 넣지 않는다.

현재 DB에는 LiqProd를 가리키는 mapping이 없고 `model_param_id=NULL`, `mapping_method=na`인 placeholder가 남아 있다. event 11·17·18은 comment까지 빈 placeholder가 여러 건이므로 숫자 ID나 행 순서만으로 LiqProd 행을 특정할 수 없다.

원본 이관 이력이 확인되지 않는 placeholder는 임의로 갱신하지 않고, 승인된 Notion 행을 기준으로 **LiqProd 전용 mapping 행을 새로 등록**하는 방식을 기본으로 한다. 특정 placeholder가 LiqProd용이라는 source-row 근거가 있을 때만 그 행을 전환한다.

등록할 공통 값은 다음과 같다.

| DB 컬럼 | 등록 기준 |
|---|---|
| `event_type_l2_id` | Notion의 `2`, `3`, `11`, `17`, `18` 중 승인된 행 |
| `dimension_key`, `dimension_label` | Notion 원문 |
| `mapping_method` | event 11은 `routing`, 나머지는 `direct` |
| `model_param_id` | 대상 DB에서 이름으로 다시 조회한 LiqProd ID |
| `comment` | 보강·승인된 Notion comment 원문 |
| `use_yn` | 준비 중 `N`, 최종 검증 후 `Y` |
| `del_yn` | `N` |

Notion의 `필수/선택`은 DB mapping 테이블에 별도 컬럼으로 저장하지 않는다. 실제 scenario의 dimension template과 `dimension_values`에 해당 key가 있는지 확인하는 업무 기준으로 사용한다.

## 5. Basecase와 실제 LUT 원본

### 5.1 Basecase: Supply 파일은 이미 등록되어 있다

`config.yaml`에는 Supply Basecase 파일이 이미 등록되어 있다.

```yaml
model_parameter_resources:
  basecase:
    supply:
      path: Supply Model_Input.xlsm
      object_storage_path: fundamental_model_artifact/input_template/복호화_(Base) Supply Model_Input.xlsm
```

파라미터마다 별도 Basecase 블록을 추가하지 않는다. `LiqProdAdjustment` sheet를 읽는 행·열 규칙은 Parameter master의 `basecase_*` 컬럼이 정한다.

실제 workbook에는 Country·Plant·Train과 Year·Month header가 있지만 현재 DB가 지정한 첫 G:DA override 영역에서는 생산량 값이 추출되지 않아 값이 있는 Basecase record는 0건이다. 뒤쪽 별도 matrix는 현재 parser가 읽지 않는다. adapter와 metadata 축이 등록되면 첫 영역의 axis-only 행은 위치·metadata 보조에 사용할 수 있지만 `basecaseValue`가 되지는 않는다. 즉 **값 기준은 LUT-only이고 Basecase metadata만 보조될 수 있다.**

같은 slot의 안정적인 metadata가 Basecase와 LUT에 모두 있으면 현재 결합 정책은 Basecase metadata를 우선한다. 따라서 `lutValue`는 raw CSV의 생산능력·이용률로 계산되더라도 최종 표시의 Life Cycle이나 Nameplate Capacity는 workbook 값일 수 있다.

### 5.2 `BCLiquefaction.csv` 실제 구조

LiqProd는 기존 LiqUtil과 같은 파일을 사용한다. 경로의 용도를 구분한다.

```text
Packaged runtime: apps/agents/model_parameter_agent/resources/lut/BCLiquefaction.csv
조사한 사용자 원본: ~/수급모델파라미터/data/LUT/supply/supply_bc/BCLiquefaction.csv
Object Storage key: fundamental_model_artifact/LUT/supply/supply_bc/BCLiquefaction.csv
```

주요 header는 다음과 같다.

| 용도 | Raw CSV header |
|---|---|
| 위치 | `Country`, `Plant Name`, `Plant Train` |
| 시간 | `Year`, `Month`, `Period` |
| 상태 | `Infra Life Cycle` |
| 월 생산능력 | `LNG train capacity (Million tonnes LNG per month)` |
| 이용률 | `LNG plant utilisation %` |

2026-07-22에 확인한 현재 파일의 검증 결과는 다음과 같다. 원본 object가 갱신되면 행 수는 달라질 수 있다.

- 전체 41,103행
- Agent horizon인 2026~2030에 19,366행
- 해당 기간 필수 header 값의 결측 0건
- `Country + Plant + Train + Year + Month` exact key 중복 0건
- 2026, 2027, 2028, 2029, 2030년 모두 존재
- 계산 결과가 0인 행 4,654건, 이용률이 1을 넘는 행 2,159건

## 6. `liq_prod` adapter가 해야 하는 일

### 6.1 기존 `liq_util`을 그대로 쓰면 안 되는 이유

`liq_util`은 같은 CSV를 읽지만 LUT value를 `LNG plant utilisation %`로 만든다. 예를 들어 이용률 `0.999435`는 `0.99943`으로 읽힌다. 이는 LiqProd의 단위인 `Mt LNG/month`가 아니다.

generic `tabular` adapter도 한 숫자 열만 value로 읽으며 두 열을 곱하지 않는다. 따라서 raw CSV를 그대로 사용할 때는 `liq_prod` adapter가 필요하다.

### 6.2 Value 계산

adapter는 다음 두 열을 곱해 LiqProd LUT value를 만든다.

```text
LiqProdAdjustment value (Mt LNG/month)
= LNG train capacity (Million tonnes LNG per month)
  × LNG plant utilisation %
```

CSV header에는 `%`가 들어 있지만 실제 값 `0.95`는 95%를 뜻하는 비율이다. 다시 100으로 나누지 않는다.

실제 한 행의 계산 예시는 다음과 같다.

```text
Country       = Australia
Plant         = Australia Pacific LNG
Train         = Australia Pacific LNG T1
Year / Month  = 2026 / 1
월 생산능력    = 0.375 Mt LNG/month
이용률         = 0.9994350333333334

LiqProd value = 0.375 × 0.9994350333333334
              = 0.3747881375
              = 0.37478  # 현재 5자리 trunc 정책 적용
```

### 6.3 Slot과 metadata 구성

| 구분 | Adapter 결과 |
|---|---|
| Exact key | `Country`, `LNG Plant`, `LNG Plant Train`, `Year`, `Month` |
| `LNG Plant` | raw `Plant Name` |
| `LNG Plant Train` | raw `Plant Train` |
| `Period` | raw `Period` |
| `Life Cycle Category` | raw `Infra Life Cycle` |
| `Nameplate Capacity (MTPA)` | 월 생산능력 × `12` |
| Value | 월 생산능력 × 이용률, `Mt LNG/month` |

추가로 다음 검증을 기존 LiqUtil과 같은 수준으로 수행한다.

- `Infra Life Cycle=Closed` 행 제외
- 공통 horizon 2026~2030만 사용
- Month는 1~12인지 확인
- 필수 위치·상태·숫자 값이 비어 있으면 시작 실패
- 동일 exact key의 값 또는 metadata가 충돌하면 시작 실패
- 현재 정밀도 정책에 따라 value를 소수 5자리에서 trunc
- Nameplate Capacity metadata는 기존 LiqUtil과 같이 월 생산능력 × 12 후 소수 2자리에서 trunc

이용률이 1을 넘는 원본 행도 있으므로 adapter가 이용률을 1로 clamp하거나 계산된 value를 임의로 생산능력 이하로 자르면 안 된다. adapter는 원본 곱셈값을 기준값으로 보존한다. `parameter_hint`와 value rationale은 LLM 제안과 사용자 검토를 유도하지만, 현재 서버가 `0 이상`이나 `월 생산능력 이하` 범위를 강제로 검증하지는 않는다.

기능 구현 범위는 `liq_prod`를 유효한 adapter 이름으로 등록하고, 위 계산을 수행하는 loader를 연결하며, raw header·계산·Closed·horizon·중복·정밀도 테스트를 추가하는 것이다. 새 계산이 기존 runtime cache와 구분되도록 adapter schema version도 갱신한다. 상세 코드를 문서에 복사하지 않고 이 기능 계약을 기준으로 구현·검증한다.

## 7. `config.yaml`과 Object Storage 등록

### 7.1 Adapter 구현 후 추가할 LUT 항목

다음 설정은 `liq_prod` adapter 구현과 테스트가 완료된 뒤 유효하다. 현재 `config.yaml`에 그대로 넣기만 해서는 시작할 수 없다.

```yaml
model_parameter_lut_enabled: true

model_parameter_resources:
  # 기존 basecase와 LUT 항목 유지
  lut:
    # 기존 GDP, PMI, PowerMix, Temperature, LiqUtilAdjustment 유지

    LiqProdAdjustment:
      adapter: liq_prod
      files:
        values:
          path: BCLiquefaction.csv
          object_storage_path: fundamental_model_artifact/LUT/supply/supply_bc/BCLiquefaction.csv
          required_columns:
            - Country
            - Plant Name
            - Plant Train
            - Year
            - Month
            - Period
            - Infra Life Cycle
            - LNG train capacity (Million tonnes LNG per month)
            - LNG plant utilisation %
      key_axes: [Country, LNG Plant, LNG Plant Train, Year, Month]
      metadata_axes:
        - Period
        - Life Cycle Category
        - Nameplate Capacity (MTPA)
```

| YAML 값 | 확인 기준 |
|---|---|
| `LiqProdAdjustment` | DB `parameter_name`과 정확히 같음 |
| `adapter: liq_prod` | 생산능력 × 이용률 계산을 수행하는 신규 adapter |
| `path` | 기존 LiqUtil과 같은 local target |
| `object_storage_path` | 기존 LiqUtil과 같은 공통 bucket 내부 object key |
| `required_columns` | adapter가 실제로 읽는 raw header |
| `key_axes` | Basecase와 같은 business key |
| `metadata_axes` | 최종 slot에 함께 보존할 보조 축 |

LiqUtil과 LiqProd가 같은 local path와 같은 object key를 참조하면 resource manifest는 한 파일로 내려받아 공유한다. 별도의 LiqProd CSV를 복제할 필요가 없다.

`liq_prod`는 custom adapter이므로 `layout`, `axis_columns`, `value_column`을 설정하지 않는다. 같은 local path에 서로 다른 object key를 지정하면 resource 시작 검증이 실패한다.

로컬 실행 설정인 `envs/config.yaml`뿐 아니라 배포 설정을 별도로 관리하는 환경에서는 `devops/k8s/configmap.yaml`의 같은 LUT manifest도 함께 반영한다.

### 7.2 Object Storage에서 load하는 순서

1. 공통 bucket에서 기존 `BCLiquefaction.csv` object의 exact key를 확인한다.
2. LiqProd config도 같은 `object_storage_path`를 가리키게 한다.
3. 애플리케이션 시작 시 같은 config fingerprint의 유효한 `current` release가 있으면 local cache를 먼저 재사용한다.
4. 재사용할 release가 없으면 원격 object를 `HEAD → GET → HEAD` 순서로 검증해 `lut/BCLiquefaction.csv`를 준비한다.
5. `liq_prod` adapter가 header, horizon, 숫자, exact key와 계산 결과를 검증한다.
6. LiqUtil과 LiqProd catalog가 모두 성공해야 새 resource release를 `current`로 전환한다.

파일별 Access Key나 Secret Key는 LUT 항목에 넣지 않는다. 공통 `model_parameter_resource_storage` 설정과 환경변수를 사용한다.

## 8. 검증과 활성화 기준

일반 runtime은 `use_yn=N`인 master를 후보로 읽지 않는다. adapter와 LUT 시작 검증을 먼저 끝내고, 비운영 환경에서 master와 mapping을 함께 임시 활성화해 proposal·confirmation을 검증한 뒤 운영에서 함께 활성화한다.

| 단계 | 성공 기준 |
|---|---|
| Adapter 단위 테스트 | 실제 sample에서 `0.375 × 0.999435... = 0.37478` |
| LUT startup | horizon record가 1건 이상이고 중복·결측 오류 없음. 같은 2026-07-22 파일이면 19,366건 |
| Basecase/LUT 결합 | 값이 있는 Basecase record가 0건이어도 axis-only metadata와 LUT slot·기준값 결합 |
| DB 조회 | LiqProd master와 승인된 mapping이 `use_yn=Y`, `del_yn=N` |
| Direct mapping | event 2·3·17·18 각각 테스트. event 2·17·18은 LiqUtil과 LiqProd가 함께 다음 단계로 들어가는지 확인 |
| Event 11 routing | 수출·액화 시설의 큰 생산량 차질이면 LiqProd, 단기·부분 차질이면 LiqUtil 선택 |
| Step2 | 실제 LUT에 있는 Train·Year·Month exact slot만 선택 |
| Step3 | `Mt LNG/month` 절대 생산량과 slot별 근거 생성 |
| 동기 API 결과 | `Supply / LiqProdAdjustment / table1`, `basecaseValue=null`, 생산량 단위 `lutValue` 존재 |
| Confirmation | 동기 응답의 `lutValue`는 제외하고 기존 confirmation schema만 전송 |

최종 `slotAxesFieldNames`는 `Country`, `LNG Plant`, `LNG Plant Train`, `Year`, `Month`, `Period`, `Life Cycle Category`, `Nameplate Capacity (MTPA)` 8개를 유지한다.

파라미터 근거는 “왜 이 scenario에 LiqProd를 선택했는가”를 설명하고, slot별 value 근거는 “왜 이 Train·월에 이 생산량을 제안했는가”를 설명한다. 전자는 보강된 mapping comment와 scenario dimension을 중심으로, 후자는 LUT 기준 생산량·차질 강도·기간·회복 패턴을 중심으로 생성되어야 한다.

## 9. 대량 LUT와 token 절약

현재 파일의 19,366개 LUT record 전체를 그대로 prompt에 넣지 않는다. Step2에서 서버가 exact slot을 compact catalog로 만들고, LLM은 `candidate_key`와 필요한 `slot_axes`만 반환한다. 서버가 이 좌표를 실제 catalog와 exact 검증한 뒤 `slot-1` 같은 요청 내부용 key를 발급한다.

Step3 값 제안 prompt에는 선택된 slot, 서버가 발급한 `slot_key`, 좌표와 단일 기준값만 전달한다. 값 제안 응답은 전체 slot 객체를 반복하지 않고 `candidate_key + slot_key + proposed_value`를 중심으로 반환하며, 서버가 보관한 좌표·기준값과 다시 결합한다. 현재 설정상 한 파라미터의 최대 slot은 100개다.

## 10. 최종 체크리스트

- [ ] Notion의 LiqProd 관련 5건과 `미대상` 상태를 확인했다.
- [ ] 실제 사용할 mapping의 대상 전환 승인을 받았다.
- [ ] event 2·3·17·18은 direct로 유지하고 동시 후보 동작을 수용하기로 확인했다.
- [ ] `parameter_hint`에 절대 생산량, 단위, 범위, LiqUtil과의 차이를 간결하게 보강했다.
- [ ] mapping comment 5건의 적용·산정 원칙을 보강해 Notion에서 승인했다.
- [ ] 대상 DB에서 `LiqProdAdjustment` ID를 이름으로 다시 조회했다.
- [ ] source-row 근거 없이 기존 `na` placeholder ID를 추측해 갱신하지 않았다.
- [ ] 기존 `BCLiquefaction.csv`를 공유하고 `liq_prod`가 월 생산능력 × 이용률을 계산한다.
- [ ] 이용률을 다시 100으로 나누거나 1로 clamp하지 않는다.
- [ ] key·metadata axes가 LiqUtil/Basecase와 일치한다.
- [ ] 2026~2030 record가 1건 이상이고 exact key 중복·필수 값 결측이 0건임을 확인했다. 같은 기준 파일이면 19,366건이다.
- [ ] 기존 설정을 보존하고 실행·배포 설정에 LiqProd 블록만 추가했다.
- [ ] LUT startup과 비운영 검증을 통과한 뒤 master와 mapping을 활성화했다.
- [ ] LUT-only 결과에서 `basecaseValue=null`과 `Mt LNG/month` 기준 `lutValue`를 확인했다.
- [ ] event 2·3·11·17·18을 각각 proposal과 confirmation까지 검증했다.
- [ ] parameter rationale과 slot별 value rationale이 서로 다른 목적에 맞게 생성되는지 확인했다.

관련 구조는 [DB 문서](03_MODEL_PARAMETER_AGENT_DB_SPEC.md), [Basecase/LUT 문서](05_MODEL_PARAMETER_AGENT_BASECASE_LUT_PARSING.md), 실제 제안 단계와 prompt는 [Flow 문서](04_MODEL_PARAMETER_AGENT_FLOW.md)를 참고한다.
