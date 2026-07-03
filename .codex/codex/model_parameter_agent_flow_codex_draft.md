# Codex Draft: 수급모델 파라미터 제안 Flow

> Codex가 `apps/agents/model_parameter_agent` 소스와
> `tests/test_model_parameter_agent_contract.py`를 기준으로 독립 작성한 리뷰용 초안입니다.

## 기능 개요

`model_parameter_agent`는 `scenario_id` 하나로 시나리오 맥락을 조회한 뒤,
Dimension-to-Parameter 매핑 XLSX와 수급모델 Basecase 입력시트를 근거로
Demand/Supply/Trade 모델 input parameter의 조정 후보를 추천한다.
추천은 API 응답으로만 반환되며 저장은 수행하지 않는다.

## Flow

```mermaid
flowchart TD
    A[POST /model-parameters/scenarios/{scenario_id}/proposals]
    A --> B[to_state: scenario_id/options 검증]
    B --> C[load_scenario_context: DB context read]
    C --> D[select_parameter_candidates: XLSX bridge 룰 매칭]
    D --> E{event_type_l2_id 6 또는 10?}
    E -- yes --> X[recommendations=[]]
    E -- no --> F[validate_parameter_candidates: LLM 후보 검증 + routing 보정]
    F --> G[load_basecase_samples: Basecase record 평탄화]
    G --> H[propose_parameter_slots: LLM slot 축 결정]
    H --> I[filter_basecase_records_by_slots: slot 일치 record만 유지]
    I --> J[propose_parameter_values: LLM value_grid 산정]
    J --> K[to_output: selected adjustment를 추천 JSON으로 그룹화]
```

## 단계별 핵심

1. **DB context 로드**
   - `ModelInputService`가 scenario, scenario_group, event, event_type, dimension_template를 읽는다.
   - repository는 select 중심의 읽기 전용 계약을 가진다.

2. **매핑 KB 로드**
   - `Dimension Parameter Mapping`은 이벤트 타입과 dimension key를 canonical parameter 후보로 연결한다.
   - `Parameter Excel Mapping`은 canonical parameter를 모델 파일/시트/파라미터명/Basecase read spec으로 연결한다.
   - `get_parameter_knowledge_base()`는 매핑과 Basecase profile을 `lru_cache`로 재사용한다.

3. **후보 선정**
   - `event_type_l2_id`와 scenario dimension key가 맞는 룰만 본다.
   - `direct`, `routing`이고 모델 target이 있는 항목만 후보가 된다.
   - 직접 input이 아닌 항목은 `non_input_items`로 분리한다.

4. **후보 검증**
   - Step1.5 LLM은 rule-based 후보 안에서 selected 여부만 판단한다.
   - sanitizer는 미지 candidate key나 누락 key를 제외한다.
   - routing 후보는 bridge comment와 dimension value가 명확히 맞으면 deterministic override를 적용한다.

5. **Basecase record 추출**
   - fixed columns, matrix time columns, 자동 matrix block 탐지 방식으로 기준값을 추출한다.
   - record는 `axes`, `value`, `unit`, `reference_id`, 원본 row/column을 포함한다.

6. **Slot 제안**
   - LLM에는 raw record 대신 축 이름과 distinct 축값 목록만 전달한다.
   - LLM은 국가/시설/기간/route 등 모델 input 좌표만 고른다.
   - 모호한 축값은 selected=false 및 사용자 검토 필요로 보정된다.

7. **Record 필터**
   - 선택 slot의 축값과 일치하는 record만 Step3에 전달한다.

8. **Value 제안**
   - Step3 LLM은 filtered record를 기준으로 `basecase_value`, `proposed_value`, `operation`을 산정한다.
   - sanitizer는 null 제안값, unknown operation, 모호 좌표를 제거한다.
   - reference id로 기준값을 역참조 보강할 수 있다.

9. **응답 생성**
   - selected adjustment만 모델 파일/시트/파라미터별로 그룹화한다.
   - 최종 응답은 `RecommendedParameter` 목록만 노출한다.

## 가드레일

- `event_type_l2_id` 6, 10은 추천 억제 대상이다.
- LLM 호출은 structured output schema, temperature 0, retry 2회로 제한된다.
- 기본적으로 LLM 실패는 예외이며, `allow_llm_fallback=True`일 때만 검토 필요 fallback을 만든다.
- 후보 범위 밖 parameter/workbook/sheet 생성은 프롬프트와 sanitizer 양쪽에서 차단한다.
- 제안 결과는 영속화하지 않는다.

## Codex 관점 보완 필요점

- 기존 최종 문서에는 “억제 이벤트 타입” 분기가 후보 단계와 출력 단계 양쪽에 존재한다는 점을 더 명확히 쓰는 편이 좋다.
- `load_basecase_samples`라는 노드명과 실제 역할(`build_basecase_records`) 사이의 차이를 설명하면 독자가 혼동하지 않는다.
- 최종 문서는 너무 긴 테스트 설명보다 검증된 계약 항목만 짧게 남기는 것이 적절하다.
