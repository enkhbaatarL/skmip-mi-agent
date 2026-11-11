from __future__ import annotations

# ruff: noqa: CPY001, ANN001, ANN201, E501, RUF001
# Embedded report templates keep readable HTML/CSS and Korean punctuation.
from collections import Counter
from datetime import datetime
from html import escape
import json
from pathlib import Path
from statistics import mean, median, stdev
from zoneinfo import ZoneInfo


LABELS = {
    "J-01": "Event 근거",
    "J-02": "Baseline",
    "J-03": "시나리오 범위",
    "J-04": "Dimension",
    "J-05": "내부 일관성",
    "J-06": "시장·지역",
    "J-11": "명확성",
}
RANK = {"FAIL": 0, "WARN": 1, "PASS": 2}


def read(path: Path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def text(value):
    if value is None:
        return "—"
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


def h(value):
    return escape(text(value))


def num(value):
    return "—" if value is None else f"{value:.4f}"


def badge(value):
    key = value if value in {"PASS", "WARN", "FAIL", "NEEDS_FACT"} else "OTHER"
    return f'<span class="badge {key}">{h(value)}</span>'


def md(value):
    return text(value).replace("|", "\\|").replace("\n", "<br>")


def at_path(data, path):
    try:
        for part in path.lstrip("/").split("/"):
            part = part.replace("~1", "/").replace("~0", "~")
            data = data[int(part)] if isinstance(data, list) else data[part]
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    return data


def changes_between(before, after, path=""):
    if type(before) is not type(after):
        return [{"path": path, "before": before, "after": after}] if before != after else []
    if isinstance(before, dict):
        rows = []
        for key in sorted(set(before) | set(after)):
            if key == "sourceOperationId":
                continue
            rows.extend(changes_between(before.get(key), after.get(key), f"{path}/{key}"))
        return rows
    if isinstance(before, list) and len(before) == len(after):
        return [
            change
            for i, (a, b) in enumerate(zip(before, after, strict=True))
            for change in changes_between(a, b, f"{path}/{i}")
        ]
    return [] if before == after else [{"path": path, "before": before, "after": after}]


def load_cases(output: Path, manifest):
    cases = []
    for meta in manifest["selectedGroups"]:
        group_id = meta["scenario_group_id"]
        directory = output / f"group_{group_id}"
        before = read(directory / "evaluation_1.json", {})
        after = read(directory / "evaluation_2.json", {})
        trace = read(directory / "llm_trace.json", [])
        completed = before.get("status") == after.get("status") == "succeeded" and bool(after.get("result"))
        applied = (after.get("retrySummary", {}).get("qualityRepair") or {}).get("state") == "applied"
        changes = changes_between(before.get("inputSnapshot", {}), after.get("inputSnapshot", {})) if applied else []
        # description is a read-model alias of narrative; do not double count the same text edit.
        changes = [
            c for c in changes if not (c["path"].startswith("/scenarios/") and c["path"].endswith("/description"))
        ]
        if completed:
            state = "수정·재평가 완료"
        elif after:
            state = "재평가 실패" if applied else "수정 차단·실패"
        elif before.get("status") == "succeeded":
            state = "자동 수정 대상 아님"
        else:
            state = "최초 평가 실패·미완료"
        delta = round(after["averageScore"] - before["averageScore"], 4) if completed else None
        before_items = {i["judgeId"]: i for i in (before.get("result") or {}).get("items", [])}
        after_items = {i["judgeId"]: i for i in (after.get("result") or {}).get("items", [])}
        converted = [
            key
            for key, item in before_items.items()
            if item["verdict"] != "PASS" and after_items.get(key, {}).get("verdict") == "PASS"
        ]
        plan = (after.get("retrySummary", {}).get("qualityRepair") or {}).get("plan")
        if not plan:
            plan = next((call.get("result") for call in trace if call["schema"] == "QualityRepairPlan"), {})
        review = (after.get("retrySummary", {}).get("qualityRepair") or {}).get("review")
        if not review:
            review = next((call.get("result") for call in trace if call["schema"] == "QualityRepairReview"), {})
        grade_improved = (
            completed
            and before["verdict"] in RANK
            and after["verdict"] in RANK
            and (RANK[after["verdict"]] > RANK[before["verdict"]])
        )
        cases.append(
            {
                "groupId": group_id,
                "source": meta,
                "before": before,
                "after": after,
                "trace": trace,
                "completed": completed,
                "applied": applied,
                "changes": changes,
                "state": state,
                "delta": delta,
                "gradeImproved": grade_improved,
                "convertedCriteria": converted,
                "plan": plan,
                "review": review,
                "beforeItems": before_items,
                "afterItems": after_items,
                "eventsUnchanged": bool(applied)
                and before["inputSnapshot"]["events"] == after["inputSnapshot"]["events"],
                "summary": read(directory / "summary.json", {}),
                "failureDetail": read(directory / "failure_detail.json", {}),
            },
        )
    return cases


def metrics(cases):
    pairs = [c for c in cases if c["completed"]]
    return {
        "groups": len(cases),
        "scenarios": sum(c["source"]["scenario_count"] for c in cases),
        "initialSucceeded": sum(c["before"].get("status") == "succeeded" for c in cases),
        "repairAttempted": sum(bool(c["after"]) for c in cases),
        "pairedCompleted": len(pairs),
        "beforeMeanPaired": mean(c["before"]["averageScore"] for c in pairs) if pairs else None,
        "afterMeanPaired": mean(c["after"]["averageScore"] for c in pairs) if pairs else None,
        "meanDeltaPaired": (round(mean(c["delta"] for c in pairs), 6) or 0.0) if pairs else None,
        "scoreImproved": sum(c["delta"] > 0 for c in pairs),
        "scoreUnchanged": sum(c["delta"] == 0 for c in pairs),
        "scoreDeclined": sum(c["delta"] < 0 for c in pairs),
        "verdictImproved": sum(c["gradeImproved"] for c in cases),
        "initialVerdicts": dict(Counter(c["before"].get("verdict") or "실행 실패" for c in cases)),
        "reevaluationVerdicts": dict(Counter(c["after"]["verdict"] for c in pairs)),
        "changedFields": sum(len(c["changes"]) for c in cases),
        "criteriaToPass": sum(len(c["convertedCriteria"]) for c in cases),
        "criteriaFromPass": sum(
            item["verdict"] == "PASS" and c["afterItems"].get(key, {}).get("verdict") != "PASS"
            for c in pairs for key, item in c["beforeItems"].items()
        ),
        "models": sorted({call["model"] for c in cases for call in c["trace"] if call.get("model")}),
        "llmCalls": sum(len(c["trace"]) for c in cases),
        "productionDbWrites": False,
    }


def successful(record):
    return record.get("status") == "succeeded" and bool(record.get("result"))


def final_record(case):
    # A skipped repair retains the original result; an attempted but failed evaluation is unknown.
    return case["after"] if case["after"] else case["before"]


def verdict(record):
    return record.get("verdict") if successful(record) else "UNKNOWN"


def rate(count, total):
    return round(100 * count / total, 4) if total else None


def wilson(count, total):
    if not total:
        return None
    z = 1.959963984540054
    p = count / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    margin = z * ((p * (1 - p) / total + z * z / (4 * total * total)) ** 0.5) / denominator
    return [round(100 * (center - margin), 2), round(100 * (center + margin), 2)]


def pass_statistics(cases):
    total = len(cases)
    before = [c["before"] for c in cases]
    after = [final_record(c) for c in cases]
    before_count = sum(verdict(r) == "PASS" for r in before)
    after_count = sum(verdict(r) == "PASS" for r in after)
    criteria = []
    for key, label in LABELS.items():
        sides = []
        for records in (before, after):
            items = [item for r in records if successful(r) for item in r["result"]["items"] if item["judgeId"] == key]
            count = sum(item["verdict"] == "PASS" for item in items)
            sides.append(
                {
                    "pass": count,
                    "total": total,
                    "known": len(items),
                    "rate": rate(count, total),
                    "mean": mean(item["score"] for item in items) if items else None,
                },
            )
        criteria.append({"judgeId": key, "label": label, "before": sides[0], "after": sides[1]})
    deltas = [c["delta"] for c in cases if c["completed"]]
    pairs = [c for c in cases if c["completed"]]
    paired_before = sum(i["verdict"] == "PASS" for c in pairs for i in c["before"]["result"]["items"])
    paired_after = sum(i["verdict"] == "PASS" for c in pairs for i in c["after"]["result"]["items"])
    transitions = Counter((verdict(c["before"]), verdict(final_record(c))) for c in cases)
    return {
        "denominator": total,
        "beforePass": before_count,
        "afterPass": after_count,
        "beforeRate": rate(before_count, total),
        "afterRate": rate(after_count, total),
        "changePercentagePoints": rate(after_count - before_count, total),
        "beforeWilson95": wilson(before_count, total),
        "afterWilson95": wilson(after_count, total),
        "initialKnown": sum(successful(r) for r in before),
        "finalKnown": sum(successful(r) for r in after),
        "retainedOriginal": sum(not c["after"] and successful(c["before"]) for c in cases),
        "finalVerdicts": dict(Counter(verdict(r) for r in after)),
        "criteria": criteria,
        "criteriaBeforePass": sum(c["before"]["pass"] for c in criteria),
        "criteriaAfterPass": sum(c["after"]["pass"] for c in criteria),
        "criteriaDenominator": total * len(LABELS),
        "criteriaBeforeRate": rate(sum(c["before"]["pass"] for c in criteria), total * len(LABELS)),
        "criteriaAfterRate": rate(sum(c["after"]["pass"] for c in criteria), total * len(LABELS)),
        "pairedCriteriaDenominator": len(pairs) * len(LABELS),
        "pairedCriteriaBeforePass": paired_before, "pairedCriteriaAfterPass": paired_after,
        "pairedCriteriaBeforeRate": rate(paired_before, len(pairs) * len(LABELS)),
        "pairedCriteriaAfterRate": rate(paired_after, len(pairs) * len(LABELS)),
        "deltaMedian": median(deltas) if deltas else None,
        "deltaStdDev": stdev(deltas) if len(deltas) > 1 else None,
        "deltaMin": min(deltas) if deltas else None,
        "deltaMax": max(deltas) if deltas else None,
        "transitions": [{"before": a, "after": b, "count": n} for (a, b), n in sorted(transitions.items())],
    }


def pass_chart(stats):
    rows = [("그룹 전체 PASS", stats["beforePass"], stats["afterPass"], stats["denominator"])]
    rows += [
        (f"{c['judgeId']} {c['label']}", c["before"]["pass"], c["after"]["pass"], c["before"]["total"])
        for c in stats["criteria"]
    ]
    height = 85 + len(rows) * 68
    parts = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 {height}" role="img" '
            'aria-label="수정 전과 평가 피드백 수정 후의 통과율, 동일 표본 기준">'
        ),
        (
            '<text x="200" y="22" fill="#64748b" font-size="13">회색: 원본</text>'
            '<text x="390" y="22" fill="#007f73" font-size="13">초록: 피드백 적용 후</text>'
        ),
    ]
    for tick in range(0, 101, 25):
        x = 200 + tick * 6
        parts.append(
            f'<line x1="{x}" x2="{x}" y1="42" y2="{height - 22}" stroke="#e3e9ef"/>'
            f'<text x="{x}" y="{height - 3}" text-anchor="middle" font-size="12" fill="#637187">{tick}%</text>',
        )
    for index, (label, a, b, total) in enumerate(rows):
        y = 48 + index * 68
        parts.append(f'<text x="8" y="{y + 22}" font-size="14" fill="#16243b">{h(label)}</text>')
        for offset, count, color in ((0, a, "#94a3b8"), (24, b, "#007f73")):
            percent = rate(count, total) or 0
            parts.append(
                f'<rect x="200" y="{y + offset}" width="{percent * 6}" height="17" rx="3" fill="{color}"/>'
                f'<text x="825" y="{y + offset + 14}" font-size="13" fill="{color}">{percent:.1f}% ({count}/{total})</text>',
            )
    return "".join(parts) + "</svg>"


