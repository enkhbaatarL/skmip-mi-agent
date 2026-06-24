from __future__ import annotations

import sys

from apps.agents.scenario_group_agent.subgraphs.scenario_generation import (
    generation_stages as _generation_stages,
)


sys.modules[__name__] = _generation_stages
