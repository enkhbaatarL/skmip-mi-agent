"""tmm_mi_mievent_m 에 확정 이벤트를 저장하고, 기존 이벤트를 근거용으로 조회하는 서비스."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

from apps.agents.event_generate_agent.constants import (
    DEFAULT_ACTOR_ID,
    EVENT_ACTOR_ID_PREFIX,
    EVENT_PUBLISH_STATUS_PUBLISHED,
    ONE_LINE_SUMMARY_MAX_LENGTH,
    SEARCH_TEXT_MAX_LENGTH,
)
from apps.agents.event_generate_agent.schemas.api.event import ConfirmedEventOut, GeneratedEventOut
from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.logger_config import logger
from apps.common.values.error_codes import ErrorCode
from apps.persistence.event.repository import EventRepository


def _parse_occurred_at(raw: str) -> datetime | None:
    """초안의 occurred_at 문자열을 DATETIME 컬럼 값으로 바꾼다.

    LLM 산출물이라 형식이 흔들릴 수 있으므로, 해석되지 않으면 NULL로 둔다.
    (occurred_at 은 nullable 이고 이 값 때문에 저장 전체를 실패시킬 이유는 없다.)
    """
    text = (raw or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        logger.warning(f"[SERVICE][EventGenerationService] UNPARSED_OCCURRED_AT | raw={text!r}")
        return None


class EventGenerationService:
    def create_event(
        self,
        event: GeneratedEventOut,
        *,
        user_id: str | None = None,
    ) -> ConfirmedEventOut:
        """이벤트 1건을 신규 insert하고 발급된 mi_event_id를 돌려준다."""
        from apps.common.configs.database.sync_database.connection import get_sync_session

        event_type_l2_id = event.event_type_l2_id
        if event_type_l2_id is None:
            raise MIBaseError(
                ErrorCode.INVALID_REQUEST,
                detail=f"event_type_l2_id is required to persist an event: summary={event.one_line_summary!r}",
            )

        actor_id = f"{EVENT_ACTOR_ID_PREFIX}{user_id if user_id is not None else DEFAULT_ACTOR_ID}"
        # 커스텀 이벤트는 원천 Record 가 없으므로 생성 시점을 latest/oldest Record 시각으로 쓴다.
        # DATETIME(6) 컬럼은 tz 정보가 없어 UTC 기준 naive 값으로 저장한다.
        created_at = datetime.now(UTC).replace(tzinfo=None)
        session = get_sync_session()
        try:
            repository = EventRepository(session=session)
            mi_event_id = repository.insert_event(
                {
                    "event_type_l2_id": event_type_l2_id,
                    # one_line_summary 는 (삭제된 event_title 을 대체하는) 제목, search_text 는 요약 컬럼이다.
                    # 별도 제목을 생성하지 않으므로 두 컬럼 모두 one_line_summary 를 저장한다.
                    # ORM 에 매핑되지 않은 신규 컬럼은 insert 에서 빠지므로 NULL(또는 DB 기본값)로 채워진다.
                    "one_line_summary": event.one_line_summary[:ONE_LINE_SUMMARY_MAX_LENGTH],
                    "search_text": event.one_line_summary[:SEARCH_TEXT_MAX_LENGTH],
                    "key_bullets_json": {"bullets": [str(bullet) for bullet in event.key_bullets]},
                    "detail_analysis": event.detail_analysis,
                    "tags_json": ({"tags": [str(tag) for tag in event.tags]} if event.tags else None),
                    "occurred_at": _parse_occurred_at(event.occurred_at),
                    "latest_record_first_created": created_at,
                    "oldest_record_first_created": created_at,
                    "new_yn": "Y",
                    "publish_status": EVENT_PUBLISH_STATUS_PUBLISHED,
                    "crt_usr_logn_id": actor_id,
                    "mod_usr_logn_id": actor_id,
                },
            )
            session.commit()
            logger.info(f"[SERVICE][EventGenerationService] EVENT_CREATED | mi_event_id={mi_event_id}")
            return ConfirmedEventOut(mi_event_id=mi_event_id, event_type_l2_id=event_type_l2_id)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def load_event_type_catalog(self) -> list[dict[str, Any]]:
        """tmm_mi_event_type_l2_m 에서 event type L2 카탈로그를 조회한다.

        읽기 전용이라 commit 없이 세션만 닫는다.
        """
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            catalog = EventRepository(session=session).list_event_types_l2()
        finally:
            session.close()

        logger.info(f"[SERVICE][EventGenerationService] EVENT_TYPE_CATALOG_LOADED | count={len(catalog)}")
        return catalog

    def search_events(
        self,
        keyword: str,
        *,
        limit: int,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[dict[str, Any]]:
        """tmm_mi_mievent_m 에서 키워드(제목·검색 요약 LIKE)로 기존 이벤트를 최신 발생순으로 조회한다.

        date_to 는 그날을 포함하도록 하루 뒤를 exclusive 경계로 넘긴다. 읽기 전용이라 commit 하지 않는다.
        """
        from apps.common.configs.database.sync_database.connection import get_sync_session

        session = get_sync_session()
        try:
            return EventRepository(session=session).search_event_analyses(
                keyword=keyword,
                date_from=date_from,
                date_to=date_to + timedelta(days=1) if date_to is not None else None,
                limit=limit,
            )
        finally:
            session.close()