def statistics_markdown(stats):
    total = stats["denominator"]
    lines = [
        "## 평가 피드백 적용 전후 통과율",
        "",
        "통과는 종합 verdict=PASS를 뜻합니다. WARN을 통과에 포함하지 않습니다. 미실행·실패도 분모에서 제외하지 않습니다.",
        "",
        "| 지표 | 원본(피드백 수정 전) | 피드백 적용 후 |",
        "|---|---:|---:|",
        f"| 그룹 통과율 | {stats['beforeRate']:.1f}% ({stats['beforePass']}/{total}) | {stats['afterRate']:.1f}% ({stats['afterPass']}/{total}) |",
        f"| 기준별 통과율 | {stats['criteriaBeforeRate']:.1f}% ({stats['criteriaBeforePass']}/{stats['criteriaDenominator']}) | {stats['criteriaAfterRate']:.1f}% ({stats['criteriaAfterPass']}/{stats['criteriaDenominator']}) |",
        "",
        f"통과율 변화: **{stats['changePercentagePoints']:+.1f}%p**. 최초 PASS 등 자동 수정 대상이 아닌 {stats['retainedOriginal']}개는 원본 판정을 유지했습니다.",
        f"최종 판정 확인 가능: {stats['finalKnown']}/{total}. 수정 또는 재평가 실패는 통과로 계산하지 않습니다.",
        "",
        "| 기준 | 원본 PASS 비율 | 적용 후 PASS 비율 | 원본 평균 | 적용 후 평균 |",
        "|---|---:|---:|---:|---:|",
    ]
    for c in stats["criteria"]:
        a, b = c["before"], c["after"]
        lines.append(
            f"| {c['judgeId']} {c['label']} | {a['rate']:.1f}% ({a['pass']}/{total}) | {b['rate']:.1f}% ({b['pass']}/{total}) | {num(a['mean'])} | {num(b['mean'])} |",
        )
    lines += [
        "",
        "기준별 평균은 해당 시점의 유효한 평가만 사용합니다. 전후 유효 수가 다르면 동일 표본 평균 비교로 해석하지 않습니다.",
        "",
        (f"재평가 완료 쌍만의 기준별 통과율: {stats['pairedCriteriaBeforePass']} → {stats['pairedCriteriaAfterPass']} / {stats['pairedCriteriaDenominator']}개 기준. "
        "전체 표본 통과율에는 실패로 확인하지 못한 기준도 포함하므로, 감소를 곧바로 내용의 악화로 해석하지 않습니다."),
        "", "### 판정 전환",
        "",
        "| 원본 | 적용 후 | 그룹 수 |",
        "|---|---|---:|",
    ]
    lines += [f"| {row['before']} | {row['after']} | {row['count']} |" for row in stats["transitions"]]
    lines += [
        "",
        "### 기술 통계와 한계",
        "",
        f"- 재평가 완료 쌍의 점수 변화: 중앙값 {num(stats['deltaMedian'])}, 표본 표준편차 {num(stats['deltaStdDev'])}, 범위 {num(stats['deltaMin'])} ~ {num(stats['deltaMax'])}.",
        f"- 그룹 통과율 Wilson 95% 구간: 원본 {stats['beforeWilson95']}%, 적용 후 {stats['afterWilson95']}%.",
        "- 구간은 작은 표본의 불확실성을 보여주는 이항 근사입니다. 모집단 효과나 전후 차이의 통계적 유의성을 보장하지 않습니다.",
        "- 7개 기준은 같은 그룹에 속하므로 70개의 독립 표본으로 해석하지 않습니다.",
        "",
    ]
    return lines


