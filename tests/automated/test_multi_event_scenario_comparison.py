from __future__ import annotations

# ruff: noqa: ANN401, ASYNC240, CPY001, S101, SLF001
import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from tests.manual import test_multi_event_scenario_versions as runner
from tests.manual.multi_event_comparison.quality import run_deterministic_checks
from tests.manual.multi_event_comparison.report import render_report


PRESSURE_BANDS = [
    "strong_bullish",
    "bullish",
    "balanced",
    "bearish",
    "strong_bearish",
]


def _dimension(index: int) -> dict[str, Any]:
    return {
        "dimensionId": f"d{index}",
        "label": f"Dimension {index}",
        "description": "LNG price driver",
        "sourceEventIds": [101, 202],
        "values": [
            {"valueId": "high", "label": "High"},
            {"valueId": "low", "label": "Low"},
        ],
    }


def _response(version: str = "v2") -> dict[str, Any]:
    rows = [
        {
            "scenarioId": 1,
            "title": "Ceiling",
            "narrative": "Supply and demand tighten together.",
            "cells": {"d0": "high", "d1": "high"},
            "globalPressureBand": "strong_bullish",
            "scenarioRole": "ceiling",
            "baselineYn": "N",
            "probabilityScore": 20,
            "globalPressureRationale": "Tight supply raises price pressure.",
        },
        {
            "scenarioId": 2,
            "title": "Mixed",
            "narrative": "Supply tightness is offset by mitigation.",
            "cells": {"d0": "high", "d1": "low"},
            "globalPressureBand": "balanced",
            "scenarioRole": "mixed",
            "baselineYn": "Y",
            "probabilityScore": 60,
            "globalPressureRationale": "Opposing drivers are balanced.",
        },
        {
            "scenarioId": 3,
            "title": "Floor",
            "narrative": "Supply recovers while demand softens.",
            "cells": {"d0": "low", "d1": "low"},
            "globalPressureBand": "strong_bearish",
            "scenarioRole": "floor",
            "baselineYn": "N",
            "probabilityScore": 20,
            "globalPressureRationale": "Recovery lowers price pressure.",
        },
    ]
    dimension_count = {"v2": 5, "v3": 4, "v4": 3}[version]
    return {
        "status": "success",
        "message": "성공",
        "data": {
            "apiVersion": version,
            "generationStrategy": f"{version}-strategy",
            "comparisonRunId": "compare-1",
            "scenarioGroup": {
                "scenarioGroupId": {"v2": 20, "v3": 30, "v4": 40}[version],
                "title": f"{version} group",
                "scenarioCount": 3,
            },
            "events": [{"miEventId": 101}, {"miEventId": 202}],
            "dimensionDefinitions": [_dimension(index) for index in range(dimension_count)],
            "table": {
                "headers": [{"key": "d0", "label": "D0"}, {"key": "d1", "label": "D1"}],
                "rows": rows,
            },
            "generationDiagnostics": {
                "targetPressureBands": PRESSURE_BANDS,
                "excludedCandidates": [
                    {"globalPressureBand": "bullish", "reasonCode": "LOW_PROBABILITY", "reason": "x"},
                    {"globalPressureBand": "bearish", "reasonCode": "LOW_PROBABILITY", "reason": "y"},
                ],
            },
            "usage": {"totalTokens": 100},
        },
    }


def _manifest(tmp_path: Path) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "batchId": "batch-1",
        "baseUrl": "http://agent.test",
        "userId": 10603,
        "comparisonRunId": "compare-1",
        "eventIds": [101, 202],
        "events": [
            {"event": {"miEventId": 101, "title": "Event A", "oneLineSummary": "A"}},
            {"event": {"miEventId": 202, "title": "Event B", "oneLineSummary": "B"}},
        ],
        "selection": {"description": "명시 Event IDs: [101, 202]"},
        "artifacts": {version: str(tmp_path / f"{version}_create_response.json") for version in ("v2", "v3", "v4")}
        | {
            "judge": str(tmp_path / "comparison_judge.json"),
            "report": str(tmp_path / "comparison_report.md"),
        },
    }


