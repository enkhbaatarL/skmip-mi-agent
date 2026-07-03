# 수급모델 파라미터 제안 Agent Flow (Claude Draft v2)

> Claude가 `apps/agents/model_parameter_agent` 소스와
> `tests/test_model_parameter_agent_contract.py`를 직접 읽고 독립 작성한 리뷰용 초안입니다.
> 소스 코드를 진실의 원천으로 삼았으며, 직접 확인하지 못한 부분은 "추정"으로 표기했습니다.

## 1. 목적

`model_parameter_agent`는 **`scenario_id` 하나**만 받아, 해당 시나리오의 이벤트·Dimension
맥락을 DB에서 조회하고, 두 가지 Excel 지식베이스(Dimension↔Parameter 매핑 XLSX,
LNG 수급모델 Basecase 입력시트)를 근거로 Demand/Supply/Trade 모델의 input parameter
조정안을 제안한다.

- 입력: `POST /model-parameters/scenarios/{scenario_id}/proposals` (body 없음, path param만)
- 출력: `ProposeParametersOut` = `scenario_id` + `recommendations[]` (selected 항목만)
- **결과는 영속화하지 않는다.** (read-only — persistence 레이어에 add/commit/insert/update/delete 금지, 테스트로 강제)

## 2. 전체 Flow

```mermaid
flowchart TD
    A[POST .../scenarios/{scenario_id}/proposals] --> B[to_state: scenario_id 검증 + 옵션 기본값]
    B --> C[load_scenario_context\nModelInputService.load_context]
    C --> D[select_parameter_candidates\nXLSX bridge 룰 매칭]
    D --> E[validate_parameter_candidates\nStep1.5 LLM gate + routing 보정]
    E --> F[load_basecase_samples\n실제로는 build_basecase_records 호출]
    F --> G[propose_parameter_slots\nStep2 LLM: 축만 결정]
    G --> H[filter_basecase_records_by_slots\n선택 slot과 일치하는 record만]
    H --> I[propose_parameter_values\nStep3 LLM: value_grid 산정]
    I --> J[to_output\nselected adjustment를 추천 JSON으로 그룹화]

    D -. "event_type_l2_id ∈ {6,10}" .-> K[candidate_mappings=[] 반환]
    J -. "event_type_l2_id ∈ {6,10}" .-> L[recommendations=[] 반환]
```

> 그래프는 **조건 분기 없는 선형 그래프**(`build_graph`의 7개 노드 + 단방향 edge)다.
> 억제 이벤트 타입(6, 10)은 별도 분기 노드가 아니라 `select_parameter_candidates`가 빈
> 후보를 반환하고 `to_output`이 다시 한번 `recommendations=[]`로 막는 **이중 차단**으로 구현된다.
> 후보가 비면 이후 LLM 노드들은 각자 early-return 한다.

## 3. 단계별 핵심 로직

1. **`to_state` (RunnableLambda)**
   - `scenario_id` 누락 시 `MIBaseError(INVALID_REQUEST)`. 나머지 body는 `ProposeParametersIn`으로
     검증 후 상태에 병합. (API는 현재 body를 노출하지 않으므로 옵션은 기본값으로 들어옴 — 추정상 내부/테스트용 경로.)

2. **`load_scenario_context`**
   - `ModelInputService().load_context(scenario_id)`로 scenario / scenario_group / event /
     event_type / dimension_template를 읽어 `scenario_context`에 적재. (read-only)

3. **`select_parameter_candidates` (Step1, 룰 기반)**
   - `event_type_l2_id ∈ {6,10}`이면 즉시 `candidate_mappings=[]` + 정책 warning 반환.
   - `get_parameter_knowledge_base(...)`(`lru_cache(maxsize=8)`)로 매핑 KB 로드.
   - `match_parameter_candidates`: `event_type_l2_id`가 같고 시나리오 dimension_key가 있는
     bridge 룰만 본다. `mapping_method ∈ {direct, routing}`이며 Parameter Excel Mapping에
     모델 target(file/sheet/canonical)이 있는 항목만 후보. 그 외는 `non_input_items`로 분리.
   - `candidate_key`는 `event_type_l2_id|dimension_key|canonical|model_file|model_sheet`를
     정규화해 조합한 결정적 키.

4. **`validate_parameter_candidates` (Step1.5, LLM gate)**
   - 후보가 없으면 그대로 통과. 있으면 LLM에 `candidate_decisions`(selected 여부)만 요청.
   - `_sanitize_candidate_decisions`: 알 수 없는 key·중복·누락 key 제거, selected=true만 유지.
   - `_apply_routing_comment_overrides`: routing 후보는 bridge sheet의 routing comment가
     DB dimension 값과 토큰 단위로 명확히 일치하면 LLM 판단을 **deterministic하게 보정**
     (일치 후보 강제 selected, 같은 그룹 비일치 후보 강제 deselect).

5. **`load_basecase_samples` (이름 ≠ 동작)**
   - 실제로는 `build_basecase_records`를 호출해 매핑 시트에서 평탄한 record를 추출.
   - 추출 모드 3종: `fixed_columns`(고정 열), `matrix_time_columns`(축 열 + 시간 열 행렬),
     명시 spec이 없으면 헤더 스캔으로 **자동 matrix block 탐지**(Base Case 영역 우선).
   - 각 record: `axes`(Country/Plant/Year/Month/Period 등), `value`, `value_name`, `unit`,
     `reference_id`, `source_row/col`, `candidate_key`.

