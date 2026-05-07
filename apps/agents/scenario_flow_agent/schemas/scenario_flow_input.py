from pydantic import BaseModel, Field
from typing import Optional


class ScenarioFlowInput(BaseModel):
    """Scenario Flow Agent Input Schema
    
    Input for the scenario generation pipeline.
    For Stage 1, only event_file_path is required (file based execution).
    """
    event_file_path: str = Field(
        default="./tmp/sample_event_ev_2a58da7f4ff2.json",
        description="Path to event JSON file (used for Stage 1 file based execution)"
    )
