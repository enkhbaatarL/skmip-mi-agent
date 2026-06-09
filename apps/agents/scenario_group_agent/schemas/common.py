from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


Status = Literal["success", "already_exist", "failure"]


class BaseScenarioDesignOut(BaseModel):
    status: Status = Field(description="Result status")
    message: str = Field(default="", description="Result message")


class DetailPayload(BaseScenarioDesignOut):
    data: dict[str, Any] | None = Field(default=None, description="Optional detailed result payload")
