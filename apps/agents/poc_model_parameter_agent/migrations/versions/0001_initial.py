"""Create the standalone model-parameter learning schema.

Revision ID: 0001_initial
Revises:
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("run_id", sa.String(36), primary_key=True),
        sa.Column("root_run_id", sa.String(36), nullable=False),
        sa.Column("parent_run_id", sa.String(36), sa.ForeignKey("agent_runs.run_id"), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("comparison_run_id", sa.String(128), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("target_market", sa.String(64), nullable=False),
        sa.Column("event_ids", sa.JSON(), nullable=False),
        sa.Column("horizon_start", sa.String(7), nullable=True),
        sa.Column("horizon_end", sa.String(7), nullable=True),
        sa.Column("include_recovery", sa.Boolean(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("source_scenario_json", sa.JSON(), nullable=False),
        sa.Column("normalized_input_json", sa.JSON(), nullable=False),
        sa.Column("clarification_answers_json", sa.JSON(), nullable=False),
        sa.Column("asset_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("validation_report_json", sa.JSON(), nullable=False),
        sa.Column("scenario_count", sa.Integer(), nullable=False),
        sa.Column("proposal_count", sa.Integer(), nullable=False),
        sa.Column("adjustment_count", sa.Integer(), nullable=False),
        *timestamps(),
        sa.CheckConstraint("revision >= 1", name="ck_agent_runs_revision_positive"),
        sa.UniqueConstraint("root_run_id", "revision", name="uq_agent_runs_root_revision"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_agent_runs_root_run_id", "agent_runs", ["root_run_id"])
    op.create_index("ix_agent_runs_parent_run_id", "agent_runs", ["parent_run_id"])
    op.create_index("ix_agent_runs_status", "agent_runs", ["status"])

    op.create_table(
        "run_artifacts",
        sa.Column("artifact_id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("agent_runs.run_id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_id", sa.String(64), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("input_json", sa.JSON(), nullable=False),
        sa.Column("output_json", sa.JSON(), nullable=False),
        sa.Column("validation_messages_json", sa.JSON(), nullable=False),
        sa.Column("exclusion_log_json", sa.JSON(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("run_id", "step_id", name="uq_run_artifacts_run_step"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_run_artifacts_run_id", "run_artifacts", ["run_id"])

    op.create_table(
        "parameter_proposals",
        sa.Column("proposal_id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("agent_runs.run_id", ondelete="CASCADE"), nullable=False),
        sa.Column("scenario_key", sa.String(128), nullable=False),
        sa.Column("parameter_code", sa.String(128), nullable=False),
        sa.Column("parameter_name", sa.String(255), nullable=False),
        sa.Column("domain", sa.String(32), nullable=False),
        sa.Column("application_start", sa.String(7), nullable=False),
        sa.Column("application_end", sa.String(7), nullable=False),
        sa.Column("baseline_peak", sa.Float(), nullable=False),
        sa.Column("proposed_peak", sa.Float(), nullable=False),
        sa.Column("delta_peak", sa.Float(), nullable=False),
        sa.Column("delta_percent", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("warning_count", sa.Integer(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("run_id", "scenario_key", "parameter_code", name="uq_proposals_run_scenario_parameter"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_parameter_proposals_run_id", "parameter_proposals", ["run_id"])

    op.create_table(
        "learning_batches",
        sa.Column("batch_id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("reviewer_mode", sa.String(32), nullable=False),
        sa.Column("feedback_ids_json", sa.JSON(), nullable=False),
        sa.Column("interim_count", sa.Integer(), nullable=False),
        sa.Column("final_count", sa.Integer(), nullable=False),
        sa.Column("candidate_count", sa.Integer(), nullable=False),
        sa.Column("classification_summary_json", sa.JSON(), nullable=False),
        sa.Column("review_summary_json", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        *timestamps(),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_learning_batches_status", "learning_batches", ["status"])

    op.create_table(
        "feedback",
        sa.Column("feedback_id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("agent_runs.run_id"), nullable=False),
        sa.Column("result_run_id", sa.String(36), sa.ForeignKey("agent_runs.run_id"), nullable=True),
        sa.Column("tag", sa.String(16), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("scope", sa.String(32), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("context_json", sa.JSON(), nullable=False),
        sa.Column("answer_json", sa.JSON(), nullable=False),
        sa.Column("interpretation_json", sa.JSON(), nullable=False),
        sa.Column("adjustment_json", sa.JSON(), nullable=False),
        sa.Column("processing_status", sa.String(32), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("learning_batch_id", sa.String(36), sa.ForeignKey("learning_batches.batch_id"), nullable=True),
        sa.Column(
            "final_run_guard",
            sa.String(36),
            sa.Computed("CASE WHEN tag = 'final' THEN run_id ELSE NULL END", persisted=True),
            nullable=True,
        ),
        *timestamps(),
        sa.CheckConstraint("tag IN ('interim', 'final')", name="ck_feedback_tag"),
        sa.CheckConstraint("source IN ('clarification', 'result_review')", name="ck_feedback_source"),
        sa.UniqueConstraint("final_run_guard", name="uq_feedback_final_per_run"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_feedback_run_id", "feedback", ["run_id"])
    op.create_index("ix_feedback_tag", "feedback", ["tag"])
    op.create_index("ix_feedback_processing_status", "feedback", ["processing_status"])

    op.create_table(
        "learning_candidates",
        sa.Column("candidate_id", sa.String(36), primary_key=True),
        sa.Column("batch_id", sa.String(36), sa.ForeignKey("learning_batches.batch_id"), nullable=False),
        sa.Column("source_feedback_id", sa.String(36), sa.ForeignKey("feedback.feedback_id"), nullable=False),
        sa.Column("source_run_id", sa.String(36), sa.ForeignKey("agent_runs.run_id"), nullable=False),
        sa.Column("source_tag", sa.String(16), nullable=False),
        sa.Column("source_context_json", sa.JSON(), nullable=False),
        sa.Column("target_type", sa.String(32), nullable=False),
        sa.Column("target_asset_key", sa.String(128), nullable=False),
        sa.Column("base_version", sa.Integer(), nullable=False),
        sa.Column("proposed_version", sa.Integer(), nullable=False),
        sa.Column("proposed_content", sa.Text(), nullable=False),
        sa.Column("change_line", sa.Text(), nullable=False),
        sa.Column("diff_text", sa.Text(), nullable=False),
        sa.Column("classification", sa.String(32), nullable=False),
        sa.Column("matched_signals_json", sa.JSON(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evaluation_json", sa.JSON(), nullable=False),
        sa.Column("risks_json", sa.JSON(), nullable=False),
        sa.Column("expected_impact", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column(
            "pending_fingerprint_guard",
            sa.String(64),
            sa.Computed(
                "CASE WHEN status IN ('pending', 'approved', 'applied') THEN fingerprint ELSE NULL END", persisted=True
            ),
            nullable=True,
        ),
        sa.Column("reviewer_note", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.UniqueConstraint("pending_fingerprint_guard", name="uq_candidate_pending_fingerprint"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_learning_candidates_batch_id", "learning_candidates", ["batch_id"])
    op.create_index("ix_learning_candidates_source_feedback_id", "learning_candidates", ["source_feedback_id"])
    op.create_index("ix_learning_candidates_status", "learning_candidates", ["status"])

    op.create_table(
        "asset_versions",
        sa.Column("asset_version_id", sa.String(36), primary_key=True),
        sa.Column("asset_type", sa.String(32), nullable=False),
        sa.Column("asset_key", sa.String(128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_json", sa.JSON(), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("learnable", sa.Boolean(), nullable=False),
        sa.Column("locked", sa.Boolean(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column(
            "source_candidate_id", sa.String(36), sa.ForeignKey("learning_candidates.candidate_id"), nullable=True
        ),
        sa.Column(
            "active_asset_guard",
            sa.String(191),
            sa.Computed("CASE WHEN active = 1 THEN CONCAT(asset_type, ':', asset_key) ELSE NULL END", persisted=True),
            nullable=True,
        ),
        *timestamps(),
        sa.UniqueConstraint("asset_type", "asset_key", "version", name="uq_asset_versions_identity"),
        sa.UniqueConstraint("active_asset_guard", name="uq_asset_versions_active"),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_asset_versions_lookup", "asset_versions", ["asset_type", "asset_key", "active"])


def downgrade() -> None:
    op.drop_table("asset_versions")
    op.drop_table("learning_candidates")
    op.drop_table("feedback")
    op.drop_table("learning_batches")
    op.drop_table("parameter_proposals")
    op.drop_table("run_artifacts")
    op.drop_table("agent_runs")
