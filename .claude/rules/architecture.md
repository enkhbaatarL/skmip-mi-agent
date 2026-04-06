# 아키텍처 규칙

## 레이어 의존성 방향
```
nodes/tools → connectors → external services
nodes        → state, schemas, prompts
subgraphs    → 자체 state/schemas, common connectors
```
- **역방향 의존성 금지**: `connectors`가 `nodes`를 import하면 안 됨
- **공통 레이어**: `apps/common/` 은 어디서나 import 가능
- **서브그래프 격리**: 서브그래프는 메인 그래프의 `MariAgentState`를 직접 mutate하지 않음

## 노드 작성 규칙
```python
from __future__ import annotations

from apps.common.logging.decorators import log_node
from apps.common.streaming.decorators import stream_step
from apps.agents.mi_agent.state.state import MariAgentState

@log_node
@stream_step(step_key="my_step")   # 스트리밍이 필요한 경우에만
async def my_node(state: MariAgentState) -> MariAgentState:
    result = await my_tool(state.rewritten_query)
    return state.model_copy(update={"field": result})
```
- 노드는 상태를 받아 새 상태를 반환 (immutable update: `model_copy(update={...})`)
- 비즈니스 로직은 `tools/` 함수로 위임, 노드는 얇게 유지

## 툴 작성 규칙
```python
from apps.common.logging.decorators import log_tool

@log_tool
async def my_tool(query: str, *, option: bool = False) -> MyResult:
    ...
```
- 툴은 순수 비즈니스 로직 — 상태 객체를 파라미터로 받지 말 것
- 파라미터는 명시적 값으로 받기 (state 객체 전달 금지)

## 서브그래프 추가 패턴
새 서브그래프 추가 시 반드시 다음 파일 생성:
1. `subgraph_builder.py` — `StateGraph` 조립, `run_xxx()` 함수
2. `subgraph_adapter.py` — `to_state()`, `to_output()` 변환 함수
3. `state.py` — 서브그래프 전용 `XxxSearchState`
4. `schemas.py` — `XxxSearchInput`, `XxxSearchOutput`
5. `stages/prepare/` — 준비 단계 노드
6. `stages/execute/` — 실행 단계 노드
7. `tools/` — 서브그래프 전용 툴

## LLM 호출 규칙
- **Structured output**: `invoke_llm_structured_output()` — JSON 스키마 강제 추출
- **Function call**: `invoke_llm_function_call()` — 함수 호출 패턴 필요 시
- `ModelPreference.SPEED` vs `ModelPreference.QUALITY` 로 모델 선택
- LLM 호출은 반드시 세마포어 내에서 실행 (커넥터가 자동 처리)

## RuntimeContext 규칙
- `RuntimeContext`는 `apps/common/runtime/runtime.py` 의 모듈 함수를 통해서만 접근
- `ensure_runtime_context_ready()` 를 호출하고 나서 리소스 접근
- MCP 풀, HTTP 클라이언트, 세마포어는 직접 생성 금지

## SearchPolicySet
- 검색 소스 활성화/비활성화는 `Settings.search_sources` (환경변수)로 제어
- `SearchPolicySet`은 `RuntimeContext.ensure_ready()` 시점에 빌드됨
- 개별 검색의 타임아웃·재시도는 `ExecutionPolicy` 로 제어

## 프롬프트 관리
- 프롬프트는 `apps/agents/mi_agent/prompts/` 에 모듈로 관리
- 프롬프트 빌더 함수는 순수 함수 (I/O 없음)로 작성
- 시스템 프롬프트 / 유저 프롬프트를 분리하여 `messages` 리스트 반환

## 스트리밍
- 스트리밍 응답이 필요한 노드: `@stream_step(step_key="unique_key")` 적용
- `step_key` 는 프론트엔드와 계약된 고유 식별자 (변경 시 프론트 협의 필요)
