# 수급모델 Input Parameter 제안 기능 분석 (Draft)

> Codex와 Claude가 공동으로 소스 코드를 분석·작성한 초안입니다.
> 저장소 코드(`apps/agents/model_parameter_agent`, `tests/test_model_parameter_agent_contract.py`)를 사실 근거로 삼았습니다.

## 1. 기능 목적

`model_parameter_agent`는 **하나의 시나리오(scenario_id)** 를 입력받아, 해당 시나리오/이벤트 맥락에 맞는
**LNG 수급모델(Demand/Supply/Trade) Input Parameter 조정값을 제안**하는 LangGraph 기반 에이전트입니다.

- DB에서 시나리오·이벤트·Dimension 맥락을 조회하고,
- 매핑 XLSX(어떤 dimension이 어떤 모델 parameter로 연결되는지)와
  Basecase 입력시트(운영 중인 실제 기준값)를 근거로,
- LLM이 단계별로 **후보 검증 → slot(축) 제안 → value(값) 제안**을 수행해
- 선택된 parameter 추천 JSON만 반환합니다. **결과는 어디에도 저장하지 않습니다.**

API: `POST /model-parameters/scenarios/{scenario_id}/proposals` (`api.py`).
입력은 `scenario_id`만 필수이며 나머지 옵션은 기본값을 사용합니다(`schemas/propose_parameters.py:ProposeParametersIn`).

## 2. 그래프/API 흐름

```mermaid
flowchart TD
    A[API: POST .../scenarios/{id}/proposals] --> B[to_state<br/>scenario_id → State]
    B --> C[load_scenario_context<br/>DB read-only 조회]
    C --> D[select_parameter_candidates<br/>XLSX bridge 룰 매칭]
    D --> E[validate_parameter_candidates<br/>LLM Step1.5 후보 gate]
    E --> F[load_basecase_samples<br/>Basecase record 추출]
    F --> G[propose_parameter_slots<br/>LLM Step2 slot 축 결정]
    G --> H[filter_basecase_records_by_slots<br/>선택 slot으로 record 축소]
    H --> I[propose_parameter_values<br/>LLM Step3 값 산정]
    I --> J[to_output<br/>추천 JSON 정형화]
    J --> K[ProposeParametersOut]

    D -. event_type_l2_id∈{6,10} .-> X[후보 = 빈 목록<br/>recommendations=[]]
```

그래프 정의는 `flows/propose_parameters/flow.py:build_graph()`,
런타임 진입은 `build_runnable_graph()` = `to_state | graph | to_output` 입니다.

## 3. 단계별 핵심 로직

### (1) DB 맥락 로드 — `load_scenario_context`
`ModelInputService().load_context(scenario_id)` → `ModelInputRepository.fetch_context_by_scenario_id`.
scenario / scenario_group / event / event_type / dimension_template를 **읽기 전용 select**로만 조회해
`scenario_context` dict로 반환합니다(`persistence/model_input/repository.py`). 미존재 시 `ENTITY_NOT_FOUND`.

### (2) XLSX 매핑 지식베이스 — `mapping.py`
`get_parameter_knowledge_base()`가 두 종류 리소스를 `lru_cache`로 적재합니다.
- **매핑 워크북**(`260625*.xlsx`)
  - `Dimension Parameter Mapping` 시트 → `MappingRule`(event_type_l2_id × dimension_key → canonical parameter, mapping_method=direct/routing/…)
  - `Parameter Excel Mapping` 시트 → `ParameterDefinition`(canonical → model_file/sheet/parameter_name, basecase 읽기 스펙)
- **Basecase 워크북**(`LNG수급모델..._Basecase_..` 폴더의 `.xlsm`)을 프로파일링(`BasecaseProfile`).

### (3) 후보 선택 — `select_parameter_candidates` + `match_parameter_candidates`
- `event_type_l2_id`와 **시나리오 dimension_key 교집합**으로 bridge 룰을 필터.
- `direct`/`routing`이고 모델 타깃(`model_file`/`model_sheet`)이 있는 룰만 후보로 채택,
  나머지는 `non_input_items`(이유 포함)로 분리.
- bridge key가 없으면 폴백 없이 빈 후보 + warning(테스트 `..._does_not_fallback...`로 보장).
- `candidate_key = event_type_l2_id|dimension_key|canonical|model_file|model_sheet`.

### (4) 후보 검증 (Step1.5) — `validate_parameter_candidates`
- `build_llm_prompt_packet`으로 맥락 패킷 구성 → `LLMCandidateValidationResponse` 구조화 출력.
- `_sanitize_candidate_decisions`: **candidate_mappings에 존재하는 candidate_key만** 채택,
  selected=true만 통과, 누락/미지 key는 제외 + warning.
- `_apply_routing_comment_overrides`: bridge 시트의 routing comment가 DB dimension 값과 명확히 일치하면
  LLM 판단을 **결정적으로 보정**(해당 route만 selected=true, 동일 그룹의 나머지는 false).

### (5) Basecase record 추출 — `load_basecase_samples` + `build_basecase_records`
매핑된 시트에서 실제 기준값 row/value를 **평탄화한 record**로 추출(축은 `axes`, 값은 `value`, 식별자 `reference_id`).
읽기 모드 3종:
- `fixed_columns` — 고정 컬럼 역할/행 필터/stop rule 기반(`_extract_fixed_column_records`)
- `matrix_time_columns` — 연/월/Period 헤더 행 기반 시간축 매트릭스(`_extract_matrix_time_column_records`)
- 스펙 미지정 시 — Country/시간라벨 자동 탐지로 Base Case 블록만 추출(`_detect_basecase_matrix_blocks`, "base case" 섹션 우선).

