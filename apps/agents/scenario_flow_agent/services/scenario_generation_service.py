"""
Scenario Generation Service

Wraps the stage_integrated_scenario_openai logic and provides service layer.
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from apps.connectors.llm.llm_client import invoke_llm_structured_output, invoke_llm_text, ModelPreference
from apps.common.logging.decorators import log_tool
from .scenario_pipeline import (
    stage1_build_context_pack,
    stage2_select_dimensions,
    stage3_reduce_values,
    stage4_synthesize_scenarios,
    stage5_validate,
    _resolve_template,
)


class ScenarioGenerationService:
    """Service layer for scenario generation pipeline"""
    
    def __init__(self):
        # Pass project standard LLM client functions to stage code
        self.llm_invoke_structured = invoke_llm_structured_output
        self.llm_invoke_text = invoke_llm_text
        self.ModelPreference = ModelPreference
    
    @log_tool
    def generate_scenario_group(self, event_file_path: str) -> Dict[str, Any]:
        """
        Run complete scenario generation pipeline for a given event file.
        
        Args:
            event_file_path: Path to event JSON file
            
        Returns:
            Complete scenario group result
        """
        # Load event
        with open(event_file_path, "r", encoding="utf-8") as f:
            event = json.load(f)
            
        # Generate scenario group ID
        scenario_group_id = f"scg_{uuid.uuid4().hex[:10]}"
        
        # Run pipeline stages with properly configured LLM client
        pack = stage1_build_context_pack(event)
        template = _resolve_template(pack.C1_base_event.event_type_l1_l2)
        stage2 = stage2_select_dimensions(pack, event, template, llm_client=self)
        stage3 = stage3_reduce_values(pack, stage2, template, llm_client=self)
        stage4 = stage4_synthesize_scenarios(pack, stage3, template, llm_client=self)
        stage5 = stage5_validate(pack, stage4, llm_client=self)
        
        # Build document
        result = {
            "scenario_group_id": scenario_group_id,
            "created_at": datetime.utcnow().isoformat(),
            "stage1_context_pack": pack.model_dump(),
            "stage2_dimension_selection": stage2.model_dump(),
            "stage3_value_selection": stage3.model_dump(),
            "stage4_scenario_synthesis": stage4.model_dump(),
            "stage5_validation": stage5.model_dump(),
            "cartesian_total": stage4.cartesian_total,
            "filtered_by_compatibility": stage4.filtered_by_compatibility,
            "scenario_count": len(stage4.scenarios),
            "mece_passed": stage5.mece_check.mutually_exclusive,
            "mi_event_id": event.get("mi_event_id"),
            "event_type_l1_l2": pack.C1_base_event.event_type_l1_l2,
            "template_id": pack.C1_base_event.event_type_l1_l2
        }
        
        return result
    
    def save_result(self, result: Dict[str, Any], output_path: str) -> None:
        """Save scenario result to file"""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)