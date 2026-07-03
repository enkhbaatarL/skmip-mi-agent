from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from apps.common.configs.database.sync_database.base import BaseSyncSQLRepository
from apps.persistence.event.models import (
    MiEventModel,
    MiEventRecordMapModel,
    MiEventTypeL2Model,
)


class EventRepository(BaseSyncSQLRepository):
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

    def _parse_json_list(self, raw_json: Any) -> list[Any]:
        if raw_json is None:
            return []
        if isinstance(raw_json, list):
            return raw_json
        if isinstance(raw_json, str):
            try:
                parsed = json.loads(raw_json)
            except (json.JSONDecodeError, TypeError):
                return []
            return parsed if isinstance(parsed, list) else []
        return []

    def _event_to_pipeline_dict(self, event: MiEventModel) -> dict[str, Any]:
        l2 = event.type_l2
        l1 = l2.level_1 if l2 else None
        source_record_ids = [int(rm.mi_record_id) for rm in event.record_maps if rm.mi_record_id]

        return {
            "mi_event_id": str(event.mi_event_id),
            "event_type_l2_id": int(event.event_type_l2_id),
            "event_title_ko": event.event_title or "",
            "one_line_summary": event.one_line_summary or "",
            "key_bullets": [str(item).strip() for item in self._parse_json_list(event.key_bullets_json) if item],
            "detail_analysis": event.detail_analysis or "",
            "source_mi_record_ids": source_record_ids,
            "created_at": event.crt_dtm.isoformat() if event.crt_dtm else "",
            "updated_at": event.mod_dtm.isoformat() if event.mod_dtm else "",
            "event_type": {
                "level_1_code": l1.level_1_code if l1 else "",
                "level_2_code": l2.level_2_code if l2 else "",
            },
            "language": "ko",
            "occurred_at": event.occurred_at.isoformat() if event.occurred_at else "",
            "tags": [str(item).strip() for item in self._parse_json_list(event.tags_json) if item],
        }

    def fetch_source_record_ids(self, mi_event_id: int) -> list[int]:
        stmt = (
            select(MiEventRecordMapModel.mi_record_id)
            .where(MiEventRecordMapModel.mi_event_id == mi_event_id, MiEventRecordMapModel.del_yn == "N")
            .order_by(MiEventRecordMapModel.mi_record_id)
        )
        return [int(row[0]) for row in self.session.execute(stmt).all() if row[0]]
