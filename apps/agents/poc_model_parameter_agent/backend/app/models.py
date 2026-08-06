from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Computed,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AgentRun(TimestampMixin, Base):
    __tablename__ = "agent_runs"

    run_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    root_run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    parent_run_id: Mapped[str | None] = mapped_column(ForeignKey("agent_runs.run_id"), nullable=True, index=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    comparison_run_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed", index=True)
    target_market: Mapped[str] = mapped_column(String(64), nullable=False)
    event_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    horizon_start: Mapped[str | None] = mapped_column(String(7), nullable=True)
    horizon_end: Mapped[str | None] = mapped_column(String(7), nullable=True)
    include_recovery: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    source_scenario_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    normalized_input_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    clarification_answers_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    asset_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    validation_report_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    scenario_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    proposal_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    adjustment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("root_run_id", "revision", name="uq_agent_runs_root_revision"),
        CheckConstraint("revision >= 1", name="ck_agent_runs_revision_positive"),
    )


class RunArtifact(TimestampMixin, Base):
    __tablename__ = "run_artifacts"

    artifact_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    step_id: Mapped[str] = mapped_column(String(64), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    input_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    output_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    validation_messages_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    exclusion_log_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (UniqueConstraint("run_id", "step_id", name="uq_run_artifacts_run_step"),)


class ParameterProposal(TimestampMixin, Base):
    __tablename__ = "parameter_proposals"

    proposal_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    scenario_key: Mapped[str] = mapped_column(String(128), nullable=False)
    parameter_code: Mapped[str] = mapped_column(String(128), nullable=False)
    parameter_name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(32), nullable=False)
    application_start: Mapped[str] = mapped_column(String(7), nullable=False)
    application_end: Mapped[str] = mapped_column(String(7), nullable=False)
    baseline_peak: Mapped[float] = mapped_column(Float, nullable=False)
    proposed_peak: Mapped[float] = mapped_column(Float, nullable=False)
    delta_peak: Mapped[float] = mapped_column(Float, nullable=False)
    delta_percent: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    warning_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    __table_args__ = (
        UniqueConstraint("run_id", "scenario_key", "parameter_code", name="uq_proposals_run_scenario_parameter"),
    )


class Feedback(TimestampMixin, Base):
    __tablename__ = "feedback"

    feedback_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.run_id"), nullable=False, index=True)
    result_run_id: Mapped[str | None] = mapped_column(ForeignKey("agent_runs.run_id"), nullable=True)
    tag: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    scope: Mapped[str] = mapped_column(String(32), nullable=False, default="run")
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    context_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    answer_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    interpretation_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    adjustment_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    processing_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    learning_batch_id: Mapped[str | None] = mapped_column(ForeignKey("learning_batches.batch_id"), nullable=True)
    final_run_guard: Mapped[str | None] = mapped_column(
        String(36), Computed("CASE WHEN tag = 'final' THEN run_id ELSE NULL END", persisted=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint("tag IN ('interim', 'final')", name="ck_feedback_tag"),
        CheckConstraint("source IN ('clarification', 'result_review')", name="ck_feedback_source"),
        UniqueConstraint("final_run_guard", name="uq_feedback_final_per_run"),
    )


class LearningBatch(TimestampMixin, Base):
    __tablename__ = "learning_batches"

    batch_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    reviewer_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="mock_deterministic")
    feedback_ids_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    interim_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    final_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    classification_summary_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    review_summary_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class LearningCandidate(TimestampMixin, Base):
    __tablename__ = "learning_candidates"

    candidate_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("learning_batches.batch_id"), nullable=False, index=True)
    source_feedback_id: Mapped[str] = mapped_column(ForeignKey("feedback.feedback_id"), nullable=False, index=True)
    source_run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.run_id"), nullable=False)
    source_tag: Mapped[str] = mapped_column(String(16), nullable=False)
    source_context_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_asset_key: Mapped[str] = mapped_column(String(128), nullable=False)
    base_version: Mapped[int] = mapped_column(Integer, nullable=False)
    proposed_version: Mapped[int] = mapped_column(Integer, nullable=False)
    proposed_content: Mapped[str] = mapped_column(Text, nullable=False)
    change_line: Mapped[str] = mapped_column(Text, nullable=False)
    diff_text: Mapped[str] = mapped_column(Text, nullable=False)
    classification: Mapped[str] = mapped_column(String(32), nullable=False)
    matched_signals_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evaluation_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    risks_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    expected_impact: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    pending_fingerprint_guard: Mapped[str | None] = mapped_column(
        String(64),
        Computed(
            "CASE WHEN status IN ('pending', 'approved', 'applied') THEN fingerprint ELSE NULL END", persisted=True
        ),
        nullable=True,
    )
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint("pending_fingerprint_guard", name="uq_candidate_pending_fingerprint"),)


class AssetVersion(TimestampMixin, Base):
    __tablename__ = "asset_versions"

    asset_version_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    asset_type: Mapped[str] = mapped_column(String(32), nullable=False)
    asset_key: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    learnable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_candidate_id: Mapped[str | None] = mapped_column(
        ForeignKey("learning_candidates.candidate_id"), nullable=True
    )
    active_asset_guard: Mapped[str | None] = mapped_column(
        String(191),
        Computed("CASE WHEN active = 1 THEN CONCAT(asset_type, ':', asset_key) ELSE NULL END", persisted=True),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint("asset_type", "asset_key", "version", name="uq_asset_versions_identity"),
        UniqueConstraint("active_asset_guard", name="uq_asset_versions_active"),
        Index("ix_asset_versions_lookup", "asset_type", "asset_key", "active"),
    )
