from __future__ import annotations

from apps.agents.scenario_group_agent.persistence.model_impact_lever_service import (
    _resolve_binding_support,
)


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