def score_chart(cases):
    width, height = 1000, 52 + len(cases) * 40
    parts = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" '
            'aria-label="그룹별 최초 점수와 재평가 점수, 5점 척도">'
        ),
    ]
    for tick in range(6):
        x = 130 + tick * 130
        parts.append(
            f'<line x1="{x}" y1="25" x2="{x}" y2="{height}" stroke="#e3e9ef"/>'
            f'<text x="{x}" y="17" text-anchor="middle" fill="#667085" font-size="13">{tick}</text>',
        )
    for index, case in enumerate(cases):
        y = 48 + index * 40
        a = case["before"].get("averageScore")
        b = case["after"].get("averageScore") if case["completed"] else None
        parts.append(f'<text x="15" y="{y + 5}" fill="#22324b" font-size="14">Group {case["groupId"]}</text>')
        if a is not None:
            x = 130 + a * 130
            if b is not None:
                end = 130 + b * 130
                color = "#007f73" if b >= a else "#d1495b"
                parts.append(
                    f'<line x1="{x}" y1="{y}" x2="{end}" y2="{y}" stroke="{color}" stroke-width="4"/>'
                    f'<circle cx="{end}" cy="{y}" r="7" fill="{color}"/>',
                )
            parts.append(f'<circle cx="{x}" cy="{y}" r="4" fill="#fff" stroke="#64748b" stroke-width="2"/>')
        label = f"{num(a)} → {num(b)}"
        parts.append(f'<text x="820" y="{y + 5}" fill="#475467" font-size="13">{label}</text>')
    return "".join(parts) + "</svg>"


