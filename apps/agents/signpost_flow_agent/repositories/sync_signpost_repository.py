"""
Signpost DB Repository 모듈

역할:
- tmm_mi_scenario_m에서 시나리오 목록을 scenario_group_id 또는 mi_event_id로 조회한다.
- tmm_signpostm에 signpost pipeline 결과를 저장한다.
- 특정 시나리오에 signpost가 이미 존재하는지 확인한다.

설계 의도:
- scenario_group_agent의 ScenarioRepository 패턴을 동일하게 적용
- Repository 계층에서 SQL 실행만 담당하고, service 계층에서 트랜잭션 처리
- SELECT 결과를 pipeline이 사용할 dict 형태로 변환
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select, exists

from apps.agents.scenario_group_agent.persistence.scenario.models import MiScenarioModel
from apps.agents.scenario_group_agent.persistence.scenario_group.models import (
    MiScenarioGroupModel,
)
from apps.agents.signpost_flow_agent.models.signpost_models_orm import SignpostModel
from apps.common.configs.database.sync_database.base import BaseSyncSQLRepository


class SyncSignpostRepository(BaseSyncSQLRepository):
    def fetch_scenarios_by_mi_event_id(self, mi_event_id: int) -> list[dict[str, Any]]:
        """tmm_mi_scenario_m에서 mi_event_id로 시나리오 목록을 ORM 조회.

        반환 형식은 stage4_scenario_synthesis.scenarios 배열과 유사한 dict 구조.
        각 시나리오 dict에는 실제 PK scenario_id가 포함된다.
        """
        stmt = (
            select(MiScenarioModel)
            .join(
                MiScenarioGroupModel,
                MiScenarioGroupModel.scenario_group_id == MiScenarioModel.scenario_group_id,
            )
            .where(
                MiScenarioGroupModel.mi_event_id == mi_event_id,
                MiScenarioGroupModel.del_yn == "N",
                MiScenarioModel.del_yn == "N",
            )
            .order_by(MiScenarioModel.scenario_id)
        )
        rows = self.session.execute(stmt).scalars().all()

        scenarios: list[dict[str, Any]] = []
        for scenario in rows:
            # JSON fields — handle both already-parsed dict and raw string
            dim_values = scenario.dimension_values
            if isinstance(dim_values, str):
                try:
                    dim_values = json.loads(dim_values)
                except (json.JSONDecodeError, TypeError):
                    dim_values = {}
            elif dim_values is None:
                dim_values = {}

            price_dir = {
                "jkm": scenario.impact_jkm,
                "ttf": scenario.impact_ttf,
                "hh": scenario.impact_hh,
            }

            scenarios.append({
                "scenario_id": int(scenario.scenario_id),
                "title": scenario.title or "",
                "description": scenario.narrative or "",
                "dimension_values": dim_values,
                "price_direction": price_dir,
                "likelihood": self._likelihood_from_probability(scenario.probability_score),
                "language": "ko",
                "status_code": self._to_string(scenario.status) or "creating",
                # Fields not persisted in DB — provide defaults
                "derivation_rationale": "",
                "compatibility_passed": True,
            })

        return scenarios

    def fetch_scenario_group_id_by_mi_event_id(self, mi_event_id: int) -> str | None:
        """mi_event_id로 scenario_group_id를 조회."""
        stmt = (
            select(MiScenarioGroupModel.scenario_group_id)
            .where(
                MiScenarioGroupModel.mi_event_id == mi_event_id,
                MiScenarioGroupModel.del_yn == "N",
            )
            .order_by(MiScenarioGroupModel.scenario_group_id.desc())
            .limit(1)
        )
        row = self.session.execute(stmt).one_or_none()
        if row is None:
            return None
        return str(row[0])

    def check_signposts_exist(self, scenario_id: int) -> bool:
        """tmm_signpostm에서 해당 scenario_id에 signpost가 이미 존재하는지 확인."""
        stmt = select(
            exists().where(
                SignpostModel.scenario_id == scenario_id,
                SignpostModel.del_yn == "N",
            )
        )
        return bool(self.session.execute(stmt).scalar())

    def insert_signpost(self, payload: dict) -> int:
        """tmm_signpostm에 signpost 1건을 저장하고 PK(signpost_id)를 반환."""
        signpost = SignpostModel(**payload)
        self.session.add(signpost)
        self.session.flush()
        return int(signpost.signpost_id)

    @staticmethod
    def _to_string(value: Any) -> str | None:
        if value is None:
            return None
        enum_value = getattr(value, "value", None)
        return str(enum_value if enum_value is not None else value)

    @classmethod
    def _likelihood_from_probability(cls, probability_score: Any) -> str:
        if probability_score is None:
            return "medium"
        try:
            score = float(probability_score)
        except (TypeError, ValueError):
            return "medium"
        if score >= 0.67:
            return "high"
        if score <= 0.33:
            return "low"
        return "medium"
