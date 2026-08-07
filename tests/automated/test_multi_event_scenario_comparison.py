from __future__ import annotations

# ruff: noqa: ANN401, ASYNC240, CPY001, S101, SLF001
import argparse
import asyncio
import json
from pathlib import Path
import sys
from typing import Any

import pytest

from tests.manual import test_multi_event_scenario_versions as runner
from tests.manual.multi_event_comparison.llm import build_agent_judge_input
from tests.manual.multi_event_comparison.quality import run_deterministic_checks
from tests.manual.multi_event_comparison.report import render_report


PRESSURE_BANDS = [
    "strong_bullish",
    "bullish",
    "balanced",
    "bearish",
    "strong_bearish",
]


def _dimension(index: int, version: str) -> dict[str, Any]:
    dimension = {
        "dimensionId": f"d{index}",
        "label": f"Dimension {index}",
        "description": "LNG price driver",
        "sourceEventIds": [101, 202],
        "values": [
            {
                "valueId": "high",
                "label": "High",
                "pressureContribution": "bullish contribution",
                "sourceAssignments": [{"rationale": "Event fact supports High."}] if version == "v2" else [],
            },
            {
                "valueId": "low",
                "label": "Low",
                "pressureContribution": "bearish contribution",
                "sourceAssignments": [{"rationale": "Event fact supports Low."}] if version == "v2" else [],
            },
        ],
    }
    if version == "v3":
        dimension["rationale"] = "v3 dimension rationale"
    else:
        dimension["selectionRationale"] = f"{version} dimension selection rationale"
    return dimension


