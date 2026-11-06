from __future__ import annotations

from datetime import UTC, datetime

from pydantic import ValidationError
from sqlalchemy import MetaData, Table, func, select
from sqlalchemy.orm import Session

from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.persistence.event.schema import EventVerificationRecord


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class EventVerificationRepository:
    """Persist server-owned evidence; reuse checks must never trigger a fresh search."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.table = Table(
            "tmm_mi_mievent_verification_m",
            MetaData(),
            autoload_with=session.connection(),
            resolve_fks=False,
        )

    def insert(self, record: EventVerificationRecord, actor: str) -> None:
        values = record.model_dump()
        values["checked_at"] = _utc(record.checked_at).replace(tzinfo=None)
        values["expires_at"] = _utc(record.expires_at).replace(tzinfo=None)
        self.session.execute(self.table.insert().values(**values, crt_usr_logn_id=actor, mod_usr_logn_id=actor))

    def get(self, event_id: int, verification_id: str, *, lock: bool = False) -> EventVerificationRecord:
        stmt = select(self.table).where(
            self.table.c.mi_event_verification_id == verification_id,
            self.table.c.mi_event_id == event_id,
            self.table.c.del_yn == "N",
        )
        if lock:
            stmt = stmt.with_for_update()
        row = self.session.execute(stmt).mappings().one_or_none()
        if row is None:
            raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail="해당 Event의 활성 검증 결과가 없습니다.")
        try:
            record = EventVerificationRecord.model_validate(dict(row))
        except ValidationError as exc:
            raise MIBaseError(ErrorCode.EVENT_VERIFICATION_INVALID) from exc
        record.checked_at = _utc(record.checked_at)
        record.expires_at = _utc(record.expires_at)
        return record

    @staticmethod
    def ensure_usable(record: EventVerificationRecord) -> None:
        if record.applied_mi_event_snapshot_id is not None:
            raise MIBaseError(
                ErrorCode.EVENT_VERIFICATION_ALREADY_APPLIED,
                context={
                    "verification_id": record.mi_event_verification_id,
                    "mi_event_snapshot_id": record.applied_mi_event_snapshot_id,
                },
            )
        if _utc(record.expires_at) <= datetime.now(UTC):
            raise MIBaseError(ErrorCode.EVENT_VERIFICATION_EXPIRED)

    def mark_applied(self, record: EventVerificationRecord, snapshot_id: int, actor: str) -> None:
        now = (
            func.current_timestamp(6)
            if self.session.get_bind().dialect.name in {"mysql", "mariadb"}
            else func.current_timestamp()
        )
        self.session.execute(
            self.table.update()
            .where(self.table.c.mi_event_verification_id == record.mi_event_verification_id)
            .values(
                applied_mi_event_snapshot_id=snapshot_id,
                mod_usr_logn_id=actor,
                mod_dtm=now,
            ),
        )
