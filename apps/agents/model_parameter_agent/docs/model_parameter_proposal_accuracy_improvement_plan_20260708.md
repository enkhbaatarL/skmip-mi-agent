# 수급모델 파라미터 제안 Agent — slot/value 정확도 개선 계획

- 작성일: 2026-07-08
- 기준 테스트: `tests/reports/model_parameter_agent/model_parameter_proposal_evaluation_parameters_GDP_PMI_PowerMix_Temperature_LiqUtilAdjustment_20260708_015111.md`
- 대상 파라미터 (1차 오픈): GDP, PMI, PowerMix, Temperature, LiqUtilAdjustment
- 결정 방식: 개선사항별 인터뷰로 개선 여부/방향 확정 (2026-07-08)
- 크로스 검증: Codex 읽기 전용 fact-check 완료 (2026-07-08) — 4개 구현 항목(A2/A4/B1/B4) 진단·수정 지점 모두 MATCHES 판정. 지적된 보완/잔여 리스크는 각 항목에 반영됨

---

## 1. 결정 요약

| ID | 이슈 | 결정 | 방식 |
|---|---|---|---|
| A1 | basecase에 없는 slot 좌표 제안 (예: PMI에 United States) | **개선 안 함** | 모델이 LUT 지원 국가 범위에서 신규 행을 받을 수 있다는 전제 유지 |
| A2 | 과거 월 좌표 제안 (2026-07 실행 시점에 2026-03 제안) | **개선** | 프롬프트 규칙만 수정 (코드 reject 없음) |
| A3 | Step2 slot 0개 시 전체 INVALID_REQUEST 에러 | **개선 안 함** | 현행 유지 (slot 0개 = 실패) |
| A4 | routing 후보 선정 개수 제어 | **개선** | routing 후보 dimension당 **최소 1개, 최대 2개** 선택. na comment는 현행대로 후보 판단에 사용하지 않음 |
| B1 | basecase 부재 시 타국 값 수준(level) 앵커링 | **개선** | Step3 프롬프트 규칙 좁히기 (형식만 참고, 수준 참조 금지) |
| B2 | dimension enum → 조정폭 기준표 | **개선 안 함** | LLM 재량 유지 |
| B3 | proposedValue 범위/단위 착오 검증 | **개선** | hint에 허용범위 명시만 (DB 컬럼/코드 검증 없음) |
| B4 | 좌표 불일치 참고값이 basecaseValue에 list로 저장 | **개선** | 좌표 정확 매칭 1건일 때만 scalar, 그 외 null (참고값 필드 추가 없음) |
| B5 | Step3.5 경량 verify LLM 호출 | **보류** | 운영 데이터에서 방향 오류 관찰 시 재검토 |
| C | hint/comment 내용 보강 | **문안만 작성** | DB 반영은 도메인 담당자가 별도 진행. v0.4 매핑 엑셀 `Parameter Excel Mapping (모델파트)` 시트의 `basecase_column_roles_detail` 내용 활용 |

---

## 2. 구현 항목 상세

### A2. 과거 좌표 — 프롬프트 규칙 수정

**문제**: scenario 289에서 실행 시점(2026-07)보다 과거인 `Year 2026, Month 3` Temperature 좌표를 제안. 원인은 `period_resolution_policy` 및 Step2/Step3 프롬프트의 "명시 연월은 현재 기준월과 무관하게 그대로 사용" 규칙.

**수정 대상**:

1. `apps/agents/model_parameter_agent/flows/propose_parameters/nodes.py` — `_period_resolution_policy()` (약 2076행) rules 목록:
   - 기존 1번 규칙 "연월이 명확하면 현재 기준월과 무관하게 그대로 사용" 을
     "연월이 명확하고 **현재 연월 이후이면** 그대로 사용" 으로 변경.
   - 규칙 추가: "명시 연월이 current_year/current_month보다 **과거이면 그대로 입력하지 말고**, 시나리오 전개 기간(현재 이후)으로 재해석합니다. 재해석 시 사건·시나리오의 계절/월 맥락이 좌표 의미에 중요하면 현재 이후 가장 가까운 동일 계절/월로 이월하고, 그렇지 않으면 현재 이후부터 전개합니다." (파라미터 유형을 명시하지 않고 사건 맥락 기준으로 일반화 — 특정 파라미터 하드코딩 회피)