def _response(version: str = "v2") -> dict[str, Any]:
    rows = [
        {
            "scenarioId": 1,
            "title": "Ceiling",
            "narrative": "Supply and demand tighten together.",
            "cells": {"d0": "high", "d1": "high"},
            "pressureBand": "strong_bullish",
            "pressureTarget": "JKM",
            "scenarioRole": "ceiling",
            "baselineYn": "N",
            "probabilityScore": 20,
            "pressureRationale": "Tight supply raises price pressure.",
        },
        {
            "scenarioId": 2,
            "title": "Mixed",
            "narrative": "Supply tightness is offset by mitigation.",
            "cells": {"d0": "high", "d1": "low"},
            "pressureBand": "balanced",
            "pressureTarget": "JKM",
            "scenarioRole": "mixed",
            "baselineYn": "Y",
            "probabilityScore": 60,
            "pressureRationale": "Opposing drivers are balanced.",
        },
        {
            "scenarioId": 3,
            "title": "Floor",
            "narrative": "Supply recovers while demand softens.",
            "cells": {"d0": "low", "d1": "low"},
            "pressureBand": "strong_bearish",
            "pressureTarget": "JKM",
            "scenarioRole": "floor",
            "baselineYn": "N",
            "probabilityScore": 20,
            "pressureRationale": "Recovery lowers price pressure.",
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
                "summary": f"{version} group summary",
                "description": f"{version} group description",
                "scenarioCount": 3,
            },
            "events": [{"miEventId": 101}, {"miEventId": 202}],
            "dimensionDefinitions": [_dimension(index, version) for index in range(dimension_count)],
            "table": {
                "headers": [{"key": "d0", "label": "D0"}, {"key": "d1", "label": "D1"}],
                "rows": rows,
            },
            "generationDiagnostics": {
                "targetPressureBands": PRESSURE_BANDS,
                "excludedCandidates": [
                    {"pressureBand": "bullish", "reasonCode": "LOW_PROBABILITY", "reason": "x"},
                    {"pressureBand": "bearish", "reasonCode": "LOW_PROBABILITY", "reason": "y"},
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
            {
                "event": {
                    "miEventId": 101,
                    "title": "Event A",
                    "oneLineSummary": "A",
                    "occurredAt": "2026-01-01T00:00:00",
                    "eventTypeL1": {"label": "Supply"},
                    "eventTypeL2": {"label": "Production"},
                    "tags": ["LNG", "supply"],
                    "keyBullets": ["Observed Event A fact."],
                    "detailAnalysis": "Event A detailed analysis.",
                },
            },
            {"event": {"miEventId": 202, "title": "Event B", "oneLineSummary": "B"}},
        ],
        "selection": {"description": "명시 Event IDs: [101, 202]"},
        "artifacts": {version: str(tmp_path / f"{version}_create_response.json") for version in ("v2", "v3", "v4")}
        | {
            "judge": str(tmp_path / "comparison_judge.json"),
            "report": str(tmp_path / "comparison_report.md"),
        },
    }


def _agent_judgment() -> dict[str, Any]:
    versions: list[dict[str, Any]] = []
    scores = {"v2": 3, "v3": 4, "v4": 5}
    for version, score in scores.items():
        response = _response(version)
        versions.append(
            {
                "apiVersion": version,
                "criteria": [
                    {
                        "criterion": criterion,
                        "score": score,
                        "verdict": "PASS" if score >= 4 else "WARN",
                        "evidence": [f"versions.{version}.data.table"],
                        "rationale": f"{version} rationale",
                    }
                    for criterion in (
                        "event_consistency",
                        "lng_dimension_quality",
                        "floor_ceiling_quality",
                        "mixed_quality",
                    )
                ],
                "scenarioJudgments": [
                    {
                        "scenarioId": str(row["scenarioId"]),
                        "title": row["title"],
                        "pressureBand": row["pressureBand"],
                        "verdict": "PASS",
                        "evidence": [f"scenarioId={row['scenarioId']}"],
                        "rationale": "coherent",
                    }
                    for row in response["data"]["table"]["rows"]
                ],
                "strengths": ["grounded"],
                "weaknesses": [],
            },
        )
    pairwise_criteria = (
        "event_grounding",
        "dimension_and_value_quality",
        "scenario_logic_and_explainability",
        "baseline_and_exclusion_quality",
        "user_comprehensibility",
    )
    pairwise_comparisons = []
    for left, right, winner in (("v2", "v3", "v3"), ("v2", "v4", "v4"), ("v3", "v4", "v4")):
        pairwise_comparisons.append(
            {
                "leftVersion": left,
                "rightVersion": right,
                "criteria": [
                    {
                        "criterion": criterion,
                        "winner": winner,
                        "evidence": [f"{left} and {right} evidence"],
                        "counterargument": f"{left}에도 장점이 있다.",
                        "rationale": f"{winner}가 {criterion}에서 우세하다.",
                    }
                    for criterion in pairwise_criteria
                ],
                "overallWinner": winner,
                "summary": f"{winner}가 직접 비교에서 우세하다.",
            },
        )
    return {
        "versions": versions,
        "pairwiseComparisons": pairwise_comparisons,
        "bestVersions": ["v4"],
        "qualityRecommendation": {
            "versions": ["v4"],
            "rationale": "근거와 설명 가능성이 가장 좋다.",
            "tradeoffs": ["토큰이 더 필요하다."],
            "selectionCondition": "품질을 우선할 때",
        },
        "practicalRecommendation": {
            "versions": ["v2"],
            "rationale": "충분한 품질을 낮은 비용으로 제공한다.",
            "tradeoffs": ["Dimension 독립성은 v4보다 낮다."],
            "selectionCondition": "비용과 속도도 중요할 때",
        },
        "conclusion": "품질은 v4, 실용 선택은 v2다.",
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


def test_prepare_defaults_to_delete_existing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "test_multi_event_scenario_versions.py",
            "prepare",
            "--event-ids",
            "101",
            "202",
        ],
    )

    args = runner.parse_args()

    assert args.delete_existing is True


