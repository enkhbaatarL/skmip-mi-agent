# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: ANN401, EM101, EM102, FBT001, S603, S607, T201, TRY003

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal
import json
from pathlib import Path
import shlex
import subprocess
import textwrap
import time
from typing import Any

import httpx


EXPECTED_OPERATIONS = {
    ("POST", "/model-parameters/scenarios/{scenario_id}/proposals/sync"),
    ("POST", "/model-parameters/scenarios/{scenario_id}/proposals"),
    ("POST", "/model-parameters/proposals/{modelParamProposalId}/confirmation"),
}
EXPECTED_PROPOSAL_ALLOWLIST = {
    "GDP",
    "PMI",
    "PowerMix",
    "Temperature",
    "LiqUtilAdjustment",
}
ROLLBACK_SNAPSHOT_FIELDS = (
    "status",
    "proposal_parameters",
    "confirmation_parameters",
    "confirmed_dtm",
    "mod_usr_logn_id",
    "mod_dtm",
)
TERMINAL_PROPOSAL_STATUSES = {"PROPOSED", "CONFIRMED", "FAILED"}
PRECISION_PROBE_VALUE = 0.123456789
STEP3_PRECISION_PROBE_VALUE = 49.123456789


class SmokeTestError(AssertionError):
    pass


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_safe(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    return value


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeTestError(message)


def _response_json(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise SmokeTestError(
            f"HTTP {response.status_code} response is not JSON: {response.text[:500]!r}",
        ) from exc
    _require(isinstance(payload, dict), f"response JSON must be an object: {type(payload).__name__}")
    return payload


def _without_lut_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _without_lut_value(item) for key, item in value.items() if key != "lutValue"}
    if isinstance(value, list):
        return [_without_lut_value(item) for item in value]
    return value


def _snapshot(row: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(row.get(field)) for field in ROLLBACK_SNAPSHOT_FIELDS}


def _proposal_id(response_payload: dict[str, Any]) -> int:
    data = response_payload.get("data") or {}
    raw = data.get("modelParamProposalId")
    _require(isinstance(raw, int) and not isinstance(raw, bool), "modelParamProposalId must be an integer")
    return int(raw)


def _proposal_parameter_names(parameters: list[dict[str, Any]]) -> set[str]:
    return {
        str(parameter.get("parameterName") or parameter.get("parameter_name") or "").strip()
        for parameter in parameters
        if str(parameter.get("parameterName") or parameter.get("parameter_name") or "").strip()
    }


def _confirmation_parameters_with_precision_probe(
    parameters: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    confirmation_parameters = deepcopy(parameters)
    _require(bool(confirmation_parameters), "precision probe requires at least one parameter")
    first_values = confirmation_parameters[0].get("values") or []
    _require(bool(first_values), "precision probe requires at least one parameter value")
    first_values[0]["proposedValue"] = PRECISION_PROBE_VALUE
    return confirmation_parameters


def _first_proposed_value(parameters: Any) -> Any:
    if not isinstance(parameters, list) or not parameters:
        return None
    first_parameter = parameters[0]
    if not isinstance(first_parameter, dict):
        return None
    first_values = first_parameter.get("values") or []
    if not isinstance(first_values, list) or not first_values:
        return None
    first_value = first_values[0]
    return first_value.get("proposedValue") if isinstance(first_value, dict) else None


def _remote_readback_program(proposal_id: int) -> str:
    return textwrap.dedent(
        f"""
        import json
        from datetime import date, datetime
        from decimal import Decimal

        from sqlalchemy import select, text

        from apps.common.configs.database.sync_database.connection import get_sync_session
        from apps.persistence.model_parameter.models import MiModelParamProposalModel


        def safe(value):
            if isinstance(value, Decimal):
                return float(value)
            if isinstance(value, (datetime, date)):
                return value.isoformat()
            if isinstance(value, dict):
                return {{str(key): safe(item) for key, item in value.items()}}
            if isinstance(value, (list, tuple)):
                return [safe(item) for item in value]
            if hasattr(value, "value"):
                return value.value
            return value


        session = get_sync_session()
        try:
            session.execute(text("SET TRANSACTION READ ONLY"))
            proposal = session.execute(
                select(MiModelParamProposalModel).where(
                    MiModelParamProposalModel.model_param_proposal_id == {proposal_id},
                    MiModelParamProposalModel.del_yn == "N",
                )
            ).scalars().one_or_none()
            if proposal is None:
                result = {{
                    "model_param_proposal_id": {proposal_id},
                    "fetch_status": "NOT_FOUND",
                }}
            else:
                result = {{
                    "model_param_proposal_id": int(proposal.model_param_proposal_id),
                    "scenario_id": int(proposal.scenario_id),
                    "scenario_group_id": int(proposal.scenario_group_id),
                    "mi_event_id": (
                        int(proposal.mi_event_id)
                        if proposal.mi_event_id is not None
                        else None
                    ),
                    "request_usr_id": (
                        int(proposal.request_usr_id)
                        if proposal.request_usr_id is not None
                        else None
                    ),
                    "status": str(proposal.status),
                    "callback_status": str(proposal.callback_status),
                    "proposal_completed_dtm": safe(proposal.proposal_completed_dtm),
                    "callback_sent_dtm": safe(proposal.callback_sent_dtm),
                    "confirmed_dtm": safe(proposal.confirmed_dtm),
                    "error_code": proposal.error_code,
                    "error_message": proposal.error_message,
                    "proposal_parameters": safe(proposal.proposal_parameters or []),
                    "confirmation_parameters": safe(proposal.confirmation_parameters),
                    "mod_usr_logn_id": proposal.mod_usr_logn_id,
                    "mod_dtm": safe(proposal.mod_dtm),
                }}
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        finally:
            session.rollback()
            session.close()
        """,
    ).strip()


def _remote_precision_probe_program() -> str:
    return textwrap.dedent(
        f"""
        import json

        from apps.agents.model_parameter_agent.flows.propose_parameters.nodes import (
            _sanitize_llm_adjustments,
        )
        from apps.agents.model_parameter_agent.persistence.model_parameter_service import (
            _parameter_json_payload,
        )
        from apps.agents.model_parameter_agent.schemas.model_parameter_proposal import (
            LLMValueAdjustment,
            LLMValueCell,
        )


        axes = {{"Country": "Japan", "Year": 2026, "Month": 1}}
        candidate = {{
            "candidate_key": "precision-probe",
            "canonical_parameter_name": "PMI",
            "parameter_name": "PMI",
            "model_file": "Demand",
            "model_sheet": "PMIAdjustment",
            "model_table": "table1",
            "basecase_read_mode": "fixed_columns",
            "basecase_column_roles": "A:Country,B:Year,C:Month,D:PMI",
        }}
        slot = {{
            "candidate_key": "precision-probe",
            "slot_axes": [
                {{"axis_name": name, "axis_value": value}}
                for name, value in axes.items()
            ],
        }}
        reference = {{
            "candidate_key": "precision-probe",
            "parameter_name": "PMI",
            "axes": axes,
            "metadata": {{}},
            "actual_basecase_value": None,
            "lut_default_value": 50.0,
            "llm_reference_value": 50.0,
            "effective_source": "lut",
            "basecase_reference_id": None,
            "lut_reference_id": "precision-probe",
            "lut_version": "precision-probe",
            "diagnostics": [],
        }}
        adjustment = LLMValueAdjustment(
            candidate_key="precision-probe",
            rationale_ko="precision probe",
            slot_values=[
                LLMValueCell(
                    slot_key="slot-1",
                    proposed_value={STEP3_PRECISION_PROBE_VALUE!r},
                    rationale_ko="precision probe",
                )
            ],
        )
        sanitized, warnings = _sanitize_llm_adjustments(
            [adjustment],
            [candidate],
            [slot],
            [reference],
        )
        step3_value = sanitized[0]["value_grid"][0]["proposed_value"]
        persisted = _parameter_json_payload(
            {{"values": [{{"proposedValue": {STEP3_PRECISION_PROBE_VALUE!r}}}]}},
        )
        print(
            json.dumps(
                {{
                    "step3_proposed_value": step3_value,
                    "persistence_proposed_value": persisted["values"][0]["proposedValue"],
                    "warning_count": len(warnings),
                }},
                sort_keys=True,
            )
        )
        """,
    ).strip()


class VmProposalReader:
    def __init__(
        self,
        *,
        host: str,
        user: str,
        key_path: Path,
        container: str,
    ) -> None:
        self.host = host
        self.user = user
        self.key_path = key_path
        self.container = container

    def _execute_json_program(self, program: str, *, label: str) -> dict[str, Any]:
        remote_command = f"docker exec {shlex.quote(self.container)} python -c {shlex.quote(program)}"
        completed: subprocess.CompletedProcess[str] | None = None
        for attempt in range(1, 4):
            completed = subprocess.run(
                [
                    "ssh",
                    "-o",
                    "BatchMode=yes",
                    "-o",
                    "ConnectTimeout=20",
                    "-i",
                    str(self.key_path),
                    f"{self.user}@{self.host}",
                    remote_command,
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if completed.returncode == 0:
                break
            if attempt < 3:
                time.sleep(float(attempt))
        if completed is None:
            raise SmokeTestError(f"VM {label} did not run")
        if completed.returncode != 0:
            detail = completed.stderr.strip()[-2000:] or completed.stdout.strip()[-2000:]
            raise SmokeTestError(f"VM {label} failed after 3 attempts: {detail}")
        for line in reversed(completed.stdout.splitlines()):
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                return value
        raise SmokeTestError(f"VM {label} did not return a JSON object")

    def fetch(self, proposal_id: int) -> dict[str, Any]:
        return self._execute_json_program(
            _remote_readback_program(proposal_id),
            label="DB read-back",
        )

    def precision_probe(self) -> dict[str, Any]:
        return self._execute_json_program(
            _remote_precision_probe_program(),
            label="runtime precision probe",
        )


def _poll_proposal(
    reader: VmProposalReader,
    proposal_id: int,
    *,
    interval_seconds: float,
    timeout_seconds: float,
) -> tuple[dict[str, Any], float]:
    started = time.perf_counter()
    latest: dict[str, Any] = {}
    while time.perf_counter() - started <= timeout_seconds:
        latest = reader.fetch(proposal_id)
        if latest.get("status") in TERMINAL_PROPOSAL_STATUSES:
            return latest, time.perf_counter() - started
        time.sleep(interval_seconds)
    raise SmokeTestError(
        f"proposal {proposal_id} did not finish within {timeout_seconds}s; latest={latest}",
    )


def _operation_set(openapi: dict[str, Any]) -> set[tuple[str, str]]:
    operations: set[tuple[str, str]] = set()
    for path, item in (openapi.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        for method in item:
            if method.lower() in {"get", "post", "put", "patch", "delete"}:
                operations.add((method.upper(), str(path)))
    return operations


def _call(
    client: httpx.Client,
    *,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> tuple[httpx.Response, dict[str, Any], float]:
    started = time.perf_counter()
    response = client.request(method, path, json=payload)
    elapsed = time.perf_counter() - started
    return response, _response_json(response), elapsed


def run_smoke_test(args: argparse.Namespace) -> dict[str, Any]:
    started_at = datetime.now().astimezone()
    expected_parameter_names = {
        name.strip()
        for name in str(args.expected_parameters).split(",")
        if name.strip()
    }
    _require(expected_parameter_names, "expected parameter names must not be empty")
    _require(
        expected_parameter_names <= EXPECTED_PROPOSAL_ALLOWLIST,
        "expected parameters must be inside the runtime proposal allow-list: "
        f"{sorted(expected_parameter_names)}",
    )
    reader = VmProposalReader(
        host=args.ssh_host,
        user=args.ssh_user,
        key_path=args.ssh_key,
        container=args.container,
    )
    result: dict[str, Any] = {
        "test_run": {
            "started_at": started_at.isoformat(),
            "base_url": args.base_url,
            "scenario_id": args.scenario_id,
            "expected_parameter_names": sorted(expected_parameter_names),
            "ssh_host": args.ssh_host,
            "container": args.container,
        },
        "preflight": {},
        "cases": [],
        "confirmation_contract": {"invalid_status": "N/A"},
    }

    timeout = httpx.Timeout(args.request_timeout, connect=10.0)
    with httpx.Client(base_url=args.base_url.rstrip("/"), timeout=timeout) as client:
        docs = client.get("/docs")
        openapi_response = client.get("/openapi.json")
        openapi = _response_json(openapi_response)
        operations = _operation_set(openapi)
        _require(docs.status_code == 200, f"/docs returned HTTP {docs.status_code}")
        _require(
            openapi_response.status_code == 200,
            f"/openapi.json returned HTTP {openapi_response.status_code}",
        )
        _require(
            operations == EXPECTED_OPERATIONS,
            f"OpenAPI operation mismatch: expected={sorted(EXPECTED_OPERATIONS)}, actual={sorted(operations)}",
        )
        runtime_precision_probe = reader.precision_probe()
        runtime_precision_checks = {
            "step3_no_quantization": (
                runtime_precision_probe.get("step3_proposed_value") == STEP3_PRECISION_PROBE_VALUE
            ),
            "persistence_no_quantization": (
                runtime_precision_probe.get("persistence_proposed_value") == STEP3_PRECISION_PROBE_VALUE
            ),
            "warning_count_zero": runtime_precision_probe.get("warning_count") == 0,
        }
        _require(
            all(runtime_precision_checks.values()),
            f"runtime precision probe failed: {runtime_precision_probe}",
        )
        result["preflight"] = {
            "docs_http_status": docs.status_code,
            "openapi_http_status": openapi_response.status_code,
            "openapi_version": openapi.get("openapi"),
            "api_info_version": (openapi.get("info") or {}).get("version"),
            "operations": [f"{method} {path}" for method, path in sorted(operations)],
            "runtime_proposal_allowlist": sorted(EXPECTED_PROPOSAL_ALLOWLIST),
            "runtime_precision_probe": {
                "status": "PASS",
                "probe_value": STEP3_PRECISION_PROBE_VALUE,
                "checks": runtime_precision_checks,
            },
        }

        sync_path = f"/model-parameters/scenarios/{args.scenario_id}/proposals/sync"
        sync_response, sync_body, sync_elapsed = _call(
            client,
            method="POST",
            path=sync_path,
            payload={},
        )
        _require(sync_response.status_code == 200, f"sync proposal returned HTTP {sync_response.status_code}")
        _require(sync_body.get("status") == "success", f"sync proposal failed: {sync_body}")
        sync_id = _proposal_id(sync_body)
        sync_data = sync_body.get("data") or {}
        sync_parameters = sync_data.get("proposalParameters")
        _require(sync_data.get("scenarioId") == args.scenario_id, "sync response scenarioId mismatch")
        _require(isinstance(sync_parameters, list) and sync_parameters, "sync proposalParameters is empty")
        sync_parameter_names = _proposal_parameter_names(sync_parameters)
        _require(
            sync_parameter_names == expected_parameter_names,
            "sync proposal parameter mismatch: "
            f"expected={sorted(expected_parameter_names)}, actual={sorted(sync_parameter_names)}",
        )
        sync_row = reader.fetch(sync_id)
        _require(sync_row.get("status") == "PROPOSED", f"sync DB status is not PROPOSED: {sync_row}")
        _require(sync_row.get("scenario_id") == args.scenario_id, "sync DB scenario_id mismatch")
        _require(
            _without_lut_value(sync_parameters) == sync_row.get("proposal_parameters"),
            "sync response and DB proposal_parameters differ after removing lutValue",
        )
        result["cases"].append(
            {
                "case_id": "MP-V024-SYNC-001",
                "operation": "POST /model-parameters/scenarios/{scenario_id}/proposals/sync",
                "status": "PASS",
                "http_status": sync_response.status_code,
                "elapsed_seconds": round(sync_elapsed, 3),
                "model_param_proposal_id": sync_id,
                "scenario_group_id": sync_row.get("scenario_group_id"),
                "parameter_count": len(sync_parameters),
                "parameter_names": sorted(sync_parameter_names),
                "runtime_scope_matches": True,
                "db_status": sync_row.get("status"),
                "callback_status": sync_row.get("callback_status"),
                "persistence_matches": True,
            },
        )

        async_path = f"/model-parameters/scenarios/{args.scenario_id}/proposals"
        async_response, async_body, async_accept_elapsed = _call(
            client,
            method="POST",
            path=async_path,
            payload={},
        )
        _require(async_response.status_code == 200, f"async proposal returned HTTP {async_response.status_code}")
        _require(async_body.get("status") == "success", f"async proposal accept failed: {async_body}")
        async_id = _proposal_id(async_body)
        async_data = async_body.get("data") or {}
        _require(async_data.get("status") == "PROCESSING", f"async accept status mismatch: {async_data}")
        async_row, async_poll_elapsed = _poll_proposal(
            reader,
            async_id,
            interval_seconds=args.poll_interval,
            timeout_seconds=args.poll_timeout,
        )
        _require(async_row.get("status") == "PROPOSED", f"async proposal failed: {async_row}")
        async_parameters = async_row.get("proposal_parameters")
        _require(isinstance(async_parameters, list) and async_parameters, "async DB proposal_parameters is empty")
        async_parameter_names = _proposal_parameter_names(async_parameters)
        _require(
            async_parameter_names == expected_parameter_names,
            "async proposal parameter mismatch: "
            f"expected={sorted(expected_parameter_names)}, actual={sorted(async_parameter_names)}",
        )
        _require(async_row.get("scenario_id") == args.scenario_id, "async DB scenario_id mismatch")
        result["cases"].append(
            {
                "case_id": "MP-V024-ASYNC-001",
                "operation": "POST /model-parameters/scenarios/{scenario_id}/proposals",
                "status": "PASS",
                "http_status": async_response.status_code,
                "accept_elapsed_seconds": round(async_accept_elapsed, 3),
                "poll_elapsed_seconds": round(async_poll_elapsed, 3),
                "model_param_proposal_id": async_id,
                "scenario_group_id": async_row.get("scenario_group_id"),
                "parameter_count": len(async_parameters),
                "parameter_names": sorted(async_parameter_names),
                "runtime_scope_matches": True,
                "db_status": async_row.get("status"),
                "callback_status": async_row.get("callback_status"),
                "error_code": async_row.get("error_code"),
            },
        )

        confirmation_path = f"/model-parameters/proposals/{async_id}/confirmation"
        before_empty = _snapshot(async_row)
        empty_response, empty_body, empty_elapsed = _call(
            client,
            method="POST",
            path=confirmation_path,
            payload={"data": {"confirmationParameters": []}},
        )
        after_empty = reader.fetch(async_id)
        empty_data = empty_body.get("data") or {}
        empty_checks = {
            "http_400": empty_response.status_code == 400,
            "status_error": empty_body.get("status") == "error",
            "invalid_request_code": empty_data.get("error_code") == -202,
            "invalid_request_name": empty_data.get("error_name") == "INVALID_REQUEST",
            "db_rollback_verified": _snapshot(after_empty) == before_empty,
        }
        _require(all(empty_checks.values()), f"empty confirmation contract failed: {empty_checks}")

        confirmation_parameters = _confirmation_parameters_with_precision_probe(async_parameters)
        valid_payload = {"data": {"confirmationParameters": confirmation_parameters}}
        valid_response, valid_body, valid_elapsed = _call(
            client,
            method="POST",
            path=confirmation_path,
            payload=valid_payload,
        )
        after_valid = reader.fetch(async_id)
        valid_data = valid_body.get("data") or {}
        valid_checks = {
            "http_200": valid_response.status_code == 200,
            "response_success": valid_body.get("status") == "success",
            "response_id_matches": valid_data.get("modelParamProposalId") == async_id,
            "response_status_confirmed": valid_data.get("status") == "CONFIRMED",
            "db_status_confirmed": after_valid.get("status") == "CONFIRMED",
            "confirmation_payload_matches": after_valid.get("confirmation_parameters") == confirmation_parameters,
            "proposal_payload_unchanged": after_valid.get("proposal_parameters") == async_parameters,
            "proposed_precision_preserved": (
                _first_proposed_value(after_valid.get("confirmation_parameters")) == PRECISION_PROBE_VALUE
            ),
            "confirmed_dtm_populated": after_valid.get("confirmed_dtm") is not None,
        }
        _require(all(valid_checks.values()), f"valid confirmation contract failed: {valid_checks}")

        first_confirmed_dtm = after_valid.get("confirmed_dtm")
        time.sleep(0.05)
        reconfirm_response, reconfirm_body, reconfirm_elapsed = _call(
            client,
            method="POST",
            path=confirmation_path,
            payload=valid_payload,
        )
        final_row = reader.fetch(async_id)
        reconfirm_data = reconfirm_body.get("data") or {}
        refreshed_dtm = final_row.get("confirmed_dtm")
        reconfirm_checks = {
            "http_200": reconfirm_response.status_code == 200,
            "response_success": reconfirm_body.get("status") == "success",
            "response_id_matches": reconfirm_data.get("modelParamProposalId") == async_id,
            "response_status_confirmed": reconfirm_data.get("status") == "CONFIRMED",
            "db_status_confirmed": final_row.get("status") == "CONFIRMED",
            "confirmation_payload_matches": final_row.get("confirmation_parameters") == confirmation_parameters,
            "proposal_payload_unchanged": final_row.get("proposal_parameters") == async_parameters,
            "proposed_precision_preserved": (
                _first_proposed_value(final_row.get("confirmation_parameters")) == PRECISION_PROBE_VALUE
            ),
            "confirmed_dtm_refreshed": (
                isinstance(first_confirmed_dtm, str)
                and isinstance(refreshed_dtm, str)
                and refreshed_dtm > first_confirmed_dtm
            ),
        }
        _require(all(reconfirm_checks.values()), f"reconfirmation contract failed: {reconfirm_checks}")

        result["cases"].append(
            {
                "case_id": "MP-V024-CONFIRM-001",
                "operation": "POST /model-parameters/proposals/{modelParamProposalId}/confirmation",
                "status": "PASS",
                "model_param_proposal_id": async_id,
                "precision_probe_value": PRECISION_PROBE_VALUE,
                "subcases": {
                    "empty_payload_rollback": {
                        "status": "PASS",
                        "http_status": empty_response.status_code,
                        "elapsed_seconds": round(empty_elapsed, 3),
                        "checks": empty_checks,
                    },
                    "valid_confirmation": {
                        "status": "PASS",
                        "http_status": valid_response.status_code,
                        "elapsed_seconds": round(valid_elapsed, 3),
                        "checks": valid_checks,
                    },
                    "reconfirmation": {
                        "status": "PASS",
                        "http_status": reconfirm_response.status_code,
                        "elapsed_seconds": round(reconfirm_elapsed, 3),
                        "checks": reconfirm_checks,
                    },
                },
            },
        )
        result["confirmation_contract"] = {
            "status": "PASS",
            "invalid_payload": "PASS",
            "valid_confirmation": "PASS",
            "reconfirmation": "PASS",
            "invalid_status": "N/A",
            "invalid_status_reason": "기존 PROCESSING/FAILED 행을 변경하지 않고 현재 실행 행만 검증함",
        }
        result["final_db_row"] = final_row
        result["sync_db_row"] = sync_row

    finished_at = datetime.now().astimezone()
    result["test_run"].update(
        {
            "finished_at": finished_at.isoformat(),
            "elapsed_seconds": round((finished_at - started_at).total_seconds(), 3),
        },
    )
    result["status"] = "PASS"
    result["error_count"] = 0
    return _json_safe(result)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Smoke-test every public Model Parameter API on a deployed VM.",
    )
    parser.add_argument("--base-url", default="http://40.82.137.178:8002")
    parser.add_argument("--scenario-id", type=int, default=1077)
    parser.add_argument(
        "--expected-parameters",
        default="LiqUtilAdjustment",
        help="Comma-separated exact parameter names expected for the selected scenario.",
    )
    parser.add_argument("--ssh-host", default="40.82.137.178")
    parser.add_argument("--ssh-user", default="azureuser")
    parser.add_argument("--ssh-key", type=Path, required=True)
    parser.add_argument("--container", default="mi-agent-model-parameter")
    parser.add_argument("--request-timeout", type=float, default=300.0)
    parser.add_argument("--poll-timeout", type=float, default=600.0)
    parser.add_argument("--poll-interval", type=float, default=5.0)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    result: dict[str, Any]
    exit_code = 0
    try:
        _require(args.ssh_key.is_file(), f"SSH key not found: {args.ssh_key}")
        result = run_smoke_test(args)
    except Exception as exc:
        result = {
            "status": "FAIL",
            "error_count": 1,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "finished_at": datetime.now().astimezone().isoformat(),
        }
        exit_code = 1
    print(json.dumps(_json_safe(result), ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
