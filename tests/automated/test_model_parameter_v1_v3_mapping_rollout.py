from __future__ import annotations

# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: S101
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from apps.persistence.model_parameter.repository import ModelParameterRepository
from scripts.model_parameter.apply_model_parameter_v1_v3_mapping import (
    BASE_MAPPING_IDS,
    CANDIDATE_DML_COLUMNS,
    CANDIDATE_MAPPING_UPDATE,
    CANDIDATE_UPDATE_IDS,
    COMMENT_ONLY_DML_COLUMNS,
    COMMENT_ONLY_MAPPING_UPDATE,
    COMMENT_ONLY_UPDATE_IDS,
    EXPECTED_CANDIDATE_NAMES,
    EXPECTED_METHOD_COUNTS,
    MAPPING_CANONICAL_PATH,
    MAPPING_TARGET_COLUMNS,
    POPULATION_UPSERT,
    SNAPSHOT_PATH,
    UPDATED_MAPPING_IDS,
    V4_IMPACT_LEVER_CANONICAL_PATH,
    V4_MODEL_PARAMETER_CANONICAL_PATH,
    RolloutArtifacts,
    _apply_mappings,
    _assert_preconditions,
    _assert_v4_rows_unchanged,
    _by_id,
    _candidate_names,
    _effective_target_row,
    _mapping_changed_fields,
    _population_row,
    _validate_mapping_target,
    validate_artifacts,
)


ROOT_DIR = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def artifacts() -> RolloutArtifacts:
    return validate_artifacts(
        mapping_canonical_path=MAPPING_CANONICAL_PATH,
        v4_model_parameter_canonical_path=V4_MODEL_PARAMETER_CANONICAL_PATH,
        v4_impact_lever_canonical_path=V4_IMPACT_LEVER_CANONICAL_PATH,
        snapshot_path=SNAPSHOT_PATH,
    )


def _final_mapping_rows(artifacts: RolloutArtifacts) -> list[dict[str, object]]:
    source_by_id = _by_id(artifacts.snapshot_mappings, "model_param_dimension_map_id")
    target_by_id = _by_id(artifacts.target_mappings, "model_param_dimension_map_id")
    rows: list[dict[str, object]] = []
    for mapping_id in sorted(BASE_MAPPING_IDS):
        row = _effective_target_row(source_by_id[mapping_id], target_by_id[mapping_id])
        if mapping_id in UPDATED_MAPPING_IDS:
            row["mod_dtm"] = "2026-08-13T12:00:00.000000"
        rows.append(row)

    population = _population_row(artifacts.target_mappings)
    assert population is not None
    persisted_population: dict[str, object] = dict(population)
    persisted_population["model_param_dimension_map_id"] = 129
    persisted_population["crt_dtm"] = "2026-08-13T12:00:00.000000"
    persisted_population["mod_dtm"] = "2026-08-13T12:00:00.000000"
    rows.append(persisted_population)
    return rows


def test_artifacts_pin_the_exact_approved_mapping_only_diff(artifacts: RolloutArtifacts) -> None:
    source_by_id = _by_id(artifacts.snapshot_mappings, "model_param_dimension_map_id")
    target_by_id = _by_id(artifacts.target_mappings, "model_param_dimension_map_id")
    changed_fields_by_id = {
        mapping_id: _mapping_changed_fields(source_by_id[mapping_id], target_by_id[mapping_id])
        for mapping_id in sorted(BASE_MAPPING_IDS)
        if _mapping_changed_fields(source_by_id[mapping_id], target_by_id[mapping_id])
    }

    assert set(changed_fields_by_id) == UPDATED_MAPPING_IDS
    assert set(changed_fields_by_id) == CANDIDATE_UPDATE_IDS | COMMENT_ONLY_UPDATE_IDS
    assert all(
        changed_fields_by_id[mapping_id] == {"mapping_method", "model_param_id", "comment", "mod_usr_logn_id"}
        for mapping_id in CANDIDATE_UPDATE_IDS
    )
    assert all(changed_fields_by_id[mapping_id] == {"comment"} for mapping_id in COMMENT_ONLY_UPDATE_IDS)
    assert len(artifacts.target_mappings) == 129
    assert len(artifacts.canonical_master) == 21
    assert len(artifacts.canonical_levers) == 16
    assert _candidate_names(artifacts.target_mappings, artifacts.canonical_master) == EXPECTED_CANDIDATE_NAMES

    method_counts = {
        method: sum(row["mapping_method"] == method for row in artifacts.target_mappings)
        for method in EXPECTED_METHOD_COUNTS
    }
    assert method_counts == EXPECTED_METHOD_COUNTS


