# ruff: noqa: ANN401

from abc import ABC, abstractmethod
from inspect import signature
from typing import Any

from langchain_core.runnables.config import RunnableConfig
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from apps.common.tracing.context import langchain_callbacks_context


class ApiModel(BaseModel):
    """API 요청/응답 스키마의 공통 베이스.

    하위 클래스는 필드를 snake_case(Python 관례)로 정의한다. 상속 시 아래 설정이 적용된다.

    - ``alias_generator=to_camel``: JSON 직렬화·역직렬화 시 camelCase alias를 사용한다
      (예: ``scenario_group_id`` <-> ``scenarioGroupId``).
    - ``populate_by_name=True``: Python 필드명(snake_case)과 camelCase alias 모두로
      인스턴스를 생성할 수 있으며, 같은 필드를 가리킨다.

    아래 dict 유사 메서드는 ``model_dump()`` 키(snake_case 필드명) 기준이며,
    camelCase alias 키로는 동작하지 않는다.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    def __getitem__(self, key: str) -> Any:
        return self.model_dump()[key]

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        return self.model_dump().get(key, default)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, dict):
            return self.model_dump() == other
        return super().__eq__(other)


class BaseNode(ABC):
    """Stateless LangGraph node.

    Compiled LangGraph runnables may cache and reuse node instances.
    Do not store request-specific mutable state on self.
    Request data must flow through the LangGraph state object.
    """

    async def __call__(
        self,
        state: Any,
        runtime: Any | None = None,
        config: RunnableConfig | None = None,
    ) -> dict[str, Any]:
        callbacks = config.get("callbacks") if isinstance(config, dict) else None
        with langchain_callbacks_context(callbacks):
            if runtime is None:
                return await self.run(state)
            return await self.run_with_runtime(state, runtime)

    async def run_with_runtime(self, state: Any, runtime: Any) -> dict[str, Any]:
        if "runtime" in signature(self.run).parameters:
            return await self.run(state, runtime)
        return await self.run(state)

    @abstractmethod
    async def run(self, state: Any) -> dict[str, Any]:
        ...
