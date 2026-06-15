from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CommonResponse(BaseModel):
    status: Literal["success", "error"] = Field(description="Result status", default="success")
    message: str = Field(default="", description="Result message")
    data: dict[str, Any] | None = Field(default=None, description="Optional detailed result payload")


class CallBackBody(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    result: Literal["success", "error"] = Field(description="Callback result", default="success")
    reason: str | None = Field(default=None, description="Reason for error, or null on success")
