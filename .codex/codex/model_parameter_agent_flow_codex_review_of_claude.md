# Claude 초안 리뷰 (Codex)

대상: `.codex/claude/model_parameter_agent_flow_claude_draft_v2.md`

## 총평

Claude 초안은 Codex 초안보다 출력 정형화 단계와 안전장치를 더 촘촘히 설명했다.
특히 선형 그래프 위에서 `select_parameter_candidates`와 `to_output`이 억제 이벤트를 이중 차단한다는 점,
Step3 sanitizer가 LLM의 model target 값을 후보 값으로 덮어쓴다는 점,
누락 candidate를 `selected=false` 검토 항목으로 보강한다는 점은 최종 문서에 반영할 가치가 높다.

## 반영할 내용

1. **Mermaid 보정**
   - 조건 edge가 있는 그래프처럼 그리면 실제 LangGraph 토폴로지와 다르다.
   - 최종 문서는 선형 그래프를 유지하되, 억제 정책은 노드 내부 가드레일 또는 dashed note로 표현한다.

2. **출력 단계 세부**
   - `_build_recommendations`의 dedup, rationale 병합, `proposed_value=None` 및 `unknown/not_applicable` 재제외를 반영한다.
   - `axis_fields`, `value_fields` 집계도 한 줄로 명시하면 응답 구조 이해가 좋아진다.

3. **Step3 안전장치**
   - `_sanitize_llm_adjustments`가 LLM 반환 `model_file`, `model_sheet`, `parameter_name`을 후보의 값으로 강제 보정한다는 점을 반영한다.
   - LLM 응답에서 누락된 candidate를 서버가 `selected=false`, `needs_user_review=true`로 보강하는 점도 반영한다.

4. **slot filter 규칙**
   - slot과 record가 겹치는 축을 하나 이상 비교해야 통과한다는 `matched_axis_count > 0` 조건은 핵심 로직으로 반영한다.

## 조정할 내용

1. **불필요한 추정 표기 제거**
   - Claude 초안은 `ModelInputService.load_context`의 정확한 repository 동작을 직접 확인하지 못했다고 썼지만,
     Codex는 `persistence/model_input/repository.py`에서 `select` 기반 조회를 직접 확인했다.
   - 최종 문서에서는 이 부분을 추정으로 남기지 않는다.

2. **테스트 세부는 요약**
   - 계약 테스트 항목을 모두 나열하면 문서가 길어진다.
   - 최종 문서에는 검증 근거를 "API/그래프/읽기 전용/매핑/Basecase/sanitizer 계약 테스트" 정도로 압축한다.

3. **노드명 설명은 간결화**
   - `load_basecase_samples`가 실제로 `build_basecase_records`를 호출한다는 점은 유용하지만,
     "이름 != 동작" 같은 표현은 최종 문서에서 더 중립적으로 다듬는다.

## 결론

Claude 초안의 정확성 보강 항목을 최종 문서에 대부분 반영하되,
불필요한 추정/테스트 상세/메타 표현은 줄여 하나의 운영 설명 문서로 정리한다.