2. `apps/agents/model_parameter_agent/prompts/model_parameter_proposal.py`
   - `SLOT_PROPOSAL_SYSTEM` 내 "`YYYY-MM`, `YYYY년 M월`, `occurred_at`처럼 연월이 명확하면 현재 기준월과 무관하게 그대로 사용합니다." 줄을 위 정책과 일치하게 수정.
   - `VALUE_PROPOSAL_SYSTEM` 내 "명시 연월은 현재 기준월과 무관하게 그대로 사용합니다." 줄 동일 수정.

**검증**: 겨울 한파(event_type 6) 시나리오 재실행 시 과거 월 좌표가 나오지 않고, 미래 동절기 월로 제안되는지 확인.

**수용된 잔여 리스크 (Codex 검증)**: 프롬프트만 수정하므로 LLM이 규칙을 무시하면 과거 좌표가 통과할 수 있음(`_coordinate_issues()`는 모호어/월 범위만 검사, nodes.py:1381). 또한 `date.today()`(nodes.py:2071)가 타임존 미지정이라 월 경계 동작이 서버 런타임 타임존에 의존.

### A4. routing 후보 최소 1개·최대 2개

**문제**: routing 후보가 있는 dimension에서 간혹 후보 전체가 선택됨. 배제 로직(na comment 참조)은 도입하지 않기로 확정 — na comment는 기존대로 후보 판단에 사용하지 않음.

**수정 대상**:

1. `prompts/model_parameter_proposal.py` — `CANDIDATE_VALIDATION_SYSTEM` 판단 기준:
   - 기존: "해당 dimension의 routing 후보 중 최소 1개는 반드시 selected=true"
   - 변경: "해당 dimension의 routing 후보 중 **최소 1개, 최대 2개**를 selected=true로 선택하십시오. 가장 적합한 후보 순으로 고르고, 세 개 이상을 selected=true로 반환하지 마십시오."
   - 기존 "복수 parameter가 실제로 동시에 필요하면 복수 선택할 수 있습니다" 문구에 "(최대 2개)" 제약 반영.
2. `flows/propose_parameters/nodes.py` — 서버측 보정(결정적 안전장치):
   - 삽입 위치는 반드시 **`_apply_routing_comment_overrides()` 이후, `_merge_candidates_by_parameter()` 이전** (`validate_parameter_candidates` 내 nodes.py:195-199 구간). 사유(Codex 검증):
     - `_apply_routing_comment_overrides()`(nodes.py:1763)가 sanitize 이후에 routing 후보를 **추가**할 수 있어, sanitize 직후에 cap을 걸면 불충분.
     - `_merge_candidates_by_parameter()`(nodes.py:777)는 병합 시 `dimension_key`를 비우고 `mapping_method`를 "merged"로 바꾸므로, merge 이후에는 dimension별 routing 식별이 불가.
   - 초과분 보정 우선순위: (1) `_apply_routing_comment_overrides`의 comment 매칭 후보 우선 유지, (2) **원본 candidate 순서**(Step1 rule 순서) 기준으로 앞선 후보 유지. LLM 응답 순서는 sanitize 단계(nodes.py:1682)에서 원본 candidate 순서로 재정렬되어 보존되지 않으므로 tie-breaker로 사용 불가.
   - 초과분은 selected=false 보정 + warning 기록.
   - dimension 그룹 키는 기존 `_apply_routing_comment_overrides`와 동일하게 `(event_type_l2_id, dimension_key)` 사용.

**검증**: routing 매핑이 3개 이상인 event_type(예: 19 impact_intensity — PowerMix 외 라우팅 후보들)에서 selected routing 후보가 dimension당 2개 이하인지 확인.

### B1. 타국 값 앵커링 차단 — Step3 프롬프트 규칙 좁히기

**문제**: 미국 7월 PMI를 China 49.5 기준으로 49.4 산정, 미국 3월 기온을 유럽국 값 평균 수준(≈5.5°C) 기준으로 3.0 산정. 원인은 `VALUE_PROPOSAL_SYSTEM`의 "다른 slot 값들을 값의 **범위**·단위·스케일·소수 자리·형식 참고용으로 사용해 보수적인 **기준값을 잡은 뒤**…" 규칙이 수준(level)까지 참고하게 만듦.

**수정 대상**: `prompts/model_parameter_proposal.py` — `VALUE_PROPOSAL_SYSTEM`의 basecase 부재 처리 규칙(약 350~354행):