def issue_cards(record):
    result = record.get("result") or {}
    cards = []
    for item in result.get("items", []):
        for index, issue in enumerate(item["violations"]):
            cards.append(f"""<article class="issue"><div>{badge(item["verdict"])}
<b>{h(item["judgeId"])} · {h(LABELS[item["judgeId"]])} · 위반 {index + 1}</b></div>
<div class="meta">시나리오 {h(issue["scenarioIds"])} · {h(issue["factDependency"])}</div>
<dl><dt>판정 사유</dt><dd>{h(issue["reason"])}</dd><dt>판단 근거</dt><dd>{h(issue["evidence"])}</dd>
<dt>수정 제안</dt><dd>{h(issue["suggestedFix"])}</dd><dt>근거 위치</dt><dd><code>{h(issue["evidencePath"])}</code></dd></dl></article>""")
    return "".join(cards) or '<p class="muted">위반 없음 또는 평가 결과 없음</p>'


def change_cards(case):
    proposed = {item["path"]: item for item in (case["plan"] or {}).get("changes", [])}
    cards = []
    for change in case["changes"]:
        reference = proposed.get(change["path"])
        item = case["beforeItems"].get(reference["judgeId"], {}) if reference else {}
        issues = item.get("violations", [])
        issue = issues[reference["violationIndex"]] if reference and reference["violationIndex"] < len(issues) else {}
        after_item = case["afterItems"].get(reference["judgeId"], {}) if reference else {}
        target = ""
        if change["path"].startswith("/scenarios/"):
            index = int(change["path"].split("/")[2])
            target = f" · 시나리오 {case['before']['inputSnapshot']['scenarios'][index]['scenario_id']}"
        check = (
            (
                f"{reference['judgeId']} 재평가: {after_item.get('verdict', '미완료')} · "
                f"{item.get('score', '—')} → {after_item.get('score', '—')}점"
            )
            if reference
            else "서버 파생값 재계산"
        )
        cards.append(f"""<article class="change"><div class="change-head"><code>{h(change["path"])}</code>{h(target)}</div>
<p class="meta">{h(check)}</p><div class="compare"><div><span class="eyebrow">기존 내용</span><p>{h(change["before"])}</p></div>
<div><span class="eyebrow">실제 반영 내용</span><p>{h(change["after"])}</p></div></div>
<p class="rationale"><b>연결된 수정 제안</b> {h(issue.get("suggestedFix") or "상대 압력·역할의 결정적 재계산")}</p></article>""")
    return (
        "".join(cards) or '<p class="muted">실제로 반영된 수정 없음. 제안만 생성됐거나 자동 수정 대상이 아닙니다.</p>'
    )


def group_card(case):
    first, second = case["before"], case["after"]
    rows = []
    for key, label in LABELS.items():
        a, b = case["beforeItems"].get(key, {}), case["afterItems"].get(key, {})
        rows.append(
            f"<tr><td>{key} {label}</td><td>{a.get('score', '—')} {badge(a.get('verdict'))}</td>"
            f"<td>{b.get('score', '—')} {badge(b.get('verdict'))}</td></tr>",
        )
    converted = ", ".join(case["convertedCriteria"]) or "없음"
    error = case["failureDetail"] or second.get("lastError") or first.get("lastError")
    review = case["review"] or {}
    unresolved = (case["plan"] or {}).get("unresolved", [])
    links = f'<a href="group_{case["groupId"]}/evaluation_1.json">최초 JSON</a>'
    if second:
        links += f' · <a href="group_{case["groupId"]}/evaluation_2.json">재평가 JSON</a>'
    links += f' · <a href="group_{case["groupId"]}/llm_trace.json">LLM 응답 원본</a>'
    return f"""<section class="group" id="group-{case["groupId"]}" data-search="{h(str(case["groupId"]) + " " + case["source"]["title"])}"
 data-improved="{"yes" if case["gradeImproved"] or (case["delta"] or 0) > 0 else "no"}">
<div class="group-title"><div><span class="eyebrow">GROUP {case["groupId"]} · {case["source"]["scenario_count"]} SCENARIOS</span>
<h2>{h(case["source"]["title"])}</h2></div><div>{badge(first.get("verdict"))} → {badge(second.get("verdict"))}</div></div>
<p>{h(case["state"])} · 평균 {num(first.get("averageScore"))} → {num(second.get("averageScore"))}
 · 변화 {f"{case['delta']:+.4f}" if case["delta"] is not None else "—"}</p>
<div class="proof"><b>전후 비교 증거</b> · 실제 변경 {len(case["changes"])}개 · 기준별 PASS 전환 {h(converted)}
 · Event 입력 {"동일" if case["eventsUnchanged"] else "변경 적용 없음/비교 불가"}<br>
<span class="meta">입력 hash: {h(first.get("inputHash"))} → {h(second.get("inputHash"))}</span></div>
<p class="meta">검증: {h(review.get("reason", "수정 검증 미실행"))}</p>
{f'<div class="note"><b>수정안에서 남긴 미해결 사유</b><ul>{"".join(f"<li>{h(reason)}</li>" for reason in unresolved)}</ul></div>' if unresolved else ''}
{f'<p class="error">실행 오류: {h(error)}</p>' if error else ""}
<div class="table-wrap"><table><thead><tr><th>평가 기준</th><th>최초</th><th>재평가</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>
<div class="compare summaries"><div><h3>최초 평가 요약</h3><p>{h((first.get("result") or {}).get("summary"))}</p></div>
<div><h3>재평가 요약</h3><p>{h((second.get("result") or {}).get("summary"))}</p></div></div>
<details><summary>기존 내용 ↔ 실제 반영 내용 ({len(case["changes"])}개)</summary>{change_cards(case)}</details>
<details><summary>최초 판정 근거·사유·수정 제안</summary>{issue_cards(first)}</details>
<details><summary>재평가에 남은 근거·사유·수정 제안</summary>{issue_cards(second)}</details>
<p class="meta">{links}</p></section>"""


