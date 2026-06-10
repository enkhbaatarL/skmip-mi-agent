from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from apps.common.values.response import CommonResponse


class ConfirmGenerationData(BaseModel):
    scenario_group_id: int
    confirmed: bool = False
    confirmed_at: datetime | None = None
    snapshot_id: int | None = None
    scenario_count: int = 0
    signpost_count: int = 0


class ConfirmGenerationOut(CommonResponse):
    data: ConfirmGenerationData | None = None
