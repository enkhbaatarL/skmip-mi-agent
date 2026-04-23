#   apps/agents/event_flow_agent/configs/event_type_taxonomy.py
#   kmj20260423목
"""
event type taxonomy 로딩 모듈

역할:
- 공통 taxonomy JSON(apps\common\configs\event_type_taxonomy.json) 파일을 읽어,
  event_flow_agent에서 사용할 허용 category 조합과 가이드 문자열을 생성한다.
- level_1_code / level_2_code 조합의 유효성을 검증하는 기준을 제공한다.

제공 값:
- ALLOWED_CATEGORY_PAIRS
- CATEGORY_GUIDE

설계 의도:
- taxonomy 기준을 코드 내부에 하드코딩하지 않고 외부 JSON 설정으로 관리
- LLM 프롬프트와 schema validation이 동일한 taxonomy 기준을 사용하도록 통일
- event type 코드 체계를 공통 설정으로 일원화
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Set, Tuple


def load_category_pairs_and_guide() -> tuple[Set[Tuple[str, str]], str]:
    current = Path(__file__).resolve()

    # apps/agents/event_flow_agent/configs/event_type_taxonomy.py
    # -> project root
    project_root = current.parents[4]

    taxonomy_path = project_root / "apps" / "common" / "configs" / "event_type_taxonomy.json"

    with open(taxonomy_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    pairs: Set[Tuple[str, str]] = set()
    guide_lines: list[str] = []

    for node in data.get("taxonomy", []):
        level_1 = node.get("level_1_code", "")
        children = node.get("children", [])
        level_2_codes: list[str] = []

        for child in children:
            level_2 = child.get("level_2_code", "")
            if level_1 and level_2:
                pairs.add((level_1, level_2))
                level_2_codes.append(level_2)

        if level_1 and level_2_codes:
            guide_lines.append(f"- {level_1}: {', '.join(level_2_codes)}")

    return pairs, "\n".join(guide_lines)


ALLOWED_CATEGORY_PAIRS, CATEGORY_GUIDE = load_category_pairs_and_guide()