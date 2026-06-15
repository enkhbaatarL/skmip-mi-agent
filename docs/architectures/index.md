# Architectures 문서 인덱스

신규 에이전트 추가/확장 시 아래 문서를 기준으로 작업한다.

## Scenario Group Agent

- [Scenario Group Agent 디렉터리 구조 가이드](./scenario_group_agent_directory_structure.md)
  - 최종 디렉터리 트리, 폴더 역할, endpoint-flow 매핑, 기존 코드 이관 매핑, 추가 체크리스트
- [Scenario Group Agent Flow 로직](./scenario_group_agent_logic.md)
  - runnable 조립 구조, 공통 state, create/validate/signpost flow의 node 체인, scenario 생성 5-stage pipeline
- [Scenario Group Agent API/Sequence](./scenario_group_agent_sequence.md)
  - Sync/Async(Callback) 시퀀스, 4개 API 요청/응답/콜백 바디, Scenario Group/Scenario status·stage 전이 및 DB 제약