def test_prepare_validation_accepts_only_two_to_five_unique_events() -> None:
    valid = argparse.Namespace(
        event_ids=[101, 202],
        keyword=None,
        event_count=None,
        event_page_size=100,
        comparison_run_id=None,
    )
    runner._validate_prepare_args(valid)

    duplicate = argparse.Namespace(
        event_ids=[101, 101],
        keyword=None,
        event_count=None,
        event_page_size=100,
        comparison_run_id=None,
    )
    with pytest.raises(ValueError, match="duplicates"):
        runner._validate_prepare_args(duplicate)


def test_deterministic_checks_cover_structure_roles_lineage_and_pressure_bands() -> None:
    results = run_deterministic_checks("v2", _response("v2"), [101, 202])

    assert {result.check_id for result in results} == {f"M-{index:02d}" for index in range(1, 9)}
    assert {result.status for result in results} == {"PASS"}


def test_deterministic_checks_reject_wrong_extrema_and_missing_lineage() -> None:
    response = _response("v3")
    response["data"]["table"]["rows"][0]["scenarioRole"] = "floor"
    response["data"]["table"]["rows"][2]["scenarioRole"] = "ceiling"
    for dimension in response["data"]["dimensionDefinitions"]:
        dimension["sourceEventIds"] = [101]

    results = {result.check_id: result for result in run_deterministic_checks("v3", response, [101, 202])}

    assert results["M-04"].status == "FAIL"
    assert results["M-06"].status == "FAIL"
    assert results["M-06"].offenders == ["202"]


