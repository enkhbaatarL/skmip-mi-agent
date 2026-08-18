from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

from apps.agents.scenario_group_agent.persistence.model_impact_lever_service import (
    ModelImpactLeverService,
    _resolve_binding_support,
)
from apps.persistence.model_impact_lever.repository import ModelImpactLeverRepository


def test_display_labels_use_lightweight_catalog_query_and_close_session() -> None:
    session = MagicMock()
    labels = {
        "inventory_condition": "재고 여건",
        "regional_price_spread": "지역 가격 스프레드",
    }
    connection_module = ModuleType("apps.common.configs.database.sync_database.connection")
    connection_module.get_sync_session = MagicMock(return_value=session)
    with (
        patch.dict(
            sys.modules,
            {"apps.common.configs.database.sync_database.connection": connection_module},
        ),
        patch.object(ModelImpactLeverRepository, "fetch_display_labels", return_value=labels) as fetch,
    ):
        result = ModelImpactLeverService().load_display_labels()

    assert result == labels
    fetch.assert_called_once_with()
    session.close.assert_called_once_with()


def test_binding_support_distinguishes_active_and_inactive_master_rows() -> None:
    assert _resolve_binding_support(
        requested_status="executable",
        master_use_yn="Y",
        requested_reason_code=None,
    ) == ("executable", None)
    assert _resolve_binding_support(
        requested_status="executable",
        master_use_yn="N",
        requested_reason_code=None,
    ) == ("known_unsupported", "INACTIVE_MODEL_PARAMETER")


def test_catalog_marked_unsupported_remains_distinguishable() -> None:
    assert _resolve_binding_support(
        requested_status="known_unsupported",
        master_use_yn="Y",
        requested_reason_code=None,
    ) == ("known_unsupported", "CATALOG_MARKED_UNSUPPORTED")
