from pydantic import BaseModel, Field
from typing import Optional


class ScenarioFlowInput(BaseModel):
    """Scenario Flow Agent Input Schema
    
    Input for the scenario generation pipeline.
    Requires mi_event_id to load the base event from database.
    """
    mi_event_id: int = Field(
        description="MI Event ID to generate scenarios for (loaded from tmm_mieventm)"
    )