def test_report_without_quality_keeps_actual_values_and_omits_ranking(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    artifacts = {
        "v2": {
            "transportStatus": "success",
            "httpStatus": 200,
            "elapsedMs": 123,
            "response": _response("v2"),
        },
        "v3": {"transportStatus": "not_run", "error": "artifact missing"},
        "v4": {"transportStatus": "not_run", "error": "artifact missing"},
    }

    report = render_report(manifest, artifacts, {}, None, quality_check=False)

    assert "Ceiling" in report
    assert "Tight supply raises price pressure." in report
    assert "품질검사를 제외" in report
    assert "우수 버전:" not in report


def test_version_claim_is_exclusive(tmp_path: Path) -> None:
    claim_path = tmp_path / "v2.running.lock"

    runner._claim_version(claim_path, "v2")

    with pytest.raises(FileExistsError, match="already claimed"):
        runner._claim_version(claim_path, "v2")


def test_run_version_sends_v4_global_request_once_and_persists_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest(tmp_path)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    for version in ("v2", "v3"):
        (tmp_path / f"{version}_create_response.json").write_text("{}", encoding="utf-8")
    calls: list[tuple[str, dict[str, Any]]] = []

    class FakeResponse:
        status_code = 200
        is_success = True
        text = ""

        def json(self) -> dict[str, Any]:
            return _response("v4")

    class FakeClient:
        def __init__(self, **_: Any) -> None:
            pass

        async def __aenter__(self) -> FakeClient:
            return self

        async def __aexit__(self, *_: Any) -> None:
            return None

        async def post(self, url: str, *, json: dict[str, Any]) -> FakeResponse:
            calls.append((url, json))
            return FakeResponse()

    monkeypatch.setattr(runner.httpx, "AsyncClient", FakeClient)
    args = argparse.Namespace(manifest=manifest_path, version="v4", timeout=1200)

    exit_code = asyncio.run(runner.run_version(args))

    assert exit_code == 0
    assert calls == [
        (
            "http://agent.test/v4/scenario-groups/sync",
            {
                "miEventIds": [101, 202],
                "userId": 10603,
                "comparisonRunId": "compare-1",
            },
        ),
    ]
    artifact = json.loads((tmp_path / "v4_create_response.json").read_text(encoding="utf-8"))
    assert artifact["attemptCount"] == 1
    assert artifact["retryPolicy"] == "disabled"
    assert not (tmp_path / "v4_create_response.running.lock").exists()


def test_v4_requires_v2_v3_artifact_barrier(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    args = argparse.Namespace(manifest=manifest_path, version="v4", timeout=1200)

    with pytest.raises(ValueError, match="completed v2/v3 artifacts"):
        asyncio.run(runner.run_version(args))


def test_success_response_must_match_manifest_contract(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    response = _response("v2")
    response["data"]["comparisonRunId"] = "wrong-run"

    with pytest.raises(ValueError, match="comparisonRunId mismatch"):
        runner._validate_version_response(response, manifest, "v2")


def test_timeout_is_recorded_as_unknown_and_cannot_be_retried(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest(tmp_path)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    class TimeoutClient:
        def __init__(self, **_: Any) -> None:
            pass

        async def __aenter__(self) -> TimeoutClient:
            return self

        async def __aexit__(self, *_: Any) -> None:
            return None

        async def post(self, *_: Any, **__: Any) -> None:
            msg = "timed out"
            raise runner.httpx.ReadTimeout(msg)

    monkeypatch.setattr(runner.httpx, "AsyncClient", TimeoutClient)
    args = argparse.Namespace(manifest=manifest_path, version="v2", timeout=1)

    assert asyncio.run(runner.run_version(args)) == 1
    artifact = json.loads((tmp_path / "v2_create_response.json").read_text(encoding="utf-8"))
    assert artifact["outcome"] == "unknown"
    assert "재호출하지 말고" in artifact["error"]
    with pytest.raises(FileExistsError):
        asyncio.run(runner.run_version(args))


def test_judge_failure_still_writes_factual_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest(tmp_path)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    for version in ("v2", "v3", "v4"):
        artifact = {
            "transportStatus": "success",
            "outcome": "success",
            "httpStatus": 200,
            "elapsedMs": 10,
            "response": _response(version),
        }
        Path(manifest["artifacts"][version]).write_text(json.dumps(artifact), encoding="utf-8")

    async def fail_judge(_: dict[str, Any]) -> None:
        msg = "judge unavailable"
        raise RuntimeError(msg)

    monkeypatch.setattr(runner, "judge_comparison", fail_judge)
    args = argparse.Namespace(manifest=manifest_path, quality_check=True)

    report_path = asyncio.run(runner.report(args))

    report = report_path.read_text(encoding="utf-8")
    assert "판정 불가" in report
    assert "judge unavailable" in report
    judge_artifact = json.loads(Path(manifest["artifacts"]["judge"]).read_text(encoding="utf-8"))
    assert judge_artifact["status"] == "error"


def test_fallback_orchestration_runs_v2_v3_together_before_v4(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest(tmp_path)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    started: set[str] = set()
    finished: set[str] = set()
    phase_one_ready = asyncio.Event()

    async def fake_run_version(args: argparse.Namespace) -> int:
        version = str(args.version)
        if version in {"v2", "v3"}:
            started.add(version)
            if started == {"v2", "v3"}:
                phase_one_ready.set()
            await phase_one_ready.wait()
            Path(manifest["artifacts"][version]).write_text("{}", encoding="utf-8")
            finished.add(version)
            return 0
        assert finished == {"v2", "v3"}
        Path(manifest["artifacts"]["v4"]).write_text("{}", encoding="utf-8")
        finished.add("v4")
        return 0

    monkeypatch.setattr(runner, "run_version", fake_run_version)
    args = argparse.Namespace(manifest=manifest_path, timeout=1200)

    assert asyncio.run(runner.orchestrate(args)) == 0
    assert finished == {"v2", "v3", "v4"}
    orchestration_path = tmp_path / "orchestration.json"
    orchestration = json.loads(orchestration_path.read_text(encoding="utf-8"))
    assert orchestration["mode"] == "async_fallback"
