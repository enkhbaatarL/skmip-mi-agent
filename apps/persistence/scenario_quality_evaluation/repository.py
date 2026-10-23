from __future__ import annotations

# ruff: noqa: CPY001
from sqlalchemy import select

from apps.common.configs.database.sync_database.base import BaseSyncSQLRepository
from apps.persistence.scenario_quality_evaluation.models import MiScenarioQualityEvaluationModel


class ScenarioQualityEvaluationRepository(BaseSyncSQLRepository):
    def fetch_by_operation_id(self, operation_id: str) -> MiScenarioQualityEvaluationModel | None:
        return self.session.get(MiScenarioQualityEvaluationModel, operation_id)

    def fetch_by_request_id(self, request_id: str) -> MiScenarioQualityEvaluationModel | None:
        stmt = select(MiScenarioQualityEvaluationModel).where(MiScenarioQualityEvaluationModel.request_id == request_id)
        return self.session.execute(stmt).scalars().one_or_none()

    def insert(self, row: MiScenarioQualityEvaluationModel) -> None:
        self.session.add(row)
        self.session.flush()