CSS = """
:root{--ink:#16243b;--muted:#637187;--teal:#007f73;--line:#e1e7ee}*{box-sizing:border-box}
body{margin:0;background:#f2f5f8;color:var(--ink);font-family:'Malgun Gothic','Apple SD Gothic Neo',sans-serif;line-height:1.75}
main{max-width:1240px;margin:auto;padding:40px 24px 100px}header{padding:42px;background:#14253e;color:#fff;border-radius:24px}
header p{color:#c8d6e6;max-width:950px}h1{font-size:32px;line-height:1.4;margin:14px 0}h2{font-size:23px;margin:8px 0}h3{font-size:16px}
.eyebrow{font-size:11px;font-weight:700;letter-spacing:1.5px;color:#508d9a}header .eyebrow{color:#79ded0}
.meta,.muted{color:var(--muted);font-size:12px}.meta{overflow-wrap:anywhere}.pill{display:inline-block;padding:4px 12px;background:#28425d;border-radius:30px;font-size:12px}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:24px 0}.kpi{background:#fff;padding:22px;border-radius:16px;border:1px solid var(--line)}
.kpi strong{font-size:27px;display:block;color:var(--teal)}.panel,.group{background:#fff;border:1px solid var(--line);border-radius:18px;padding:28px;margin:22px 0}
.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px}th{text-align:left;background:#eef3f7;color:#526174;white-space:nowrap}
td,th{padding:12px 10px;border-bottom:1px solid var(--line);vertical-align:top}td.title{min-width:250px}a{color:#006f8b;text-decoration:none}a:hover{text-decoration:underline}
.badge{font-size:11px;font-weight:700;padding:3px 8px;border-radius:6px;display:inline-block;white-space:nowrap}.PASS{background:#daf4e9;color:#076b4b}
.WARN{background:#fff1cf;color:#966000}.FAIL{background:#ffe2e6;color:#b01d43}.NEEDS_FACT{background:#e8e2ff;color:#6942aa}.OTHER{background:#edf0f4;color:#67758b}
.positive{color:#007f73;font-weight:bold}.negative{color:#be3150;font-weight:bold}.group-title{display:flex;gap:20px;align-items:center;justify-content:space-between}
.group-title h2{font-size:21px}.compare{display:grid;grid-template-columns:1fr 1fr;gap:14px}.compare>div{background:#f7f9fb;border-radius:10px;padding:18px;min-width:0}
.compare>div:nth-child(2){background:#f0f8f6}.compare p{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px;margin-bottom:0}
.proof{border-left:4px solid #2c9b8b;background:#f1f9f7;padding:14px 18px;font-size:13px;margin:18px 0}.error{background:#fff0f2;padding:12px;color:#a12c44}
details{margin:18px 0}summary{cursor:pointer;font-weight:700;padding:14px 0;border-bottom:1px solid var(--line)}
.change,.issue{margin:16px 0;border:1px solid var(--line);border-radius:12px;padding:18px}.change-head{font-weight:bold;font-size:13px;overflow-wrap:anywhere}
code{font-family:Consolas,monospace;font-size:12px;background:#eef2f6;padding:2px 5px;border-radius:4px;overflow-wrap:anywhere}
.rationale{font-size:12px;color:#4e5e73;background:#f8f9fc;padding:12px}.issue dl{font-size:13px}.issue dt{font-weight:bold;margin-top:12px}
.issue dd{margin:3px 0;white-space:pre-wrap;overflow-wrap:anywhere}.issue .badge{margin-right:8px}.controls{display:flex;gap:10px;margin:18px 0}
input,select{font:inherit;font-size:13px;border:1px solid #cad4df;border-radius:9px;padding:10px;background:#fff}input{flex:1}
.note{font-size:13px;background:#fff8e9;border:1px solid #f0dfb6;padding:18px;border-radius:12px}.hidden{display:none}
svg{width:100%;min-width:680px}footer{color:var(--muted);font-size:12px;margin:30px 0}@media(max-width:760px){.kpis{grid-template-columns:1fr 1fr}.compare{grid-template-columns:1fr}.group-title{display:block}main{padding:18px 12px}header{padding:25px}.panel,.group{padding:18px}}
@media print{body{background:white}main{max-width:none;padding:0}header{border-radius:0}.controls{display:none}.group{break-before:page}details{break-inside:auto}a{color:inherit}.hidden{display:block}}
"""


