from pydantic import BaseModel, Field
from typing import List


class ScenarioFlowInput(BaseModel):
    """Scenario Flow Agent Input Schema
    
    Input for the scenario generation pipeline.
    Accepts a list of mi_event_ids. For each event, if scenarios already exist, 
    it is skipped. Otherwise, the pipeline processes and saves the generated scenarios.
    After completion, returns a list of per-event results.
    """
    mi_event_ids: List[int] = Field(
        description="List of MI Event IDs to generate scenarios for"
    )
