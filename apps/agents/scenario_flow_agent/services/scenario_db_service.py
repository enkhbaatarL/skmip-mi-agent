"""
Scenario DB Service 모듈

역할:
- SyncScenarioRepository를 사용하여 DB 트랜잭션을 관리한다.
- Base Event 로드와 시나리오 저장/조회를 담당한다.

설계 의도:
- event_flow_agent의 EventPersistenceService 패턴과 동일하게 적용
- service 계층에서 세션 관리와 Payload 구성을 담당하고,
  repository 계층에서 SQL 실행만 담당
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from apps.common.configs.settings import Settings, get_settings
from apps.agents.scenario_flow_agent.repositories.sync_scenario_repository import (
    SyncScenarioRepository,
)
from apps.common.configs.database.sync_database.connection import get_sync_session


class ScenarioDbService:
    """scenario DB interaction service layer."""

    def check_scenarios_exist(self, mi_event_id: int) -> bool:
        """Check if scenarios already exist for the given mi_event_id."""
        session = get_sync_session()
        try:
            repository = SyncScenarioRepository(session=session)
            return repository.check_scenarios_exist(mi_event_id)
        finally:
            session.close()

    def load_event(self, mi_event_id: int) -> dict[str, Any] | None:
        """Base Event를 DB에서 로드.

        Args:
            mi_event_id: 조회할 MI Event ID

        Returns:
            sample_event JSON 형식의 dict, 없으면 None
        """
        session = get_sync_session()
        try:
            repository = SyncScenarioRepository(session=session)
            return repository.fetch_event_by_id(mi_event_id)
        finally:
            session.close()

    def save_scenario_group(
        self,
        scenario_group_id: str,
        mi_event_id: int,
        stage4: dict[str, Any],
        stage5: dict[str, Any],
    ) -> list[int]:
        """시나리오 그룹을 DB(tmm_scenariom)에 저장.

        stage4의 각 scenario를 개별 row로 INSERT한다.

        Args:
            scenario_group_id: 시나리오 그룹 키
            mi_event_id: Base MI Event ID (FK)
            stage4: Stage 4 결과 dict (scenarios 리스트 포함)
            stage5: Stage 5 결과 dict (likelihood_prior 포함)

        Returns:
            저장된 시나리오 PK(scenario_id) 목록
        """
        session = get_sync_session()
        try:
            repository = SyncScenarioRepository(session=session)
            saved_ids: list[int] = []

            scenarios = stage4.get("scenarios", [])
            likelihood_prior = stage5.get("likelihood_prior", {})

            for scenario in scenarios:
                scenario_id = scenario.get("scenario_id", "")
                dimension_values = scenario.get("dimension_values", {})
                price_direction = scenario.get("price_direction", {})
                likelihood = likelihood_prior.get(scenario_id, "medium")

                settings: Settings = get_settings()
                tz = ZoneInfo(settings.time_zone)
                now_dt = datetime.now(tz)
                valid_duration_days = int(os.getenv("REF_SCENARIO_VALID_DURATION", "30"))

                payload = {
                    "scenario_group_id": scenario_group_id,
                    "crt_usr_logn_id": "SYSTEM",
                    "mod_usr_logn_id": "SYSTEM",
                    "del_yn": "N",
                    "name": scenario.get("title", ""),
                    "description": scenario.get("description", ""),
                    "mi_event_id": mi_event_id,
                    "status_code": "draft",
                    "valid_from": now_dt.isoformat(timespec="seconds"),
                    "valid_to": (now_dt + timedelta(days=valid_duration_days)).isoformat(timespec="seconds"),
                    "language": "ko",
                    "dimension_values": json.dumps(dimension_values, ensure_ascii=False),
                    "likelihood": likelihood,
                    "price_direction": json.dumps(price_direction, ensure_ascii=False),
                }

                saved_id = repository.insert_scenario(payload)
                session.commit()
                saved_ids.append(saved_id)

            return saved_ids

        except Exception:
            session.rollback()
            raise
        finally:
            session.close()