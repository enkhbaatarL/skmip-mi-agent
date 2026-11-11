from __future__ import annotations

# ruff: noqa: CPY001, S101, ANN001, ANN201, ANN202, PT011
import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from apps.agents.scenario_group_agent.flows.evaluate_scenarios import flow
from apps.agents.scenario_group_agent.flows.evaluate_scenarios.repair import build_repaired_snapshot
from apps.agents.scenario_group_agent.persistence.scenario_group_operation_service import ScenarioGroupOperationService
from apps.agents.scenario_group_agent.persistence.scenario_quality_repair_service import ScenarioQualityRepairService
from apps.agents.scenario_group_agent.persistence.scenario_service import ScenarioService
from apps.agents.scenario_group_agent.prompts.scenario_quality_evaluation import summarize
from apps.agents.scenario_group_agent.prompts.scenario_quality_repair import QualityRepairPlan, QualityRepairReview
from apps.common.exceptions.custom import MIBaseError
from apps.persistence.scenario_group.models import MiScenarioGroupModel
from apps.persistence.scenario_group_operation.models import MiScenarioGroupOperationModel
from apps.persistence.scenario_quality_evaluation.models import MiScenarioQualityEvaluationModel
from apps.persistence.scenario_quality_evaluation.schema import JUDGE_IDS, InputOnlyScenarioQualityJudgment
from tests.manual.quality_eval.repair_sandbox import repair_sandbox


def snapshot():
    return {
        "schemaVersion": 1,
        "group": {
            "scenario_group_id": 130,
            "title": "공급과 수요",
            "summary": "잘린 요약",
            "description": "수급 경로 비교",
            "dimension_selected": ["d1", "d2", "d3"],
            "dimension_definitions": [
                {
                    "dimension_id": key,
                    "label": key,
                    "description": key,
                    "dimension_type": "occurrence",
                    "values": [
                        {
                            "value_id": f"{key}_v{i}",
                            "label": str(i),
                            "pressure_contribution": band,
                            "assumption_rationale": "가정",
                        }
                        for i, band in enumerate(("bearish", "balanced", "bullish"), 1)
                    ],
                }
                for key in ("d1", "d2", "d3")
            ],
        },
        "scenarios": [
            {
                "scenario_id": 513 + i,
                "scenario_group_id": 130,
                "title": title,
                "narrative": "선택값에 따른 경로",
                "global_pressure_rationale": "수급 근거",
                "dimension_values": {key: f"{key}_v{i + 1}" for key in ("d1", "d2", "d3")},
                "probability_score": probability,
                "probability_delta": 0,
                "display_order": i,
                "baseline_yn": "Y" if i == 1 else "N",
                "global_pressure_band": band,
                "related_markets": [],
                "scenario_role": None,
            }
            for i, (title, probability, band) in enumerate(
                (
                    ("공급 회복", 20, "strong_bearish"),
                    ("기준 경로", 60, "balanced"),
                    ("수요 증가", 20, "strong_bullish"),
                ),
            )
        ],
        "events": [],
    }


def judgment(verdict="WARN"):
    items = [{"judgeId": key, "score": 5, "verdict": "PASS", "violations": []} for key in JUDGE_IDS]
    if verdict != "PASS":
        items[-1] = {
            "judgeId": "J-11",
            "score": 2 if verdict == "FAIL" else 3,
            "verdict": verdict,
            "violations": [
                {
                    "scenarioIds": [513, 514, 515],
                    "evidencePath": "/group/summary",
                    "evidence": "잘린 요약",
                    "reason": "요약 불완전",
                    "suggestedFix": "완전한 요약",
                },
            ],
        }
    return InputOnlyScenarioQualityJudgment.model_validate({"summary": "평가", "items": items})


def plan(path="/group/summary", value="공급 회복과 수요 증가에 따른 시장 경로를 비교한다."):
    return QualityRepairPlan.model_validate(
        {
            "changes": [
                {
                    "judgeId": "J-11",
                    "violationIndex": 0,
                    "path": path,
                    "value": value,
                },
            ],
            "unresolved": [],
        },
    )


@pytest.mark.parametrize(("before", "after"), [("WARN", "PASS"), ("FAIL", "WARN"), ("FAIL", "FAIL")])
def test_repair_once_keeps_two_evaluations_and_signpost_gate(before, after, monkeypatch):
    with repair_sandbox(snapshot()) as db:
        first, _ = db.service.prepare(130, 42, str(uuid4()))
        responses = iter(
            (judgment(before), plan(), QualityRepairReview(can_proceed=True, reason="근거 보존"), judgment(after)),
        )
        calls = []

        async def invoke(**kwargs: object):
            calls.append(kwargs["output_schema"])
            # Both the initial evaluation and repair/review/re-evaluation remain active.
            with pytest.raises(MIBaseError):
                ScenarioGroupOperationService().create_validation_operation(scenario_group_id=130, user_id=42)
            with pytest.raises(MIBaseError):
                ScenarioService().accept_validation_change_set(scenario_group_id=130, user_id=42)
            return SimpleNamespace(result=next(responses), model="mock", usage=None)

        monkeypatch.setattr(flow, "invoke_llm_structured_output", invoke)
        asyncio.run(flow.run_quality_evaluation(130, first.operation_id))
        with db.factory() as session:
            rows = session.scalars(
                select(MiScenarioQualityEvaluationModel).order_by(MiScenarioQualityEvaluationModel.operation_id),
            ).all()
            assert len(rows) == 2
            assert [row.verdict for row in rows] == [before, after]
            assert rows[0].input_snapshot["group"]["summary"] == "잘린 요약"
            assert rows[1].input_snapshot["group"]["summary"] == plan().changes[0].value
            assert rows[0].input_hash != rows[1].input_hash
            assert session.get(MiScenarioGroupModel, 130).summary == plan().changes[0].value
            retry = session.get(MiScenarioGroupOperationModel, rows[1].operation_id)
            assert retry.retry_summary["qualityRepair"]["attempt"] == 1
            assert retry.retry_summary["qualityRepair"]["state"] == "applied"
            assert retry.status == "succeeded"
        assert len(calls) == 4
        assert ScenarioGroupOperationService().get_active(130) is None
        accepted = ScenarioService().accept_validation_change_set(
            scenario_group_id=130,
            user_id=42,
            create_signpost_operation=False,
        )
        assert accepted["validation_operation_id"]
        # A completed child must never rerun the repair or judge.
        asyncio.run(flow.run_quality_evaluation(130, retry.operation_id))
        assert len(calls) == 4


