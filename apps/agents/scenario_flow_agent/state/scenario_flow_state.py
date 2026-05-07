from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ScenarioFlowState(BaseModel):
    """Scenario Flow Agent State
    
    Follows the same state pattern as existing agents.
    Holds the complete pipeline execution state for scenario generation.
    """
    # --- Input ---
    mi_event_id: Optional[str] = Field(
        default=None,
        description="Base MI Event ID. Loaded from event file during execution."
    )
    event_file_path: Optional[str] = Field(
        default=None,
        description="Path to event JSON file (for Stage 1 file based)"
    )
    
    # --- Metadata ---
    scenario_group_id: Optional[str] = Field(
        default=None,
        description="Scenario group unique ID"
    )
    event_type_l1_l2: Optional[str] = Field(
        default=None,
        description="Event type L1::L2 key"
    )
    template_id: Optional[str] = Field(
        default=None,
        description="Template Registry ID used"
    )
    
    # --- Pipeline Stage Results ---
    stage1_context_pack: Optional[Dict] = Field(
        default=None,
        description="Stage 1 Context Pack result"
    )
    stage2_dimension_selection: Optional[Dict] = Field(
        default=None,
        description="Stage 2 Dimension Selection result"
    )
    stage3_value_selection: Optional[Dict] = Field(
        default=None,
        description="Stage 3 Value Selection result"
    )
    stage4_scenario_synthesis: Optional[Dict] = Field(
        default=None,
        description="Stage 4 Scenario Synthesis result"
    )
    stage5_validation: Optional[Dict] = Field(
        default=None,
        description="Stage 5 Validation result"
    )
    
    # --- Pipeline Statistics ---
    cartesian_total: Optional[int] = Field(
        default=None,
        description="Total Cartesian product combinations"
    )
    filtered_by_compatibility: Optional[int] = Field(
        default=None,
        description="Combinations passed compatibility rules"
    )
    scenario_count: Optional[int] = Field(
        default=None,
        description="Final number of scenarios"
    )
    mece_passed: Optional[bool] = Field(
        default=None,
        description="MECE check passed status"
    )
    
    # --- Output ---
    output_file_path: Optional[str] = Field(
        default=None,
        description="Path where result JSON was saved"
    )
    
    # --- Execution Metadata ---
    started_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Pipeline start time"
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="Pipeline completion time"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if pipeline failed"
    )