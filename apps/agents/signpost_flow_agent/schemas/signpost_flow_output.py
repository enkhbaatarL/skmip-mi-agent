from pydantic import BaseModel, Field
from typing import List


class EventResult(BaseModel):
    """Per-event result for batch signpost generation."""
    mi_event_id: int = Field(description="MI Event ID")
    status: str = Field(description="Result status: success / already_exist / failure")
    message: str = Field(default="", description="Detail message or error description")


class SignpostFlowOutput(BaseModel):
    """Signpost Flow Agent Output Schema

    Output of the batch signpost generation pipeline.
    Contains per-event results and summary statistics.
    """
    results: List[EventResult] = Field(
        description="Per-event generation results"
    )
    summary: dict = Field(
        description="Summary statistics: total, success, already_exist, failure counts"
    )