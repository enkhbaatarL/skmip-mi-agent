# Codex 초안 리뷰 (Claude)

대상: `.codex/codex/model_parameter_agent_flow_codex_draft.md`
기준: `apps/agents/model_parameter_agent` 소스 + `tests/test_model_parameter_agent_contract.py`

## 총평

전반적으로 **정확하고 구조가 깔끔**하다. 9단계 분해, 가드레일 정리, KB/매핑 설명이 소스와
일치한다. 분량도 적절(과하지 않음)하다. 다만 Mermaid의 흐름 표현과 출력 단계 설명에 일부
정확성/누락 이슈가 있다.

## 정확성 이슈

1. **Mermaid의 억제 분기 표현이 그래프 토폴로지를 오해시킴** (중요도: 중)
   - 초안은 `D → E{event_type 6/10?} -- yes --> X[recommendations=[]]` / `-- no --> F`로
     그려, 마치 그래프에 조건 분기 edge가 있는 것처럼 보인다.
   - 실제 `build_graph`는 **조건 edge가 없는 선형 그래프**다. 억제는 (a)
     `select_parameter_candidates`가 빈 candidate를 반환하고 (b) `to_output`이 다시
     `recommendations=[]`로 막는 **이중 차단**이며, 중간 노드들은 빈 후보에 early-return한다.
   - 초안 본문 가드레일에는 "후보·출력 양쪽 분기"를 맞게 썼지만, 그림과 본문이 어긋난다.
     보완 섹션에서 스스로 지적한 내용을 그림에도 반영하면 좋다.

2. **출력 단계의 이중 필터·dedup 누락** (중요도: 중)
   - 초안 9번은 "selected adjustment만 그룹화"로만 기술한다. 실제 `_build_recommendations`는
     sanitizer가 이미 거른 뒤에도 `proposed_value is None`과 `operation ∈ {unknown,
     not_applicable}` cell을 **다시 제외**하고, 동일 좌표/값 cell을 dedup하며 rationale을 병합한다.
   - `test_to_output_excludes_unusable_values`가 이 출력단 방어를 직접 검증하므로, "이중 방어 +
     value dedup + axis/value_fields 집계"를 한 줄 추가하는 게 정확하다.

3. **Step3의 이름 강제 덮어쓰기 강조 부족** (중요도: 하)
   - 초안 8번은 "candidate_key만 사용"까지는 맞지만, `_sanitize_llm_adjustments`가 LLM이 반환한
     model_file/model_sheet/parameter_name을 **후보 값으로 강제 치환**하는 점(테스트의 "Invented"
     케이스가 "Trade/ShippingCostInput/ShippingCost"로 교정됨)을 명시하면 가드레일 설명이 더 강해진다.

## 누락된 핵심 로직

4. **누락 candidate 보강** — Step3에서 LLM 응답에 빠진 candidate_key를 서버가
   `selected=false` 검토 항목으로 자동 보강하는 로직(테스트 `c2` 케이스)이 초안에 없다.
   "후보 검증/slot/value 단계의 누락 key 처리"는 이 agent의 핵심 안전장치라 한 줄 가치가 있다.

5. **slot 필터의 매칭 규칙** — `filter_basecase_records_by_slots`가 `matched_axis_count > 0`
   조건(겹치는 축이 하나도 없으면 제외)을 쓴다는 점이 "slot 일치 record만 유지"보다 구체적이다. 선택.

## 명료성 / 범위

6. **"Codex 관점 보완 필요점" 섹션은 독립 초안 범위를 벗어남** (중요도: 하)
   - 이 섹션은 *기존 최종 문서*에 대한 메타 코멘트라, "독립 초안"보다는 리뷰 노트에 가깝다.
     상호 리뷰 단계에서 다룰 내용이므로 초안 본문에서는 빼거나 별도 노트로 분리하는 편이 깔끔하다.

7. **표기 정확성** — "Step1.5 LLM은 selected 여부만 판단"은 정확. "lru_cache 재사용"도 정확
   (`_load_parameter_knowledge_base` maxsize=8, `get_runnable_graph` maxsize=1).

## 분량 평가

- 너무 장황하지 않고, 너무 얇지도 않다. 9단계 + 가드레일 구성은 적절하다.
- 보강할 곳은 "출력 단계(2번)"와 "누락 candidate 보강(4번)" 정도이며, 나머지는 한 줄 보완으로 충분.

## 결론

골격은 그대로 최종 문서로 가져갈 만하다. **(1) Mermaid를 선형 그래프 + 이중 차단으로 수정**,
**(2) 출력 단계의 이중 필터/dedup/이름 덮어쓰기/누락 보강을 보완**, **(3) 메타 코멘트 섹션 정리**
세 가지만 반영하면 정확성과 완결성이 충분하다.