### (6) slot 제안 (Step2) — `propose_parameter_slots`
- record에서 `_build_basecase_slot_options`로 **축 이름/distinct 축값 목록만** 만들어 LLM에 제공(원시 값 row는 미제공).
- LLM이 candidate별 `slot_axes`(지역/국가/시설/연/월/계약/route 등)만 결정. 값 산정은 금지.
- `_sanitize_llm_slots`: 미지 candidate_key 제외, **모호 축값**(미정/후보/추정/“또는”/`?`/세미콜론 결합 등)은
  selected=false + needs_user_review로 보정(`_axis_value_issue`).

### (7) record 필터 — `filter_basecase_records_by_slots`
선택된 slot의 축값과 일치하는 record만 남겨(`_record_matches_slot`, 정규화 비교) Step3 입력을 축소.

### (8) value 제안 (Step3) — `propose_parameter_values`
- 패킷에 선택 slot + 필터된 basecase_records를 넣어 `LLMValueProposalResponse` 산출.
- LLM이 slot별 `value_grid`(basecase_value, proposed_value, operation, 근거)를 제안.
  범위형 dimension은 명확한 수치로 자동 변환(<5%→3%, +300%초과→300% 등) 규칙을 프롬프트로 강제.
- `_sanitize_llm_adjustments`:
  - 미지 candidate_key 제외, Step2에서 slot 미확정 candidate는 selected=false 보정,
  - 모호 좌표/`proposed_value=null`/`operation∈{unknown,not_applicable}` cell 제거,
  - 유효 cell이 하나도 없으면 selected=false,
  - 누락 candidate는 selected=false 검토 항목으로 보강,
  - `basecase_reference_ids`로 basecase_value 역참조 보정(`_patch_basecase_value`).

### (9) 출력 정형화 — `to_output` / `_build_recommendations`
selected=true adjustment만 (model_file, model_sheet, parameter_name)로 그룹화해
`RecommendedParameter`(axis_fields/value_fields/values/rationale)로 변환.
camelCase 키(`basecaseValue`, `proposedValue` 등)로 값을 구성하고 중복 좌표는 근거를 병합.

## 4. 주요 가드레일

- **억제 이벤트 타입**: `event_type_l2_id ∈ {6, 10}` 이면 후보 단계에서 즉시 빈 목록 + 정책 warning,
  `to_output`도 `should_suppress_recommendations`로 `recommendations=[]` 반환
  (`nodes.py:SUPPRESSED_RECOMMENDATION_EVENT_TYPE_L2_IDS`, 테스트 `..._suppressed_event_type...`).
- **읽기 전용 DB**: repository는 select만 수행, service는 세션을 열고 finally에서 close.
  쓰기/commit/flush 없음(테스트 `..._read_only_static_contract`로 정적 보장).
- **제안 비영속**: 추천 결과를 DB/파일에 저장하지 않고 응답 JSON으로만 반환(`api.py` description, state에만 보관).
- **LLM 구조화 출력 + 정제 + 폴백**:
  - 모든 LLM 호출은 `invoke_llm_structured_output`(QUALITY, temperature=0, max_retries=2)로 스키마 강제.
  - 각 단계 `_sanitize_*`가 후보/축/값을 후처리해 모호값·범위이탈을 제거.
  - `allow_llm_fallback=True`일 때만 LLM 실패 시 rule-based 폴백 응답 생성(기본값 False → 실패 시 예외 전파).
- **후보 범위 봉인**: 모든 단계가 `candidate_mappings`의 candidate_key 밖 parameter/workbook/sheet 생성 금지.

## 5. 소스 참조

- `apps/agents/model_parameter_agent/api.py` — FastAPI 라우터/엔드포인트
- `apps/agents/model_parameter_agent/flows/propose_parameters/flow.py` — 그래프 빌드, to_state/to_output, 추천 정형화
- `apps/agents/model_parameter_agent/flows/propose_parameters/nodes.py` — 7개 노드, 정제기, 폴백, 억제 정책
- `apps/agents/model_parameter_agent/mapping.py` — XLSX KB 로딩, 후보 매칭, Basecase record 추출
- `apps/agents/model_parameter_agent/state.py` — `ModelParameterProposalState`
- `apps/agents/model_parameter_agent/schemas/propose_parameters.py` — 입출력/LLM 스키마
- `apps/agents/model_parameter_agent/persistence/model_input/{service,repository}.py` — 읽기 전용 DB 맥락 로드
- `tests/test_model_parameter_agent_contract.py` — 위 계약/가드레일 회귀 테스트

> 비고(추론 표시): mermaid 흐름의 “억제 분기”는 `select_parameter_candidates`/`to_output` 두 곳 모두에서
> 동일 정책이 적용되는 것을 단순화해 표기했습니다. Basecase 자동 블록 탐지(스펙 미지정 경로)의 일부 휴리스틱은
> 실제 워크북 레이아웃 의존성이 있어, 구체 동작은 해당 테스트 케이스 기준으로 확인이 필요합니다.
