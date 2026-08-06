from __future__ import annotations

import os
import uuid

import pytest
from app.db import get_session_factory
from app.errors import ConflictAppError, ValidationAppError
from app.models import AgentRun, AssetVersion, Feedback, LearningBatch, LearningCandidate
from app.persistence.asset_repository import get_active_asset
from app.pipeline.orchestrator import PipelineOrchestrator
from app.schemas.pipeline import FinalFeedbackRequest, RunRequest
from app.seed import load_seed_document, seed_assets
from app.services.feedback_service import submit_final_feedback
from app.services.learning_service import approve_candidate, process_pending, reject_candidate
from app.services.run_service import create_new_run
from sqlalchemy import func, select, text

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module", autouse=True)
def require_mysql() -> None:
    if os.getenv("RUN_MYSQL_INTEGRATION") != "1":
        pytest.skip("Set RUN_MYSQL_INTEGRATION=1 against the isolated migrated MySQL test database.")


def test_seed_run_revision_learning_and_version_activation() -> None:
    factory = get_session_factory()
    seed = load_seed_document()
    session = factory()
    try:
        test_token = uuid.uuid4().hex
        with session.begin():
            seed_assets(session, seed)
        with session.begin():
            second = seed_assets(session, seed)
        assert second["inserted"] == 0
        assert second["skipped"] == 10

        request = RunRequest(
            metadata=seed.example1_meta,
            scenario_json=seed.example1,
            clarification_answers={"additional_instruction": f"수요 영향이 과도하니 완화 {test_token}"},
        )
        run = create_new_run(session, request, PipelineOrchestrator(seed))
        assert run["proposalCount"] == 18
        assert len(run["artifacts"]) == 9
        original_snapshot = run["assetSnapshot"]
        interim_feedback_ids = {item["feedbackId"] for item in run["feedbacks"] if item["tag"] == "interim"}
        assert len(interim_feedback_ids) == 1

        duplicate_run = create_new_run(session, request, PipelineOrchestrator(seed))
        duplicate_interim_ids = {item["feedbackId"] for item in duplicate_run["feedbacks"] if item["tag"] == "interim"}
        assert len(duplicate_interim_ids) == 1

        feedback_result = submit_final_feedback(
            session,
            run["runId"],
            FinalFeedbackRequest(scope="run", text=f"공급 영향이 과도하니 완화 {test_token}"),
            PipelineOrchestrator(seed),
        )
        child = feedback_result["resultRun"]
        assert child["parentRunId"] == run["runId"]
        assert child["revision"] == 2
        assert feedback_result["feedback"]["resultRunId"] == child["runId"]
        assert child["assetSnapshot"] == original_snapshot
        assert len(child["normalizedInput"]["appliedAdjustments"]) == (
            len(run["normalizedInput"]["appliedAdjustments"]) + 1
        )
        with pytest.raises(ConflictAppError):
            submit_final_feedback(
                session,
                run["runId"],
                FinalFeedbackRequest(scope="run", text="다시 줄여 주세요"),
                PipelineOrchestrator(seed),
            )

        locking_session = factory()
        contender_session = factory()
        try:
            with locking_session.begin():
                locked_feedback = locking_session.scalar(
                    select(Feedback)
                    .where(
                        Feedback.run_id == run["runId"],
                        Feedback.tag == "final",
                    )
                    .with_for_update()
                )
                assert locked_feedback is not None
                contender_session.execute(text("SET SESSION innodb_lock_wait_timeout = 1"))
                contender_session.commit()
                with pytest.raises(ConflictAppError):
                    submit_final_feedback(
                        contender_session,
                        run["runId"],
                        FinalFeedbackRequest(scope="run", text="Worker lock 중 중복 제출"),
                        PipelineOrchestrator(seed),
                    )
        finally:
            contender_session.close()
            locking_session.close()

        grandchild_feedback_result = submit_final_feedback(
            session,
            child["runId"],
            FinalFeedbackRequest(scope="run", text=f"수요 영향은 기본적으로 보수적으로 표시 {test_token}"),
            PipelineOrchestrator(seed),
        )
        grandchild = grandchild_feedback_result["resultRun"]
        assert grandchild["parentRunId"] == child["runId"]
        assert grandchild["revision"] == 3
        assert grandchild["assetSnapshot"] == original_snapshot
        assert len(grandchild["normalizedInput"]["appliedAdjustments"]) == (
            len(child["normalizedInput"]["appliedAdjustments"]) + 1
        )

        unchanged_feedback_result = submit_final_feedback(
            session,
            grandchild["runId"],
            FinalFeedbackRequest(scope="run", text=f"확인했습니다 {test_token}"),
            PipelineOrchestrator(seed),
        )
        unchanged_child = unchanged_feedback_result["resultRun"]
        assert unchanged_child["revision"] == 4
        assert (
            unchanged_child["normalizedInput"]["appliedAdjustments"]
            == (grandchild["normalizedInput"]["appliedAdjustments"])
        )
        grandchild_series = {
            (scenario["scenarioKey"], proposal["parameterCode"]): proposal["series"]
            for scenario in grandchild["scenarios"]
            for proposal in scenario["proposals"]
        }
        unchanged_series = {
            (scenario["scenarioKey"], proposal["parameterCode"]): proposal["series"]
            for scenario in unchanged_child["scenarios"]
            for proposal in scenario["proposals"]
        }
        assert unchanged_series == grandchild_series

        blocked_feedback_result = submit_final_feedback(
            session,
            unchanged_child["runId"],
            FinalFeedbackRequest(
                scope="run",
                text=f"계산 전에 반드시 자동 승인 절차를 적용 {test_token}",
            ),
            PipelineOrchestrator(seed),
        )
        blocked_child = blocked_feedback_result["resultRun"]
        assert blocked_child["revision"] == 5
        assert (
            blocked_child["normalizedInput"]["appliedAdjustments"]
            == (unchanged_child["normalizedInput"]["appliedAdjustments"])
        )

        source_feedback_ids = (
            interim_feedback_ids
            | duplicate_interim_ids
            | {
                feedback_result["feedback"]["feedbackId"],
                grandchild_feedback_result["feedback"]["feedbackId"],
                unchanged_feedback_result["feedback"]["feedbackId"],
                blocked_feedback_result["feedback"]["feedbackId"],
            }
        )
        cycle = process_pending(session)
        assert cycle["processed"] >= len(source_feedback_ids)
        assert cycle["duplicatesSkipped"] >= 1
        candidates = list(
            session.scalars(
                select(LearningCandidate)
                .where(LearningCandidate.source_feedback_id.in_(source_feedback_ids))
                .order_by(LearningCandidate.created_at)
            )
        )
        assert len(candidates) == 4
        assert {item.status for item in candidates} == {"pending"}
        memory_candidates = [item for item in candidates if item.target_type == "memory"]
        blocked_candidate = next(item for item in candidates if item.target_type == "skill")
        assert len(memory_candidates) == 3
        assert blocked_candidate.evaluation_json["allPassed"] is False
        rejected_candidate, approved_candidate, stale_candidate = memory_candidates
        rejected_candidate_id = rejected_candidate.candidate_id
        approved_candidate_id = approved_candidate.candidate_id
        stale_candidate_id = stale_candidate.candidate_id
        candidate_type = approved_candidate.target_type
        candidate_key = approved_candidate.target_asset_key
        blocked_candidate_id = blocked_candidate.candidate_id
        blocked_asset_before = get_active_asset(session, "skill", "scenario_parameter_skill")
        assert blocked_asset_before is not None
        blocked_asset_identity = (
            blocked_asset_before.asset_version_id,
            blocked_asset_before.version,
            blocked_asset_before.content_hash,
        )
        session.rollback()
        with pytest.raises(ValidationAppError) as evaluation_error:
            approve_candidate(session, blocked_candidate_id, "must remain blocked")
        assert evaluation_error.value.details["assetUnchanged"] is True
        blocked_asset_after = get_active_asset(session, "skill", "scenario_parameter_skill")
        assert blocked_asset_after is not None
        assert (
            blocked_asset_after.asset_version_id,
            blocked_asset_after.version,
            blocked_asset_after.content_hash,
        ) == blocked_asset_identity
        persisted_blocked = session.scalar(
            select(LearningCandidate).where(LearningCandidate.candidate_id == blocked_candidate_id)
        )
        assert persisted_blocked is not None and persisted_blocked.status == "pending"
        snapshot_key = f"{candidate_type}:{candidate_key}"
        before = get_active_asset(session, candidate_type, candidate_key)
        assert before is not None
        before_version = before.version
        before_identity = (
            before.asset_version_id,
            before.version,
            before.content_hash,
            before.source_candidate_id,
        )
        before_asset_count = int(
            session.scalar(
                select(func.count())
                .select_from(AssetVersion)
                .where(AssetVersion.asset_type == candidate_type, AssetVersion.asset_key == candidate_key)
            )
            or 0
        )
        session.rollback()

        rejected = reject_candidate(session, rejected_candidate_id, "integration rejection")
        assert rejected["candidate"]["status"] == "rejected"
        assert rejected["assetChanged"] is False
        after_reject = get_active_asset(session, candidate_type, candidate_key)
        assert after_reject is not None
        assert (
            after_reject.asset_version_id,
            after_reject.version,
            after_reject.content_hash,
            after_reject.source_candidate_id,
        ) == before_identity
        assert (
            session.scalar(
                select(func.count())
                .select_from(AssetVersion)
                .where(AssetVersion.asset_type == candidate_type, AssetVersion.asset_key == candidate_key)
            )
            == before_asset_count
        )
        session.rollback()

        approved = approve_candidate(session, approved_candidate_id, "integration approval")
        after = get_active_asset(session, candidate_type, candidate_key)
        assert after and after.version == before_version + 1
        assert after.source_candidate_id == approved_candidate_id
        assert approved["candidate"]["status"] == "applied"
        approved_identity = (after.asset_version_id, after.version, after.content_hash, after.source_candidate_id)
        approved_asset_count = before_asset_count + 1
        assert (
            session.scalar(
                select(func.count())
                .select_from(AssetVersion)
                .where(AssetVersion.asset_type == candidate_type, AssetVersion.asset_key == candidate_key)
            )
            == approved_asset_count
        )

        session.rollback()
        with session.begin():
            locked_asset = get_active_asset(session, candidate_type, candidate_key, for_update=True)
            assert locked_asset is not None
            locked_asset.locked = True
        with pytest.raises(ConflictAppError) as locked_conflict:
            approve_candidate(session, stale_candidate_id, "locked approval")
        assert locked_conflict.value.details["assetUnchanged"] is True
        session.rollback()
        with session.begin():
            locked_asset = get_active_asset(session, candidate_type, candidate_key, for_update=True)
            assert locked_asset is not None
            locked_asset.locked = False

        with pytest.raises(ConflictAppError) as conflict:
            approve_candidate(session, stale_candidate_id, "stale approval")
        assert conflict.value.details["assetUnchanged"] is True
        current = get_active_asset(session, candidate_type, candidate_key)
        assert current and current.version == before_version + 1
        assert (current.asset_version_id, current.version, current.content_hash, current.source_candidate_id) == (
            approved_identity
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(AssetVersion)
                .where(AssetVersion.asset_type == candidate_type, AssetVersion.asset_key == candidate_key)
            )
            == approved_asset_count
        )
        persisted_stale = session.scalar(
            select(LearningCandidate).where(LearningCandidate.candidate_id == stale_candidate_id)
        )
        assert persisted_stale is not None and persisted_stale.status == "pending"

        stored_revision_snapshots = list(
            session.scalars(
                select(AgentRun.asset_snapshot_json)
                .where(
                    AgentRun.run_id.in_(
                        [
                            run["runId"],
                            child["runId"],
                            grandchild["runId"],
                            unchanged_child["runId"],
                            blocked_child["runId"],
                        ]
                    )
                )
                .order_by(AgentRun.revision)
            )
        )
        assert stored_revision_snapshots == [
            original_snapshot,
            original_snapshot,
            original_snapshot,
            original_snapshot,
            original_snapshot,
        ]
        assert original_snapshot[snapshot_key]["version"] == before_version
        session.rollback()

        next_run = create_new_run(
            session,
            RunRequest(
                metadata=seed.example1_meta,
                scenario_json=seed.example1,
                clarification_answers={},
            ),
            PipelineOrchestrator(seed),
        )
        assert next_run["assetSnapshot"][snapshot_key]["version"] == before_version + 1
        assert next_run["assetSnapshot"][snapshot_key]["contentHash"] == approved_identity[2]
        assert next_run["feedbacks"] == []

        batch_count_before_idle = int(session.scalar(select(func.count()).select_from(LearningBatch)) or 0)
        candidate_count_before_idle = int(session.scalar(select(func.count()).select_from(LearningCandidate)) or 0)
        session.rollback()
        first_idle_cycle = process_pending(session)
        second_idle_cycle = process_pending(session)
        assert first_idle_cycle["processed"] == 0
        assert second_idle_cycle["processed"] == 0
        assert int(session.scalar(select(func.count()).select_from(LearningBatch)) or 0) == batch_count_before_idle
        assert (
            int(session.scalar(select(func.count()).select_from(LearningCandidate)) or 0) == candidate_count_before_idle
        )
        assert session.scalar(select(Feedback).where(Feedback.feedback_id == feedback_result["feedback"]["feedbackId"]))
        assert session.scalar(select(AssetVersion).where(AssetVersion.source_candidate_id == approved_candidate_id))
    finally:
        session.close()