- 기존: "basecase_value_groups에 있는 같은 parameter의 다른 slot 값들을 값의 범위·단위·스케일·소수 자리·형식 참고용으로만 사용해 보수적인 기준값을 잡은 뒤 … proposed_value를 산정하십시오."
- 변경(요지):
  - 다른 slot 값은 **단위·스케일·소수 형식** 확인용으로만 사용한다. "범위" 문구 삭제.
  - **다른 국가/시설/좌표의 값을 현재 slot의 수치 수준(level) 기준값으로 삼지 말 것**을 명시.
  - 국가·시설별 절대 수준이 서로 다른 파라미터(PMI 지수, 기온, 발전 비중 등)는 타 좌표 값 기반 기준값 산정을 금지하고, scenario/event/dimension과 parameter_hint의 도메인 지식 범위에서 해당 좌표 자체의 타당한 값을 산정한다. 근거가 부족하면 rationale에 불확실성을 명시한다.
- 연관 규칙 "no-change/neutral이면 다른 slot들의 범위와 형식을 참고한 보수적 유지값을 사용" 도 동일 원칙으로 수정.

**검증**: PMI(미국 등 basecase 부재 국가) 케이스 재실행 시 rationale에 "China 값 기준" 류 표현이 사라지고, 해당 국가 자체 기준으로 산정하거나 불확실성이 명시되는지 확인.

**수용된 잔여 리스크 (Codex 검증)**: Step3 payload에는 여전히 candidate 전체의 `basecase_value_groups`가 전달됨 — `_filter_records_by_selected_slots()`는 record 수가 100 이하면 전체 통과, 초과 시 prefix 매칭 fallback(nodes.py:1476, 1511). 프롬프트 수준 차단이므로 payload 수준 차단이 필요해지면 이 필터를 후속 조정.

### B4. basecaseValue scalar화 (참고값 버림)

**문제**: `_patch_basecase_value()`(nodes.py 약 2193행)가 LLM의 `basecase_reference_ids` 값을 그대로 채우면서, (1) 좌표가 일치하지 않는 타국 record 값이 basecaseValue로 위장되고, (2) 매칭 여러 건이면 list가 저장됨 (예: 미국 3월 cell에 `[4.9, 6.4, 6.7]` = 독일/네덜란드/벨기에 3월 기온).

**수정 대상**: `flows/propose_parameters/nodes.py` — `_patch_basecase_value()`:

1. reference record의 `axes`가 cell `coordinates`와 **정확히 일치**하는 경우만 basecaseValue 채움 대상으로 인정.
   - 비교는 기존 `_normalize_axis_value()` 정규화 기준 재사용 (Year/Month int 캐스팅 포함).
   - record axes가 cell coordinates의 부분집합인 경우(시간축만 매칭 등)는 불일치로 간주.
2. 일치 record가 **정확히 1건**이면 scalar로 채우고, 0건 또는 2건 이상이면 `basecase_value=null` 유지.
3. list를 만드는 분기(`matched_values[0] if len(...)==1 else matched_values`) 제거.
4. 좌표 불일치 reference가 버려진 경우 validation_warnings에 기록 (예: "참고 record 좌표가 cell 좌표와 불일치하여 basecaseValue를 채우지 않았습니다").
   - 주의(Codex 검증): 현재 `_patch_basecase_value()`는 warning을 반환하지 않고 호출부(`_sanitize_llm_adjustments`, nodes.py:2009)도 cell만 append하므로, **warning 반환 경로를 함수 시그니처에 추가**해야 함 (예: `tuple[ParameterValueCell, str | None]` 반환 또는 호출부에서 좌표 검증 수행).

**참고**: `basecase_reference_ids` 필드 자체는 유지 (rationale 추적용). 별도 referenceValues 필드는 추가하지 않기로 확정.

**추가 확인 사항 (Codex 검증)**: scalar 강제는 서버 로직에서만 이루어지며 스키마/DB 레벨 방어는 없음 — `basecase_value: Any`(schemas/model_parameter_proposal.py:49), DB는 top-level JSON array 여부만 검사(apps/persistence/model_parameter/models.py:35), confirm 플로우 검증도 존재 여부만 확인(confirm_parameters/validation.py:277). 이번 범위에서는 서버 로직 수정으로 충분하나, 스키마 타입을 `float | int | None`으로 좁히는 것을 후속 과제로 검토.

