# MLflow Trace 가이드

이 문서는 `scenario_group_agent`와 비슷한 디렉터리 구조, LangGraph, 공통 connector를 사용하는
신규 Agent 개발자가 MLflow trace를 붙일 때 따르는 기준입니다.

## 1) 공통 설정

MLflow 설정은 `apps/common/configs/config.py`와 `envs/config.yaml`을 공통으로 사용합니다.
신규 Agent에서 별도 설정 로더를 만들지 말고, 일반 앱 코드에서는 항상 `get_settings()`를 사용합니다.

```python
from apps.common.configs.config import get_settings
```

`envs/config.yaml`에는 공통 MLflow 접속 정보와 Agent별 trace profile을 둡니다.

```yaml
agents:
  scenario_group_agent:
    mlflow_experiment_name: scenario_agent_local
    aip_app_id: scenario_agent
    mlflow_tracing_enabled: true
  default:
    mlflow_experiment_name: mi_agent_local
    aip_app_id: mi_agent
    mlflow_tracing_enabled: false
mlflow_tracking_uri: "http://<mlflow-host>:5001"
mlflow_tracking_username: "${MLFLOW_TRACKING_USERNAME}"
mlflow_tracking_password: "${MLFLOW_TRACKING_PASSWORD}"
mlflow_langchain_run_tracer_inline: false
```

- `mlflow_tracking_uri`: MLflow tracking server 주소입니다.
- `agents.<agent_name>.mlflow_experiment_name`: Agent별 MLflow experiment 이름입니다.
- `agents.<agent_name>.aip_app_id`: AIP 호출 header의 `aip-app-id`로 전달되는 Agent 식별자입니다.
- `agents.<agent_name>.mlflow_tracing_enabled`: 해당 Agent의 trace 활성화 여부입니다.
- `agents.default`: Agent 이름에 해당하는 profile이 없을 때 사용하는 fallback입니다.
- `mlflow_langchain_run_tracer_inline`: `false`이면 LangChain trace 처리가 요청 흐름을 덜 막도록 합니다.
- username/password는 config에 직접 쓰지 말고 환경변수 placeholder로 주입합니다.

## 2) main.py 초기화

각 Agent는 `main.py`를 다르게 가질 수 있지만, MLflow 초기화는 FastAPI lifespan에서 한 번만 수행합니다.
`config.py`와 `config.yaml`은 공통으로 공유하고, `agent_name`으로 Agent별 profile을 선택합니다.

```python
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from apps.agents.new_agent.constants import AGENT_NAME


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    from apps.common.configs.config import get_settings
    from apps.common.logging.logger_config import setup_logging
    from apps.connectors.mlflow.tracing import setup_mlflow_tracing

    cfg = get_settings()
    setup_logging(cfg.log_level)
    setup_mlflow_tracing(cfg, agent_name=AGENT_NAME)

    yield


app = FastAPI(lifespan=lifespan)
```

`setup_mlflow_tracing()`은 다음을 처리합니다.

- MLflow tracking URI 설정
- Agent 이름에 맞는 experiment 선택
- `mlflow.langchain.autolog()` 활성화
- MLflow import나 설정 실패 시 앱 실행을 막지 않고 warning log만 남김

## 3) LangGraph invoke에 config와 context 전달

요청 또는 background task가 실제 LangGraph를 실행하기 직전에 `TraceContext`를 만들고,
graph 실행 시 `config`와 `context`에 같은 trace context를 전달합니다.
MLflow trace 연동에서 가장 중요한 규칙은 아래 한 줄입니다.

```python
await graph.ainvoke(state, config=build_langgraph_config(trace_context), context=trace_context)
```

이때 `TraceContext`는 MLflow metadata/tag, LangGraph thread/session, AIP header의 공통 기준이 됩니다.

```python
from apps.agents.new_agent.constants import AGENT_NAME
from apps.common.configs.config import get_settings
from apps.common.tracing.context import (
    TraceContext,
    build_langgraph_config,
    mlflow_trace_context,
    new_transaction_id,
)


async def run_new_agent_background(resource_id: int, payload: dict[str, object]) -> None:
    cfg = get_settings()
    agent_config = cfg.get_agent_config(AGENT_NAME)
    trace_context = TraceContext(
        transaction_id=new_transaction_id(),
        app_identifier=agent_config.aip_app_id,
        agent_name=AGENT_NAME,
        scenario_group_id=str(resource_id),
    )

    state = NewAgentState(
        resource_id=resource_id,
        payload=payload,
    )

    with mlflow_trace_context(trace_context):
        final_state = await get_compiled_graph().ainvoke(
            state,
            config=build_langgraph_config(trace_context),
            context=trace_context,
        )
```

