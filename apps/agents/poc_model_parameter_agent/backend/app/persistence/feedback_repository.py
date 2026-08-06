from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Feedback


def get_feedback(session: Session, feedback_id: str) -> Feedback | None:
    return session.scalar(select(Feedback).where(Feedback.feedback_id == feedback_id))


def final_feedback_for_run(session: Session, run_id: str, for_update: bool = False) -> Feedback | None:
    statement = select(Feedback).where(Feedback.run_id == run_id, Feedback.tag == "final")
    if for_update:
        statement = statement.with_for_update()
    return session.scalar(statement)


def list_feedback(
    session: Session,
    page: int,
    page_size: int,
    tag: str | None = None,
    source: str | None = None,
    processing_status: str | None = None,
) -> tuple[list[Feedback], int]:
    filters = []
    if tag:
        filters.append(Feedback.tag == tag)
    if source:
        filters.append(Feedback.source == source)
    if processing_status:
        filters.append(Feedback.processing_status == processing_status)
    total = int(session.scalar(select(func.count()).select_from(Feedback).where(*filters)) or 0)
    rows = list(
        session.scalars(
            select(Feedback)
            .where(*filters)
            .order_by(Feedback.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return rows, total


def claim_pending_feedback(session: Session, limit: int) -> list[Feedback]:
    now = datetime.now(UTC)
    statement = (
        select(Feedback)
        .where(
            Feedback.learning_batch_id.is_(None),
            Feedback.processing_status.in_(["pending", "retry"]),
            or_(Feedback.next_retry_at.is_(None), Feedback.next_retry_at <= now),
        )
        .order_by(Feedback.created_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    return list(session.scalars(statement))


def pending_counts(session: Session) -> dict[str, int]:
    rows = session.execute(
        select(Feedback.tag, func.count())
        .where(Feedback.learning_batch_id.is_(None), Feedback.processing_status.in_(["pending", "retry"]))
        .group_by(Feedback.tag)
    ).all()
    counts = {tag: int(count) for tag, count in rows}
    return {"interim": counts.get("interim", 0), "final": counts.get("final", 0), "total": sum(counts.values())}