**검증**: DB `tmm_mi_model_param_proposal_m.proposal_parameters`에서 `basecaseValue`가 항상 scalar 또는 null인지 확인. Temperature 미국 케이스 재실행 시 `basecaseValue: null`이 되는지 확인.

### B3. 허용범위 — hint 문안에 포함 (3절 참조)

DB 컬럼·코드 검증은 도입하지 않음. 3절 hint 문안의 "허용범위" 항목으로만 대응.

---

## 3. hint/comment 개선 문안 (C — DB 반영은 도메인 담당자 별도 진행)

### 3.1 작성 원칙

`tmm_mi_model_param_m.parameter_hint` (varchar 500) 표준 구성:

1. 입력값 의미 + 단위/스케일/형식 (예시값 포함)
2. 허용범위 (B3 대응)
3. 대상 좌표 제약 (지원 국가/시설의 출처, 신규 행 가능 여부)
4. 다른 파라미터와의 우선/충돌 관계
5. 변경 불필요 시 basecase 유지 원칙

출처: 아래 문안은 `resources/mapping/260702_시나리오가정_MI수급모델_input_매핑_모델파트수정_v0.4.xlsx` → `Parameter Excel Mapping (모델파트)` 시트의 `basecase_column_roles_detail` 컬럼(수급모델 파트 제공 설명)을 반영해 작성함.

### 3.2 parameter_hint 제안 문안 (5개)

**GDP** (현행: "Country/year real GDP change rate (% change +/-)")

> 국가·연도별 실질 GDP 전년 대비 성장률(% change, 소수 입력: 0.042=4.2%). 모델은 % change 입력 시 2023 base GDP부터 누적 implied GDP를 계산해 사용. 통상 범위 -0.10~+0.10. 대상 국가는 모델 General LUT 기준. 1년 미만 단기 이벤트는 연간 성장 경로를 바꾸지 말고 basecase 유지가 원칙이며, 구조적·장기 변화일 때만 조정.

**PMI** (현행: "Country/year-month PMI index value")

> 국가·월별 제조업 PMI 지수 절대값(예: 49.5, 기준선 50). 통상 범위 35~65. 국가별 절대 수준이 달라 **타국 값을 기준으로 새 국가 값을 산정하지 말 것**. 단기 심리 충격 ±0.3~1p, 강한 충격 ±2~4p 수준. 구조적 장기 변화는 GDP 경로를 우선 검토.
>
> ※ 모델파트 detail 미제공 파라미터 — 지원 국가 범위(basecase는 현재 China/Philippines만 존재)와 신규 국가 행 허용 여부를 모델파트에 확인 후 문구 확정 필요.

**PowerMix** (현행: "Country/year/energy-source generation share (%; source shares sum to 100%)")

> 국가·연도·에너지원별 전체 발전량 중 비중(소수, 0.32=32%). 허용 에너지원은 Liquids/Hydro/Solar/Wind/Bioenergy/Gas/Coal/Nuclear/Geothermal/Other 10종(POWERMIXLOGIC_ENERGY_SOURCES). 모든 에너지원을 입력하는 경우 합계가 100%가 되어야 하며, 일부 에너지원만 조정할 때는 나머지 비중과의 정합을 rationale에 명시. 대상 국가는 모델 General LUT 기준. 통상 조정폭 ±0.005~0.03.

**Temperature** (현행: "Country/year-month temperature value (°C)")

> 국가·월별 평균 기온(°C) 절대값. basecase 기온은 별도 LUT 없이 HDD/CDD에서 역산됨(HDD>0이면 18−HDD/30, CDD>0이면 18+CDD/30, 그 외 18). 국가별 기후가 달라 **타국 값을 기준값으로 삼지 말 것**. 한파/폭염 강도에 따라 평년 대비 편차를 월별 차등 적용. **과거 월은 입력하지 말고 예측 대상 기간(현재 이후)의 해당 계절 월에 적용**. 대상 국가는 모델 General LUT 기준.

**LiqUtilAdjustment** (현행: "Train/month liquefaction utilization ratio (0-1; 1.0 = 100%)")

