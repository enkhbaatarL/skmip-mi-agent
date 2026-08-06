from __future__ import annotations

import copy
from typing import Any

from fastapi import APIRouter

from app.seed import load_seed_document

router = APIRouter(tags=["examples"])


@router.get("/examples")
def get_examples() -> dict[str, Any]:
    seed = load_seed_document()
    example3 = copy.deepcopy(seed.example1)
    for fact in example3.get("eventImpactFacts", []):
        if fact.get("eventId") == 101:
            fact["timing"] = "다가오는 동절기 후반"
    return {
        "syntheticBaselineLabel": "Prototype synthetic baseline",
        "items": [
            {
                "exampleId": "example1",
                "label": "예시 1 — 동북아 한파와 액화설비 정비",
                "metadata": seed.example1_meta,
                "scenarioJson": seed.example1,
                "requiresClarification": False,
            },
            {
                "exampleId": "example2",
                "label": "예시 2 — 폭염과 액화설비 재가동",
                "metadata": seed.example2_meta,
                "scenarioJson": seed.example2,
                "requiresClarification": False,
            },
            {
                "exampleId": "example3",
                "label": "예시 3 — 모호한 Event Timing",
                "metadata": seed.example1_meta,
                "scenarioJson": example3,
                "requiresClarification": True,
            },
        ],
    }
