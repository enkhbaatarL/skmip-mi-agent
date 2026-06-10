from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class CommonResponse(BaseModel):
    status: Literal["success", "error"] = Field(description="Result status", default="success")
    message: str = Field(default="", description="Result message")
    data: dict[str, Any] | None = Field(default=None, description="Optional detailed result payload")
