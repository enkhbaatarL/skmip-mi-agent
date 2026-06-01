from __future__ import annotations

from pathlib import Path
from typing import Any

from stage_integrated_scenario import (
    ScenarioGroupState,
    _build_scenario_group_id,
    _now_iso,
    _resolve_template,
    build_document,
    load_base_event,
    stage1_build_context_pack,
    stage2_select_dimensions,
    stage3_reduce_values,
    stage4_synthesize_scenarios,
    stage5_validate,
)


def load_event(event_path: str | Path) -> dict[str, Any]:
    return load_base_event(Path(event_path).resolve())


def generate_scenario_state_from_event(event: dict[str, Any]) -> dict[str, Any]:
    pack = stage1_build_context_pack(event)
    template = _resolve_template(pack.C1_base_event.event_type_l1_l2)
    stage2 = stage2_select_dimensions(pack, event, template)
    stage3 = stage3_reduce_values(pack, stage2, template)
    stage4 = stage4_synthesize_scenarios(pack, stage3, template)
    stage5 = stage5_validate(pack, stage4)

    state = ScenarioGroupState(
        scenario_group_id=_build_scenario_group_id(event),
        created_at=_now_iso(),
        stage1_context_pack=pack,
        stage2_dimension_selection=stage2,
        stage3_value_selection=stage3,
        stage4_scenario_synthesis=stage4,
        stage5_validation=stage5,
    )
    return build_document(state)


def load_event_and_generate(event_path: str | Path) -> dict[str, Any]:
    event = load_event(event_path)
    return generate_scenario_state_from_event(event)
