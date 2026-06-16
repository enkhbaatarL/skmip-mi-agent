"""
Signpost DB Service 모듈

역할:
- SyncSignpostRepository를 사용하여 DB 트랜잭션을 관리한다.
- 시나리오 로드와 signpost 저장/조회를 담당한다.

설계 의도:
- scenario_flow_agent의 ScenarioDbService 패턴과 동일하게 적용
- service 계층에서 세션 관리와 Payload 구성을 담당하고,
  repository 계층에서 SQL 실행만 담당
"""

from __future__ import annotations

from typing import Any

from apps.agents.scenario_group_agent.schemas.create_signposts import GeneratedSignpost
from apps.agents.signpost_flow_agent.repositories.sync_signpost_repository import (
    SyncSignpostRepository,
)
from apps.common.configs.database.sync_database.connection import get_sync_session


class SignpostDbService:
    """signpost DB interaction service layer."""

    def load_scenarios_for_event(self, mi_event_id: int) -> tuple[str | None, list[dict[str, Any]]]:
        """시나리오 그룹 ID와 시나리오 목록을 DB에서 로드.

        Args:
            mi_event_id: 조회할 MI Event ID

        Returns:
            (scenario_group_id, scenarios list) — 각 scenario dict에는 PK scenario_id 포함
        """
        session = get_sync_session()
        try:
            repository = SyncSignpostRepository(session=session)
            scenario_group_id = repository.fetch_scenario_group_id_by_mi_event_id(mi_event_id)
            scenarios = repository.fetch_scenarios_by_mi_event_id(mi_event_id)
            return scenario_group_id, scenarios
        finally:
            session.close()

    def check_signposts_exist(self, scenario_id: int) -> bool:
        """특정 시나리오에 signpost가 이미 존재하는지 확인."""
        session = get_sync_session()
        try:
            repository = SyncSignpostRepository(session=session)
            return repository.check_signposts_exist(scenario_id)
        finally:
            session.close()

    def save_signposts(
        self,
        signposts: list[GeneratedSignpost],
    ) -> list[int]:
        """생성된 signpost들을 tmm_signpostm에 저장.

        각 signpost dict에는 다음 키가 포함되어야 함:
            - scenario_id (INT): tmm_scenariom FK
            - label (str): signpost label
            - signpost_class (str): 'observation' 고정
            - signpost_source (str): 'mi_record' 고정
            - direction (str): 'SUP' 고정
            - strength (str): 'STRONG' / 'MEDIUM' / 'WEAK'
            - keyword_hints (list[str]): 모니터링 키워드 리스트

        Args:
            signposts: 저장할 signpost dict 리스트

        Returns:
            저장된 signpost PK(signpost_id) 목록
        """
        session = get_sync_session()
        try:
            repository = SyncSignpostRepository(session=session)
            saved_ids: list[int] = []

            for sp in signposts:
                keyword_hints = sp.keyword_hints or []

                payload = {
                    "scenario_id": sp.scenario_id,
                    "crt_usr_logn_id": "SYSTEM",
                    "mod_usr_logn_id": "SYSTEM",
                    "del_yn": "N",
                    "status_code": "draft",
                    "language": "ko",
                    "label": sp.label,
                    "signpost_class": sp.signpost_class,
                    "signpost_source": sp.signpost_source,
                    "direction": sp.direction.to_string(),
                    "strength": sp.strength.to_string() if sp.strength else None,
                    "keyword_hints": keyword_hints,
                }

                saved_id = repository.insert_signpost(payload)
                session.commit()
                saved_ids.append(saved_id)

            return saved_ids

        except Exception:
            session.rollback()
            raise
        finally:
            session.close()