from __future__ import annotations

import sys

from apps.agents.scenario_group_agent.subgraphs.scenario_generation import (
    flow as _flow,
)


sys.modules[__name__] = _flow
