"""
Shared LLM Usage Model

Minimal usage tracking model for internal LLM response parsing.
Uses extra="ignore" to tolerate unexpected API response fields
(e.g. latency_checkpoint) that are not part of the output contract.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class LLMUsageModel(BaseModel):
    """LLM 사용량 정보 (내부 usage tracking 용)."""

    model_config = ConfigDict(extra="ignore")

    prompt_tokens: int = Field(default=0, description="프롬프트 토큰 수")
    completion_tokens: int = Field(default=0, description="응답 생성 토큰 수")
    total_tokens: int = Field(default=0, description="총 토큰 수 (prompt + completion)")