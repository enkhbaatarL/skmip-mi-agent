# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: S101

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from apps.agents.model_parameter_agent.flows.propose_parameters.nodes import (
    _guard_prompt_bytes,
    _slot_catalog_for_prompt,
)
from apps.agents.model_parameter_agent.utils.basecase import (
    basecase_slot_axis_names_from_candidate,
    build_basecase_records,
)
from apps.agents.model_parameter_agent.utils.lut import (
    ReferenceLoadPolicy,
    build_basecase_index,
    build_slot_catalog,
)
from apps.agents.model_parameter_agent.utils.parameter_mapping import (
    get_parameter_knowledge_base_from_resources,
)
from apps.agents.model_parameter_agent.utils.resource_runtime import (
    get_model_parameter_resource_paths,
)


ROOT_DIR = Path(__file__).resolve().parents[2]
CANONICAL_PATH = ROOT_DIR / "scripts/model_parameter/model-parameter-canonical-v4.json"
BASECASE_ONLY_EXPECTATIONS = {
    "User-Adjusted Gas Demand": (
        12,
        ("Country", "Year", "Month", "Demand Sub-Sector"),
    ),
    "RegasAdjustment": (
        22_920,
        (
            "Continent",
            "Region",
            "Country",
            "Regasification plant",
            "Life Cycle Category",
            "Nameplate capacity (MTPA)",
            "Year",
            "Month",
        ),
    ),
    "PNG Contract Volume": (684, ("Year", "From Country", "To Country")),
    "RemainingUnrestrictedAmount": (
        3,
        ("Year", "From Country", "To Country"),
    ),
    "ShippingCost": (5, ("Year",)),
    "VolumeCancelled": (3, ("Year", "From Country", "To Country")),
}


def _candidate(parameter: Any) -> dict[str, Any]:  # noqa: ANN401
    return {
        **parameter.__dict__,
        "candidate_key": f"v4-basecase|{parameter.canonical_parameter_name}",
        "canonical_parameter_name": parameter.canonical_parameter_name,
    }


def test_v4_basecase_only_parameters_have_exact_slots_without_lut() -> None:
    canonical = json.loads(CANONICAL_PATH.read_text(encoding="utf-8"))
    parameter_rows = [
        {
            **row,
            "canonical_parameter_name": row["parameter_name"],
        }
        for row in canonical["master"]
        if row["parameter_name"] in BASECASE_ONLY_EXPECTATIONS
    ]
    paths = get_model_parameter_resource_paths()
    knowledge_base = get_parameter_knowledge_base_from_resources(
        mapping_rows=[],
        parameter_rows=parameter_rows,
        basecase_dir_path=str(paths.basecase_dir),
        allow_empty_mapping_rows=True,
    )
    candidates = [
        _candidate(knowledge_base.definition_for(parameter_name)) for parameter_name in BASECASE_ONLY_EXPECTATIONS
    ]
    assert all(paths.lut_registry.get(parameter_name) is None for parameter_name in BASECASE_ONLY_EXPECTATIONS)

    records, warnings = build_basecase_records(
        knowledge_base,
        candidates,
        {},
        registry=paths.lut_registry,
    )
    assert not warnings
    basecase_index = build_basecase_index(
        records,
        candidates,
        policy=ReferenceLoadPolicy(start_year=2026, end_year=2030),
        registry=paths.lut_registry,
    )
    slot_catalog = build_slot_catalog(basecase_index, None)

    for candidate in candidates:
        parameter_name = candidate["canonical_parameter_name"]
        expected_count, expected_axes = BASECASE_ONLY_EXPECTATIONS[parameter_name]
        assert tuple(basecase_slot_axis_names_from_candidate(candidate)) == expected_axes
        assert basecase_index.candidate_key_axes[candidate["candidate_key"]] == expected_axes
        assert len(basecase_index.records_for_candidate(candidate["candidate_key"])) == expected_count
        candidate_catalog = slot_catalog.for_candidate(candidate["candidate_key"])
        assert candidate_catalog is not None
        assert sum(len(leaf.available_periods) for leaf in candidate_catalog.leaves) == expected_count

    regas_catalog = slot_catalog.for_candidate("v4-basecase|RegasAdjustment")
    assert regas_catalog is not None
    assert len(regas_catalog.leaves) == 382
    assert regas_catalog.time_axes == ("Year", "Month")
    assert "Period" not in regas_catalog.key_axes

    compact_catalog = _slot_catalog_for_prompt(slot_catalog)
    regas_prompt_catalog = next(item for item in compact_catalog if item["parameter_name"] == "RegasAdjustment")
    packet = {
        "parameter_slot_tasks": [
            {
                "parameter": {
                    "candidate_key": "v4-basecase|RegasAdjustment",
                    "parameter_name": "RegasAdjustment",
                },
                "slot_catalog": regas_prompt_catalog,
            },
        ],
    }
    _, prompt_bytes, parameter_bytes = _guard_prompt_bytes(
        packet,
        step="Step2",
        task_field="parameter_slot_tasks",
        limit=262_144,
    )
    assert prompt_bytes < 262_144
    assert parameter_bytes["RegasAdjustment"] < 262_144
