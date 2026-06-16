"""
Signpost DB Repository 모듈

역할:
- tmm_scenariom에서 시나리오 목록을 scenario_group_id 또는 mi_event_id로 조회한다.
- tmm_signpostm에 signpost pipeline 결과를 저장한다.
- 특정 시나리오에 signpost가 이미 존재하는지 확인한다.

설계 의도:
- scenario_flow_agent의 SyncScenarioRepository 패턴을 동일하게 적용
- Repository 계층에서 SQL 실행만 담당하고, service 계층에서 트랜잭션 처리
- SELECT 결과를 pipeline이 사용할 dict 형태로 변환
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select, exists

from apps.agents.scenario_agent.models.scenario_models_orm import ScenarioModel
from apps.agents.signpost_flow_agent.models.signpost_models_orm import SignpostModel
from apps.common.configs.database.sync_database.base import BaseSyncSQLRepository


class SyncSignpostRepository(BaseSyncSQLRepository):
    def fetch_scenarios_by_mi_event_id(self, mi_event_id: int) -> list[dict[str, Any]]:
        """tmm_scenariom에서 mi_event_id로 시나리오 목록을 ORM 조회.

        반환 형식은 stage4_scenario_synthesis.scenarios 배열과 유사한 dict 구조.
        각 시나리오 dict에는 실제 PK scenario_id가 포함된다.
        """
        stmt = (
            select(ScenarioModel)
            .where(
                ScenarioModel.mi_event_id == mi_event_id,
                ScenarioModel.del_yn == "N",
            )
            .order_by(ScenarioModel.scenario_id)
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

            price_dir = scenario.price_direction
            if isinstance(price_dir, str):
                try:
                    price_dir = json.loads(price_dir)
                except (json.JSONDecodeError, TypeError):
                    price_dir = {}
            elif price_dir is None:
                price_dir = {}

            scenarios.append({
                "scenario_id": int(scenario.scenario_id),
                "title": scenario.name or "",
                "description": scenario.description or "",
                "dimension_values": dim_values,
                "price_direction": price_dir,
                "likelihood": scenario.likelihood or "medium",
                "language": scenario.language or "ko",
                "status_code": scenario.status_code or "draft",
                # Fields not persisted in DB — provide defaults
                "derivation_rationale": "",
                "compatibility_passed": True,
            })

        return scenarios

    def fetch_scenario_group_id_by_mi_event_id(self, mi_event_id: int) -> str | None:
        """mi_event_id로 scenario_group_id를 조회."""
        stmt = (
            select(ScenarioModel.scenario_group_id)
            .where(
                ScenarioModel.mi_event_id == mi_event_id,
                ScenarioModel.del_yn == "N",
            )
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