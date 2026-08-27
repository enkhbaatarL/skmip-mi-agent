from __future__ import annotations  # noqa: CPY001

import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pydantic import BaseModel
import yaml

from apps.agents.model_parameter_agent.constants import AGENT_NAME
from apps.agents.model_parameter_agent.utils.tracing import build_trace_context


ROOT_DIR = Path(__file__).resolve().parents[2]
MODEL_PARAMETER_AIP_APP_ID = "parameter-agent-local"


class _StructuredOutput(BaseModel):
    value: str


def test_model_parameter_aip_app_id_is_configured_for_local_and_kubernetes() -> None:
    local_config = yaml.safe_load((ROOT_DIR / "envs/config.yaml").read_text(encoding="utf-8"))
    configmap = yaml.safe_load((ROOT_DIR / "devops/k8s/configmap.yaml").read_text(encoding="utf-8"))
    kubernetes_config = yaml.safe_load(configmap["data"]["config.yaml"])

    assert local_config["agents"][AGENT_NAME]["aip_app_id"] == MODEL_PARAMETER_AIP_APP_ID  # noqa: S101
    assert kubernetes_config["agents"][AGENT_NAME]["aip_app_id"] == MODEL_PARAMETER_AIP_APP_ID  # noqa: S101


def test_model_parameter_structured_llm_request_includes_aip_app_id_header() -> None:
    with patch.dict(os.environ, {"METADATA_DB_PORT": "3306"}):
        from apps.connectors.llm.llm_client import _structured_output_request_kwargs

    settings = SimpleNamespace(
        get_agent_config=lambda agent_name: SimpleNamespace(
            aip_app_id=MODEL_PARAMETER_AIP_APP_ID if agent_name == AGENT_NAME else "unexpected",
        ),
    )
    with (
        patch("apps.common.configs.config.get_settings", return_value=settings),
        patch(
            "apps.agents.model_parameter_agent.utils.tracing.new_transaction_id",
            return_value="tx-parameter",
        ),
    ):
        trace_context = build_trace_context(session_id="proposal-42")

    with patch(
        "apps.connectors.llm.llm_client.get_settings",
        return_value=SimpleNamespace(llm_structured_output_strict=False),
    ):
        request_kwargs = _structured_output_request_kwargs(
            output_schema=_StructuredOutput,
            model="test-model",
            messages=[{"role": "user", "content": "test"}],
            trace_context=trace_context,
            stream=False,
            reasoning_effort=None,
        )

    assert request_kwargs["extra_headers"] == {  # noqa: S101
        "aip-transaction-id": "tx-parameter",
        "aip-app-id": MODEL_PARAMETER_AIP_APP_ID,
        "aip-chat-id": "proposal-42",
    }
