from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from apps.common.values.response import CommonResponse


class CreateSignpostsIn(BaseModel):
    pass


class CreateSignpostsData(BaseModel):
    scenario_group_id: int
    signpost_count: int = 0
    saved_signpost_ids: list[int] = Field(default_factory=list)
    signpost_result: dict[str, Any] | None = None


class CreateSignpostsOut(CommonResponse):
    data: CreateSignpostsData | None = None