def test_prepare_allows_disabling_delete_existing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "test_multi_event_scenario_versions.py",
            "prepare",
            "--event-ids",
            "101",
            "202",
            "--no-delete-existing",
        ],
    )

    args = runner.parse_args()

    assert args.delete_existing is False


def test_prepare_accepts_v4_only_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "test_multi_event_scenario_versions.py",
            "prepare",
            "--event-ids",
            "101",
            "202",
            "--v4-only",
        ],
    )

    args = runner.parse_args()

    assert args.v4_only is True


def test_prepare_v4_only_writes_scoped_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Target:
        base_url = "http://agent.test"
        user_id = 10603

    class FakeResponse:
        def __init__(self, event_id: int) -> None:
            self.event_id = event_id

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {"event": {"miEventId": self.event_id, "title": f"Event {self.event_id}"}}

    class FakeClient:
        def __init__(self, **_: Any) -> None:
            pass

        async def __aenter__(self) -> FakeClient:
            return self

        async def __aexit__(self, *_: Any) -> None:
            return None

        async def get(self, url: str) -> FakeResponse:
            return FakeResponse(int(url.rsplit("/", maxsplit=1)[1]))

    monkeypatch.setattr(runner, "load_runtime_target", lambda **_: Target())
    monkeypatch.setattr(runner.httpx, "AsyncClient", FakeClient)
    args = argparse.Namespace(
        agent=None,
        base_url="http://agent.test",
        user_id=10603,
        test_info=None,
        timeout=120,
        event_ids=[101, 202],
        event_count=None,
        event_sort="latest",
        keyword=None,
        event_page_size=100,
        comparison_run_id=None,
        batch_id="v4-only-test",
        output_root=tmp_path,
        v4_only=True,
        delete_existing=False,
        admin_token=None,
    )

    manifest_path = asyncio.run(runner.prepare(args))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["versions"] == ["v4"]
    assert manifest["executionMode"] == "v4-only"
    assert manifest["comparisonRunId"] == "v4-only-v4-only-test"
    assert "v4" in manifest["artifacts"]
    assert "v2" not in manifest["artifacts"]
    assert "v3" not in manifest["artifacts"]


def test_soft_delete_existing_groups_deduplicates_groups_across_events() -> None:
    calls: list[tuple[str, dict[str, Any], dict[str, str] | None]] = []

    class FakeResponse:
        def __init__(self, payload: dict[str, Any]) -> None:
            self.payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return self.payload

    class FakeClient:
        async def get(self, _: str, *, params: dict[str, Any]) -> FakeResponse:
            event_id = int(params["miEventId"])
            rows = {
                101: [{"scenarioGroupId": 10}, {"scenarioGroupId": 20}],
                202: [{"scenarioGroupId": 20}],
            }[event_id]
            return FakeResponse({"rows": rows})

        async def request(
            self,
            method: str,
            url: str,
            *,
            json: dict[str, Any],
            headers: dict[str, str] | None,
        ) -> FakeResponse:
            assert method == "DELETE"
            calls.append((url, json, headers))
            return FakeResponse({"scenarioGroupDeleted": 1, "scenarioDeleted": 3, "signpostDeleted": 0})

    results = asyncio.run(
        runner._soft_delete_existing_groups(
            FakeClient(),
            base_url="http://agent.test",
            event_ids=[101, 202],
            user_id=10603,
            admin_token="admin-token",  # noqa: S106
        ),
    )

    assert [item["scenarioGroupId"] for item in results] == [10, 20]
    assert results[1]["matchedEventIds"] == [101, 202]
    assert calls == [
        (
            "http://agent.test/scenario-groups/10",
            {"userId": 10603},
            {"Authorization": "Bearer admin-token"},
        ),
        (
            "http://agent.test/scenario-groups/20",
            {"userId": 10603},
            {"Authorization": "Bearer admin-token"},
        ),
    ]


