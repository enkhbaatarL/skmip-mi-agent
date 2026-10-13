# ruff: noqa: PT009

from __future__ import annotations

import os
from typing import Any
import unittest


os.environ.setdefault("METADATA_DB_PORT", "3306")

from apps.connectors.web.provider import _collect_citations


_GP_FIRST = "https://www.goldenpasslng.com/newsroom/first-lng-production"
_EIA_A = "https://www.eia.gov/todayinenergy/detail.php?id=67564"
_EIA_B = "https://www.eia.gov/todayinenergy/detail.php?id=68064"


def _link(domain: str, url: str) -> str:
    return f"([{domain}]({url}))"


def _response(lines: list[str], links: list[tuple[str, str]]) -> dict[str, Any]:
    """Responses API 처럼 답변 본문에 링크를 삽입하고, annotation 이 그 링크 구간을 가리키게 만든다."""
    text = "\n".join(lines)
    annotations: list[dict[str, Any]] = []
    cursor = 0
    for domain, url in links:
        link = _link(domain, url)
        start = text.index(link, cursor)
        annotations.append(
            {"type": "url_citation", "url": url, "title": domain, "start_index": start, "end_index": start + len(link)},
        )
        cursor = start + len(link)
    return {
        "output": [{"type": "message", "content": [{"type": "output_text", "text": text, "annotations": annotations}]}],
    }


class CollectCitationsTests(unittest.TestCase):
    def test_snippet_is_cited_sentence_not_link(self) -> None:
        response = _response(
            [
                "| 날짜 | 이벤트 | 근거 |",
                "|---|---|---|",
                (
                    f"| **2026-03-30** | Train 1에서 **첫 LNG 생산** 달성. | 공식 보도자료, 발행일 2026-03-30. "
                    f"{_link('goldenpasslng.com', _GP_FIRST)} |"
                ),
            ],
            [("goldenpasslng.com", _GP_FIRST)],
        )
        [citation] = _collect_citations(response, max_results=10)
        self.assertEqual(citation.url, _GP_FIRST)
        self.assertIn("첫 LNG 생산 달성", citation.snippet)
        self.assertIn("발행일 2026-03-30", citation.snippet)
        self.assertNotIn("](", citation.snippet)
        self.assertNotIn("**", citation.snippet)

    def test_same_url_cited_twice_keeps_both_passages(self) -> None:
        response = _response(
            [
                f"- 첫 cargo 는 first LNG 이후 23일 만에 출항했다. {_link('eia.gov', _EIA_A)}",
                f"- Train 3 startup 목표는 2027년 상반기다. {_link('eia.gov', _EIA_A)}",
            ],
            [("eia.gov", _EIA_A), ("eia.gov", _EIA_A)],
        )
        [citation] = _collect_citations(response, max_results=10)
        self.assertIn("23일 만에 출항", citation.snippet)
        self.assertIn("2027년 상반기", citation.snippet)

    def test_adjacent_links_share_the_preceding_sentence(self) -> None:
        response = _response(
            [f"- 전체 용량은 약 18.1 mtpa 다. {_link('goldenpasslng.com', _GP_FIRST)} {_link('eia.gov', _EIA_A)}"],
            [("goldenpasslng.com", _GP_FIRST), ("eia.gov", _EIA_A)],
        )
        citations = _collect_citations(response, max_results=10)
        self.assertEqual([c.url for c in citations], [_GP_FIRST, _EIA_A])
        for citation in citations:
            self.assertEqual(citation.snippet, "전체 용량은 약 18.1 mtpa 다.")

    def test_sentences_in_one_paragraph_go_to_their_own_link(self) -> None:
        response = _response(
            [
                (
                    f"Train 2 는 연말 완공 예상이다. {_link('eia.gov', _EIA_B)} "
                    f"Train 3 는 2027년 가동 목표다. {_link('eia.gov', _EIA_A)}"
                ),
            ],
            [("eia.gov", _EIA_B), ("eia.gov", _EIA_A)],
        )
        by_url = {c.url: c.snippet for c in _collect_citations(response, max_results=10)}
        self.assertEqual(by_url[_EIA_B], "Train 2 는 연말 완공 예상이다.")
        self.assertEqual(by_url[_EIA_A], "Train 3 는 2027년 가동 목표다.")

    def test_max_results_limits_unique_urls(self) -> None:
        response = _response(
            [f"a {_link('x', _EIA_A)}", f"b {_link('y', _EIA_B)}", f"c {_link('z', _GP_FIRST)}"],
            [("x", _EIA_A), ("y", _EIA_B), ("z", _GP_FIRST)],
        )
        self.assertEqual(len(_collect_citations(response, max_results=2)), 2)


if __name__ == "__main__":
    unittest.main()
