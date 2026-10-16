# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: S101

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from apps.persistence.model_impact_lever.service import _hydrate_catalog
from scripts.model_parameter.build_model_impact_lever_v4_1_0050 import (
    EXPECTED_HYDRATED_CHECKSUM,
    TARGET_PATH,
    build_document,
)
from scripts.model_parameter.build_model_parameter_v4_1_0050 import (
    OUTPUT_PATH as MASTER_TARGET_PATH,
    build_document as build_master_document,
)


def test_v4_1_v0050_canonical_is_reproducible_and_splits_canal_parameters() -> None:
    checked_in = json.loads(TARGET_PATH.read_text(encoding="utf-8"))
    generated = build_document()

    assert generated == checked_in
    assert generated["catalog_version"] == "v4.1"
    assert generated["hydrated_catalog_checksum"] == EXPECTED_HYDRATED_CHECKSUM
    assert generated["impact_lever_count"] == 21
    assert generated["binding_occurrence_count"] == 56
    assert generated["effective_executable_binding_occurrence_count"] == 56
    assert generated["conditional_binding_occurrence_count"] == 41
    assert generated["conditional_binding_lever_count"] == 6
    assert generated["executable_parameter_count"] == 17

    rows = generated["impact_levers"]
    assert isinstance(rows, list)
    parameter_names = {binding["parameter_name"] for row in rows for binding in row["parameter_bindings"]}
    assert "CanalToll" not in parameter_names
    assert {"Suez Canal Cost", "Panama Canal Cost"} <= parameter_names
    assert {row["target_impact_lever_id"] for row in rows} == set(range(56, 77))

    canal_lever = next(row for row in rows if row["lever_code"] == "canal_toll")
    canal_bindings = canal_lever["parameter_bindings"]
    assert [binding["parameter_name"] for binding in canal_bindings] == [
        "Suez Canal Cost",
        "Panama Canal Cost",
    ]
    assert all(binding["selection_mode"] == "conditional" for binding in canal_bindings)


def test_v4_1_v0050_canonical_path_is_versioned_artifact() -> None:
    root = Path(__file__).resolve().parents[2]

    assert root / "scripts/model_parameter/model-impact-lever-canonical-v4.1-0050.json" == TARGET_PATH


def test_v4_1_v0050_master_is_reproducible_and_adds_only_split_parameters() -> None:
    checked_in = json.loads(MASTER_TARGET_PATH.read_text(encoding="utf-8"))
    generated = build_master_document()

    assert generated == checked_in
    assert generated["canonical_version"] == "model-parameter-canonical-v4.1-0050"
    assert generated["master_count"] == 26
    assert generated["expected_counts"] == {
        "master": 26,
        "active_parameters": 18,
        "inactive_parameters": 8,
        "dimension_mappings": 129,
    }
    rows_by_id = {row["model_param_id"]: row for row in generated["master"]}
    assert rows_by_id[24]["parameter_name"] == "CanalToll"
    assert rows_by_id[25]["parameter_name"] == "Suez Canal Cost"
    assert rows_by_id[25]["model_table"] == "table4"
    assert rows_by_id[26]["parameter_name"] == "Panama Canal Cost"
    assert rows_by_id[26]["model_table"] == "table5"


def test_v4_1_v0050_checksum_matches_runtime_hydration() -> None:
    impact = json.loads(TARGET_PATH.read_text(encoding="utf-8"))
    master = json.loads(MASTER_TARGET_PATH.read_text(encoding="utf-8"))["master"]

    class Repository:
        def fetch_active_impact_levers(self, *, catalog_version: str) -> list[dict[str, Any]]:
            assert catalog_version == "v4.1"
            return sorted(
                [
                    {
                        "impact_lever_id": row["target_impact_lever_id"],
                        "lever_code": row["lever_code"],
                        "domain": row["domain"],
                        "label": row["label"],
                        "description": row["description"],
                        "applicability_hint": row.get("applicability_hint"),
                        "parent_lever_code": row.get("parent_lever_code"),
                        "parameter_bindings": row["parameter_bindings"],
                        "catalog_version": row["catalog_version"],
                    }
                    for row in impact["impact_levers"]
                ],
                key=lambda row: (row["domain"], row["lever_code"]),
            )

        def fetch_parameter_definitions_by_names(
            self,
            parameter_names: list[str],
        ) -> list[dict[str, Any]]:
            requested = set(parameter_names)
            return [
                {
                    "canonical_parameter_name": row["parameter_name"],
                    "use_yn": row["use_yn"],
                    "semantic_axes": row["semantic_axes"],
                }
                for row in master
                if row["parameter_name"] in requested
            ]

    catalog, version, checksum = _hydrate_catalog(Repository(), catalog_version="v4.1")  # type: ignore[arg-type]

    assert version == "v4.1"
    assert checksum == EXPECTED_HYDRATED_CHECKSUM
    assert len(catalog) == 21
    assert (
        sum(binding.support_status == "executable" for lever in catalog for binding in lever.parameter_bindings) == 56
    )