def test_soft_delete_existing_groups_requires_admin_token_when_groups_exist() -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {"rows": [{"scenarioGroupId": 10}]}

    class FakeClient:
        async def get(self, _: str, *, params: dict[str, Any]) -> FakeResponse:
            return FakeResponse()

    with pytest.raises(ValueError, match="no admin token"):
        asyncio.run(
            runner._soft_delete_existing_groups(
                FakeClient(),
                base_url="http://agent.test",
                event_ids=[101, 202],
                user_id=10603,
                admin_token=None,
            ),
        )


def test_deterministic_checks_cover_structure_roles_lineage_and_pressure_bands() -> None:
    results = run_deterministic_checks("v2", _response("v2"), [101, 202])

    assert {result.check_id for result in results} == {f"M-{index:02d}" for index in range(1, 9)}
    assert {result.status for result in results} == {"PASS"}


def test_deterministic_checks_allow_missing_optional_mixed_role() -> None:
    response = _response("v3")
    response["data"]["table"]["rows"][1]["scenarioRole"] = None

    results = {result.check_id: result for result in run_deterministic_checks("v3", response, [101, 202])}

    assert results["M-04"].status == "PASS"


def test_agent_judge_rubric_does_not_require_optional_bands_or_mixed() -> None:
    judge_input = build_agent_judge_input({"versions": {}})

    floor_criterion = judge_input["criteria"]["floor_ceiling_quality"]
    mixed_criterion = judge_input["criteria"]["mixed_quality"]
    constraints = " ".join(judge_input["constraints"])

    assert "존재 자체를 요구하지 말고" in floor_criterion
    assert "mixed는 optional" in mixed_criterion
    assert "Do not penalize a missing pressure band" in constraints
    assert "Do not penalize the absence of an optional mixed scenario" in constraints


def test_agent_judge_requires_direct_pairwise_comparison_and_separate_recommendations() -> None:
    judge_input = build_agent_judge_input({"versions": {}, "performance": {}})

    assert set(judge_input["pairwiseCriteria"]) == {
        "event_grounding",
        "dimension_and_value_quality",
        "scenario_logic_and_explainability",
        "baseline_and_exclusion_quality",
        "user_comprehensibility",
    }
    constraints = " ".join(judge_input["constraints"])
    assert "absolute criteria scores as eligibility" in constraints
    assert "every unordered successful-version pair" in constraints
    assert "qualityRecommendation" in constraints
    assert "practicalRecommendation" in constraints


def test_v2_pressure_coverage_accepts_server_derived_unrepresented_bands() -> None:
    response = _response("v2")
    response["data"]["generationDiagnostics"] = {
        "targetPressureBands": PRESSURE_BANDS,
        "unrepresentedPressureBands": ["bullish", "bearish"],
    }

    results = {result.check_id: result for result in run_deterministic_checks("v2", response, [101, 202])}

    assert results["M-08"].status == "PASS"


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