@pytest.mark.parametrize(
    "path",
    [
        "/events/0/payload/title",
        "/scenarios/0/probability_score",
        "/group/dimension_definitions/0/values/0/pressure_contribution",
    ],
)
def test_forbidden_repair_fields(path):
    with pytest.raises(ValueError, match="forbidden"):
        build_repaired_snapshot(snapshot(), judgment(), plan(path), {})


def test_invalid_choice_and_noop_are_blocked():
    with pytest.raises(ValueError):
        build_repaired_snapshot(snapshot(), judgment(), plan("/scenarios/0/dimension_values/d1", "unknown"), {})
    with pytest.raises(ValueError, match="no changes"):
        build_repaired_snapshot(snapshot(), judgment(), plan(value="잘린 요약"), {})


def test_stale_repair_cannot_overwrite_newer_data():
    with repair_sandbox(snapshot()) as db:
        first, _ = db.service.prepare(130, 42, str(uuid4()))
        result = judgment()
        verdict, score = summarize(result)
        retry_id = db.service.complete(
            130,
            first.operation_id,
            result=result,
            verdict=verdict,
            average_score=score,
            llm_metadata={},
            repair_once=True,
        )
        repair = ScenarioQualityRepairService()
        assert repair.claim(130, retry_id) is not None
        assert repair.claim(130, retry_id) is None
        with db.factory.begin() as session:
            session.get(MiScenarioGroupModel, 130).summary = "다른 편집"
        with pytest.raises(MIBaseError):
            repair.apply(130, retry_id, plan(), QualityRepairReview(can_proceed=True, reason="통과"), llm_metadata={})
        with db.factory() as session:
            assert session.get(MiScenarioGroupModel, 130).summary == "다른 편집"


def test_review_block_preserves_original_and_records_failed_retry(monkeypatch):
    with repair_sandbox(snapshot()) as db:
        first, _ = db.service.prepare(130, 42, str(uuid4()))
        responses = iter((judgment(), plan(), QualityRepairReview(can_proceed=False, reason="근거 왜곡")))

        async def invoke(**kwargs: object):
            return SimpleNamespace(result=next(responses), model="mock", usage=None)

        monkeypatch.setattr(flow, "invoke_llm_structured_output", invoke)
        asyncio.run(flow.run_quality_evaluation(130, first.operation_id))
        with db.factory() as session:
            assert session.get(MiScenarioGroupModel, 130).summary == "잘린 요약"
            rows = session.scalars(
                select(MiScenarioGroupOperationModel).order_by(MiScenarioGroupOperationModel.operation_id),
            ).all()
            assert [row.status for row in rows] == ["succeeded", "failed"]


def test_no_repair_after_signpost():
    with repair_sandbox(snapshot()) as db:
        with db.factory.begin() as session:
            session.get(MiScenarioGroupModel, 130).stage = "signpost_created"
        first, _ = db.service.prepare(130, 42, str(uuid4()))
        result = judgment()
        verdict, score = summarize(result)
        assert (
            db.service.complete(
                130,
                first.operation_id,
                result=result,
                verdict=verdict,
                average_score=score,
                llm_metadata={},
                repair_once=True,
            )
            is None
        )


@pytest.mark.parametrize("step", [1, 2, 3])
@pytest.mark.parametrize("cancelled", [False, True])
def test_retry_error_or_shutdown_never_creates_third_evaluation(step, cancelled, monkeypatch):
    with repair_sandbox(snapshot()) as db:
        first, _ = db.service.prepare(130, 42, str(uuid4()))
        responses = [judgment(), plan(), QualityRepairReview(can_proceed=True, reason="통과"), judgment("PASS")]
        calls = 0

        async def invoke(**kwargs: object):
            nonlocal calls
            index = calls
            calls += 1
            if index == step:
                if cancelled:
                    raise asyncio.CancelledError
                raise TimeoutError
            return SimpleNamespace(result=responses[index], model="mock", usage=None)

        monkeypatch.setattr(flow, "invoke_llm_structured_output", invoke)
        if cancelled:
            with pytest.raises(asyncio.CancelledError):
                asyncio.run(flow.run_quality_evaluation(130, first.operation_id))
        else:
            asyncio.run(flow.run_quality_evaluation(130, first.operation_id))
        with db.factory() as session:
            rows = session.scalars(select(MiScenarioQualityEvaluationModel).order_by(
                MiScenarioQualityEvaluationModel.operation_id,
            )).all()
            assert len(rows) == 2
            assert rows[0].verdict == "WARN"
            assert rows[1].result_payload is None
            child = session.get(MiScenarioGroupOperationModel, rows[1].operation_id)
            assert child.status == ("interrupted" if cancelled else "failed")
            assert session.get(MiScenarioGroupModel, 130).summary == (
                plan().changes[0].value if step == 3 else "잘린 요약"
            )