권장 규칙:

- `transaction_id`는 요청 단위로 새로 생성합니다.
- `app_identifier`는 `cfg.get_agent_config(AGENT_NAME).aip_app_id`를 사용합니다.
  - 이 값은 AIP 호출 시 `aip-app-id` header로 전달됩니다.
  - 같은 값이 MLflow metadata의 `aip.app_id`와 trace tag의 `app_id`에도 기록됩니다.
  - 따라서 배포 환경, endpoint, 요청마다 바뀌는 값이 아니라 "어떤 Agent가 호출했는지"를 식별하는 안정적인 app id로 정합니다.
  - 권장 형식은 소문자 snake_case입니다. 예: `scenario_agent`, `market_research_agent`
- `agent_name`은 `AGENT_NAME` constant를 사용합니다. MLflow trace on/off와 experiment profile 조회 기준입니다.
- `scenario_group_id`처럼 사용자가 MLflow UI에서 묶어 보고 싶은 business id를 넣습니다.
- business id가 없다면 `scenario_group_id`는 생략해도 됩니다. 이 경우 `transaction_id`가 LangGraph thread id가 됩니다.

## 4) Graph와 Subgraph 전파 규칙

graph와 subgraph 구현 방식은 Agent별로 자유롭게 정해도 됩니다.
다만 trace context를 node와 하위 graph까지 쓰려면 graph 생성 시 `context_schema=TraceContext`를 지정하고,
모든 graph/subgraph `ainvoke()`에 같은 `config`와 `context`를 전달합니다.

```python
from langchain_core.runnables import Runnable
from langgraph.graph import StateGraph

from apps.common.tracing.context import TraceContext


def build_new_agent_graph() -> Runnable:
    graph = StateGraph(
        state_schema=NewAgentState,
        context_schema=TraceContext,
    )
    graph.add_node("load_context", LoadContextNode())
    graph.add_node("generate_answer", GenerateAnswerNode())
    graph.set_entry_point("load_context")
    graph.add_edge("load_context", "generate_answer")
    graph.set_finish_point("generate_answer")
    return graph.compile()
```

subgraph도 동일합니다. 상위 graph에서 받은 `runtime.context`를 그대로 넘기는 것이 핵심입니다.

```python
from langgraph.runtime import Runtime
from apps.common.tracing.context import TraceContext, build_langgraph_config


async def run_subgraph_node(
    state: NewAgentState,
    runtime: Runtime[TraceContext] | None = None,
) -> dict[str, object]:
    trace_context = runtime.context if runtime is not None else None

    result_state = await get_new_agent_subgraph().ainvoke(
        NewAgentSubgraphState(payload=state.payload),
        config=build_langgraph_config(trace_context) if trace_context is not None else None,
        context=trace_context,
    )

    return {"result": result_state.result}
```

`context_schema`를 쓰지 않거나 node에서 trace context가 필요 없는 구조라면 node 모양은 달라도 됩니다.
그래도 top-level graph와 subgraph 실행 시 `config=build_langgraph_config(trace_context)`,
`context=trace_context`를 넣는 규칙은 유지합니다.

## 5) Node에서 LLM connector에 trace_context 전달

공통 LLM connector를 사용할 때 `trace_context`를 전달하면 다음이 자동으로 붙습니다.

- AIP header: `aip-transaction-id`, `aip-app-id`, 필요 시 `aip-chat-id`
- MLflow LLM span attribute: transaction id, app id, business id
- LangChain callback context

```python
from langgraph.runtime import Runtime
from apps.common.tracing.context import TraceContext
from apps.connectors.llm.llm_client import invoke_llm_structured_output


class GenerateAnswerNode:
    async def __call__(
        self,
        state: NewAgentState,
        runtime: Runtime[TraceContext] | None = None,
    ) -> dict[str, object]:
        trace_context: TraceContext | None = runtime.context if runtime is not None else None

        result = await invoke_llm_structured_output(
            messages=[
                {"role": "system", "content": "You are a helpful domain agent."},
                {"role": "user", "content": state.prompt},
            ],
            output_schema=NewAgentOutput,
            trace_context=trace_context,
        )

        return {"answer": result.result}
```

node가 공통 `BaseNode` 패턴을 쓰는 경우에도 원칙은 같습니다.
`run(self, state, runtime)`에서 `runtime.context`를 꺼내 connector 또는 하위 함수로 전달합니다.

