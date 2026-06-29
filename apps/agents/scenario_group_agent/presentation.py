from __future__ import annotations

from collections import defaultdict
from typing import Any

from apps.agents.scenario_group_agent.persistence.scenario.service import (
    ScenarioService,
)
from apps.agents.scenario_group_agent.schemas.api.manage_scenario_groups import (
    ScenarioGroupDetailOut,
)
from apps.agents.scenario_group_agent.schemas.api.table import (
    ScenarioGroupQueryPayload,
    ScenarioGroupTableData,
    ScenarioHeader,
    ScenarioImpact,
    ScenarioMetrics,
    ScenarioQueryRow,
    ScenarioQueryTable,
    ScenarioRow,
    ScenarioTable,
    SignpostQueryPayload,
)
from apps.agents.scenario_group_agent.schemas.domain.scenario_group import (
    ScenarioGroupPayload,
)
from apps.agents.scenario_group_agent.schemas.domain.signpost import SignpostBasePayload


def build_scenario_group_table_data(
    group: dict[str, Any],
    scenarios: list[dict[str, Any]],
    signposts: list[dict[str, Any]] | None = None,
) -> ScenarioGroupTableData:
    template_by_key, selected_keys, headers = _build_headers(group)
    signposts_by_scenario_id = _group_signposts(signposts)

    rows: list[ScenarioRow] = []
    for scenario in scenarios:
        scenario_id = int(scenario["scenario_id"])
        rows.append(
            ScenarioRow(
                **_row_common_payload(scenario, template_by_key, selected_keys),
                signposts=[
                    SignpostBasePayload(
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


def build_scenario_group_query_data(
    group: dict[str, Any],
    scenarios: list[dict[str, Any]],
    signposts: list[dict[str, Any]] | None = None,
) -> ScenarioGroupDetailOut:
    template_by_key, selected_keys, headers = _build_headers(group)
    signposts_by_scenario_id = _group_signposts(signposts)

    rows: list[ScenarioQueryRow] = []
    for scenario in scenarios:
        scenario_id = int(scenario["scenario_id"])
        rows.append(
            ScenarioQueryRow(
                **_row_common_payload(scenario, template_by_key, selected_keys),
                del_yn=scenario.get("del_yn") or "N",
                signposts=[
                    SignpostQueryPayload(
                        signpost_id=int(signpost["signpost_id"]),
                        label=signpost.get("label") or "",
                        probability_direction_code=signpost.get("probability_direction_code"),
                        probability_impact_score=signpost.get("probability_impact_score"),
                        signpost_reason=signpost.get("signpost_reason"),
                        display_order=int(signpost.get("display_order") or 0),
                        strength=signpost.get("strength"),
                        use_yn=signpost.get("use_yn"),
                        keyword_hints=signpost.get("keyword_hints") or [],
                        del_yn=signpost.get("del_yn") or "N",
                    )
                    for signpost in signposts_by_scenario_id.get(scenario_id, [])
                ],
            )
        )

    signposts_list = signposts or []
    return ScenarioGroupDetailOut(
        scenario_group=ScenarioGroupQueryPayload.model_validate(group),
        table=ScenarioQueryTable(headers=headers, rows=rows),
        scenario_count=sum(1 for scenario in scenarios if scenario.get("del_yn") != "Y"),
        signpost_count=sum(
            1 for signpost in signposts_list if signpost.get("del_yn") != "Y"
        ),
        deleted_scenario_count=sum(
            1 for scenario in scenarios if scenario.get("del_yn") == "Y"
        ),
        deleted_signpost_count=sum(
            1 for signpost in signposts_list if signpost.get("del_yn") == "Y"
        ),
    )


def _build_headers(
    group: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[str], list[ScenarioHeader]]:
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
    return template_by_key, selected_keys, headers


def _group_signposts(
    signposts: list[dict[str, Any]] | None,
) -> dict[int, list[dict[str, Any]]]:
    signposts_by_scenario_id: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for signpost in signposts or []:
        signposts_by_scenario_id[int(signpost["scenario_id"])].append(signpost)
    return signposts_by_scenario_id


def _row_common_payload(
    scenario: dict[str, Any],
    template_by_key: dict[str, dict[str, Any]],
    selected_keys: list[str],
) -> dict[str, Any]:
    raw_values = scenario.get("dimension_values") or {}
    cells = {
        key: _enum_id_to_label(key, raw_values.get(key), template_by_key.get(key))
        for key in selected_keys
    }
    return {
        "scenario_id": int(scenario["scenario_id"]),
        "display_order": int(scenario.get("display_order") or 0),
        "title": scenario.get("title") or "",
        "narrative": scenario.get("narrative"),
        "cells": cells,
        "metrics": ScenarioMetrics(
            probability_score=scenario.get("probability_score"),
            probability_delta=scenario.get("probability_delta"),
        ),
        "impact": ScenarioImpact(
            jkm=scenario.get("impact_jkm"),
            ttf=scenario.get("impact_ttf"),
            hh=scenario.get("impact_hh"),
        ),
        "baseline_yn": scenario.get("baseline_yn"),
    }


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