def write_report(output: Path) -> None:  # noqa: C901 - assemble parallel report formats
    manifest = read(output / "manifest.json")
    cases = load_cases(output, manifest)
    stats = metrics(cases)
    pass_stats = pass_statistics(cases)
    stats["passStatistics"] = pass_stats
    generated = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M KST")
    rows = []
    for c in cases:
        a, b = c["before"], c["after"]
        change = f"{c['delta']:+.4f}" if c["delta"] is not None else "—"
        color = "positive" if (c["delta"] or 0) > 0 else "negative" if (c["delta"] or 0) < 0 else ""
        rows.append(
            f'<tr><td><a href="#group-{c["groupId"]}">{c["groupId"]}</a></td><td class="title">{h(c["source"]["title"])}</td>'
            f"<td>{c['source']['scenario_count']}</td><td>{num(a.get('averageScore'))}<br>{badge(a.get('verdict'))}</td>"
            f'<td>{num(b.get("averageScore"))}<br>{badge(b.get("verdict"))}</td><td class="{color}">{change}</td>'
            f"<td>{len(c['changes'])}</td><td>{h(c['state'])}</td></tr>",
        )
    delta = stats["meanDeltaPaired"]
    hero_delta = f"{delta:+.4f}" if delta is not None else "—"
    conclusion = (
        f"{stats['groups']}개 그룹 중 {stats['pairedCompleted']}개에서 수정·재평가가 완료됐습니다. "
        f"완료된 동일 표본의 평균은 {num(stats['beforeMeanPaired'])} → {num(stats['afterMeanPaired'])}입니다. "
        f"점수 상승 {stats['scoreImproved']}개, 동일 {stats['scoreUnchanged']}개, 하락 {stats['scoreDeclined']}개이며 "
        f"종합 verdict가 개선된 그룹은 {stats['verdictImproved']}개입니다."
    )
    assessment = (
        "그룹 전체 PASS 통과율 개선은 확인되지 않았습니다. 일부 문장과 개별 기준의 개선을 전체 품질 개선으로 확대 해석하지 않습니다."
        if pass_stats["afterPass"] <= pass_stats["beforePass"] else
        "이 표본에서는 그룹 전체 PASS 통과율이 상승했습니다. 실제 수정 내용과 남은 경고를 함께 확인해야 합니다."
    )
    sample_note = (
        f"최초 분포: {dict(stats['initialVerdicts'])}. "
        + ("최초 FAIL 표본이 없어 FAIL → WARN/PASS 개선은 이번 실행에서 검증하지 못했습니다. "
           if not stats["initialVerdicts"].get("FAIL") else "")
        + f"재평가 완료 그룹에서 PASS로 전환된 기준은 {stats['criteriaToPass']}개, "
        f"기존 PASS에서 다른 판정으로 바뀐 기준은 {stats['criteriaFromPass']}개입니다."
    )
    methodology = (
        f"평가 단위는 그룹 전체이며 {stats['groups']}개 그룹 / {stats['scenarios']}개 시나리오입니다. "
        f"평가 결과를 보기 전 적격 {manifest['eligibleCount']}개 중 seed={manifest['seed']}로 무작위 비복원 추출했습니다. "
        "명시적인 검증용·가상 데이터 및 구조상 실행 불가 자료만 사전 제외했습니다. "
        "현재 저장된 내용을 복사해 Signpost 전 단계로 재현했으며, 신규 시나리오 생성 실험은 아닙니다. "
        "실제 DB는 조회 전용이며 모든 수정·평가 저장은 프로세스별 메모리 SQLite에서 수행했습니다. "
        "PASS/NEEDS_FACT는 자동 수정하지 않고, WARN/FAIL도 한 번만 수정합니다. "
        "평균 변화는 최초·재평가가 모두 성공한 동일 그룹 쌍만 계산하며, 제외/실패도 전체 표에 남깁니다."
        " '평가를 하지 않았을 때'의 통과율은 피드백을 적용하지 않은 원본을 최초 평가한 값입니다. "
        "평가 자체가 내용을 개선하는 것이 아니라 평가→수정→재평가 과정의 효과를 비교합니다."
    )
    limitations = (
        "실제 변경은 저장 전후 JSON과 수정 경로로 확인합니다. 평가 개선은 동일 루브릭의 LLM 판정으로 확인하며 "
        "외부 사실의 진실성이나 일반적인 품질 향상을 독립적으로 증명하는 실험은 아닙니다. "
        "평가와 수정은 같은 모델 계열을 사용하며, 반복 평가의 변동성과 대조군 부재가 있습니다. "
        "점수가 올라가도 미해결 경고가 남을 수 있고, 제안 생성만으로 실제 반영됐다고 계산하지 않습니다. "
        "최초 WARN/FAIL 항목이 재평가에서 PASS로 바뀐 경우만 ‘기준별 PASS 전환’으로 표시합니다."
    )
    svg = score_chart(cases)
    (output / "score_comparison.svg").write_text(svg, encoding="utf-8")
    pass_svg = pass_chart(pass_stats)
    (output / "pass_rates.svg").write_text(pass_svg, encoding="utf-8")
    transition_rows = "".join(
        f"<tr><td>{badge(r['before'])}</td><td>{badge(r['after'])}</td><td>{r['count']}</td></tr>"
        for r in pass_stats["transitions"]
    )
    highlights = []
    for case in sorted(cases, key=lambda c: c["delta"] or 0, reverse=True):
        if not case["completed"] or not case["convertedCriteria"]:
            continue
        plan = (case["plan"] or {}).get("changes", [])
        match = next(
            (
                change
                for change in case["changes"]
                if any(p["path"] == change["path"] and p["judgeId"] in case["convertedCriteria"] for p in plan)
                and any(word in change["path"] for word in ("rationale", "narrative", "description", "summary"))
            ),
            None,
        )
        if match:
            highlights.append(
                f'<h3><a href="#group-{case["groupId"]}">그룹 {case["groupId"]}</a> · '
                f"{num(case['before']['averageScore'])} → {num(case['after']['averageScore'])}</h3>"
                + change_cards({**case, "changes": [match]}),
            )
        if len(highlights) == 3:
            break
    html = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>시나리오 품질 개선 검증 · {stats["groups"]}개 그룹</title><style>{CSS}</style></head><body><main>
