---
name: add-subgraph
description: 새 검색 서브그래프를 추가합니다. 서브그래프 추가, 새 검색 소스 추가 요청 시 사용.
disable-model-invocation: true
allowed-tools: Read Edit Write Bash(git status)
argument-hint: [subgraph-name]
---

사용자가 요청한 서브그래프 이름: **$ARGUMENTS** (예: `xxx_search`)

`$ARGUMENTS` 이름을 기반으로 아래 절차로 파일을 생성한다.
기존 `rdb_search`, `vdb_search`, `web_search` 패턴을 그대로 따른다.

## 생성할 파일 목록

```
apps/agents/mi_agent/subgraphs/$ARGUMENTS/
├── __init__.py
├── schemas.py
├── state.py
├── subgraph_adapter.py
├── subgraph_builder.py
├── stages/
│   ├── __init__.py
│   ├── prepare/
│   │   ├── __init__.py
│   │   └── <prepare_node>.py
│   └── execute/
│       ├── __init__.py
│       └── <execute_node>.py
└── tools/
    ├── __init__.py
    └── <tool_name>.py
```

## 파일별 템플릿

### schemas.py
```python
from __future__ import annotations
from pydantic import BaseModel, Field

class XxxSearchInput(BaseModel):
    company_code: str | None = None
    rewritten_query: str | None = None

class XxxSearchOutput(BaseModel):
    results: list[...] = Field(default_factory=list)
```

### state.py
```python
from __future__ import annotations
from apps.agents.mi_agent.subgraphs.$ARGUMENTS.schemas import XxxSearchInput, XxxSearchOutput

class XxxSearchState(XxxSearchInput):
    xxx_search_results: XxxSearchOutput | None = None
```

### subgraph_adapter.py
```python
from __future__ import annotations
from apps.agents.mi_agent.state.state import MariAgentState
from apps.agents.mi_agent.subgraphs.$ARGUMENTS.schemas import XxxSearchInput, XxxSearchOutput
from apps.agents.mi_agent.subgraphs.$ARGUMENTS.state import XxxSearchState

def to_state(mari_state: MariAgentState) -> XxxSearchState:
    return XxxSearchState(
        company_code=mari_state.company_code,
        rewritten_query=mari_state.rewritten_query,
    )

def to_output(xxx_state: XxxSearchState) -> XxxSearchOutput:
    return xxx_state.xxx_search_results or XxxSearchOutput()
```

### subgraph_builder.py
```python
from __future__ import annotations
from langchain_core.runnables import Runnable, RunnableLambda
from langgraph.graph import StateGraph
from apps.agents.mi_agent.state.state import MariAgentState
from apps.agents.mi_agent.subgraphs.$ARGUMENTS.schemas import XxxSearchOutput
from apps.agents.mi_agent.subgraphs.$ARGUMENTS.state import XxxSearchState
from apps.agents.mi_agent.subgraphs.$ARGUMENTS.subgraph_adapter import to_state, to_output
from apps.agents.mi_agent.subgraphs.$ARGUMENTS.stages.prepare.<node> import prepare_node
from apps.agents.mi_agent.subgraphs.$ARGUMENTS.stages.execute.<node> import execute_node
from apps.common.streaming.decorators import stream_step

def build_xxx_subgraph() -> Runnable:
    graph = StateGraph(state_schema=XxxSearchState)
    graph.add_node("prepare_node", prepare_node)
    graph.add_node("execute_node", execute_node)
    graph.set_entry_point("prepare_node")
    graph.add_edge("prepare_node", "execute_node")
    graph.set_finish_point("execute_node")
    return graph.compile()

_xxx_subgraph = build_xxx_subgraph()

runnable_graph: Runnable = (
    RunnableLambda(to_state) | _xxx_subgraph | RunnableLambda(to_output)
).with_types(input_type=MariAgentState, output_type=XxxSearchOutput)

@stream_step(step_key="search_xxx")
async def run_xxx(agent_state: MariAgentState) -> XxxSearchOutput:
    return await runnable_graph.ainvoke(agent_state)
```

## 서브그래프 등록 (SearchSupervisor)

`apps/agents/mi_agent/orchestration/supervisors/search_supervisor.py` 에 `run_xxx` 추가.

## 체크리스트
- [ ] 모든 파일 `from __future__ import annotations` 첫 줄
- [ ] `@log_node` / `@log_tool` / `@log_connector` 데코레이터 적용
- [ ] `to_state()`, `to_output()` 변환 함수 구현
- [ ] `SearchPolicySet` 에 새 소스 추가 (필요 시)
- [ ] `Settings.search_sources` 기본값에 새 소스 포함 (필요 시)
- [ ] `SearchOutput` 스키마에 새 결과 필드 추가
