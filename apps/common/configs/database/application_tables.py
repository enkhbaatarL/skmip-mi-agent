from __future__ import annotations

from sqlalchemy import Table

from apps.persistence.event.models import (
    MiEventModel,
    MiEventRecordMapModel,
    MiEventTypeL1Model,
    MiEventTypeL2Model,
)
from apps.persistence.model_impact_lever.models import MiModelImpactLeverModel
from apps.persistence.model_parameter.models import (
    MiModelParamDimensionMapModel,
    MiModelParamModel,
    MiModelParamProposalModel,
)
from apps.persistence.scenario.models import (
    MiDimensionValueMappingModel,
    MiScenarioDimensionTemplateModel,
    MiScenarioModel,
)
from apps.persistence.scenario_group.models import (
    MiScenarioGroupEventModel,
    MiScenarioGroupModel,
)
from apps.persistence.scenario_group_operation.models import (
    MiScenarioGroupOperationEventModel,
    MiScenarioGroupOperationModel,
)
from apps.persistence.signpost.models import MiSignpostModel


APPLICATION_TABLES: tuple[Table, ...] = (
    MiEventTypeL1Model.__table__,
    MiEventTypeL2Model.__table__,
    MiEventModel.__table__,
    MiEventRecordMapModel.__table__,
    MiScenarioGroupModel.__table__,
    MiScenarioDimensionTemplateModel.__table__,
    MiScenarioGroupEventModel.__table__,
    MiScenarioGroupOperationModel.__table__,
    MiScenarioGroupOperationEventModel.__table__,
    MiScenarioModel.__table__,
    MiDimensionValueMappingModel.__table__,
    MiModelImpactLeverModel.__table__,
    MiSignpostModel.__table__,
)

MODEL_PARAMETER_TABLES: tuple[Table, ...] = (
    MiModelParamModel.__table__,
    MiModelParamDimensionMapModel.__table__,
    MiModelParamProposalModel.__table__,
)
