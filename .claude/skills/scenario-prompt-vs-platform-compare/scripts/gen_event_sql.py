"""Generate (and optionally execute) INSERT SQL for MI Event markdown files.

Usage:
  poetry run python gen_event_sql.py --events-dir DIR --out insert.sql [--tag compare_YYYYMMDD]
      [--occurred-at "키워드=YYYY-MM-DD" ...] [--order "키워드1,키워드2,..."] [--execute]

- event_title / one_line_summary: markdown H1 (원문 short title is not in the markdown)
- key_bullets_json: '### 핵심요약' bullets, detail_analysis: '### 상세분석' body
- institution_view_synthesis: '### 기관 전망 종합 분석' paragraph (<=1000 chars)
- latest/oldest_record_first_created: dates in the '## MI Records' table
- event_type_l2_id: '- 세부 카테고리:' label looked up in tmm_mi_event_type_l2_m
- occurred_at: --occurred-at override, else the first date in the first 핵심요약 bullet
  (YYYY-MM-DD or 'M월 D일' with the year of '- 갱신:')
- tags_json: NULL unless the markdown has tags (v4 uses tags only for group metadata)
Without --execute nothing is written to the DB.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from common import db_connect, db_target, nfc, query

DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")
KO_DATE = re.compile(r"(\d{1,2})월\s*(\d{1,2})일")


def section(text: str, start: str, end: str) -> str:
    match = re.search(re.escape(start) + r"\n(.*?)(?=\n" + end + ")", text, re.S)
    return match.group(1).strip() if match else ""


def parse_event(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8-sig")
    title = text.splitlines()[0].lstrip("# ").strip()
    bullets = [
        line[2:].strip() for line in section(text, "### 핵심요약", r"### 상세분석").splitlines() if line.startswith("- ")
    ]
    detail = section(text, "### 상세분석", r"## 영향도 분석")
    inst = section(text, "### 기관 전망 종합 분석", r"\| 일자").strip()[:1000]
    records = re.findall(r"^\| (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \| ", text, re.M)
    l2_label = (re.search(r"^- 세부 카테고리:\s*(.+)$", text, re.M) or [None, ""])[1].strip()
    updated = (re.search(r"^- 갱신:\s*(\d{4})", text, re.M) or [None, ""])[1]
    occurred = ""
    if bullets:
        if m := DATE.search(bullets[0]):
            occurred = m.group(1)
        elif (m := KO_DATE.search(bullets[0])) and updated:
            occurred = f"{updated}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    missing = [name for name, value in (("title", title), ("핵심요약", bullets), ("상세분석", detail)) if not value]
    if missing:
        raise ValueError(f"{path.name}: missing {missing}")
    return {
        "file": path.name,
        "title": title[:300],
        "bullets": bullets,
        "detail": detail,
        "inst": inst or None,
        "records": records,
        "l2_label": l2_label,
        "occurred_at": occurred,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--tag", default="prompt_vs_platform")
    parser.add_argument("--occurred-at", action="append", default=[], help="'파일명 키워드=YYYY-MM-DD'")
    parser.add_argument("--order", default="", help="쉼표로 구분한 파일명 키워드 순서 (E1, E2, ...)")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    from pymysql.converters import escape_string as esc

    files = sorted(Path(args.events_dir).glob("*.md"))
    files = [f for f in files if not nfc(f.name).startswith("0")]  # skip 00_input.md etc.
    if args.order:
        keys = [nfc(k.strip()) for k in args.order.split(",") if k.strip()]
        files = [next(f for f in files if key in nfc(f.name)) for key in keys]
    overrides = dict(item.split("=", 1) for item in args.occurred_at)

    labels = {row["level_2_label"]: row["event_type_l2_id"] for row in query(
        "SELECT event_type_l2_id, level_2_label FROM tmm_mi_event_type_l2_m WHERE del_yn='N'"
    )}
    events = [parse_event(f) for f in files]
    statements: list[str] = []
    lines = [f"-- MI Event INSERT ({len(events)}건), tag={args.tag}, target={db_target()}", "START TRANSACTION;", ""]
    for event in events:
        for key, value in overrides.items():
            if nfc(key) in nfc(str(event["file"])):
                event["occurred_at"] = value
        l2 = labels.get(str(event["l2_label"]))
        if l2 is None:
            raise SystemExit(f"{event['file']}: 세부 카테고리 '{event['l2_label']}' 를 L2 테이블에서 찾지 못함")
        if not event["occurred_at"]:
            raise SystemExit(f"{event['file']}: occurred_at 을 추론하지 못함. --occurred-at 으로 지정")
        records = list(event["records"]) or [f"{event['occurred_at']} 00:00:00"]
        values = [
            str(l2),
            f"'{esc(str(event['title']))}'",
            f"'{esc(str(event['title']))}'",
            f"'{esc(json.dumps({'bullets': event['bullets']}, ensure_ascii=False))}'",
            f"'{esc(str(event['detail']))}'",
            "NULL",
            f"'{event['occurred_at']} 00:00:00'",
            f"'{max(records)}'",
            f"'{min(records)}'",
            f"'{esc(str(event['inst']))}'" if event["inst"] else "NULL",
            "'Y'", "'Y'", "'Y'", f"'{esc(args.tag)}'", f"'{esc(args.tag)}'",
        ]
        lines.append(f"-- {event['title']}  (l2={l2} {event['l2_label']}, occurred_at={event['occurred_at']})")
        statements.append(
            "INSERT INTO tmm_mi_mievent_m (event_type_l2_id, event_title, one_line_summary, key_bullets_json, "
            "detail_analysis, tags_json, occurred_at, latest_record_first_created, oldest_record_first_created, "
            "institution_view_synthesis, signal_yn, scenario_suggest_yn, new_yn, crt_usr_logn_id, mod_usr_logn_id) "
            f"VALUES ({', '.join(values)})"
        )
        lines.append(statements[-1] + ";\n")
    lines += [
        "COMMIT;",
        "",
        f"SELECT mi_event_id, event_type_l2_id, event_title, occurred_at FROM tmm_mi_mievent_m "
        f"WHERE crt_usr_logn_id = '{esc(args.tag)}' ORDER BY mi_event_id;",
        "",
    ]
    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    for event in events:
        print(f"- {event['file'][:70]} | l2={event['l2_label']} | occurred_at={event['occurred_at']} "
              f"| bullets={len(event['bullets'])}")
    print(f"SQL written: {args.out}")

    if not args.execute:
        return 0
    conn = db_connect()
    try:
        with conn.cursor() as cur:
            for statement in statements:
                cur.execute(statement)
        conn.commit()
    finally:
        conn.close()
    rows = query(
        "SELECT mi_event_id, event_title FROM tmm_mi_mievent_m WHERE crt_usr_logn_id=%s ORDER BY mi_event_id DESC LIMIT %s",
        (args.tag, len(events)),
    )
    ids = sorted(int(r["mi_event_id"]) for r in rows)
    print("inserted mi_event_ids (request order):", ",".join(map(str, ids)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
