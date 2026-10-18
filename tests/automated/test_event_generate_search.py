# ruff: noqa: PT009

from __future__ import annotations

import os
from typing import Any
import unittest
from unittest.mock import MagicMock, patch


os.environ.setdefault("METADATA_DB_PORT", "3306")

from sqlalchemy.dialects import mysql

from apps.agents.event_generate_agent.persistence.event_generation_service import EventGenerationService
from apps.persistence.event.repository import EventRepository


def _row(event_id: int, score: int) -> dict[str, Any]:
    return {"mi_event_id": event_id, "one_line_summary": f"event {event_id}", "match_score": score}


class SearchEventAnalysesSqlTest(unittest.TestCase):
    def _compiled_sql(self, *, include_detail: bool) -> str:
        session = MagicMock()
        session.execute.return_value.all.return_value = []
        EventRepository(session=session).search_event_analyses(
            keyword="오만산 카고",
            limit=5,
            include_detail=include_detail,
        )
        stmt = session.execute.call_args[0][0]
        return str(stmt.compile(dialect=mysql.dialect(), compile_kwargs={"literal_binds": True}))

    def test_title_only_search_skips_detail_analysis_in_where(self) -> None:
        where = self._compiled_sql(include_detail=False).split("WHERE", 1)[1]
        self.assertIn("one_line_summary LIKE", where)
        self.assertNotIn("detail_analysis LIKE", where)
        self.assertIn("ORDER BY match_score DESC", where)

    def test_detail_search_matches_each_token_in_both_columns(self) -> None:
        where = self._compiled_sql(include_detail=True).split("WHERE", 1)[1]
        for token in ("오만산", "카고"):
            self.assertIn(f"one_line_summary LIKE '%%{token}%%'", where)
            self.assertIn(f"detail_analysis LIKE '%%{token}%%'", where)

    def test_blank_keyword_returns_without_query(self) -> None:
        session = MagicMock()
        self.assertEqual(EventRepository(session=session).search_event_analyses(keyword="  ", limit=5), [])
        session.execute.assert_not_called()


class SearchEventsDetailFallbackTest(unittest.TestCase):
    def _search(self, title_rows: list[dict[str, Any]], detail_rows: list[dict[str, Any]]) -> tuple[Any, MagicMock]:
        repository = MagicMock()
        repository.search_event_analyses.side_effect = [title_rows, detail_rows]
        with (
            patch(
                "apps.common.configs.database.sync_database.connection.get_sync_session",
                return_value=MagicMock(),
            ),
            patch(
                "apps.agents.event_generate_agent.persistence.event_generation_service.EventRepository",
                return_value=repository,
            ),
        ):
            result = EventGenerationService().search_events("오만산 LNG 카고", limit=5)
        return result, repository

    def test_title_hit_with_all_tokens_skips_detail_search(self) -> None:
        result, repository = self._search([_row(1, 3), _row(2, 1)], [])
        self.assertEqual([row["mi_event_id"] for row in result], [1, 2])
        self.assertEqual(repository.search_event_analyses.call_count, 1)
        self.assertFalse(repository.search_event_analyses.call_args.kwargs.get("include_detail", False))

    def test_partial_title_hits_fall_back_to_detail_search(self) -> None:
        result, repository = self._search([_row(2, 1)], [_row(7, 3), _row(2, 1)])
        self.assertEqual([row["mi_event_id"] for row in result], [7, 2])
        self.assertEqual(repository.search_event_analyses.call_count, 2)
        self.assertTrue(repository.search_event_analyses.call_args.kwargs["include_detail"])

    def test_no_title_hits_fall_back_to_detail_search(self) -> None:
        result, repository = self._search([], [_row(9, 2)])
        self.assertEqual([row["mi_event_id"] for row in result], [9])
        self.assertEqual(repository.search_event_analyses.call_count, 2)


if __name__ == "__main__":
    unittest.main()
