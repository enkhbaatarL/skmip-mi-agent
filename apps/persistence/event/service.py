from __future__ import annotations

from datetime import date, timedelta
import hashlib
import json
from typing import Any

from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.persistence.event.repository import EventRepository
from apps.persistence.scenario.repository import ScenarioRepository
from apps.persistence.scenario_group.repository import ScenarioGroupRepository
from apps.persistence.signpost.repository import SignpostRepository


class EventService:
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
