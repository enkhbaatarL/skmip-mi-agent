from pydantic import BaseModel, Field
from typing import List


class SignpostFlowInput(BaseModel):
    """Signpost Flow Agent Input Schema

    Input for the signpost generation pipeline.
    Accepts a list of mi_event_ids. For each event's scenarios, if signposts already 
    exist, they are skipped. Otherwise, the pipeline processes and saves the generated 
    signposts. After completion, returns a list of per-event results.
    """
    mi_event_ids: List[int] = Field(
        description="List of MI Event IDs to generate signposts for"
    )