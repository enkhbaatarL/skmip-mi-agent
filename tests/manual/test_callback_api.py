#!/usr/bin/env python
"""Callback API 통합 테스트 스크립트.

실행 순서:
  1. POST /scenario-groups           → 200 즉시 반환 (create_scenarios)
  2. 사용자 확인: callback 수신 여부 입력 대기
  3. GET  /scenario-groups/{id}      → stage=scenario_created 검증

  4. POST /scenario-groups/{id}/validation  → 200 즉시 반환
  5. 사용자 확인: callback 수신 여부 입력 대기
  6. GET  /scenario-groups/{id}             → stage=scenario_validated 검증
     (isValid=false이면 경고 후 계속 진행 여부 확인)

  7. POST /scenario-groups/{id}/signposts   → 200 즉시 반환
  8. 사용자 확인: callback 수신 여부 입력 대기
  9. GET  /scenario-groups/{id}             → stage=signpost_created, signpost_count>0 검증
 10. POST /scenario-groups/{id}/confirmation → 200 반환, stage=completed 검증

사용법:
  python tests/manual/test_callback_api.py \\
      --mi-event-id 9 \\
      --user-id 1

옵션:
  --base-url      서버 주소 (기본: http://localhost:8000)
  --mi-event-id   MI 이벤트 ID (필수)
  --user-id       사용자 ID (필수)
  --skip-step     건너뛸 스텝 번호 (예: --skip-step 1 2), 이미 진행된 스텝 재사용 시
  --group-id      --skip-step 1 사용 시 직접 지정할 scenarioGroupId
  --timeout       httpx 타임아웃 초 (기본: 30)

실행 중 인터랙티브 입력:
  callback 수신 완료? [y/n/p]
    y → callback 수신 확인, GET 검증 수행
    n → callback 미수신, GET 검증 건너뜀
    p → 이 단계 전체 패스, 다음 단계로 이동

  단계 실행 여부? [Enter/p]
    Enter → 해당 단계 POST 실행
    p     → 해당 단계 POST 건너뜀
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import httpx

OUTPUT_DIR = Path("local/output/callback_api_test")


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def get_group(base_url: str, group_id: int, timeout: int) -> dict[str, Any]:
    url = f"{base_url}/scenario-groups/{group_id}"
    resp = httpx.get(url, timeout=timeout)
    resp.raise_for_status()
    payload = resp.json()

    # 일부 게이트웨이 환경에서 공통 응답 래퍼(status/data)를 씌우는 케이스를 흡수한다.
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        data = payload["data"]
        if "scenarioGroup" in data and "table" in data:
            return data

    return payload


def post_create_scenarios(base_url: str, mi_event_id: int, user_id: int, timeout: int) -> dict[str, Any]:
    resp = httpx.post(
        f"{base_url}/scenario-groups",
        json={"miEventId": mi_event_id, "userId": user_id},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()


def normalize_table_for_validate_or_signposts(table: dict[str, Any]) -> dict[str, Any]:
    headers: list[dict[str, Any]] = []
    for idx, header in enumerate(table.get("headers") or [], start=1):
        headers.append(
            {
                "key": header.get("key", ""),
                "label": header.get("label", ""),
                "displayOrder": int(header.get("displayOrder") or idx),
            }
        )

    rows: list[dict[str, Any]] = []
    for idx, row in enumerate(table.get("rows") or [], start=1):
        cells = row.get("cells")
        if not isinstance(cells, dict):
            cells = {}
        rows.append(
            {
                "scenarioId": row.get("scenarioId"),
                "displayOrder": int(row.get("displayOrder") or idx),
                "title": row.get("title") or "",
                "cells": cells,
            }
        )

    return {"headers": headers, "rows": rows}


def normalize_table_for_confirmation(table: dict[str, Any]) -> dict[str, Any]:
    headers: list[dict[str, Any]] = []
    for idx, header in enumerate(table.get("headers") or [], start=1):
        headers.append(
            {
                "key": header.get("key", ""),
                "label": header.get("label", ""),
                "displayOrder": int(header.get("displayOrder") or idx),
            }
        )

    rows: list[dict[str, Any]] = []
    for idx, row in enumerate(table.get("rows") or [], start=1):
        cells = row.get("cells")
        if not isinstance(cells, dict):
            cells = {}

        normalized_row: dict[str, Any] = {
            "scenarioId": row.get("scenarioId"),
            "displayOrder": int(row.get("displayOrder") or idx),
            "title": row.get("title") or "",
            "narrative": row.get("narrative"),
            "cells": cells,
        }
        for key in ("metrics", "impact", "baselineYn"):
            if key in row:
                normalized_row[key] = row.get(key)

        signposts: list[dict[str, Any]] = []
        for signpost_idx, signpost in enumerate(row.get("signposts") or [], start=1):
            signposts.append(
                {
                    "signpostId": signpost.get("signpostId"),
                    "label": signpost.get("label") or "",
                    "probabilityDirectionCode": signpost.get("probabilityDirectionCode"),
                    "probabilityImpactScore": signpost.get("probabilityImpactScore"),
                    "signpostReason": signpost.get("signpostReason"),
                    "displayOrder": int(signpost.get("displayOrder") or signpost_idx),
                    "strength": signpost.get("strength"),
                    "useYn": signpost.get("useYn"),
                    "keywordHints": signpost.get("keywordHints") or [],
                }
            )
        normalized_row["signposts"] = signposts
        rows.append(normalized_row)

    return {"headers": headers, "rows": rows}


def build_confirmation_scenario_group(scenario_group: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": scenario_group.get("title") or "",
        "summary": scenario_group.get("summary"),
        "description": scenario_group.get("description"),
    }


def post_validate_scenarios(
    base_url: str, group_id: int, user_id: int, table: dict[str, Any], timeout: int
) -> dict[str, Any]:
    resp = httpx.post(
        f"{base_url}/scenario-groups/{group_id}/validation",
        json={"userId": user_id, "table": table},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()


def post_create_signposts(
    base_url: str, group_id: int, user_id: int, table: dict[str, Any], timeout: int
) -> dict[str, Any]:
    resp = httpx.post(
        f"{base_url}/scenario-groups/{group_id}/signposts",
        json={"userId": user_id, "table": table},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()


def post_confirm_generation(
    base_url: str,
    group_id: int,
    user_id: int,
    scenario_group: dict[str, Any],
    table: dict[str, Any],
    timeout: int,
) -> dict[str, Any]:
    resp = httpx.post(
        f"{base_url}/scenario-groups/{group_id}/confirmation",
        json={
            "userId": user_id,
            "scenarioGroup": build_confirmation_scenario_group(scenario_group),
            "table": table,
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# User prompt helpers
# ---------------------------------------------------------------------------


def wait_for_callback(step_name: str) -> str:
    """Returns 'y' (received), 'n' (not received), 'p' (pass/skip this step)."""
    print(f"\n{'=' * 60}")
    print(f"[{step_name}] background 작업이 실행 중입니다.")
    print("callback이 수신되면 'y'를 입력하세요.")
    print("callback 없이 건너뛰려면 'n'을 입력하세요.")
    print("이 단계를 완전히 건너뛰려면 'p'를 입력하세요.")
    while True:
        answer = input("callback 수신 완료? [y/n/p]: ").strip().lower()
        if answer in ("y", "n", "p"):
            return answer
        print("  → 'y', 'n', 또는 'p'를 입력해주세요.")


def ask_run_step(step_num: int, label: str) -> bool:
    """Returns True to proceed with this step, False to skip/pass."""
    answer = input(f"\n  Step {step_num} ({label})을(를) 실행할까요? [Enter=실행 / p=건너뜀]: ").strip().lower()
    if answer == "p":
        print(f"  → Step {step_num} 건너뜁니다.")
        return False
    return True


def print_step(label: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {label}")
    print(f"{'─' * 60}")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Assertion helpers
# ---------------------------------------------------------------------------


def assert_accepted(response: dict[str, Any], step: str) -> dict[str, Any]:
    data = response.get("data") or {}
    group_id = data.get("scenarioGroupId")
    assert group_id, f"[{step}] scenarioGroupId가 없습니다: {response}"
    assert response.get("status") == "success", f"[{step}] status != success: {response}"
    print(f"  ✓ 200 접수 완료 | scenarioGroupId={group_id} | status={data.get('status')} | stage={data.get('stage')}")
    return data


def assert_get_stage(get_response: dict[str, Any], expected_stage: str, step: str) -> None:
    group = get_response.get("scenarioGroup") or {}
    actual_stage = group.get("stage")
    assert actual_stage == expected_stage, f"[{step}] stage 불일치: expected={expected_stage}, actual={actual_stage}"
    print(f"  ✓ stage={actual_stage} 확인")


def assert_signpost_created(get_response: dict[str, Any], step: str) -> None:
    signpost_count = get_response.get("signpostCount", 0)
    assert signpost_count > 0, f"[{step}] signpost_count={signpost_count} — signpost가 생성되지 않았습니다"
    print(f"  ✓ signpostCount={signpost_count} 확인")


def check_validate_stage(get_response: dict[str, Any]) -> bool:
    """validate_scenarios 후 stage 검증. 실패 시 계속 진행 여부를 묻는다.

    Returns False if the caller should abort (user chose not to continue).
    """
    group = get_response.get("scenarioGroup") or {}
    actual_stage = group.get("stage")
    is_valid = group.get("isValid")

    if actual_stage == "scenario_validated":
        print(f"  ✓ stage={actual_stage} 확인")
        return True

    if actual_stage == "scenario_created" and is_valid is False:
        print(f"  ⚠ stage={actual_stage}, isValid=False — 시나리오 검증 실패 상태입니다.")
        print("  다음 단계(signpost 생성)로 계속 진행하시겠습니까?")
        while True:
            cont = input("  계속 진행? [y/n]: ").strip().lower()
            if cont == "y":
                print("  → 검증 실패 상태로 계속 진행합니다.")
                return True
            if cont == "n":
                print("  → 테스트를 종료합니다.")
                return False
            print("  → 'y' 또는 'n'을 입력해주세요.")

    # 예상치 못한 stage
    raise AssertionError(f"[validate_scenarios] stage 불일치: expected=scenario_validated, actual={actual_stage}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    args = parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    skip = set(args.skip_step or [])

    group_id: int | None = args.group_id
    scenario_group: dict[str, Any] | None = None
    table: dict[str, Any] | None = None

    # ── Step 1: create_scenarios ──────────────────────────────────────────
    if 1 not in skip:
        print_step("Step 1 — POST /scenario-groups")
        try:
            resp = post_create_scenarios(args.base_url, args.mi_event_id, args.user_id, args.timeout)
        except httpx.HTTPStatusError as e:
            try:
                err_body = e.response.json()
            except Exception:
                err_body = {}
            err_name = (err_body.get("data") or {}).get("error_name", "")
            if e.response.status_code == 400 and err_name == "SCENARIO_GROUP_ALREADY_CREATED":
                print(f"  ⚠ {err_body.get('message', '시나리오 그룹이 이미 생성되었습니다.')}")
                print("  기존 scenarioGroupId를 입력하면 이후 단계를 계속 진행합니다.")
                print("  건너뛰려면 Enter를 누르세요.")
                raw = input("  scenarioGroupId: ").strip()
                if raw.isdigit():
                    group_id = int(raw)
                    print(f"  → scenarioGroupId={group_id} 로 계속 진행합니다.")
                else:
                    print("  → 테스트를 종료합니다.")
                    return 1
            else:
                print(f"  [ERROR] {e.response.status_code}: {e.response.text}")
                return 1
        else:
            write_json(OUTPUT_DIR / "step1_create_scenarios_response.json", resp)
            data = assert_accepted(resp, "create_scenarios")
            group_id = data["scenarioGroupId"]
    else:
        assert group_id, "--group-id가 필요합니다 (--skip-step 1 사용 시)"
        print_step(f"Step 1 — skip (scenarioGroupId={group_id} 사용)")

    # ── Step 1 callback 대기 → GET 검증 ──────────────────────────────────
    received = wait_for_callback("create_scenarios")
    if received == "y":
        get_resp = get_group(args.base_url, group_id, args.timeout)
        write_json(OUTPUT_DIR / "step1_get_after_callback.json", get_resp)
        print(f"\n[GET /scenario-groups/{group_id}]")
        assert_get_stage(get_resp, "scenario_created", "create_scenarios")
        scenario_count = get_resp.get("scenarioCount", 0)
        assert scenario_count > 0, f"scenarioCount={scenario_count} — 시나리오가 없습니다"
        print(f"  ✓ scenarioCount={scenario_count} 확인")
        scenario_group = get_resp.get("scenarioGroup")
        table = get_resp.get("table")
    elif received == "n":
        print("  → callback 미수신으로 GET 검증을 건너뜁니다.")
        if table is None:
            get_resp = get_group(args.base_url, group_id, args.timeout)
            scenario_group = get_resp.get("scenarioGroup")
            table = get_resp.get("table")
    else:  # p
        print("  → Step 1 패스합니다.")

    # ── Step 2: validate_scenarios ────────────────────────────────────────
    if 2 not in skip and ask_run_step(2, "validate_scenarios"):
        print_step(f"Step 2 — POST /scenario-groups/{group_id}/validation")
        if table is None:
            get_resp = get_group(args.base_url, group_id, args.timeout)
            scenario_group = get_resp.get("scenarioGroup")
            table = get_resp.get("table")
        assert table, "table 데이터가 없어 validation 요청을 구성할 수 없습니다"
        request_table = normalize_table_for_validate_or_signposts(table)
        write_json(
            OUTPUT_DIR / "step2_validation_request_body.json",
            {"userId": args.user_id, "table": request_table},
        )
        try:
            resp = post_validate_scenarios(args.base_url, group_id, args.user_id, request_table, args.timeout)
        except httpx.HTTPStatusError as e:
            print(f"  [ERROR] {e.response.status_code}: {e.response.text}")
            return 1
        write_json(OUTPUT_DIR / "step2_validate_response.json", resp)
        assert_accepted(resp, "validate_scenarios")
    else:
        print_step(f"Step 2 — skip (scenarioGroupId={group_id})")

    # ── Step 2 callback 대기 → GET 검증 ──────────────────────────────────
    received = wait_for_callback("validate_scenarios")
    if received == "y":
        get_resp = get_group(args.base_url, group_id, args.timeout)
        write_json(OUTPUT_DIR / "step2_get_after_callback.json", get_resp)
        print(f"\n[GET /scenario-groups/{group_id}]")
        if not check_validate_stage(get_resp):
            return 1
        scenario_group = get_resp.get("scenarioGroup")
        table = get_resp.get("table")
    elif received == "n":
        print("  → callback 미수신으로 GET 검증을 건너뜁니다.")
        if table is None:
            get_resp = get_group(args.base_url, group_id, args.timeout)
            scenario_group = get_resp.get("scenarioGroup")
            table = get_resp.get("table")
    else:  # p
        print("  → Step 2 패스합니다.")

    # ── Step 3: create_signposts ──────────────────────────────────────────
    if 3 not in skip and ask_run_step(3, "create_signposts"):
        print_step(f"Step 3 — POST /scenario-groups/{group_id}/signposts")
        if table is None:
            get_resp = get_group(args.base_url, group_id, args.timeout)
            scenario_group = get_resp.get("scenarioGroup")
            table = get_resp.get("table")
        assert table, "table 데이터가 없어 signpost 요청을 구성할 수 없습니다"
        request_table = normalize_table_for_validate_or_signposts(table)
        write_json(
            OUTPUT_DIR / "step3_signpost_request_body.json",
            {"userId": args.user_id, "table": request_table},
        )
        try:
            resp = post_create_signposts(args.base_url, group_id, args.user_id, request_table, args.timeout)
        except httpx.HTTPStatusError as e:
            print(f"  [ERROR] {e.response.status_code}: {e.response.text}")
            return 1
        write_json(OUTPUT_DIR / "step3_signposts_response.json", resp)
        assert_accepted(resp, "create_signposts")
    else:
        print_step(f"Step 3 — skip (scenarioGroupId={group_id})")

    # ── Step 3 callback 대기 → GET 검증 ──────────────────────────────────
    received = wait_for_callback("create_signposts")
    if received == "y":
        get_resp = get_group(args.base_url, group_id, args.timeout)
        write_json(OUTPUT_DIR / "step3_get_after_callback.json", get_resp)
        print(f"\n[GET /scenario-groups/{group_id}]")
        assert_get_stage(get_resp, "signpost_created", "create_signposts")
        assert_signpost_created(get_resp, "create_signposts")
        scenario_group = get_resp.get("scenarioGroup")
        table = get_resp.get("table")
    elif received == "n":
        print("  → callback 미수신으로 GET 검증을 건너뜁니다.")
    else:  # p
        print("  → Step 3 패스합니다.")

    # ── Step 4: confirm_generation ────────────────────────────────────────
    if 4 not in skip and ask_run_step(4, "confirm_generation"):
        print_step(f"Step 4 — POST /scenario-groups/{group_id}/confirmation")
        if scenario_group is None or table is None:
            get_resp = get_group(args.base_url, group_id, args.timeout)
            scenario_group = get_resp.get("scenarioGroup")
            table = get_resp.get("table")
        assert isinstance(scenario_group, dict), "scenarioGroup 데이터가 없어 confirmation 요청을 구성할 수 없습니다"
        assert isinstance(table, dict), "table 데이터가 없어 confirmation 요청을 구성할 수 없습니다"
        request_table = normalize_table_for_confirmation(table)
        request_body = {
            "userId": args.user_id,
            "scenarioGroup": build_confirmation_scenario_group(scenario_group),
            "table": request_table,
        }
        write_json(OUTPUT_DIR / "step4_confirmation_request_body.json", request_body)
        try:
            resp = post_confirm_generation(
                args.base_url,
                group_id,
                args.user_id,
                scenario_group,
                request_table,
                args.timeout,
            )
        except httpx.HTTPStatusError as e:
            print(f"  [ERROR] {e.response.status_code}: {e.response.text}")
            return 1
        write_json(OUTPUT_DIR / "step4_confirmation_response.json", resp)
        data = resp.get("data") or {}
        assert resp.get("status") == "success", f"[confirm_generation] status != success: {resp}"
        assert data.get("stage") == "completed", f"[confirm_generation] stage != completed: {resp}"
        print(f"  ✓ confirmation 완료 | status={data.get('status')} | stage={data.get('stage')}")
    else:
        print_step(f"Step 4 — skip (scenarioGroupId={group_id})")

    print(f"\n{'=' * 60}")
    print("  모든 스텝 완료")
    print(f"  결과 파일: {OUTPUT_DIR}")
    print(f"{'=' * 60}\n")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Callback API 통합 테스트 — create/validate/signpost 순서로 실행",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--base-url", default="http://localhost:8000", help="서버 주소")
    parser.add_argument("--mi-event-id", type=int, required=True, help="MI 이벤트 ID")
    parser.add_argument("--user-id", type=int, required=True, help="사용자 ID")
    parser.add_argument(
        "--skip-step",
        type=int,
        nargs="+",
        metavar="N",
        help="건너뛸 스텝 번호 (예: --skip-step 1 2)",
    )
    parser.add_argument(
        "--group-id",
        type=int,
        default=None,
        help="--skip-step 1 사용 시 직접 지정할 scenarioGroupId",
    )
    parser.add_argument("--timeout", type=int, default=30, help="httpx 타임아웃 초 (기본: 30)")
    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(main())
