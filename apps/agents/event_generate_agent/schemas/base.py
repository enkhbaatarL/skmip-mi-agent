from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    """camelCase alias를 쓰는 event generate agent API 모델 base."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    def __getitem__(self, key: str) -> Any:
        return self.model_dump()[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.model_dump().get(key, default)
