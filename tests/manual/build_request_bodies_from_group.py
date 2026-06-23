#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "GET /scenario-groups/{id} 응답을 기반으로 "
            "validation/signposts/confirmation 요청 바디를 생성합니다."
        )
    )
    parser.add_argument("--base-url", default="http://localhost:8000", help="API 서버 주소")
    parser.add_argument("--scenario-group-id", type=int, required=True, help="시나리오 그룹 ID")
    parser.add_argument(
        "--user-id",
        type=int,
        default=None,
        help="요청 사용자 ID (미지정 시 GET 응답의 scenarioGroup.requestUsrId 사용)",
    )
    parser.add_argument(
        "--include-deleted",
        action="store_true",
        help="GET 조회 시 includeDeleted=true 사용",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("local/output/request_bodies"),
        help="생성 JSON 파일 저장 디렉토리",
    )
    parser.add_argument(
        "--print-json",
        action="store_true",
        help="생성된 요청 바디를 콘솔에 JSON으로 출력",
    )
    return parser.parse_args()


def get_scenario_group(base_url: str, scenario_group_id: int, include_deleted: bool) -> dict[str, Any]:
    response = httpx.get(
        f"{base_url}/scenario-groups/{scenario_group_id}",
        params={"includeDeleted": str(include_deleted).lower()},
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()

    # 일부 게이트웨이 환경에서 공통 응답 래퍼(status/data)를 씌우는 케이스를 흡수한다.
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        data = payload["data"]
        if "scenarioGroup" in data and "table" in data:
            return data

    return payload


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


def build_confirmation_scenario_group(scenario_group: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": scenario_group.get("title") or "",
        "summary": scenario_group.get("summary"),
        "description": scenario_group.get("description"),
    }


def resolve_user_id(cli_user_id: int | None, scenario_group: dict[str, Any]) -> int:
    if cli_user_id is not None:
        return cli_user_id

    response_user_id = scenario_group.get("requestUsrId")
    if isinstance(response_user_id, int):
        return response_user_id

    raise ValueError(
        "userId를 결정할 수 없습니다. --user-id를 지정하거나, "
        "GET 응답에 scenarioGroup.requestUsrId가 있어야 합니다."
    )


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def print_paths(paths: list[Path]) -> None:
    print("\n[generated files]")
    for path in paths:
        print(f"- {path}")


def main() -> int:
    args = parse_args()

    source = get_scenario_group(args.base_url, args.scenario_group_id, args.include_deleted)
    scenario_group = source.get("scenarioGroup")
    table = source.get("table")

    if not isinstance(scenario_group, dict):
        raise ValueError("GET 응답에 scenarioGroup 객체가 없습니다.")
    if not isinstance(table, dict):
        raise ValueError("GET 응답에 table 객체가 없습니다.")

    user_id = resolve_user_id(args.user_id, scenario_group)
    minimal_table = normalize_table_for_validate_or_signposts(table)

    # HTTP API body (scenario_group_id는 URL path parameter)
    validation_body = {"userId": user_id, "table": minimal_table}
    signpost_body = {"userId": user_id, "table": minimal_table}
    confirmation_body = {
        "userId": user_id,
        "scenarioGroup": build_confirmation_scenario_group(scenario_group),
        "table": table,
    }

    output_root = args.output_dir / f"scenario_group_{args.scenario_group_id}"
    files = {
        "get_response": output_root / "scenario_group_get_response.json",
        "validation": output_root / "validation_request_body.json",
        "signposts": output_root / "signpost_request_body.json",
        "confirmation": output_root / "confirmation_request_body.json",
    }

    write_json(files["get_response"], source)
    write_json(files["validation"], validation_body)
    write_json(files["signposts"], signpost_body)
    write_json(files["confirmation"], confirmation_body)

    print(f"[ok] scenario_group_id={args.scenario_group_id}, user_id={user_id}")
    print_paths(list(files.values()))
    print("\n[usage]")
    print("- 모든 출력은 HTTP API 요청 바디 기준입니다.")
    print("- scenario_group_id는 URL path parameter로 전달하세요.")

    if args.print_json:
        print("\n[validation request body]")
        print(json.dumps(validation_body, ensure_ascii=False, indent=2))
        print("\n[signpost request body]")
        print(json.dumps(signpost_body, ensure_ascii=False, indent=2))
        print("\n[confirmation request body]")
        print(json.dumps(confirmation_body, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[error] {exc}", file=sys.stderr)
        raise
