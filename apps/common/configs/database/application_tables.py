from __future__ import annotations

from sqlalchemy import Table

from apps.agents.event_flow_agent.models.mi_event_models_orm import (
    MiEventModel,
    MiEventRecordMapModel,
    MiEventTypeL1Model,
    MiEventTypeL2Model,
)
from apps.agents.scenario_group_agent.persistence.scenario.models import MiScenarioModel
from apps.agents.scenario_group_agent.persistence.scenario_group.models import (
    MiScenarioGroupModel,
    MiScenarioSnapModel,
    MiSignpostSnapModel,
    MiSnapshotModel,
)
from apps.agents.scenario_group_agent.persistence.signpost.models import MiSignpostModel


APPLICATION_TABLES: tuple[Table, ...] = (
    MiEventTypeL1Model.__table__,
    MiEventTypeL2Model.__table__,
    MiEventModel.__table__,
    MiEventRecordMapModel.__table__,
    MiScenarioGroupModel.__table__,
    MiScenarioModel.__table__,
    MiSignpostModel.__table__,
    MiSnapshotModel.__table__,
    MiScenarioSnapModel.__table__,
    MiSignpostSnapModel.__table__,
)