6. **`propose_parameter_slots` (Step2, LLM)**
   - LLM에는 raw record 대신 `basecase_slot_options`(candidate별 축 이름·distinct 축값·value_name)만 전달.
   - LLM은 국가/시설/기간/route 등 **모델 input 좌표(축)만** 선택, 값은 산정하지 않음.
   - `_sanitize_llm_slots`: 모호 토큰(미정/후보/추정/`?`/"또는"/세미콜론 결합/미변환 "향후" 등)이
     있으면 `selected=false`, `slot_axes=[]`, `needs_user_review=true`로 보정.

7. **`filter_basecase_records_by_slots`**
   - selected slot의 축값과 일치하는 record만 남김. 매칭은 record의 axes에 존재하는 slot 축을
     정규화 비교하며, **최소 1개 축이라도 일치 비교가 일어나야** 통과(`matched_axis_count > 0`).

8. **`propose_parameter_values` (Step3, LLM)**
   - slot이 없으면 early-return. 있으면 filtered record + slot을 packet에 넣어 LLM에 value_grid 요청.
   - `_sanitize_llm_adjustments`: model_file/sheet/parameter_name은 후보 값으로 **강제 덮어쓰기**
     (LLM이 지어낸 이름 무시). slot 미확정/모호 좌표/`proposed_value=null`/`operation ∈ {unknown,
     not_applicable}` cell 제거, 유효 cell이 없으면 `selected=false`. 응답에서 누락된 candidate_key는
     서버가 `selected=false` 검토 항목으로 보강. `basecase_reference_ids`로 basecase_value 역참조 보강.

9. **`to_output` (RunnableLambda)**
   - 억제 이벤트면 `recommendations=[]`.
   - 아니면 `_build_recommendations`: selected adjustment를 `(model_file, model_sheet,
     parameter_name)`로 그룹화, value cell을 dedup(동일 좌표/값 병합·rationale 합치기), `axis_fields`·
     `value_fields` 집계. **출력 단계에서도** `proposed_value None` 및 `operation ∈ {unknown,
     not_applicable}` cell을 다시 제외(sanitizer와 이중 방어). 값이 하나도 없는 그룹은 제외.

## 4. LLM 호출 규약

- 호출 지점: Step1.5(검증) / Step2(slot) / Step3(value) — 총 3회.
- 공통: `invoke_llm_structured_output`, `preference=ModelPreference.QUALITY`,
  `temperature=0.0`, `max_retries=2`, 스키마 강제 structured output.
- 시스템 프롬프트는 "후보 밖 parameter/workbook/sheet/candidate_key 생성 금지"를 반복 명시.

## 5. 가드레일

- **억제 이벤트 타입**: `event_type_l2_id ∈ {6, 10}`은 후보 단계와 출력 단계 양쪽에서 차단.
- **후보 범위 봉인**: candidate_mappings의 `candidate_key`·model target 밖 항목은 프롬프트와
  sanitizer 양쪽에서 차단. Step3는 LLM의 model_file/sheet/name을 후보 값으로 덮어씀.
- **모호값 차단**: `AMBIGUOUS_AXIS_TOKENS` / 다중값 결합 마커 / 미변환 기간 표현을 slot·coordinate
  양쪽에서 검사 → 검토 필요로 강등.
- **LLM 실패 처리**: 기본 `allow_llm_fallback=False`이면 예외 전파. `True`일 때만 rule-based
  fallback(낮은 confidence·needs_user_review)을 생성.
- **read-only**: persistence는 select 전용. 제안 결과 저장 없음.
- **결정성 보정**: routing 후보는 bridge comment 매칭으로 LLM 판단을 덮어쓸 수 있음.

## 6. 계약(테스트로 보증되는 항목, 요약)

- 그래프에 7개 노드 등록, 엔드포인트는 `scenario_id` path param만 요구(body 없음).
- 옵션 스키마는 camelCase 허용(`maxCandidates` 등).
- bridge 매핑은 event_type_l2_id + dimension_key 기준, 키가 없으면 fallback 없이 빈 결과 + warning.
- routing 다중 target 보존, direct지만 target 없으면 non_input.
- Basecase record 추출 3모드 + 자동 block 탐지(두 번째 섹션·#REF! 행 회피) 동작.
- 억제 이벤트는 recommendations=[]; null/unknown operation 값은 출력에서 제외.
- LLM sanitizer가 모호 축·좌표·null·unknown operation을 일관되게 강등.

## 7. 불확실/추정 항목

- `ModelInputService.load_context`의 정확한 SQL/repository 동작은 본 초안에서 직접 확인하지 않음
  (스키마와 packet 키로 역추정). read-only 계약만 테스트로 확인.
- API가 body 옵션을 노출하지 않으므로 `mapping_excel_path` 등 상태 옵션은 실서비스 경로에서
  기본값으로 고정 — 옵션 주입 경로는 테스트/내부용으로 추정.
