# /add-node — 새 LangGraph 노드 추가

사용자가 요청한 노드 이름과 역할을 파악하여 아래 절차로 파일을 생성/수정한다.

## 절차

### 1. 툴 파일 생성 (`apps/agents/mi_agent/tools/<node_name>.py`)
```python
from __future__ import annotations

from apps.common.logging.decorators import log_tool
# 필요한 커넥터 import

@log_tool
async def <node_name>_tool(<param>: <type>) -> <ReturnType>:
    """비즈니스 로직."""
    ...
```

### 2. 노드 파일 생성 (`apps/agents/mi_agent/nodes/<node_name>.py`)
```python
from __future__ import annotations

from apps.agents.mi_agent.state.state import MariAgentState
from apps.agents.mi_agent.tools.<node_name> import <node_name>_tool
from apps.common.logging.decorators import log_node
# 스트리밍이 필요하면:
# from apps.common.streaming.decorators import stream_step

@log_node
# @stream_step(step_key="<node_name>")  # 스트리밍 필요 시 추가
async def <node_name>_node(state: MariAgentState) -> MariAgentState:
    result = await <node_name>_tool(state.<field>)
    return state.model_copy(update={"<output_field>": result})
```

### 3. 상태에 출력 필드 추가 (`apps/agents/mi_agent/state/state.py`)
```python
<output_field>: <Type> | None = Field(
    default=None,
    description="<설명>",
)
```

### 4. 그래프에 노드 등록 (`apps/agents/mi_agent/flows/mari_agent_graph.py`)
```python
from apps.agents.mi_agent.nodes.<node_name> import <node_name>_node

graph.add_node("<node_name>", <node_name>_node)
graph.add_edge("<prev_node>", "<node_name>")
graph.add_edge("<node_name>", "<next_node>")
```

## 체크리스트
- [ ] `from __future__ import annotations` 첫 줄
- [ ] `@log_node` 데코레이터 적용
- [ ] `@log_tool` 데코레이터 적용
- [ ] 노드는 `model_copy(update={...})` 로 상태 반환 (immutable)
- [ ] 툴은 상태 객체 직접 받지 않고 필요한 값만 파라미터로 받기
- [ ] 타입 힌트 완성