def test_source_and_final_live_states_both_satisfy_idempotent_preconditions(
    artifacts: RolloutArtifacts,
) -> None:
    _assert_preconditions(
        deepcopy(artifacts.canonical_master),
        deepcopy(artifacts.snapshot_mappings),
        deepcopy(artifacts.canonical_levers),
        artifacts,
    )
    _assert_preconditions(
        deepcopy(artifacts.canonical_master),
        _final_mapping_rows(artifacts),
        deepcopy(artifacts.canonical_levers),
        artifacts,
    )


def test_second_apply_is_a_physical_no_op_for_already_final_mapping_state(
    artifacts: RolloutArtifacts,
) -> None:
    session = Mock()

    updated_count, population_inserted = _apply_mappings(
        session,
        _final_mapping_rows(artifacts),
        artifacts.target_mappings,
        artifacts.snapshot_mappings,
    )

    assert updated_count == 0
    assert population_inserted is False
    session.execute.assert_not_called()


def test_source_apply_targets_only_the_approved_16_rows_and_population(
    artifacts: RolloutArtifacts,
) -> None:
    session = Mock()
    session.execute.return_value = Mock(rowcount=1)

    updated_count, population_inserted = _apply_mappings(
        session,
        artifacts.snapshot_mappings,
        artifacts.target_mappings,
        artifacts.snapshot_mappings,
    )

    assert updated_count == 16
    assert population_inserted is True
    assert session.execute.call_count == 17
    update_calls = session.execute.call_args_list[:-1]
    for mapping_id, call in zip(sorted(UPDATED_MAPPING_IDS), update_calls, strict=True):
        statement, parameters = call.args
        expected_columns = CANDIDATE_DML_COLUMNS if mapping_id in CANDIDATE_UPDATE_IDS else COMMENT_ONLY_DML_COLUMNS
        expected_statement = (
            CANDIDATE_MAPPING_UPDATE if mapping_id in CANDIDATE_UPDATE_IDS else COMMENT_ONLY_MAPPING_UPDATE
        )
        assert statement is expected_statement
        assert set(parameters) == {*expected_columns, "model_param_dimension_map_id"}
        assert parameters["model_param_dimension_map_id"] == mapping_id
    assert session.execute.call_args_list[-1].args[0] is POPULATION_UPSERT


def test_precondition_rejects_any_master_or_impact_lever_drift(
    artifacts: RolloutArtifacts,
) -> None:
    drifted_master = deepcopy(artifacts.canonical_master)
    drifted_master[0]["parameter_hint"] = "unauthorized drift"
    with pytest.raises(RuntimeError, match="master row does not match canonical v4"):
        _assert_preconditions(
            drifted_master,
            deepcopy(artifacts.snapshot_mappings),
            deepcopy(artifacts.canonical_levers),
            artifacts,
        )

    drifted_levers = deepcopy(artifacts.canonical_levers)
    drifted_levers[0]["label"] = "unauthorized drift"
    with pytest.raises(RuntimeError, match="Impact Lever row does not match canonical v4"):
        _assert_preconditions(
            deepcopy(artifacts.canonical_master),
            deepcopy(artifacts.snapshot_mappings),
            drifted_levers,
            artifacts,
        )


def test_precondition_rejects_unapproved_or_hybrid_mapping_state(
    artifacts: RolloutArtifacts,
) -> None:
    unapproved = deepcopy(artifacts.snapshot_mappings)
    next(row for row in unapproved if row["model_param_dimension_map_id"] == 1)["comment"] = "unapproved drift"
    with pytest.raises(RuntimeError, match="unapproved live mapping drift"):
        _assert_preconditions(
            deepcopy(artifacts.canonical_master),
            unapproved,
            deepcopy(artifacts.canonical_levers),
            artifacts,
        )

    hybrid = deepcopy(artifacts.snapshot_mappings)
    target_by_id = _by_id(artifacts.target_mappings, "model_param_dimension_map_id")
    next(row for row in hybrid if row["model_param_dimension_map_id"] == 2)["comment"] = target_by_id[2]["comment"]
    with pytest.raises(RuntimeError, match="neither approved source nor final"):
        _assert_preconditions(
            deepcopy(artifacts.canonical_master),
            hybrid,
            deepcopy(artifacts.canonical_levers),
            artifacts,
        )


