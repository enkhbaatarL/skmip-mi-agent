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
        search_text: str = "",
        user_id: str | None = None,
    ) -> ConfirmedEventOut:
        """이벤트 1건을 신규 insert하고 발급된 mi_event_id를 돌려준다.

        search_text 는 API 응답에 노출하지 않는 저장 전용 값이라 GeneratedEventOut 과 별도 인자로 받는다.
        """
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
                    # one_line_summary 는 (삭제된 event_title 을 대체하는) 제목, search_text 는 검색용 요약 컬럼이다.
                    # search_text 는 NOT NULL 이라 LLM 이 비워 두면 one_line_summary 로 대신한다.
                    # ORM 에 매핑되지 않은 신규 컬럼은 insert 에서 빠지므로 NULL(또는 DB 기본값)로 채워진다.
                    "one_line_summary": event.one_line_summary[:ONE_LINE_SUMMARY_MAX_LENGTH],
                    "search_text": (search_text.strip() or event.one_line_summary)[:SEARCH_TEXT_MAX_LENGTH],
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
        """tmm_mi_mievent_m 에서 키워드(단어별 LIKE)로 기존 이벤트를 조회한다.

        맞은 단어 수가 많은 순, 같으면 최신 발생순으로 정렬한다.
        먼저 짧은 제목(one_line_summary)만 찾고, 키워드 단어가 전부 맞은 이벤트가 없을 때만
        긴 상세 분석(detail_analysis)까지 넓혀 다시 찾는다. 본문 검색은 무겁고 흔한 단어가 잘 걸리므로
        제목으로 충분히 가려지면 건너뛴다.

        date_to 는 그날을 포함하도록 하루 뒤를 exclusive 경계로 넘긴다. 읽기 전용이라 commit 하지 않는다.
        """
        from apps.common.configs.database.sync_database.connection import get_sync_session

        token_count = len(set(keyword.split()))
        exclusive_date_to = date_to + timedelta(days=1) if date_to is not None else None
        session = get_sync_session()
        try:
            repository = EventRepository(session=session)
            rows = repository.search_event_analyses(
                keyword=keyword,
                date_from=date_from,
                date_to=exclusive_date_to,
                limit=limit,
            )
            best_score = max((row["match_score"] for row in rows), default=0)
            if best_score >= token_count:
                return rows

            logger.info(
                f"[SERVICE][EventGenerationService] SEARCH_DETAIL_FALLBACK | keyword={keyword!r} "
                f"| title_hits={len(rows)} | best_score={best_score}/{token_count}",
            )
            return repository.search_event_analyses(
                keyword=keyword,
                date_from=date_from,
                date_to=exclusive_date_to,
                limit=limit,
                include_detail=True,
            )
        finally:
            session.close()
