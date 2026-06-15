from __future__ import annotations

from collections import defaultdict
from typing import Any

from apps.agents.scenario_group_agent.persistence.scenario.service import (
    ScenarioService,
)
from apps.agents.scenario_group_agent.schemas.common import (
    ScenarioGroupPayload,
    ScenarioGroupTableData,
    ScenarioHeader,
    ScenarioImpact,
    ScenarioMetrics,
    ScenarioRow,
    ScenarioTable,
    SignpostPayload,
)


def build_scenario_group_table_data(
    group: dict[str, Any],
    scenarios: list[dict[str, Any]],
    signposts: list[dict[str, Any]] | None = None,
) -> ScenarioGroupTableData:
    template_json = ScenarioService()._load_template_json_from_db(
        int(group["event_type_l2_id"])
    )
    template_by_key = {
        str(item.get("dim_key")): item
        for item in template_json
        if isinstance(item, dict) and item.get("dim_key")
    }
    selected_keys = [str(key) for key in group.get("dimension_selected") or []]
    selected_keys.sort(
        key=lambda key: (
            _display_order(template_by_key.get(key)),
            key,
        )
    )
    headers = [
        ScenarioHeader(
            key=key,
            label=str(template_by_key.get(key, {}).get("label") or key),
            display_order=index,
        )
        for index, key in enumerate(selected_keys, start=1)
    ]

    signposts_by_scenario_id: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for signpost in signposts or []:
        signposts_by_scenario_id[int(signpost["scenario_id"])].append(signpost)

    rows: list[ScenarioRow] = []
    for scenario in scenarios:
        scenario_id = int(scenario["scenario_id"])
        raw_values = scenario.get("dimension_values") or {}
        cells = {
            key: _enum_id_to_label(key, raw_values.get(key), template_by_key.get(key))
            for key in selected_keys
        }
        rows.append(
            ScenarioRow(
                scenario_id=scenario_id,
                display_order=int(scenario.get("display_order") or 0),
                title=scenario.get("title") or "",
                narrative=scenario.get("narrative"),
                cells=cells,
                metrics=ScenarioMetrics(
                    probability_score=scenario.get("probability_score"),
                    probability_delta=scenario.get("probability_delta"),
                ),
                impact=ScenarioImpact(
                    jkm=scenario.get("impact_jkm"),
                    ttf=scenario.get("impact_ttf"),
                    hh=scenario.get("impact_hh"),
                ),
                baseline_yn=scenario.get("baseline_yn"),
                signposts=[
                    SignpostPayload(
                        signpost_id=int(signpost["signpost_id"]),
                        label=signpost.get("label") or "",
                        probability_direction_code=signpost.get("probability_direction_code"),
                        probability_impact_score=signpost.get("probability_impact_score"),
                        signpost_reason=signpost.get("signpost_reason"),
                        display_order=int(signpost.get("display_order") or 0),
                        strength=signpost.get("strength"),
                        use_yn=signpost.get("use_yn"),
                        keyword_hints=signpost.get("keyword_hints") or [],
                    )
                    for signpost in signposts_by_scenario_id.get(scenario_id, [])
                ],
            )
        )

    return ScenarioGroupTableData(
        scenario_group=ScenarioGroupPayload.model_validate(group),
        table=ScenarioTable(headers=headers, rows=rows),
    )


def _enum_id_to_label(
    dimension_key: str, value: Any, template: dict[str, Any] | None
) -> Any:
    if value is None or not template:
        return value
    prefix = f"{dimension_key}_v"
    value_text = str(value)
    if not value_text.startswith(prefix):
        return value
    try:
        index = int(value_text.removeprefix(prefix)) - 1
    except ValueError:
        return value
    value_enums = template.get("value_enums") or []
    return value_enums[index] if 0 <= index < len(value_enums) else value


def _display_order(template: dict[str, Any] | None) -> int:
    try:
        return int((template or {}).get("display_order", 999999))
    except (TypeError, ValueError):
        return 999999