> LNG Plant Train·월별 액화 가동률(0~1 소수, 1.0=100%). **100 같은 percent 표기 입력 금지(10000%로 해석됨)**. 1.0 초과는 코드상 차단되지 않으나 100% 초과 가동이므로 명확한 근거가 있을 때만 제안. 값이 있으면 생산량 = nameplate capacity × 가동률로 계산되고, 같은 Train/월에 LiqProdAdjustment 값이 있으면 그쪽이 우선 적용됨. **Base Case(BCLiquefaction.csv)에 존재하는 Plant Train만 수정 가능하며 신규 Train/Plant는 기준정보 정비가 선행 필요**. 대체 배분 시 잔여 여력(1.0−현재 가동률) 기준으로 차등 배분하고 이미 고가동인 설비는 제외.

### 3.3 dimension_map.comment 보강 문안 (주요 row)

comment 작성 규칙: ① 선택 조건을 구체 술어로, ② 배분/조정 원칙은 판단 기준을 수치·수식으로, ③ 기간-파라미터 관계 명시. (na comment의 배제 조건 활용은 A4 결정에 따라 도입하지 않음)

| event_type | dimension | 현행 comment | 보강 제안 |
|---|---|---|---|
| 2 | alt_lng_supply_availability | "…잔여 액화 가동 여력에 배분하고, 이미 고가동 설비는 배분 제외" | "잔여 여력 = 1.0 − 현재 가동률 기준 비례 배분. 가동률 0.9 이상 Train은 배분 제외. Life Cycle Category가 운영 중인 Train만 대상" |
| 5 | capacity_change_scale | "발전부문 가스 비중 조정(capa GW→비중 환산)" | "capa 변화(GW)를 해당 국가 전체 발전량 대비 비중 변화로 환산해 Gas 비중에 반영. 환산 근거(용량, 이용률 가정)를 rationale에 명시" |
| 6/7 | cold_wave_intensity / heatwave_intensity | "…강도에 따라 평년 대비 온도 편차를 월별로 차등 적용" | "적용 월은 현재 이후 동절기(11~3월)/하절기(6~9월)로 한정. 과거 발생 월을 그대로 입력하지 말 것" |
| 17/18 | demand_response_alternative_lng | "타 공급국 상향으로 상쇄" / "대체 공급 형성 time delay 존재" | "부족 물량 중 대체 가능분만 잔여 여력 보유 공급국 Train에 배분. 대체 공급 형성까지 1~3개월 지연을 반영해 시작 월을 늦출 것" |
| 21 | economic_intensity (GDP) | "장기·구조적 경기 변화는 GDP 경로 조정, 일시적 충격은 PMI 우선" | (양호 — 유지) 말미에 "기간 1년 미만이면 GDP는 basecase 유지" 추가 |

---

## 4. 개선하지 않기로 한 항목 (기록)

| ID | 내용 | 사유/전제 |
|---|---|---|
| A1 | basecase 부재 slot 코드 검증 (slot_policy) | 모델이 General LUT 지원 국가 범위에서 신규 행을 수용한다는 전제. 단, LiqUtilAdjustment는 모델파트 detail상 "Base Case 존재 Train만 수정 가능"이므로 hint 문안(3.2)으로 대응 |
| A3 | slot 0개의 "조정 불필요" 정상 응답화 | 현행 에러 처리 유지 |
| B2 | dimension enum별 조정폭 기준표 | LLM 재량 유지. 시나리오 간 차등 검증(그룹 테스트)으로 충분 |
| B5 | Step3.5 verify LLM 호출 | 보류. 운영에서 방향/단위 오류 사례 관찰 시 재검토 |

---

## 5. 구현 순서 제안 (실제 구현은 별도 진행)

1. **B4** basecaseValue scalar화 — 단일 함수 수정, 회귀 위험 최소. 데이터 계약 이슈라 최우선
2. **B1** Step3 프롬프트 앵커링 차단 — 프롬프트 수정
3. **A2** 과거 좌표 프롬프트 규칙 — 프롬프트 + `_period_resolution_policy()` 문구 수정
4. **A4** routing 최소 1·최대 2 — 프롬프트 수정 + 서버 보정 로직 추가
5. **C** hint/comment 문안 → 도메인 담당자 검토 후 DB UPDATE (별도)

구현 후 검증: `model-parameter-agent-test` 스킬로 동일 5개 파라미터 × 14개 event_type 재실행하여 본 리포트와 비교 (특히 scenario 289 Temperature, 305 PMI, event 19 routing 케이스).