`invoke_llm_function_call()`, `invoke_llm_structured_output()`, `invoke_llm_text()`의 `trace_context`는
선택 인자입니다. 넘기지 않으면 `None`으로 처리되어 LLM 호출은 정상 수행되지만, AIP header와 MLflow trace는 붙지 않습니다.

```text
trace_context 있음
  -> AIP extra header 전달
  -> agents.<agent_name>.mlflow_tracing_enabled 기준으로 MLflow span 생성

trace_context 없음
  -> AIP extra header 없음
  -> MLflow span 생성 안 함
  -> LLM 호출은 정상 수행
```

따라서 trace가 필요한 Agent flow에서는 LLM connector 호출마다 `trace_context=trace_context`를 명시합니다.
공통 connector를 trace 없이 재사용하는 호출자는 별도 설정 없이 `trace_context`를 생략해도 됩니다.

## 6) Trace가 연결되는 방식

현재 공통 trace helper의 연결 기준은 다음과 같습니다.


| 위치                       | 사용하는 값                                                                                  |
| ------------------------ | --------------------------------------------------------------------------------------- |
| MLflow experiment        | `agents.<agent_name>.mlflow_experiment_name` 또는 `agents.default.mlflow_experiment_name` |
| MLflow trace on/off      | `TraceContext.agent_name` 기준의 `agents.<agent_name>.mlflow_tracing_enabled`              |
| MLflow trace metadata    | `aip.transaction_id`, `aip.app_id`, `scenario_group_id`                                 |
| MLflow trace tag         | `app_id`, `scenario_group_id`                                                           |
| LangGraph thread/session | `scenario_group_id`가 있으면 해당 값, 없으면 `transaction_id`                                     |
| AIP request header       | `aip-transaction-id`, `aip-app-id`, `aip-chat-id`                                       |


따라서 같은 업무 단위의 graph/subgraph/LLM 호출을 하나의 trace로 묶으려면
처음 만든 `TraceContext`를 끝까지 재사용해야 합니다.

## 7) 개발 체크리스트

신규 Agent에 trace를 붙일 때 아래를 확인합니다.

- `envs/config.yaml`의 `agents.<agent_name>`에 `mlflow_experiment_name`, `aip_app_id`, `mlflow_tracing_enabled`를 추가했다.
- Agent `main.py` lifespan에서 `setup_mlflow_tracing(cfg, agent_name=AGENT_NAME)`를 호출했다.
- flow 시작 지점에서 `TraceContext`를 한 번 생성한다.
- `TraceContext.app_identifier`는 하드코딩하지 않고 `cfg.get_agent_config(AGENT_NAME).aip_app_id`를 사용한다.
- `TraceContext.agent_name`은 `AGENT_NAME`을 사용한다.
- graph와 subgraph의 `StateGraph(..., context_schema=TraceContext)`를 설정했다.
- 모든 top-level graph 실행에 `config=build_langgraph_config(trace_context)`와 `context=trace_context`를 전달한다.
- subgraph `ainvoke()`에도 같은 `config`와 `context`를 전달한다.
- LLM connector 호출에 `trace_context=trace_context`를 전달한다.
- trace 실패가 비즈니스 로직 실패로 이어지지 않도록, MLflow 관련 예외를 직접 raise하지 않는다.
- MLflow UI에서 experiment, session/thread, LLM span, metadata/tag가 보이는지 확인한다.

## 8) 자주 생기는 누락

### MLflow UI에 graph는 보이는데 LLM span이 비어 있음

LLM connector 호출에 `trace_context`가 전달되지 않았거나, 공통 connector를 우회해 직접 OpenAI client를 호출했을 가능성이 큽니다.
신규 Agent에서는 특별한 이유가 없으면 `apps.connectors.llm.llm_client`를 사용합니다.

### subgraph trace가 별도 session처럼 보임

subgraph `ainvoke()`에 상위 flow의 `config` 또는 `context`가 재전달되지 않은 경우입니다.
상위 graph에서 받은 `runtime.context`를 그대로 넘깁니다.

### experiment가 기본값으로만 들어감

`setup_mlflow_tracing(cfg, agent_name=AGENT_NAME)`의 Agent 이름과
`envs/config.yaml`의 `agents.<agent_name>` key가 일치하는지 확인합니다.

### trace는 꺼졌지만 앱은 정상 실행됨

정상 동작입니다. `agents.<agent_name>.mlflow_tracing_enabled: false`이거나 MLflow import/setup 실패 시 trace helper는 no-op으로 동작하고
warning log만 남깁니다.