<header><span class="eyebrow">SCENARIO QUALITY · EVIDENCE REPORT</span><h1>평가에서 수정으로,<br>시나리오 품질은 얼마나 달라졌나</h1>
<p>{h(conclusion)}</p><span class="pill">{stats["groups"]} GROUPS · {stats["scenarios"]} SCENARIOS</span>
 <span class="pill">수정 최대 1회</span> <span class="pill">실제 DB 쓰기 0</span><p class="meta">{generated}</p></header>
<div class="note" style="margin-top:24px"><b>실험 결론</b> · {h(assessment)}<p>{h(sample_note)}</p></div>
<div class="kpis"><div class="kpi"><span>완료 쌍의 평균 점수 변화</span><strong>{hero_delta}</strong><small>{num(stats["beforeMeanPaired"])} → {num(stats["afterMeanPaired"])} / 5점</small></div>
<div class="kpi"><span>종합 판정 개선</span><strong>{stats["verdictImproved"]} / {stats["pairedCompleted"]}</strong><small>재평가 완료 그룹 기준</small></div>
<div class="kpi"><span>수정·재평가 완료</span><strong>{stats["pairedCompleted"]} / {stats["repairAttempted"]}</strong><small>자동 수정 시도 그룹 기준</small></div>
<div class="kpi"><span>실제 변경 필드</span><strong>{stats["changedFields"]}</strong><small>입력 JSON 비교 · narrative 별칭 중복 제외</small></div></div>
<section class="panel"><span class="eyebrow">PASS RATE · SAME COHORT</span><h2>피드백 수정 전 → 적용 후 통과율</h2>
<div class="compare"><div><h3>그룹 전체 PASS</h3><h2>{pass_stats["beforeRate"]:.1f}% → {pass_stats["afterRate"]:.1f}%</h2>
<p>{pass_stats["beforePass"]}/{stats["groups"]} → {pass_stats["afterPass"]}/{stats["groups"]}개 · {pass_stats["changePercentagePoints"]:+.1f}%p</p></div>
<div><h3>7개 평가 기준 PASS</h3><h2>{pass_stats["criteriaBeforeRate"]:.1f}% → {pass_stats["criteriaAfterRate"]:.1f}%</h2>
<p>{pass_stats["criteriaBeforePass"]} → {pass_stats["criteriaAfterPass"]} / {pass_stats["criteriaDenominator"]}개 기준</p></div></div>
<p>통과는 PASS만 집계합니다. 최초 PASS 등 수정 미대상 {pass_stats["retainedOriginal"]}개는 원본 판정을 유지하고,
수정·재평가 실패도 전체 {stats["groups"]}개 분모에 남겨 통과로 계산하지 않습니다. 최종 판정 확인 가능 {pass_stats["finalKnown"]}개.</p>
<div class="note">재평가 완료 그룹만 비교하면 기준별 PASS는
{pass_stats["pairedCriteriaBeforePass"]} → {pass_stats["pairedCriteriaAfterPass"]} / {pass_stats["pairedCriteriaDenominator"]}개입니다.
전체 실행 기준 통과율에는 실패로 확인하지 못한 기준도 포함됩니다. 따라서 전체 비율의 감소를 곧바로 내용의 악화로 해석하지 않습니다.</div>
<div class="table-wrap">{pass_svg}</div><details><summary>판정 전환 및 기술 통계</summary>
<table><thead><tr><th>원본</th><th>적용 후</th><th>그룹 수</th></tr></thead><tbody>{transition_rows}</tbody></table>
<p>완료 쌍 점수 변화 · 중앙값 {num(pass_stats["deltaMedian"])} · 표본 표준편차 {num(pass_stats["deltaStdDev"])}
 · 범위 {num(pass_stats["deltaMin"])} ~ {num(pass_stats["deltaMax"])}</p>
<p class="meta">그룹 통과율 Wilson 95% 구간: 원본 {h(pass_stats["beforeWilson95"])}% → 적용 후 {h(pass_stats["afterWilson95"])}%.
작은 표본의 불확실성을 나타내는 이항 근사이며, 전후 차이의 통계적 유의성을 뜻하지 않습니다.
그룹 내 7개 기준은 독립 표본이 아닙니다.</p></details></section>
<section class="panel"><h2>{stats["groups"]}개 그룹의 전후 결과</h2><p class="meta">회색 빈 점: 최초 · 채운 점: 재평가 · ‘—’: 재평가 결과 없음. 점수와 verdict는 별개 지표입니다.</p>
<div class="table-wrap">{svg}</div><div class="table-wrap"><table><thead><tr><th>그룹</th><th>제목</th><th>시나리오</th><th>최초</th><th>재평가</th><th>Δ점수</th><th>변경</th><th>실행 결과</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div></section>
<section class="panel"><span class="eyebrow">TEXTUAL EVIDENCE</span><h2>실제 내용이 달라진 사례</h2>
<p class="meta">재평가 완료 사례 중 해당 기준이 PASS로 전환된 실제 변경만 발췌합니다. 점수 상승순 최대 3개이며 전체 표본은 위 표에 모두 포함합니다.</p>
{"".join(highlights) or "<p>기준 PASS 전환과 연결된 실제 수정 사례 없음.</p>"}</section>
<section class="panel"><h2>실험 조건과 해석</h2><p>{h(methodology)}</p><p class="meta">평가 {h(manifest["promptVersion"])} · 수정 {h(manifest["repairPromptVersion"])}
 · 실제 응답 모델 {h(stats["models"])} · LLM 호출 {stats["llmCalls"]}회</p><div class="note">{h(limitations)}</div>
