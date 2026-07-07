from __future__ import annotations

from sqlalchemy import Table

from apps.persistence.event.models import (
    MiEventModel,
    MiEventRecordMapModel,
    MiEventTypeL1Model,
    MiEventTypeL2Model,
)
from apps.persistence.model_parameter.models import (
    MiModelParamDimensionMapModel,
    MiModelParamModel,
    MiModelParamProposalModel,
)
from apps.persistence.scenario.models import (
    MiScenarioDimensionTemplateModel,
    MiScenarioModel,
)
from apps.persistence.scenario_group.models import (
    MiScenarioGroupModel,
    MiScenarioSnapModel,
    MiSignpostSnapModel,
    MiSnapshotModel,
)
from apps.persistence.signpost.models import MiSignpostModel


APPLICATION_TABLES: tuple[Table, ...] = (
    MiEventTypeL1Model.__table__,
    MiEventTypeL2Model.__table__,
    MiEventModel.__table__,
    MiEventRecordMapModel.__table__,
    MiScenarioGroupModel.__table__,
    MiScenarioDimensionTemplateModel.__table__,
    MiScenarioModel.__table__,
    MiSignpostModel.__table__,
    MiSnapshotModel.__table__,
    MiScenarioSnapModel.__table__,
    MiSignpostSnapModel.__table__,
    MiModelParamModel.__table__,
    MiModelParamDimensionMapModel.__table__,
    MiModelParamProposalModel.__table__,
)
