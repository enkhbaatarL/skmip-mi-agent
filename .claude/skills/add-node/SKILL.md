---
name: add-node
description: 새 LangGraph 노드와 툴 파일을 생성하고 그래프에 등록합니다. 노드 추가, 노드 생성 요청 시 사용.
disable-model-invocation: true
allowed-tools: Read Edit Write Bash(git status)
argument-hint: [node-name]
---

사용자가 요청한 노드 이름: **$ARGUMENTS**

`$ARGUMENTS` 이름을 기반으로 아래 절차로 파일을 생성/수정한다.

## 절차

### 1. 툴 파일 생성 (`apps/agents/mi_agent/tools/$ARGUMENTS.py`)
```python
from __future__ import annotations

from apps.common.logging.decorators import log_tool
# 필요한 커넥터 import

@log_tool
async def $ARGUMENTS_tool(<param>: <type>) -> <ReturnType>:
    ...
```

### 2. 노드 파일 생성 (`apps/agents/mi_agent/nodes/$ARGUMENTS.py`)
```python
from __future__ import annotations

from apps.agents.mi_agent.state.state import MariAgentState
from apps.agents.mi_agent.tools.$ARGUMENTS import $ARGUMENTS_tool
from apps.common.logging.decorators import log_node
# from apps.common.streaming.decorators import stream_step  # 스트리밍 필요 시

@log_node
# @stream_step(step_key="$ARGUMENTS")  # 스트리밍 필요 시 추가
async def $ARGUMENTS_node(state: MariAgentState) -> MariAgentState:
    result = await $ARGUMENTS_tool(state.<field>)
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
from apps.agents.mi_agent.nodes.$ARGUMENTS import $ARGUMENTS_node

graph.add_node("$ARGUMENTS", $ARGUMENTS_node)
graph.add_edge("<prev_node>", "$ARGUMENTS")
graph.add_edge("$ARGUMENTS", "<next_node>")
```

## 체크리스트
- [ ] `from __future__ import annotations` 첫 줄
- [ ] `@log_node` 데코레이터 적용
- [ ] `@log_tool` 데코레이터 적용
- [ ] 노드는 `model_copy(update={...})` 로 상태 반환 (immutable)
- [ ] 툴은 상태 객체 직접 받지 않고 필요한 값만 파라미터로 받기
- [ ] 타입 힌트 완성