<p><a href="manifest.json">표본 선정 기록</a> · <a href="comparison.json">집계 JSON</a> · <a href="report.md">Markdown 보고서</a> · <a href="score_comparison.svg">점수 SVG</a> · <a href="pass_rates.svg">통과율 SVG</a></p></section>
<h2>그룹별 근거와 실제 수정 내용</h2><div class="controls"><input id="search" placeholder="그룹 ID 또는 제목 검색" aria-label="그룹 검색">
<select id="filter" aria-label="개선 여부 필터"><option value="all">모든 그룹</option><option value="yes">점수 또는 판정 개선</option><option value="no">개선 없음·미완료</option></select></div>
{"".join(group_card(case) for case in cases)}<footer>평가값·수정 전후 본문은 실행 산출물에서 자동 구성했습니다. 실제 DB 데이터는 변경하지 않았습니다.</footer></main>
<script>function filterGroups(){{const q=document.getElementById('search').value.toLowerCase();const f=document.getElementById('filter').value;
document.querySelectorAll('.group').forEach(e=>e.classList.toggle('hidden',!e.dataset.search.toLowerCase().includes(q)||(f!=='all'&&e.dataset.improved!==f)));}}
document.getElementById('search').addEventListener('input',filterGroups);document.getElementById('filter').addEventListener('change',filterGroups);
window.addEventListener('beforeprint',()=>document.querySelectorAll('details').forEach(e=>e.open=true));</script></body></html>"""
    (output / "report.html").write_text(html, encoding="utf-8")
    lines = [
        "# 시나리오 품질 개선 검증 보고서",
        "",
        generated,
        "",
        conclusion,
        "", assessment, "", sample_note,
        "",
        "## 실험 조건",
        "",
        methodology,
        "",
        f"- 실제 응답 모델: {', '.join(stats['models'])}",
        f"- 평가/수정 버전: {manifest['promptVersion']} / {manifest['repairPromptVersion']}",
        "",
        "## 전체 비교",
        "",
        "| 그룹 | 시나리오 수 | 최초 점수 / verdict | 재평가 점수 / verdict | 점수 변화 | 실제 변경 필드 | 결과 |",
        "|---|---:|---|---|---:|---:|---|",
    ]
    for c in cases:
        a, b = c["before"], c["after"]
        lines.append(
            f"| {c['groupId']} | {c['source']['scenario_count']} | {num(a.get('averageScore'))} / {a.get('verdict', '—')} | "
            f"{num(b.get('averageScore'))} / {b.get('verdict', '—')} | {num(c['delta'])} | {len(c['changes'])} | {c['state']} |",
        )
    lines += ["", "## 해석 범위", "", limitations]
    lines += [
        "",
        *statistics_markdown(pass_stats),
        "![통과율 비교](pass_rates.svg)",
        "",
        "![평균 점수 비교](score_comparison.svg)",
        "",
    ]
    for c in cases:
        lines += [
            "",
            f"## 그룹 {c['groupId']} · {c['source']['title']}",
            "",
            c["state"],
            "",
            f"수정 검증: {text((c['review'] or {}).get('reason', c['failureDetail'] or '미실행'))}",
            "",
            f"수정안의 미해결 사유: {text((c['plan'] or {}).get('unresolved', []))}",
            "",
            f"기준별 PASS 전환: {', '.join(c['convertedCriteria']) or '없음'}",
            "",
            "### 평가 기준별 점수",
            "",
            "| 기준 | 최초 | 재평가 |",
            "|---|---|---|",
        ]
        for key, label in LABELS.items():
            a, b = c["beforeItems"].get(key, {}), c["afterItems"].get(key, {})
            lines.append(
                f"| {key} {label} | {a.get('score', '—')} / {a.get('verdict', '—')} | {b.get('score', '—')} / {b.get('verdict', '—')} |",
            )
        for title, record in (("최초 평가", c["before"]), ("재평가", c["after"])):
            lines += [
                "",
                f"### {title}: 근거·사유·수정 제안",
                "",
                text((record.get("result") or {}).get("summary")),
                "",
            ]
            for item in (record.get("result") or {}).get("items", []):
                for issue in item["violations"]:
                    lines += [
                        f"**{item['judgeId']} {item['verdict']} · 시나리오 {issue['scenarioIds']}**",
                        "",
                        f"- 사유: {issue['reason']}",
                        f"- 근거: {issue['evidence']}",
                        f"- 수정 제안: {issue['suggestedFix']}",
                        f"- 위치: `{issue['evidencePath']}`",
                        "",
                    ]
        lines += ["### 실제 변경 전후", "", "| 필드 | 기존 내용 | 실제 반영 내용 |", "|---|---|---|"]
        for change in c["changes"]:
            lines.append(f"| {md(change['path'])} | {md(change['before'])} | {md(change['after'])} |")
        if not c["changes"]:
            lines.append("| — | 실제 반영된 변경 없음 | — |")
        lines += ["", f"[원본 자료](group_{c['groupId']}/evaluation_1.json)", ""]
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output / "comparison.json").write_text(
        json.dumps(
            {
                "metrics": stats,
                "groups": [
                    {
                        "groupId": c["groupId"],
                        "state": c["state"],
                        "delta": c["delta"],
                        "gradeImproved": c["gradeImproved"],
                        "convertedCriteria": c["convertedCriteria"],
                        "eventsUnchanged": c["eventsUnchanged"],
                        "changes": c["changes"],
                        "beforeScore": c["before"].get("averageScore"),
                        "afterScore": c["after"].get("averageScore"),
                        "beforeVerdict": verdict(c["before"]),
                        "finalVerdict": verdict(final_record(c)),
                    }
                    for c in cases
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
