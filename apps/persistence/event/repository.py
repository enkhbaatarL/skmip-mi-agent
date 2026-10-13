from __future__ import annotations

from datetime import date
import json
from typing import Any

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import joinedload

from apps.common.configs.database.sync_database.base import BaseSyncSQLRepository
from apps.persistence.event.models import (
    MiEventModel,
    MiEventRecordMapModel,
    MiEventSnapshotModel,
    MiEventTypeL2Model,
)


class EventRepository(BaseSyncSQLRepository):
    def insert_event(self, payload: dict[str, Any]) -> int:
        """tmm_mi_mievent_m 에 Event 1건을 insert하고 발급된 PK를 돌려준다.

        commit은 호출하는 service 계층이 담당한다.
        """
        event = MiEventModel(**payload)
        self.session.add(event)
        self.session.flush()
        return int(event.mi_event_id)

    def lock_events(self, mi_event_ids: list[int]) -> list[int]:
        """Lock active Event source rows in a deterministic order for create preparation."""
        if not mi_event_ids:
            return []
        stmt = (
            select(MiEventModel.mi_event_id)
            .where(
                MiEventModel.mi_event_id.in_(sorted(mi_event_ids)),
                MiEventModel.del_yn == "N",
            )
            .order_by(MiEventModel.mi_event_id)
            .with_for_update()
        )
        return [int(mi_event_id) for mi_event_id in self.session.execute(stmt).scalars().all()]

    def list_events(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        event_type_l1_id: int | None = None,
        event_type_l2_id: int | None = None,
        recommended_only: bool = False,
        date_from: date | None = None,
        date_to: date | None = None,
        sort: str = "latest",
        offset: int = 0,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        stmt = (
            select(MiEventModel)
            .options(
                joinedload(MiEventModel.type_l2).joinedload(MiEventTypeL2Model.level_1),
                joinedload(MiEventModel.record_maps),
            )
            .where(MiEventModel.del_yn == "N")
        )
        stmt = self._apply_filters(
            stmt,
            keyword=keyword,
            status=status,
            event_type_l1_id=event_type_l1_id,
            event_type_l2_id=event_type_l2_id,
            recommended_only=recommended_only,
            date_from=date_from,
            date_to=date_to,
        )
        if sort == "oldest":
            stmt = stmt.order_by(MiEventModel.occurred_at.asc(), MiEventModel.mi_event_id.asc())
        else:
            stmt = stmt.order_by(MiEventModel.occurred_at.desc(), MiEventModel.mi_event_id.desc())
        events = self.session.execute(stmt.offset(offset).limit(limit)).scalars().unique().all()
        return [self._event_to_backoffice_dict(event) for event in events]

    def count_events(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        event_type_l1_id: int | None = None,
        event_type_l2_id: int | None = None,
        recommended_only: bool = False,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> int:
        stmt = select(MiEventModel.mi_event_id).join(MiEventModel.type_l2).where(MiEventModel.del_yn == "N")
        stmt = self._apply_filters(
            stmt,
            keyword=keyword,
            status=status,
            event_type_l1_id=event_type_l1_id,
            event_type_l2_id=event_type_l2_id,
            recommended_only=recommended_only,
            date_from=date_from,
            date_to=date_to,
        )
        return len(self.session.execute(stmt).all())

    def fetch_event_by_id(self, mi_event_id: int) -> dict[str, Any] | None:
        stmt = (
            select(MiEventModel)
            .options(
                joinedload(MiEventModel.type_l2).joinedload(MiEventTypeL2Model.level_1),
                joinedload(MiEventModel.record_maps),
            )
            .where(MiEventModel.mi_event_id == mi_event_id, MiEventModel.del_yn == "N")
        )
        event = self.session.execute(stmt).scalars().unique().one_or_none()
        if event is None:
            return None
        return self._event_to_pipeline_dict(event)

    def fetch_event_core_by_id(self, mi_event_id: int) -> dict[str, Any] | None:
        """Load Event evidence without joining the legacy Event Type catalog."""
        stmt = (
            select(MiEventModel)
            .options(joinedload(MiEventModel.record_maps))
            .where(MiEventModel.mi_event_id == mi_event_id, MiEventModel.del_yn == "N")
        )
        event = self.session.execute(stmt).scalars().unique().one_or_none()
        if event is None:
            return None
        return self._event_to_core_pipeline_dict(event)

    def fetch_event_detail_by_id(self, mi_event_id: int) -> dict[str, Any] | None:
        stmt = (
            select(MiEventModel)
            .options(
                joinedload(MiEventModel.type_l2).joinedload(MiEventTypeL2Model.level_1),
                joinedload(MiEventModel.record_maps),
            )
            .where(MiEventModel.mi_event_id == mi_event_id, MiEventModel.del_yn == "N")
        )
        event = self.session.execute(stmt).scalars().unique().one_or_none()
        if event is None:
            return None
        return self._event_to_backoffice_dict(event)

    def fetch_event_type_by_l2_id(self, event_type_l2_id: int) -> dict[str, Any] | None:
        stmt = (
            select(MiEventTypeL2Model)
            .options(joinedload(MiEventTypeL2Model.level_1))
            .where(
                MiEventTypeL2Model.event_type_l2_id == event_type_l2_id,
                MiEventTypeL2Model.del_yn == "N",
            )
        )
        l2 = self.session.execute(stmt).scalars().one_or_none()
        if l2 is None:
            return None
        l1 = l2.level_1
        return {
            "event_type_l1_id": int(l2.event_type_l1_id),
            "event_type_l2_id": int(l2.event_type_l2_id),
            "level_1_code": l1.level_1_code if l1 else "",
            "level_1_label": l1.level_1_label if l1 else "",
            "level_2_code": l2.level_2_code,
            "level_2_label": l2.level_2_label,
        }

    def list_event_types_l2(self) -> list[dict[str, Any]]:
        """활성 Event Type L2 전체를 코드·한글명과 함께 조회한다.

        분류 프롬프트에 넣을 카탈로그 용도라 L1 조인 없이 L2 컬럼만 읽는다.
        """
        stmt = (
            select(
                MiEventTypeL2Model.event_type_l2_id,
                MiEventTypeL2Model.level_2_code,
                MiEventTypeL2Model.level_2_label,
            )
            .where(MiEventTypeL2Model.del_yn == "N")
            .order_by(MiEventTypeL2Model.event_type_l2_id)
        )
        return [
            {
                "event_type_l2_id": int(row.event_type_l2_id),
                "level_2_code": row.level_2_code,
                "level_2_label": row.level_2_label,
            }
            for row in self.session.execute(stmt).all()
        ]

    def _apply_filters(
        self,
        stmt: Select[tuple[Any]] | Select[tuple[MiEventModel]],
        *,
        keyword: str | None,
        status: str | None,
        event_type_l1_id: int | None,
        event_type_l2_id: int | None,
        recommended_only: bool,
        date_from: date | None,
        date_to: date | None,
    ) -> Select[tuple[Any]] | Select[tuple[MiEventModel]]:
        if keyword:
            like = f"%{keyword.strip()}%"
            stmt = stmt.where(or_(MiEventModel.one_line_summary.like(like), MiEventModel.search_text.like(like)))
        if status == "new":
            stmt = stmt.where(MiEventModel.new_yn == "Y")
        elif status == "updated":
            stmt = stmt.where(MiEventModel.new_yn == "N")
        if event_type_l1_id is not None:
            stmt = stmt.join(MiEventModel.type_l2).where(MiEventTypeL2Model.event_type_l1_id == event_type_l1_id)
        if event_type_l2_id is not None:
            stmt = stmt.where(MiEventModel.event_type_l2_id == event_type_l2_id)
        if recommended_only:
            stmt = stmt.where(MiEventModel.scenario_suggest_yn == "Y")
        if date_from is not None:
            stmt = stmt.where(MiEventModel.occurred_at >= date_from)
        if date_to is not None:
            stmt = stmt.where(MiEventModel.occurred_at < date_to)
        return stmt

    def _parse_json_list(self, raw_json: Any, *, wrapper_key: str) -> list[Any]:
        if raw_json is None:
            return []
        if isinstance(raw_json, list):
            return raw_json
        if isinstance(raw_json, dict):
            wrapped = raw_json.get(wrapper_key)
            return wrapped if isinstance(wrapped, list) else []
        if isinstance(raw_json, str):
            try:
                parsed = json.loads(raw_json)
            except (json.JSONDecodeError, TypeError):
                return []
            return self._parse_json_list(parsed, wrapper_key=wrapper_key)
        return []

    def _event_to_pipeline_dict(self, event: MiEventModel) -> dict[str, Any]:
        l2 = event.type_l2
        l1 = l2.level_1 if l2 else None
        source_record_ids = [int(rm.mi_record_id) for rm in event.record_maps if rm.mi_record_id]

        return {
            "mi_event_id": str(event.mi_event_id),
            "event_type_l2_id": int(event.event_type_l2_id),
            # event_title 컬럼은 one_line_summary 로 대체되고, 기존 요약은 search_text 에 담긴다.
            "event_title_ko": event.one_line_summary or "",
            "one_line_summary": event.search_text or "",
            "key_bullets": [
                str(item).strip()
                for item in self._parse_json_list(event.key_bullets_json, wrapper_key="bullets")
                if item
            ],
            "detail_analysis": event.detail_analysis or "",
            "source_mi_record_ids": source_record_ids,
            "created_at": event.crt_dtm.isoformat() if event.crt_dtm else "",
            "updated_at": event.mod_dtm.isoformat() if event.mod_dtm else "",
            "latest_record_first_created": (
                event.latest_record_first_created.isoformat() if event.latest_record_first_created else ""
            ),
            "oldest_record_first_created": (
                event.oldest_record_first_created.isoformat() if event.oldest_record_first_created else ""
            ),
            "event_type": {
                "event_type_l1_id": (int(l1.event_type_l1_id) if l1 else None),
                "event_type_l2_id": (int(l2.event_type_l2_id) if l2 else None),
                "level_1_code": l1.level_1_code if l1 else "",
                "level_1_label": l1.level_1_label if l1 else "",
                "level_2_code": l2.level_2_code if l2 else "",
                "level_2_label": l2.level_2_label if l2 else "",
            },
            "language": "ko",
            "occurred_at": event.occurred_at.isoformat() if event.occurred_at else "",
            "tags": [str(item).strip() for item in self._parse_json_list(event.tags_json, wrapper_key="tags") if item],
        }

    def _event_to_core_pipeline_dict(self, event: MiEventModel) -> dict[str, Any]:
        """Serialize Event evidence without dereferencing its Event Type relationship."""
        source_record_ids = [int(record.mi_record_id) for record in event.record_maps if record.mi_record_id]
        return {
            "mi_event_id": str(event.mi_event_id),
            # event_title 컬럼은 one_line_summary 로 대체되고, 기존 요약은 search_text 에 담긴다.
            "event_title_ko": event.one_line_summary or "",
            "one_line_summary": event.search_text or "",
            "key_bullets": [
                str(item).strip()
                for item in self._parse_json_list(event.key_bullets_json, wrapper_key="bullets")
                if item
            ],
            "detail_analysis": event.detail_analysis or "",
            "source_mi_record_ids": source_record_ids,
            "created_at": event.crt_dtm.isoformat() if event.crt_dtm else "",
            "updated_at": event.mod_dtm.isoformat() if event.mod_dtm else "",
            "latest_record_first_created": (
                event.latest_record_first_created.isoformat() if event.latest_record_first_created else ""
            ),
            "oldest_record_first_created": (
                event.oldest_record_first_created.isoformat() if event.oldest_record_first_created else ""
            ),
            "language": "ko",
            "occurred_at": event.occurred_at.isoformat() if event.occurred_at else "",
            "tags": [str(item).strip() for item in self._parse_json_list(event.tags_json, wrapper_key="tags") if item],
        }

    def _event_to_backoffice_dict(self, event: MiEventModel) -> dict[str, Any]:
        payload = self._event_to_pipeline_dict(event)
        l2 = event.type_l2
        l1 = l2.level_1 if l2 else None
        payload.update(
            {
                "mi_event_id": int(event.mi_event_id),
                "title": event.one_line_summary or "",
                "event_title": event.one_line_summary or "",
                "event_time": event.occurred_at.isoformat() if event.occurred_at else "",
                "latest_record_first_created": event.latest_record_first_created.isoformat()
                if event.latest_record_first_created
                else "",
                "oldest_record_first_created": event.oldest_record_first_created.isoformat()
                if event.oldest_record_first_created
                else "",
                "category": l1.level_1_label if l1 else "",
                "event_type_l1": {
                    "id": int(l1.event_type_l1_id) if l1 else None,
                    "code": l1.level_1_code if l1 else "",
                    "label": l1.level_1_label if l1 else "",
                },
                "event_type_l2": {
                    "id": int(l2.event_type_l2_id) if l2 else None,
                    "code": l2.level_2_code if l2 else "",
                    "label": l2.level_2_label if l2 else "",
                },
                "new_yn": event.new_yn,
                "signal_yn": event.signal_yn,
                "signal_confidence": float(event.signal_confidence or 0),
                "signal_reason": event.signal_reason,
                "scenario_suggest_yn": event.scenario_suggest_yn,
                "scenario_suggest_reason": event.scenario_suggest_reason,
            },
        )
        return payload

    def fetch_latest_snapshot_id(self, mi_event_id: int) -> int | None:
        """생성 시점에 고정할 스냅샷 ID 조회 (해당 Event에 대한 가장 최근 스냅샷)."""
        stmt = (
            select(MiEventSnapshotModel.mi_event_snapshot_id)
            .where(MiEventSnapshotModel.mi_event_id == mi_event_id)
            .order_by(MiEventSnapshotModel.mi_event_snapshot_id.desc())
            .limit(1)
        )
        return self.session.execute(stmt).scalars().first()

    def fetch_snapshot_by_id(self, mi_event_snapshot_id: int) -> dict[str, Any] | None:
        stmt = select(MiEventSnapshotModel).where(
            MiEventSnapshotModel.mi_event_snapshot_id == mi_event_snapshot_id,
        )
        snapshot = self.session.execute(stmt).scalars().one_or_none()
        if snapshot is None:
            return None
        return self._snapshot_to_pipeline_dict(snapshot)

    def _snapshot_to_pipeline_dict(self, snapshot: MiEventSnapshotModel) -> dict[str, Any]:
        """스냅샷 row를 `_event_to_pipeline_dict()`와 동일한 shape으로 변환 (EventPayload 재사용 목적).

        record_maps는 스냅샷이 없어 항상 live 조회로 대체하며, event_type_l2_id는
        FK가 없어 live 카탈로그(tmm_mi_event_type_l2_m)를 별도 조회한다.
        """
        event_type = self.fetch_event_type_by_l2_id(int(snapshot.event_type_l2_id)) or {}
        return {
            "mi_event_id": str(snapshot.mi_event_id),
            "event_type_l2_id": int(snapshot.event_type_l2_id),
            "event_title_ko": snapshot.one_line_summary or "",
            "one_line_summary": snapshot.search_text or "",
            "key_bullets": [
                str(item).strip()
                for item in self._parse_json_list(snapshot.key_bullets_json, wrapper_key="bullets")
                if item
            ],
            "detail_analysis": snapshot.detail_analysis or "",
            "source_mi_record_ids": self.fetch_source_record_ids(int(snapshot.mi_event_id)),
            "created_at": snapshot.event_crt_dtm.isoformat() if snapshot.event_crt_dtm else "",
            "updated_at": snapshot.event_mod_dtm.isoformat() if snapshot.event_mod_dtm else "",
            "latest_record_first_created": (
                snapshot.latest_record_first_created.isoformat() if snapshot.latest_record_first_created else ""
            ),
            "oldest_record_first_created": (
                snapshot.oldest_record_first_created.isoformat() if snapshot.oldest_record_first_created else ""
            ),
            "event_type": {
                "event_type_l1_id": event_type.get("event_type_l1_id"),
                "event_type_l2_id": event_type.get("event_type_l2_id", int(snapshot.event_type_l2_id)),
                "level_1_code": event_type.get("level_1_code", ""),
                "level_1_label": event_type.get("level_1_label", ""),
                "level_2_code": event_type.get("level_2_code", ""),
                "level_2_label": event_type.get("level_2_label", ""),
            },
            "language": "ko",
            "occurred_at": snapshot.occurred_at.isoformat() if snapshot.occurred_at else "",
            "tags": [
                str(item).strip() for item in self._parse_json_list(snapshot.tags_json, wrapper_key="tags") if item
            ],
        }

    def fetch_source_record_ids(self, mi_event_id: int) -> list[int]:
        stmt = (
            select(MiEventRecordMapModel.mi_record_id)
            .where(MiEventRecordMapModel.mi_event_id == mi_event_id, MiEventRecordMapModel.del_yn == "N")
            .order_by(MiEventRecordMapModel.mi_record_id)
        )
        return [int(row[0]) for row in self.session.execute(stmt).all() if row[0]]
