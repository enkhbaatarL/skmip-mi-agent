from __future__ import annotations

# ruff: noqa: ANN401, EM101, N818, T201, TRY301
import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sqlite3
import sys
import time
from typing import Any
import uuid

import httpx


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from test_callback_api import (  # noqa: E402
    build_confirmation_scenario_group,
    get_group,
    normalize_table_for_confirmation,
    normalize_table_for_validate_or_signposts,
    print_step,
    write_json,
)


OUTPUT_DIR = Path("local/output/sync_pipeline_api_test")
EVENT_TYPE_L2_IDS = list(range(1, 22))


@dataclass(frozen=True)
class TargetEvent:
    mi_event_id: int
    event_type_l2_id: int | None = None
    initial_scenario_group_id: int | None = None
    initial_action_state: str | None = None
    initial_action_reason: str | None = None


class PipelineStop(Exception):
    def __init__(self, step: str, reason: str) -> None:
        super().__init__(reason)
        self.step = step
        self.reason = reason


class MetricsStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def close(self) -> None:
        self.conn.close()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                run_id TEXT PRIMARY KEY,
                batch_id TEXT NOT NULL,
                event_type_l2_id INTEGER,
                mi_event_id INTEGER NOT NULL,
                initial_scenario_group_id INTEGER,
                initial_action_state TEXT,
                initial_action_reason TEXT,
                pre_deleted INTEGER NOT NULL DEFAULT 0,
                retried_create INTEGER NOT NULL DEFAULT 0,
                scenario_group_id INTEGER,
                status TEXT NOT NULL,
                error_step TEXT,
                error_reason TEXT,
                started_at REAL NOT NULL,
                ended_at REAL,
                elapsed_ms INTEGER
            );

            CREATE TABLE IF NOT EXISTS api_call_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                step TEXT NOT NULL,
                method TEXT NOT NULL,
                url TEXT NOT NULL,
                status_code INTEGER,
                ok INTEGER NOT NULL,
                elapsed_ms INTEGER NOT NULL,
                reason TEXT,
                created_at REAL NOT NULL
            );
            """,
        )
        self._ensure_pipeline_run_columns()
        self.conn.commit()

    def _ensure_pipeline_run_columns(self) -> None:
        existing_columns = {
            str(row["name"])
            for row in self.conn.execute("PRAGMA table_info(pipeline_runs)").fetchall()
        }
        migrations = {
            "initial_scenario_group_id": "ALTER TABLE pipeline_runs ADD COLUMN initial_scenario_group_id INTEGER",
            "initial_action_state": "ALTER TABLE pipeline_runs ADD COLUMN initial_action_state TEXT",
            "initial_action_reason": "ALTER TABLE pipeline_runs ADD COLUMN initial_action_reason TEXT",
            "pre_deleted": "ALTER TABLE pipeline_runs ADD COLUMN pre_deleted INTEGER NOT NULL DEFAULT 0",
            "retried_create": "ALTER TABLE pipeline_runs ADD COLUMN retried_create INTEGER NOT NULL DEFAULT 0",
        }
        for column, statement in migrations.items():
            if column not in existing_columns:
                self.conn.execute(statement)

    def start_run(self, run_id: str, batch_id: str, target: TargetEvent) -> None:
        self.conn.execute(
            """
            INSERT INTO pipeline_runs (
                run_id,
                batch_id,
                event_type_l2_id,
                mi_event_id,
                initial_scenario_group_id,
                initial_action_state,
                initial_action_reason,
                status,
                started_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'running', ?)
            """,
            (
                run_id,
                batch_id,
                target.event_type_l2_id,
                target.mi_event_id,
                target.initial_scenario_group_id,
                target.initial_action_state,
                target.initial_action_reason,
                time.time(),
            ),
        )
        self.conn.commit()

    def mark_pre_deleted(self, run_id: str) -> None:
        self.conn.execute("UPDATE pipeline_runs SET pre_deleted = 1 WHERE run_id = ?", (run_id,))
        self.conn.commit()

    def mark_retried_create(self, run_id: str) -> None:
        self.conn.execute("UPDATE pipeline_runs SET retried_create = 1 WHERE run_id = ?", (run_id,))
        self.conn.commit()

    def finish_run(
        self,
        run_id: str,
        *,
        status: str,
        scenario_group_id: int | None,
        error_step: str | None = None,
        error_reason: str | None = None,
    ) -> None:
        ended_at = time.time()
        row = self.conn.execute("SELECT started_at FROM pipeline_runs WHERE run_id = ?", (run_id,)).fetchone()
        started_at = float(row["started_at"]) if row is not None else ended_at
        self.conn.execute(
            """
            UPDATE pipeline_runs
               SET status = ?,
                   scenario_group_id = ?,
                   error_step = ?,
                   error_reason = ?,
                   ended_at = ?,
                   elapsed_ms = ?
             WHERE run_id = ?
            """,
            (
                status,
                scenario_group_id,
                error_step,
                error_reason,
                ended_at,
                int((ended_at - started_at) * 1000),
                run_id,
            ),
        )
        self.conn.commit()

    def record_api_call(
        self,
        run_id: str,
        *,
        step: str,
        method: str,
        url: str,
        status_code: int | None,
        ok: bool,
        elapsed_ms: int,
        reason: str | None = None,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO api_call_metrics (
                run_id, step, method, url, status_code, ok, elapsed_ms, reason, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (run_id, step, method, url, status_code, int(ok), elapsed_ms, reason, time.time()),
        )
        self.conn.commit()

    def print_summary(self, batch_id: str) -> None:
        total = self.conn.execute(
            "SELECT COUNT(*) AS count FROM pipeline_runs WHERE batch_id = ?",
            (batch_id,),
        ).fetchone()["count"]
        success = self.conn.execute(
            "SELECT COUNT(*) AS count FROM pipeline_runs WHERE batch_id = ? AND status = 'success'",
            (batch_id,),
        ).fetchone()["count"]
        print(f"\n{'=' * 80}")
        print(f"Batch: {batch_id}")
        print(f"Pipeline success: {success}/{total}")

        retry = self.conn.execute(
            """
            SELECT SUM(retried_create) AS retried_create
              FROM pipeline_runs
             WHERE batch_id = ?
            """,
            (batch_id,),
        ).fetchone()
        soft_delete = self.conn.execute(
            """
            SELECT COUNT(*) AS count
              FROM api_call_metrics m
              JOIN pipeline_runs r ON r.run_id = m.run_id
             WHERE r.batch_id = ?
               AND m.step = 'soft_delete_existing'
               AND m.ok = 1
            """,
            (batch_id,),
        ).fetchone()
        print(
            "Cleanup/retry: "
            f"soft_deleted={soft_delete['count'] or 0} retried_create={retry['retried_create'] or 0}",
        )

        print("\n[API average elapsed]")
        for row in self.conn.execute(
            """
            SELECT m.step,
                   COUNT(*) AS count,
                   ROUND(AVG(m.elapsed_ms), 1) AS avg_ms,
                   MIN(m.elapsed_ms) AS min_ms,
                   MAX(m.elapsed_ms) AS max_ms
              FROM api_call_metrics m
              JOIN pipeline_runs r ON r.run_id = m.run_id
             WHERE r.batch_id = ?
             GROUP BY m.step
             ORDER BY MIN(m.id)
            """,
            (batch_id,),
        ):
            print(
                f"  {row['step']}: count={row['count']} avg={row['avg_ms']}ms "
                f"min={row['min_ms']}ms max={row['max_ms']}ms",
            )

        failures = self.conn.execute(
            """
            SELECT event_type_l2_id,
                   mi_event_id,
                   initial_action_state,
                   scenario_group_id,
                   error_step,
                   error_reason,
                   elapsed_ms
              FROM pipeline_runs
             WHERE batch_id = ? AND status != 'success'
             ORDER BY started_at
            """,
            (batch_id,),
        ).fetchall()
        if failures:
            print("\n[Failures]")
            for row in failures:
                print(
                    "  "
                    f"eventTypeL2Id={row['event_type_l2_id']} miEventId={row['mi_event_id']} "
                    f"actionState={row['initial_action_state']} groupId={row['scenario_group_id']} "
                    f"step={row['error_step']} "
                    f"elapsed={row['elapsed_ms']}ms reason={row['error_reason']}",
                )
        print(f"\nSQLite metrics: {self.db_path}")
        print(f"{'=' * 80}\n")


def request_json(
    client: httpx.Client,
    metrics: MetricsStore,
    run_id: str,
    *,
    step: str,
    method: str,
    url: str,
    json_body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    started_at = time.perf_counter()
    status_code: int | None = None
    try:
        resp = client.request(method, url, json=json_body, headers=headers)
        status_code = resp.status_code
        resp.raise_for_status()
        payload = resp.json()
    except httpx.HTTPStatusError as exc:
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        reason = response_reason(exc.response)
        metrics.record_api_call(
            run_id,
            step=step,
            method=method,
            url=url,
            status_code=exc.response.status_code,
            ok=False,
            elapsed_ms=elapsed_ms,
            reason=reason,
        )
        raise PipelineStop(step, f"HTTP {exc.response.status_code}: {reason}") from exc
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        metrics.record_api_call(
            run_id,
            step=step,
            method=method,
            url=url,
            status_code=status_code,
            ok=False,
            elapsed_ms=elapsed_ms,
            reason=str(exc),
        )
        raise PipelineStop(step, str(exc)) from exc

    elapsed_ms = int((time.perf_counter() - started_at) * 1000)
    metrics.record_api_call(
        run_id,
        step=step,
        method=method,
        url=url,
        status_code=status_code,
        ok=True,
        elapsed_ms=elapsed_ms,
        reason=callback_reason(payload),
    )
    print(f"  - {step}: {elapsed_ms}ms")
    return payload


def response_reason(resp: httpx.Response) -> str:
    try:
        payload = resp.json()
    except Exception:
        return resp.text
    return callback_reason(payload) or payload.get("message") or json.dumps(payload, ensure_ascii=False)


def callback_reason(payload: dict[str, Any]) -> str | None:
    reason = payload.get("reason")
    if reason:
        return str(reason)
    data = payload.get("data")
    if isinstance(data, dict):
        return str(data.get("reason") or data.get("error_name") or data.get("message") or "") or None
    return None


def field(payload: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in payload:
            return payload[name]
    return None


def scenario_group_from(payload: dict[str, Any]) -> dict[str, Any] | None:
    group = field(payload, "scenarioGroup", "scenario_group")
    return group if isinstance(group, dict) else None


def table_from(payload: dict[str, Any]) -> dict[str, Any] | None:
    table = payload.get("table")
    return table if isinstance(table, dict) else None


def related_group_id_from(row: dict[str, Any]) -> int | None:
    related = row.get("relatedScenarioGroup") or row.get("related_scenario_group")
    if not isinstance(related, dict):
        return None
    group_id = related.get("scenarioGroupId") or related.get("scenario_group_id")
    return int(group_id) if group_id is not None else None


def event_type_l2_id_from(row: dict[str, Any]) -> int | None:
    event_type_l2 = row.get("eventTypeL2") or row.get("event_type_l2") or {}
    if not isinstance(event_type_l2, dict):
        return None
    event_type_l2_id = event_type_l2.get("id")
    return int(event_type_l2_id) if event_type_l2_id is not None else None


def action_state_from(row: dict[str, Any]) -> dict[str, Any]:
    action = row.get("scenarioActionState") or row.get("scenario_action_state") or {}
    return action if isinstance(action, dict) else {}


def target_event_from_row(row: dict[str, Any], fallback_event_type_l2_id: int | None = None) -> TargetEvent | None:
    mi_event_id = row.get("miEventId") or row.get("mi_event_id")
    if mi_event_id is None:
        return None
    action = action_state_from(row)
    return TargetEvent(
        mi_event_id=int(mi_event_id),
        event_type_l2_id=event_type_l2_id_from(row) or fallback_event_type_l2_id,
        initial_scenario_group_id=related_group_id_from(row),
        initial_action_state=str(action.get("type")) if action.get("type") is not None else None,
        initial_action_reason=str(action.get("reason")) if action.get("reason") is not None else None,
    )


def require_success_callback(payload: dict[str, Any], step: str) -> None:
    if payload.get("result") != "success":
        raise PipelineStop(step, callback_reason(payload) or f"{step} result != success")


def handle_validation_result(payload: dict[str, Any]) -> None:
    if payload.get("result") != "success":
        print(f"  ⚠ validate_scenarios failure: {callback_reason(payload)}")
        return

    group = scenario_group_from(payload) or {}
    stage = field(group, "stage")
    is_valid = field(payload, "isValid", "is_valid")
    if stage == "scenario_validated":
        print("  ✓ validate_scenarios 통과")
        return
    if stage == "scenario_created" or is_valid is False:
        print(f"  ⚠ validate_scenarios 미통과 | stage={stage} | isValid={is_valid} | reason={callback_reason(payload)}")
        return
    raise PipelineStop("validate_scenarios", f"unexpected validation stage={stage}, isValid={is_valid}")


def ask_continue(args: argparse.Namespace, message: str) -> bool:
    if args.yes:
        return True
    answer = input(f"{message} [Enter=계속 / p=중단]: ").strip().lower()
    return answer != "p"


def find_existing_group_id(client: httpx.Client, base_url: str, mi_event_id: int) -> int | None:
    resp = client.get(
        f"{base_url}/scenario-groups",
        params={"includeDeleted": False, "miEventId": mi_event_id, "sort": "latest"},
    )
    resp.raise_for_status()
    payload = resp.json()
    rows = payload.get("rows") or []
    if not rows:
        return None
    group_id = rows[0].get("scenarioGroupId") or rows[0].get("scenario_group_id")
    return int(group_id) if group_id is not None else None


def soft_delete_group(
    client: httpx.Client,
    metrics: MetricsStore,
    run_id: str,
    *,
    base_url: str,
    group_id: int,
    user_id: int,
    admin_token: str | None,
) -> None:
    headers = {"Authorization": f"Bearer {admin_token}"} if admin_token else None
    payload = request_json(
        client,
        metrics,
        run_id,
        step="soft_delete_existing",
        method="DELETE",
        url=f"{base_url}/scenario-groups/{group_id}",
        json_body={"userId": user_id},
        headers=headers,
    )
    print(f"  ⚠ existing scenario group soft-deleted | groupId={group_id} | response={payload}")


def soft_delete_existing_group(
    client: httpx.Client,
    metrics: MetricsStore,
    run_id: str,
    args: argparse.Namespace,
    *,
    mi_event_id: int,
    group_id: int | None,
) -> None:
    existing_group_id = group_id or find_existing_group_id(client, args.base_url, mi_event_id)
    if existing_group_id is None:
        return
    soft_delete_group(
        client,
        metrics,
        run_id,
        base_url=args.base_url,
        group_id=existing_group_id,
        user_id=args.user_id,
        admin_token=args.admin_token,
    )
    metrics.mark_pre_deleted(run_id)


def create_scenarios_with_retry(
    client: httpx.Client,
    metrics: MetricsStore,
    run_id: str,
    args: argparse.Namespace,
    mi_event_id: int,
) -> dict[str, Any]:
    try:
        return request_json(
            client,
            metrics,
            run_id,
            step="create_scenarios",
            method="POST",
            url=f"{args.base_url}/scenario-groups/sync",
            json_body={"miEventId": mi_event_id, "userId": args.user_id},
        )
    except PipelineStop as exc:
        if "SCENARIO_GROUP_ALREADY_CREATED" not in exc.reason and "이미" not in exc.reason:
            raise
        group_id = find_existing_group_id(client, args.base_url, mi_event_id)
        if group_id is None:
            raise
        print(f"  ⚠ create_scenarios already exists | reason={exc.reason}")
        metrics.mark_retried_create(run_id)
        soft_delete_group(
            client,
            metrics,
            run_id,
            base_url=args.base_url,
            group_id=group_id,
            user_id=args.user_id,
            admin_token=args.admin_token,
        )
        metrics.mark_pre_deleted(run_id)
        return request_json(
            client,
            metrics,
            run_id,
            step="create_scenarios_retry",
            method="POST",
            url=f"{args.base_url}/scenario-groups/sync",
            json_body={"miEventId": mi_event_id, "userId": args.user_id},
        )


def run_pipeline(
    client: httpx.Client,
    metrics: MetricsStore,
    args: argparse.Namespace,
    *,
    batch_id: str,
    target: TargetEvent,
) -> bool:
    run_id = str(uuid.uuid4())
    metrics.start_run(run_id, batch_id, target)
    scenario_group_id: int | None = None

    try:
        print_step(
            f"miEventId={target.mi_event_id} eventTypeL2Id={target.event_type_l2_id} "
            f"actionState={target.initial_action_state}",
        )

        if args.delete_existing or target.initial_scenario_group_id is not None:
            soft_delete_existing_group(
                client,
                metrics,
                run_id,
                args,
                mi_event_id=target.mi_event_id,
                group_id=target.initial_scenario_group_id,
            )

        create_resp = create_scenarios_with_retry(client, metrics, run_id, args, target.mi_event_id)
        write_json(OUTPUT_DIR / batch_id / f"{target.mi_event_id}_step1_create_response.json", create_resp)
        require_success_callback(create_resp, "create_scenarios")
        scenario_group = scenario_group_from(create_resp)
        table = table_from(create_resp)
        if not scenario_group or not table:
            raise PipelineStop("create_scenarios", "scenarioGroup/table 누락")
        scenario_group_id = int(field(scenario_group, "scenarioGroupId", "scenario_group_id"))

        if not ask_continue(args, "validation으로 진행할까요?"):
            raise PipelineStop("manual", "사용자 중단")

        validation_table = normalize_table_for_validate_or_signposts(table)
        validate_resp = request_json(
            client,
            metrics,
            run_id,
            step="validate_scenarios",
            method="POST",
            url=f"{args.base_url}/scenario-groups/{scenario_group_id}/validation/sync",
            json_body={"userId": args.user_id, "table": validation_table},
        )
        write_json(OUTPUT_DIR / batch_id / f"{target.mi_event_id}_step2_validate_response.json", validate_resp)
        handle_validation_result(validate_resp)
        table = table_from(validate_resp) or table

        if not ask_continue(args, "signpost 생성으로 진행할까요?"):
            raise PipelineStop("manual", "사용자 중단")

        signpost_table = normalize_table_for_validate_or_signposts(table)
        signpost_resp = request_json(
            client,
            metrics,
            run_id,
            step="create_signposts",
            method="POST",
            url=f"{args.base_url}/scenario-groups/{scenario_group_id}/signposts/sync",
            json_body={"userId": args.user_id, "table": signpost_table},
        )
        write_json(OUTPUT_DIR / batch_id / f"{target.mi_event_id}_step3_signposts_response.json", signpost_resp)
        require_success_callback(signpost_resp, "create_signposts")
        scenario_group = scenario_group_from(signpost_resp) or scenario_group
        table = table_from(signpost_resp) or table

        if not ask_continue(args, "confirmation으로 진행할까요?"):
            raise PipelineStop("manual", "사용자 중단")

        detail = get_group(args.base_url, scenario_group_id, args.timeout)
        scenario_group = detail.get("scenarioGroup") or scenario_group
        table = detail.get("table") or table
        confirmation_table = normalize_table_for_confirmation(table)
        confirmation_resp = request_json(
            client,
            metrics,
            run_id,
            step="confirm_generation",
            method="POST",
            url=f"{args.base_url}/scenario-groups/{scenario_group_id}/confirmation",
            json_body={
                "userId": args.user_id,
                "scenarioGroup": build_confirmation_scenario_group(scenario_group),
                "table": confirmation_table,
            },
        )
        write_json(OUTPUT_DIR / batch_id / f"{target.mi_event_id}_step4_confirmation_response.json", confirmation_resp)
        data = confirmation_resp.get("data") or {}
        if confirmation_resp.get("status") != "success" or data.get("stage") != "completed":
            raise PipelineStop("confirm_generation", json.dumps(confirmation_resp, ensure_ascii=False))
        print("  ✓ confirmation 완료")

    except PipelineStop as exc:
        print(f"  [ERROR] {exc.step}: {exc.reason}")
        metrics.finish_run(
            run_id,
            status="failure",
            scenario_group_id=scenario_group_id,
            error_step=exc.step,
            error_reason=exc.reason,
        )
        return False
    except Exception as exc:
        print(f"  [ERROR] unexpected: {exc}")
        metrics.finish_run(
            run_id,
            status="failure",
            scenario_group_id=scenario_group_id,
            error_step="unexpected",
            error_reason=str(exc),
        )
        return False

    metrics.finish_run(run_id, status="success", scenario_group_id=scenario_group_id)
    return True


def discover_event_ids(client: httpx.Client, args: argparse.Namespace) -> list[TargetEvent]:
    targets: list[TargetEvent] = []
    for event_type_l2_id in EVENT_TYPE_L2_IDS:
        selected = 0
        page = 1
        while True:
            resp = client.get(
                f"{args.base_url}/events",
                params={
                    "eventTypeL2Id": event_type_l2_id,
                    "page": page,
                    "pageSize": args.event_page_size,
                    "sort": args.event_sort,
                },
            )
            resp.raise_for_status()
            payload = resp.json()
            rows = payload.get("rows") or []
            for row in rows:
                target = target_event_from_row(row, fallback_event_type_l2_id=event_type_l2_id)
                if target is None:
                    continue
                if target.initial_scenario_group_id is not None and not args.include_events_with_groups:
                    continue
                if target.initial_action_state == "disabled" and not args.include_disabled_events:
                    continue
                targets.append(target)
                selected += 1
                if args.events_per_type > 0 and selected >= args.events_per_type:
                    break
            pagination = payload.get("pagination") or {}
            if args.events_per_type > 0 and selected >= args.events_per_type:
                break
            if not pagination.get("hasNext") and not pagination.get("has_next"):
                break
            page += 1

        print(f"eventTypeL2Id={event_type_l2_id}: selected={selected}")
    return targets


def discover_recent_event_ids(client: httpx.Client, args: argparse.Namespace) -> list[TargetEvent]:
    targets: list[TargetEvent] = []
    page = 1
    remaining = int(args.recent_events)
    while remaining > 0:
        page_size = min(args.event_page_size, remaining, 100)
        resp = client.get(
            f"{args.base_url}/events",
            params={
                "page": page,
                "pageSize": page_size,
                "sort": args.event_sort,
            },
        )
        resp.raise_for_status()
        payload = resp.json()
        rows = payload.get("rows") or []
        for row in rows:
            target = target_event_from_row(row)
            if target is None:
                continue
            targets.append(target)
            remaining -= 1
            if remaining <= 0:
                break
        pagination = payload.get("pagination") or {}
        if remaining <= 0:
            break
        if not rows or (not pagination.get("hasNext") and not pagination.get("has_next")):
            break
        page += 1

    print(f"recent events: requested={args.recent_events} selected={len(targets)}")
    return targets


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync API manual/integration runner for scenario generation pipeline",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--base-url", default="http://localhost:8000", help="Agent API base URL")
    parser.add_argument("--mi-event-id", type=int, help="단건 실행할 MI 이벤트 ID")
    parser.add_argument("--recent-events", type=int, help="GET /events sort=latest 기준 최근 N개 이벤트를 실행")
    parser.add_argument("--user-id", type=int, required=True, help="요청 사용자 ID")
    parser.add_argument("--timeout", type=int, default=900, help="httpx timeout seconds")
    parser.add_argument("--yes", action="store_true", help="사용자 확인 없이 다음 API로 자동 진행")
    parser.add_argument(
        "--delete-existing",
        action="store_true",
        help="시작 전 기존 scenario group이 있으면 soft delete",
    )
    parser.add_argument("--admin-token", help="soft delete API Authorization Bearer token")
    parser.add_argument("--all-event-types", action="store_true", help="eventTypeL2Id=1..21 이벤트를 조회해 반복 실행")
    parser.add_argument("--events-per-type", type=int, default=1, help="eventTypeL2Id별 선택 개수. 0이면 가능한 전체")
    parser.add_argument("--event-page-size", type=int, default=100, help="GET /events pageSize")
    parser.add_argument("--event-sort", default="latest", choices=["latest", "oldest"], help="GET /events sort")
    parser.add_argument(
        "--include-events-with-groups",
        action="store_true",
        help="이미 scenario group이 있는 이벤트도 선택. 보통 --delete-existing과 같이 사용",
    )
    parser.add_argument(
        "--include-disabled-events",
        action="store_true",
        help="scenarioActionState.type=disabled 이벤트도 선택",
    )
    parser.add_argument(
        "--db-path",
        default=str(OUTPUT_DIR / "sync_pipeline_metrics.sqlite3"),
        help="SQLite metrics path",
    )
    return parser.parse_args()


def selected_modes(args: argparse.Namespace) -> list[str]:
    modes: list[str] = []
    if args.mi_event_id is not None:
        modes.append("--mi-event-id")
    if args.all_event_types:
        modes.append("--all-event-types")
    if args.recent_events is not None:
        modes.append("--recent-events")
    return modes


def main() -> int:
    args = parse_args()
    modes = selected_modes(args)
    if not modes:
        print("--mi-event-id, --all-event-types, --recent-events 중 하나가 필요합니다.")
        return 2
    if len(modes) > 1:
        print(f"대상 선택 옵션은 하나만 사용할 수 있습니다: {', '.join(modes)}")
        return 2
    if args.recent_events is not None and args.recent_events < 1:
        print("--recent-events는 1 이상의 정수여야 합니다.")
        return 2

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    batch_id = time.strftime("%Y%m%d_%H%M%S")
    metrics = MetricsStore(Path(args.db_path))
    client = httpx.Client(timeout=args.timeout)

    try:
        if args.all_event_types:
            targets = discover_event_ids(client, args)
        elif args.recent_events:
            targets = discover_recent_event_ids(client, args)
        else:
            targets = [TargetEvent(mi_event_id=args.mi_event_id)]

        if not targets:
            print("실행할 miEventId가 없습니다.")
            return 1
        write_json(OUTPUT_DIR / batch_id / "selected_events.json", [asdict(target) for target in targets])

        for target in targets:
            run_pipeline(
                client,
                metrics,
                args,
                batch_id=batch_id,
                target=target,
            )

        metrics.print_summary(batch_id)
    finally:
        client.close()
        metrics.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
