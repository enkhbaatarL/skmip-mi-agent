from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any, Dict, List, Optional


class SignpostFlowState(BaseModel):
    """Signpost Flow Agent State

    Follows the same state pattern as the scenario_flow_agent.
    Holds the complete pipeline execution state for signpost generation.
    """
    # --- Input ---
    mi_event_id: Optional[str] = Field(
        default=None,
        description="Base MI Event ID (from API parameter mi_event_id)"
    )
    event_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Loaded event data dict (reconstructed from DB in sample_event format)"
    )

    # --- Scenarios loaded from DB ---
    scenario_group_id: Optional[str] = Field(
        default=None,
        description="Scenario group ID from tmm_scenariom"
    )
    scenarios_from_db: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Scenarios loaded from tmm_scenariom with their PK scenario_ids"
    )

    # --- Pipeline Stage Results ---
    stage1_context_pack: Optional[Dict] = Field(
        default=None,
        description="Stage 1 Context Pack (reused from loaded data)"
    )

    # --- Signpost results ---
    signposts_generated: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Generated signposts with their scenario_id FK mapping"
    )

    # --- Output ---
    saved_signpost_ids: Optional[List[int]] = Field(
        default=None,
        description="IDs of signposts saved to tmm_signpostm"
    )

    # --- Per-scenario results ---
    scenario_results: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Per-scenario results: scenario_id, status (success/skip/failure)"
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