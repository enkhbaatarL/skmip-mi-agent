from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import hashlib
import json
from typing import Any, get_args

from sqlalchemy import MetaData, Table, func, select
from sqlalchemy.orm import Session

from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.persistence.event.schema import EventSearchSource, EventUpdateApplied, EventUpdateContext, EventUpdateField


UPDATE_TRIGGER = "LLM_VALIDATION_UPDATE"
_AUDIT_SOURCE = {
    "event_del_yn": "del_yn",
    "event_crt_usr_logn_id": "crt_usr_logn_id",
    "event_crt_dtm": "crt_dtm",
    "event_mod_usr_logn_id": "mod_usr_logn_id",
    "event_mod_dtm": "mod_dtm",
}
_SNAPSHOT_METADATA = frozenset(
    {
        "mi_event_snapshot_id",
        "snapshot_version_no",
        "previous_mi_event_snapshot_id",
        "crt_usr_logn_id",
        "crt_dtm",
        "mod_usr_logn_id",
        "mod_dtm",
        "del_yn",
        "update_trigger_cd",
        "update_reason",
        "changed_fields_json",
    },
)


def _fingerprint(row: dict[str, Any]) -> str:
    canonical = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


class EventUpdateRepository:
    """Reflect the two owned tables to preserve columns not mapped by the Agent read model.

    The current schema uses one_line_summary for the display title and search_text for search context.
    Only the explicit content allowlist can be updated. No DDL is issued.
    """

    def __init__(self, session: Session) -> None:
        self.session = session
        metadata = MetaData()
        connection = session.connection()
        self.event = Table("tmm_mi_mievent_m", metadata, autoload_with=connection, resolve_fks=False)
        self.snapshot = Table("tmm_mi_mievent_snapshot_m", metadata, autoload_with=connection, resolve_fks=False)
        self._validate_schema()

    def _validate_schema(self) -> None:
        required_event = {
            "mi_event_id",
            "one_line_summary",
            "search_text",
            "publish_status",
            "key_bullets_json",
            "detail_analysis",
            "crt_usr_logn_id",
            "crt_dtm",
            "mod_usr_logn_id",
            "mod_dtm",
            "del_yn",
        }
        required_snapshot = (
            _SNAPSHOT_METADATA
            | set(_AUDIT_SOURCE)
            | {
                "mi_event_id",
                "one_line_summary",
                "search_text",
                "key_bullets_json",
                "detail_analysis",
            }
        )
        if not required_event <= set(self.event.c.keys()) or not required_snapshot <= set(self.snapshot.c.keys()):
            raise MIBaseError(
                ErrorCode.EVENT_UPDATE_SCHEMA_ERROR,
                detail="필수 본문·Snapshot 감사 컬럼을 확인해주세요.",
            )
        # Every Event column represented by the snapshot must be copied, including v0046 extension fields.
        for column in self.snapshot.c:
            if column.name in _SNAPSHOT_METADATA or column.name in _AUDIT_SOURCE or column.name in self.event.c:
                continue
            if not column.nullable and column.server_default is None:
                raise MIBaseError(ErrorCode.EVENT_UPDATE_SCHEMA_ERROR, detail=f"Snapshot 원본 컬럼 없음: {column.name}")
        for name in get_args(EventUpdateField):
            if name in self.event.c and name not in self.snapshot.c:
                raise MIBaseError(ErrorCode.EVENT_UPDATE_SCHEMA_ERROR, detail=f"Snapshot 보존 컬럼 없음: {name}")

    def read_event(self, event_id: int, *, lock: bool = False) -> dict[str, Any]:
        stmt = select(self.event).where(self.event.c.mi_event_id == event_id)
        if lock:
            stmt = stmt.with_for_update()
        row = self.session.execute(stmt).mappings().one_or_none()
        if row is None or row["del_yn"] != "N" or row["publish_status"] != "PUBLISHED":
            raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail="Event가 없거나 게시 상태가 아닙니다.")
        return dict(row)

    def prepare(self, event_id: int, expected_updated_at: datetime | None) -> EventUpdateContext:
        row = self.read_event(event_id)
        if expected_updated_at is not None and row["mod_dtm"] != expected_updated_at:
            raise MIBaseError(ErrorCode.EVENT_UPDATE_STALE)
        source = EventSearchSource.model_validate(row)
        return EventUpdateContext(
            source=source,
            fingerprint=_fingerprint(row),
            content={name: row[name] for name in get_args(EventUpdateField) if name in row},
        )

    def _changes(self, row: dict[str, Any], proposed: dict[str, Any]) -> dict[str, Any]:
        changes: dict[str, Any] = {}
        for name, value in proposed.items():
            if name not in get_args(EventUpdateField) or name not in row:
                raise MIBaseError(ErrorCode.INVALID_REQUEST, detail=f"수정할 수 없는 컬럼: {name}")
            if name == "key_bullets_json":
                if (
                    not isinstance(value, list)
                    or not value
                    or any(not isinstance(v, str) or not v.strip() for v in value)
                ):
                    raise MIBaseError(
                        ErrorCode.INVALID_REQUEST,
                        detail="핵심 bullet은 비어 있지 않은 문자열 배열이어야 합니다.",
                    )
                if isinstance(row[name], dict):
                    if "bullets" not in row[name]:
                        raise MIBaseError(
                            ErrorCode.INVALID_REQUEST,
                            detail="지원하지 않는 핵심 bullet JSON 구조입니다.",
                        )
                    value = {**deepcopy(row[name]), "bullets": value}
            elif not isinstance(value, str) or not value.strip():
                raise MIBaseError(ErrorCode.INVALID_REQUEST, detail=f"빈 문자열로 수정할 수 없습니다: {name}")
            length = getattr(self.event.c[name].type, "length", None)
            if length and len(value) > length:
                raise MIBaseError(ErrorCode.INVALID_REQUEST, detail=f"컬럼 최대 길이 초과: {name}")
            if value != row[name]:
                changes[name] = value
        return changes

    def apply(
        self,
        event_id: int,
        fingerprint: str,
        proposed: dict[str, Any],
        actor: str,
        reason: str,
    ) -> EventUpdateApplied:
        # Parent row lock serializes snapshot version allocation, including the first snapshot.
        row = self.read_event(event_id, lock=True)
        if _fingerprint(row) != fingerprint:
            raise MIBaseError(ErrorCode.EVENT_UPDATE_STALE)
        changes = self._changes(row, proposed)
        if not changes:
            return EventUpdateApplied(
                mi_event_id=event_id,
                snapshot_id=None,
                snapshot_version_no=None,
                previous_snapshot_id=None,
                changed_fields=[],
                updated_at=row["mod_dtm"],
            )
        previous = self.session.execute(
            select(self.snapshot.c.mi_event_snapshot_id)
            .where(self.snapshot.c.mi_event_id == event_id)
            .order_by(self.snapshot.c.mi_event_snapshot_id.desc())
            .limit(1)
            .with_for_update(),
        ).scalar_one_or_none()
        last_version = self.session.execute(
            select(self.snapshot.c.snapshot_version_no)
            .where(self.snapshot.c.mi_event_id == event_id)
            .order_by(self.snapshot.c.snapshot_version_no.desc())
            .limit(1)
            .with_for_update(),
        ).scalar_one_or_none()
        version = (last_version or 0) + 1
        snapshot_values = {
            column.name: deepcopy(row[column.name])
            for column in self.snapshot.c
            if column.name not in _SNAPSHOT_METADATA and column.name not in _AUDIT_SOURCE and column.name in row
        }
        snapshot_values.update({target: row[source] for target, source in _AUDIT_SOURCE.items()})
        snapshot_values.update(
            snapshot_version_no=version,
            previous_mi_event_snapshot_id=previous,
            crt_usr_logn_id=actor,
            mod_usr_logn_id=actor,
            update_trigger_cd=UPDATE_TRIGGER,
            update_reason=reason,
            changed_fields_json=sorted(changes) if previous is not None else [],
        )
        # Execute INSERT before UPDATE. Session transaction ownership stays in EventService.
        inserted = self.session.execute(self.snapshot.insert().values(**snapshot_values))
        snapshot_id = int(inserted.inserted_primary_key[0])
        now = (
            func.current_timestamp(6)
            if self.session.bind.dialect.name in {"mysql", "mariadb"}
            else func.current_timestamp()
        )
        values = {**changes, "mod_usr_logn_id": actor, "mod_dtm": now}
        if "new_yn" in row:
            values["new_yn"] = "N"
        if "event_revision" in row:
            values["event_revision"] = row["event_revision"] + 1
        self.session.execute(self.event.update().where(self.event.c.mi_event_id == event_id).values(**values))
        updated_at = self.session.execute(
            select(self.event.c.mod_dtm).where(self.event.c.mi_event_id == event_id),
        ).scalar_one()
        return EventUpdateApplied(
            mi_event_id=event_id,
            snapshot_id=snapshot_id,
            snapshot_version_no=version,
            previous_snapshot_id=previous,
            changed_fields=sorted(changes),
            updated_at=updated_at,
        )
