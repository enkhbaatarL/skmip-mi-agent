from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, List, Optional


class ScenarioFlowOutput(BaseModel):
    """Scenario Flow Agent Output Schema
    
    Output of the scenario generation pipeline.
    Contains complete results, metadata and execution status.
    """
    scenario_group_id: str = Field(
        description="Generated scenario group ID"
    )
    mi_event_id: str = Field(
        description="Base MI Event ID"
    )
    event_type_l1_l2: str = Field(
        description="Event type L1::L2 key"
    )
    template_id: str = Field(
        description="Template ID used"
    )
    
    # --- Statistics ---
    cartesian_total: int = Field(
        description="Total Cartesian product combinations"
    )
    filtered_by_compatibility: int = Field(
        description="Combinations passed compatibility rules"
    )
    scenario_count: int = Field(
        description="Final number of scenarios generated"
    )
    mece_passed: bool = Field(
        description="MECE check passed status"
    )
    
    # --- Results ---
    scenarios: List[Dict] = Field(
        description="Final generated scenarios with full details"
    )
    likelihood_prior: Dict[str, str] = Field(
        description="Scenario ID to likelihood category mapping"
    )
    
    # --- Execution ---
    success: bool = Field(
        description="Pipeline execution success status"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if execution failed"
    )
    execution_time_ms: int = Field(
        description="Total execution time in milliseconds"
    )
    completed_at: datetime = Field(
        description="Pipeline completion time"
    )
    output_file_path: Optional[str] = Field(
        default=None,
        description="Path where result was saved"
    )