def test_report_explains_failed_deterministic_check_in_plain_language(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    response = _response("v2")
    for dimension in response["data"]["dimensionDefinitions"]:
        dimension["sourceEventIds"] = [101]
    artifacts = {
        "v2": {
            "transportStatus": "success",
            "httpStatus": 200,
            "elapsedMs": 123,
            "response": response,
        },
    }
    checks = {"v2": run_deterministic_checks("v2", response, [101, 202])}

    report = render_report(manifest, artifacts, checks, None, quality_check=True)

    assert "### FAIL 항목 상세 설명" in report
    assert "#### v2 · M-06 — 전체 Event의 Dimension lineage 포함 여부" in report
    assert "선택된 모든 Event가 적어도 하나의 Dimension 또는 Value source에 연결됐는지" in report
    assert "Event `202`이 어떤 Dimension lineage에도 포함되지 않았습니다" in report
    assert "multi-event 시나리오가 입력 전체를 대표하지 못합니다" in report
    assert "sourceEventIds/sourceRefs/sourceAssignments" in report


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
    assert "비교 범위: **v2/v3/v4 create API**" in report
    assert "사전 Scenario Group 정리: 미실행" in report
    assert "### 입력 Event 상세" in report
    assert "#### 101 · Event A" in report
    assert "Event Type: Supply / Production" in report
    assert "Observed Event A fact." in report
    assert "Event A detailed analysis." in report
    assert "#### Scenario Group 설명" in report
    assert "v2 group description" in report
    assert "#### 시나리오별 Dimension Value" in report
    assert "| Scenario ID · 레이블 | scenario_role | pressure_band | Dimension 0 | Dimension 1 |" in report
    assert "| 1 · Ceiling | ceiling | strong_bullish | High | High |" in report
    assert "| 2 · Mixed | mixed | balanced | High | Low |" in report
    assert "| 3 · Floor | floor | strong_bearish | Low | Low |" in report
    assert "#### 시나리오별 Dimension/Value 선택 근거" in report
    assert "v2 dimension selection rationale" in report
    assert "Event fact supports High." in report
    assert "Dimension 0 = High; Dimension 1 = High" in report
    assert '"d0": "high"' not in report
    assert "품질검사를 제외" in report
    assert "우수 버전:" not in report


def test_report_uses_each_versions_available_dimension_and_value_rationale(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    artifacts = {
        version: {
            "transportStatus": "success",
            "httpStatus": 200,
            "elapsedMs": 123,
            "response": _response(version),
        }
        for version in ("v2", "v3", "v4")
    }

    report = render_report(manifest, artifacts, {}, None, quality_check=False)

    assert "v2 dimension selection rationale" in report
    assert "v3 dimension rationale" in report
    assert "v4 dimension selection rationale" in report
    assert "Event fact supports High." in report
    assert "가격 압력 기여: bullish contribution" in report


def test_report_resolves_v4_label_based_cells(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    response = _response("v4")
    dimensions = response["data"]["dimensionDefinitions"]
    rows = response["data"]["table"]["rows"]
    for row in rows:
        for dimension in dimensions:
            dimension_id = dimension["dimensionId"]
            selected_id = row["cells"].get(dimension_id)
            selected = next(
                (value for value in dimension["values"] if value["valueId"] == selected_id),
                None,
            )
            if selected is not None:
                row["cells"][dimension_id] = selected["label"]
    artifacts = {
        "v4": {
            "transportStatus": "success",
            "httpStatus": 200,
            "elapsedMs": 123,
            "response": response,
        },
    }

    report = render_report(manifest, artifacts, {}, None, quality_check=False)

    assert "미정의 Value" not in report
    assert "| 1 · Ceiling | ceiling | strong_bullish | High | High |" in report


def test_version_claim_is_exclusive(tmp_path: Path) -> None:
    claim_path = tmp_path / "v2.running.lock"

    runner._claim_version(claim_path, "v2")

    with pytest.raises(FileExistsError, match="already claimed"):
        runner._claim_version(claim_path, "v2")


def test_run_version_sends_v4_only_request_without_v2_v3_barrier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _manifest(tmp_path)
    manifest["versions"] = ["v4"]
    manifest["executionMode"] = "v4-only"
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
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


def test_v4_only_manifest_rejects_v2_execution(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    manifest["versions"] = ["v4"]
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="outside this manifest's execution scope"):
        asyncio.run(
            runner.run_version(argparse.Namespace(manifest=manifest_path, version="v2", timeout=1200)),
        )


def test_v4_requires_v2_v3_artifact_barrier(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    args = argparse.Namespace(manifest=manifest_path, version="v4", timeout=1200)

    with pytest.raises(ValueError, match="completed v2/v3 artifacts"):
        asyncio.run(runner.run_version(args))


def test_v4_only_report_contains_only_v4_and_skips_relative_judge(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    manifest["versions"] = ["v4"]
    manifest["executionMode"] = "v4-only"
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    Path(manifest["artifacts"]["v4"]).write_text(
        json.dumps(
            {
                "transportStatus": "success",
                "outcome": "success",
                "httpStatus": 200,
                "elapsedMs": 10,
                "response": _response("v4"),
            },
        ),
        encoding="utf-8",
    )

    report_path = asyncio.run(
        runner.report(argparse.Namespace(manifest=manifest_path, quality_check=True)),
    )

    report = report_path.read_text(encoding="utf-8")
    assert "# V4 Multi-Event Scenario API Run" in report
    assert "실행 범위: **v4 create API only**" in report
    assert "실행 방식: **v4-only**" in report
    assert "| v4 | Y | 200 | 40 | 10 | 100 |" in report
    assert "| v2 |" not in report
    assert "| v3 |" not in report
    assert "v4-only 실행은 상대 비교 대상이 없으므로" in report
    assert not (tmp_path / "comparison_judge_input.json").exists()


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


def test_invalid_agent_judge_still_writes_factual_report_and_input(tmp_path: Path) -> None:
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

    Path(manifest["artifacts"]["judge"]).write_text("{}", encoding="utf-8")
    args = argparse.Namespace(manifest=manifest_path, quality_check=True)

    report_path = asyncio.run(runner.report(args))

    report = report_path.read_text(encoding="utf-8")
    assert "판정 불가" in report
    assert "agent judge result validation failure" in report
    judge_input = json.loads((tmp_path / "comparison_judge_input.json").read_text(encoding="utf-8"))
    assert judge_input["judgeRuntime"].endswith("Do not call an LLM API.")
    assert set(judge_input["evidence"]["versions"]) == {"v2", "v3", "v4"}
    assert judge_input["evidence"]["performance"] == {
        "v2": {"elapsedMs": 10, "totalTokens": 100},
        "v3": {"elapsedMs": 10, "totalTokens": 100},
        "v4": {"elapsedMs": 10, "totalTokens": 100},
    }
    judge_artifact = json.loads(Path(manifest["artifacts"]["judge"]).read_text(encoding="utf-8"))
    assert judge_artifact == {}


def test_valid_agent_judge_is_loaded_without_an_api_call(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    for version in ("v2", "v3", "v4"):
        Path(manifest["artifacts"][version]).write_text(
            json.dumps(
                {
                    "transportStatus": "success",
                    "outcome": "success",
                    "httpStatus": 200,
                    "elapsedMs": 10,
                    "response": _response(version),
                },
            ),
            encoding="utf-8",
        )
    Path(manifest["artifacts"]["judge"]).write_text(json.dumps(_agent_judgment()), encoding="utf-8")

    report_path = asyncio.run(runner.report(argparse.Namespace(manifest=manifest_path, quality_check=True)))

    report = report_path.read_text(encoding="utf-8")
    assert "**절대 점수 최고 버전:** v4" in report
    assert "### 버전별 절대 점수 단순 평균" in report
    assert "| v4 | event_consistency 5/5; lng_dimension_quality 5/5;" in report
    assert "| 5.00/5 | Y |" in report
    assert "### 버전별 잘한 점과 아쉬운 점" in report
    assert "### Pairwise 직접 상대평가" in report
    assert "#### v2 vs v3 — 종합 승자: v3" in report
    assert "| 비교 기준 | 승자 | 실제 evidence | 반론 | 최종 rationale |" in report
    assert "#### 품질 우선 — v4" in report
    assert "#### 비용·속도 포함 실용 선택 — v2" in report
    scenario_judge = report.split("### Scenario별 Agent Judge 판단", maxsplit=1)[1]
    assert "Role / Baseline / Probability" in scenario_judge
    assert "Supply and demand tighten together." in scenario_judge
    assert "Dimension 0 = High; Dimension 1 = High; Dimension 2 = -" in scenario_judge
    assert "Tight supply raises price pressure." in scenario_judge
    assert "ceiling / N / 20" in scenario_judge
    assert "agent judge pending" not in report


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
