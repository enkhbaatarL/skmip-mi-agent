from __future__ import annotations

import copy

import pytest
from app.errors import ServiceUnavailableAppError, ValidationAppError
from app.persistence.asset_repository import seed_for_snapshot
from app.pipeline.orchestrator import PipelineOrchestrator
from app.pipeline.validation import validate_input
from app.schemas.pipeline import RunMetadata
from app.seed import load_seed_document


@pytest.fixture
def seed_and_metadata() -> tuple[object, RunMetadata]:
    seed = load_seed_document()
    return seed, RunMetadata.model_validate(seed.example1_meta)


def test_examples_one_and_two_run_without_required_clarification(seed_and_metadata: tuple[object, RunMetadata]) -> None:
    seed, metadata = seed_and_metadata
    orchestrator = PipelineOrchestrator(seed)
    assert orchestrator.plan(metadata, seed.example1, {})["canRun"] is True
    metadata2 = RunMetadata.model_validate(seed.example2_meta)
    assert orchestrator.plan(metadata2, seed.example2, {})["canRun"] is True


def test_example_three_requires_timing_answer(seed_and_metadata: tuple[object, RunMetadata]) -> None:
    seed, metadata = seed_and_metadata
    scenario = copy.deepcopy(seed.example1)
    scenario["eventImpactFacts"][0]["timing"] = "다가오는 동절기 후반"
    orchestrator = PipelineOrchestrator(seed)
    plan = orchestrator.plan(metadata, scenario, {})
    assert plan["canRun"] is False
    assert [item["questionId"] for item in plan["clarifications"] if item["required"]] == ["timing_event_101"]
    with pytest.raises(ValidationAppError):
        orchestrator.run(metadata, scenario, {}, {})
    result = orchestrator.run(metadata, scenario, {"timing_event_101": "2027-12:2028-02"}, {})
    assert result["horizon"]["start"] == "2027-12"


def test_metadata_mismatch_duplicate_dimension_and_unknown_value(seed_and_metadata: tuple[object, RunMetadata]) -> None:
    seed, _ = seed_and_metadata
    scenario = copy.deepcopy(seed.example1)
    scenario["dimensionDefinitions"].append(copy.deepcopy(scenario["dimensionDefinitions"][0]))
    scenario["scenarios"][0]["dimensionValues"]["cold_wave_intensity"] = "unknown"
    report = validate_input(RunMetadata(mi_event_ids=[999], target_market="JKM"), scenario, seed, 1_048_576)
    codes = {item["code"] for item in report["messages"]}
    assert {"EVENT_ID_MISMATCH", "DUPLICATE_DIMENSION", "UNKNOWN_DIMENSION_VALUE"}.issubset(codes)


def test_duplicate_event_fact_and_metadata_ids_are_rejected(seed_and_metadata: tuple[object, RunMetadata]) -> None:
    seed, metadata = seed_and_metadata
    scenario = copy.deepcopy(seed.example1)
    scenario["eventImpactFacts"].append(copy.deepcopy(scenario["eventImpactFacts"][0]))
    report = validate_input(metadata, scenario, seed, 1_048_576)
    assert "DUPLICATE_EVENT_ID" in {item["code"] for item in report["messages"]}

    report = validate_input(
        RunMetadata.model_construct(mi_event_ids=[101, 101, 202], target_market="JKM", comparison_run_id=None),
        seed.example1,
        seed,
        1_048_576,
    )
    assert "DUPLICATE_METADATA_EVENT_ID" in {item["code"] for item in report["messages"]}


def test_runtime_seed_refuses_incomplete_asset_snapshot(seed_and_metadata: tuple[object, RunMetadata]) -> None:
    seed, _ = seed_and_metadata
    with pytest.raises(ServiceUnavailableAppError) as error:
        seed_for_snapshot(object(), {}, seed)  # type: ignore[arg-type]
    assert error.value.status_code == 503
    assert "memory:default_memory" in error.value.details["missingAssets"]


@pytest.mark.parametrize("invalid_facts", ["not-a-list", None, ["not-an-object"]])
def test_schema_invalid_event_facts_return_plan_errors_instead_of_crashing(
    seed_and_metadata: tuple[object, RunMetadata], invalid_facts: object
) -> None:
    seed, metadata = seed_and_metadata
    scenario = copy.deepcopy(seed.example1)
    scenario["eventImpactFacts"] = invalid_facts
    plan = PipelineOrchestrator(seed).plan(metadata, scenario, {})
    assert plan["canRun"] is False
    assert any(item["code"] == "SCHEMA_ERROR" for item in plan["validationReport"]["messages"])


def test_pipeline_has_nine_artifacts_and_single_structured_result_source(
    seed_and_metadata: tuple[object, RunMetadata],
) -> None:
    seed, metadata = seed_and_metadata
    result = PipelineOrchestrator(seed).run(metadata, seed.example1, {}, {})
    assert [item["stepId"] for item in result["artifacts"]] == [item["stepId"] for item in seed.flow_profile["steps"]]
    assert len(result["artifacts"]) == 9
    assert all(result["evaluationInvariants"].values())
    assert all(
        proposal["parameterCode"] in proposal["formula"]
        for scenario in result["scenarios"]
        for proposal in scenario["proposals"]
    )
    assert all(
        point["proposed"] - point["baseline"] == pytest.approx(point["delta"], abs=1e-5)
        for scenario in result["scenarios"]
        for proposal in scenario["proposals"]
        for point in proposal["series"]
    )
    for scenario in result["scenarios"]:
        for proposal in scenario["proposals"]:
            peak_point = max(proposal["series"], key=lambda point: abs(point["deltaPercent"]))
            assert proposal["baselinePeak"] == peak_point["baseline"]
            assert proposal["proposedPeak"] == peak_point["proposed"]
            assert proposal["delta"] == peak_point["delta"]
            assert proposal["deltaPercent"] == peak_point["deltaPercent"]
            assert proposal["trace"][-1]["data"]["peakMonth"] == peak_point["month"]