def test_document_validation_rejects_a_seventeenth_mapping_change(
    artifacts: RolloutArtifacts,
) -> None:
    target_document = deepcopy(artifacts.target_document)
    next(row for row in target_document["dimension_mappings"] if row["model_param_dimension_map_id"] == 1)[
        "comment"
    ] = "unapproved seventeenth diff"

    with pytest.raises(RuntimeError, match="unapproved mapping target diff"):
        _validate_mapping_target(
            target_document,
            artifacts.canonical_master,
            artifacts.snapshot_mappings,
            artifacts.snapshot_templates,
        )


def test_protected_v4_rows_are_compared_with_all_database_columns(
    artifacts: RolloutArtifacts,
) -> None:
    after_master = deepcopy(artifacts.canonical_master)
    after_master[0]["mod_dtm"] = "2026-08-13T12:00:00.000000"
    with pytest.raises(RuntimeError, match="protected v4 master row changed"):
        _assert_v4_rows_unchanged(
            artifacts.canonical_master,
            after_master,
            artifacts.canonical_levers,
            artifacts.canonical_levers,
        )

    after_levers = deepcopy(artifacts.canonical_levers)
    after_levers[0]["mod_dtm"] = "2026-08-13T12:00:00.000000"
    with pytest.raises(RuntimeError, match="protected v4 Impact Lever row changed"):
        _assert_v4_rows_unchanged(
            artifacts.canonical_master,
            artifacts.canonical_master,
            artifacts.canonical_levers,
            after_levers,
        )


def test_runner_sql_scope_contains_only_mapping_dml() -> None:
    document = (ROOT_DIR / "scripts/model_parameter/apply_model_parameter_v1_v3_mapping.py").read_text(
        encoding="utf-8",
    )
    lowered = document.lower()

    assert "update tmm_mi_model_param_dimension_map" in lowered
    assert "insert into tmm_mi_model_param_dimension_map" in lowered
    assert "update tmm_mi_model_param_m" not in lowered
    assert "insert into tmm_mi_model_param_m" not in lowered
    assert "update tmm_mi_model_impact_lever_m" not in lowered
    assert "insert into tmm_mi_model_impact_lever_m" not in lowered
    assert set(MAPPING_TARGET_COLUMNS) == {
        "use_yn",
        "event_type_l2_id",
        "dimension_key",
        "dimension_label",
        "mapping_method",
        "model_param_id",
        "comment",
        "mod_usr_logn_id",
        "del_yn",
    }
    assert set(CANDIDATE_DML_COLUMNS) == {"mapping_method", "model_param_id", "comment", "mod_usr_logn_id"}
    assert set(COMMENT_ONLY_DML_COLUMNS) == {"comment"}


def test_legacy_resource_query_returns_only_direct_or_routing_definitions() -> None:
    repository = ModelParameterRepository(session=Mock())
    mapping_rules = [
        {"canonical_parameter_name": "GDP", "mapping_method": "direct"},
        {"canonical_parameter_name": "Population", "mapping_method": "routing"},
        {"canonical_parameter_name": "", "mapping_method": "indirect"},
    ]
    definitions = [
        {"canonical_parameter_name": "GDP"},
        {"canonical_parameter_name": "Population"},
        {"canonical_parameter_name": "ShippingCost"},
    ]

    with (
        patch.object(repository, "_fetch_dimension_mapping_rules", return_value=mapping_rules),
        patch.object(repository, "_fetch_model_parameter_definitions", return_value=definitions),
    ):
        actual_rules, actual_definitions = repository.fetch_parameter_mapping_resources()

    assert actual_rules == mapping_rules
    assert actual_definitions == definitions[:2]
