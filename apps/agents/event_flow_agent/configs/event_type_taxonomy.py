#   apps/agents/event_flow_agent/configs/event_type_taxonomy.py

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