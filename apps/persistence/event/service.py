from __future__ import annotations

from datetime import date, datetime, timedelta
import hashlib
import json
from typing import Any

from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.logger_config import logger
from apps.common.values.error_codes import ErrorCode
from apps.persistence.event.repository import EventRepository
from apps.persistence.event.schema import (
    EventSearchSource,
    EventUpdateApplied,
    EventUpdateContext,
    EventVerificationRecord,
)
from apps.persistence.scenario.repository import ScenarioRepository
from apps.persistence.scenario_group.repository import ScenarioGroupRepository
from apps.persistence.signpost.repository import SignpostRepository


class EventService:
    def prepare_verifications(self, event_ids: list[int]) -> list[EventUpdateContext]:
        from apps.common.configs.database.sync_database.connection import get_sync_session
        from apps.persistence.event.update_repository import EventUpdateRepository
        from apps.persistence.event.verification_repository import EventVerificationRepository

        with get_sync_session() as session:
            EventVerificationRepository(session)  # Fail before external calls when the persistence schema is missing.
            repository = EventUpdateRepository(session)
            return [repository.prepare(event_id, None) for event_id in event_ids]

    def store_verifications(self, records: list[EventVerificationRecord], actor: str) -> None:
        from apps.common.configs.database.sync_database.connection import get_sync_session
        from apps.persistence.event.verification_repository import EventVerificationRepository

        with get_sync_session() as session, session.begin():
            repository = EventVerificationRepository(session)
            for record in records:
                repository.insert(record, actor)

    def load_verification_update(
        self, event_id: int, verification_id: str, expected_updated_at: datetime | None = None,
    ) -> tuple[EventUpdateContext, EventVerificationRecord]:
        from apps.common.configs.database.sync_database.connection import get_sync_session
        from apps.persistence.event.update_repository import EventUpdateRepository
        from apps.persistence.event.verification_repository import EventVerificationRepository

        with get_sync_session() as session:
            logger.info(
                "[EVENT_VERIFICATION_UPDATE] DB_TARGET | event_id={} | database={}",
                event_id,
                session.get_bind().engine.url.database,
            )
            repository = EventVerificationRepository(session)
            record = repository.get(event_id, verification_id)
            repository.ensure_usable(record)
            context = EventUpdateRepository(session).prepare(event_id, expected_updated_at)
            if context.fingerprint != record.event_fingerprint:
                raise MIBaseError(ErrorCode.EVENT_UPDATE_STALE)
            return context, record

    def prepare_verification_update(
        self, event_id: int, expected_updated_at: datetime | None = None,
    ) -> EventUpdateContext:
        from apps.common.configs.database.sync_database.connection import get_sync_session
        from apps.persistence.event.update_repository import EventUpdateRepository

        with get_sync_session() as session:
            logger.info(
                "[EVENT_VERIFICATION_UPDATE] DB_TARGET | event_id={} | database={}",
                event_id,
                session.get_bind().engine.url.database,
            )
            return EventUpdateRepository(session).prepare(event_id, expected_updated_at)

    def apply_verification_update(
        self, event_id: int, fingerprint: str, changes: dict[str, Any], actor: str, reason: str,
        *, verification_id: str | None = None,
    ) -> EventUpdateApplied:
        from apps.common.configs.database.sync_database.connection import get_sync_session
        from apps.persistence.event.update_repository import EventUpdateRepository
        from apps.persistence.event.verification_repository import EventVerificationRepository

        with get_sync_session() as session, session.begin():
            database = session.get_bind().engine.url.database
            update_repository = EventUpdateRepository(session)
            record = None
            if verification_id is not None:
                verification_repository = EventVerificationRepository(session)
                record = verification_repository.get(event_id, verification_id, lock=True)
                verification_repository.ensure_usable(record)
                if record.event_fingerprint != fingerprint:
                    raise MIBaseError(ErrorCode.EVENT_UPDATE_STALE)
                update_repository.read_event(event_id, lock=True)
                # A lock wait can cross the expiration boundary: check again before INSERT/UPDATE.
                verification_repository.ensure_usable(record)
            applied = update_repository.apply(event_id, fingerprint, changes, actor, reason)
            if record is not None and applied.snapshot_id is not None:
                verification_repository.mark_applied(record, applied.snapshot_id, actor)
        # session.begin() must exit successfully before reporting a committed write.
        if applied.changed_fields:
            logger.info(
                "[EVENT_VERIFICATION_UPDATE] DB_COMMITTED | event_id={} | database={} | snapshot_id={} "
                "| snapshot_version_no={} | changed_fields={} | updated_at={}",
                event_id,
                database,
                applied.snapshot_id,
                applied.snapshot_version_no,
                applied.changed_fields,
                applied.updated_at,
            )
        return applied

    def load_search_sources(
        self,
        *,
        limit: int = 200,
        event_ids: list[int] | None = None,
    ) -> list[EventSearchSource]:
        """Bounded internal export, not a user-authorized search endpoint."""
        from apps.common.configs.database.sync_database.connection import get_sync_session

        if not 1 <= limit <= 200 or (
            event_ids is not None and (len(event_ids) > limit or any(event_id <= 0 for event_id in event_ids))
        ):
            raise MIBaseError(
                ErrorCode.INVALID_REQUEST,
                detail="검색 문서 조회는 양의 Event ID와 limit 1~200이 필요합니다.",
            )
        with get_sync_session() as session:
            rows = EventRepository(session=session).list_search_sources(limit=limit, event_ids=event_ids)
            return [EventSearchSource.model_validate(row) for row in rows]

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
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        normalized_page = max(page, 1)
        normalized_page_size = max(min(page_size, 100), 1)
        offset = (normalized_page - 1) * normalized_page_size
        inclusive_date_to = date_to + timedelta(days=1) if date_to is not None else None

        session = get_sync_session()
        try:
            event_repository = EventRepository(session=session)
            rows = event_repository.list_events(
                keyword=keyword,
                status=status,
                event_type_l1_id=event_type_l1_id,
                event_type_l2_id=event_type_l2_id,
                recommended_only=recommended_only,
                date_from=date_from,
                date_to=inclusive_date_to,
                sort=sort,
                offset=offset,
                limit=normalized_page_size,
            )
            total = event_repository.count_events(
                keyword=keyword,
                status=status,
                event_type_l1_id=event_type_l1_id,
                event_type_l2_id=event_type_l2_id,
                recommended_only=recommended_only,
                date_from=date_from,
                date_to=inclusive_date_to,
            )
            return {
                "rows": [self._with_related_group(row, session) for row in rows],
                "pagination": {
                    "page": normalized_page,
                    "page_size": normalized_page_size,
                    "total": total,
                    "has_previous": normalized_page > 1,
                    "has_next": offset + len(rows) < total,
                },
                "source": {"type": "agent_db"},
            }
        finally:
            session.close()

    def get_event_detail(self, mi_event_id: int) -> dict[str, Any]:
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            event_repository = EventRepository(session=session)
            event = event_repository.fetch_event_detail_by_id(mi_event_id)
            if event is None:
                raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail=f"Event not found: {mi_event_id}")

            template_model = ScenarioRepository(session=session).fetch_template_model(
                int(event["event_type_l2_id"]),
            )
            template_json = (
                template_model.template_json
                if template_model is not None and isinstance(template_model.template_json, list)
                else []
            )
            canonical = json.dumps(
                {
                    "event_type_definition": (
                        template_model.event_type_definition if template_model is not None else ""
                    )
                    or "",
                    "lng_price_impact_examples": (
                        template_model.lng_price_impact_examples if template_model is not None else ""
                    )
                    or "",
                    "dimensions": template_json,
                },
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            return {
                "event": self._with_related_group(event, session),
                "scenario_template": {
                    "event_type_l2_id": int(event["event_type_l2_id"]),
                    "scenario_dimension_template_id": (
                        int(template_model.scenario_dimension_template_id) if template_model is not None else None
                    ),
                    "event_type_definition": (
                        template_model.event_type_definition if template_model is not None else None
                    ),
                    "lng_price_impact_examples": (
                        template_model.lng_price_impact_examples if template_model is not None else None
                    ),
                    "template_checksum": hashlib.sha256(canonical.encode()).hexdigest(),
                    "dimensions": self._template_dimensions(template_json),
                    "raw_template_json": template_json or [],
                },
                "source": {"type": "agent_db"},
            }
        finally:
            session.close()

    def _with_related_group(self, event: dict[str, Any], session: Any) -> dict[str, Any]:
        group_repository = ScenarioGroupRepository(session=session)
        scenario_repository = ScenarioRepository(session=session)
        signpost_repository = SignpostRepository(session=session)
        group = group_repository.fetch_by_any_event_id(
            int(event["mi_event_id"]),
        )
        related = None
        action_state = {"type": "create", "label": "생성하기", "disabled": False, "reason": None}
        if group is not None:
            scenarios = scenario_repository.fetch_models_by_group_id(int(group.scenario_group_id))
            signposts = signpost_repository.fetch_models_by_scenario_ids(
                [int(scenario.scenario_id) for scenario in scenarios]
            )
            status = str(group.status.value if hasattr(group.status, "value") else group.status)
            stage = str(group.stage.value if hasattr(group.stage, "value") else group.stage)
            related = {
                "scenario_group_id": int(group.scenario_group_id),
                "status": status,
                "stage": stage,
                "deleted": group.del_yn == "Y",
                "del_yn": group.del_yn,
                "scenario_count": len(scenarios),
                "signpost_count": len(signposts),
                "title": group.title,
            }
            action_type = "open_detail" if status == "created" and stage == "completed" else "continue_generation"
            action_state = {
                "type": action_type,
                "label": "상세보기" if action_type == "open_detail" else "생성하기",
                "disabled": False,
                "reason": None,
            }
        elif event.get("scenario_suggest_yn") == "N":
            action_state = {
                "type": "disabled",
                "label": "생성불가",
                "disabled": True,
                "reason": event.get("scenario_suggest_reason") or "scenarioSuggestYn=N",
            }

        return {
            **event,
            "related_scenario_group": related,
            "scenario_action_state": action_state,
        }

    @staticmethod
    def _template_dimensions(template_json: Any) -> list[dict[str, Any]]:
        if not isinstance(template_json, list):
            return []
        dimensions: list[dict[str, Any]] = []
        for index, item in enumerate(template_json, start=1):
            if not isinstance(item, dict):
                continue
            dimensions.append(
                {
                    "key": str(item.get("dim_key") or item.get("key") or ""),
                    "label": str(item.get("label") or item.get("dim_label") or item.get("dim_key") or ""),
                    "required": bool(item.get("required", False)),
                    "description": (
                        str(item.get("description") or "").strip()
                        or str(
                            item.get("label") or item.get("dim_label") or item.get("dim_key") or "",
                        )
                    ),
                    "display_order": int(item.get("display_order") or index),
                    "enum_values": (item.get("value_enums") or item.get("enum_values") or item.get("values") or []),
                    "raw": item,
                }
            )
        return dimensions
