from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
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

    async def __call__(self, state: Any) -> dict[str, Any]:
        return await self.run(state)

    @abstractmethod
    async def run(self, state: Any) -> dict[str, Any]:
        ...
