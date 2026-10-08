"""Build workshop workspaces: verbatim guide prompts + event markdowns + 00_input template.

Usage:
  poetry run python build_workshop_workspace.py --events-dir DIR --out-dir OUT/workshop --as-of 2026-10-01
      [--runs 3] [--catalog platform|guide] [--catalog-version v4]
      [--guide /Users/a10093/projects/2604_SKGAS/AI_Friday/20260828_실습/lng_scenario_workshop_guide_v4_final.html]

- prompts are extracted from the guide's <pre> blocks into OUT/workshop/prompts/
- --catalog platform (default): replace the template catalog with the DB catalog the platform uses
  (tmm_mi_model_impact_lever_m, applicability_hint = the text the platform prompt shows)
- --catalog guide: keep the guide template catalog as-is
- --runs N creates OUT/workshop/run_01 .. run_N, each an independent workspace
"""

from __future__ import annotations

import argparse
import html
import re
import shutil
import sys
from pathlib import Path

from common import nfc, query

DEFAULT_GUIDE = "/Users/a10093/projects/2604_SKGAS/AI_Friday/20260828_실습/lng_scenario_workshop_guide_v4_final.html"
PROMPT_NAMES = [
    "00a_input_prompt", "00b_input_template", "step1_event_impact", "step2_interactions", "step3_dimensions",
    "step4_scenarios", "step4a_additional", "step5_review", "step6_remediation",
]
EXPECTED_HEADS = {
    "00b_input_template": "# Scenario 생성 입력",
    "step1_event_impact": "당신은 LNG 시장의 Event Impact Analyst다",
    "step5_review": "당신은 Scenario 생성 결과의 검수 전용 Reviewer다",
}


def extract_prompts(guide: Path) -> dict[str, str]:
    raw = guide.read_text(encoding="utf-8")
    blocks = [html.unescape(re.sub(r"<[^>]+>", "", b)) for b in re.findall(r"<pre[^>]*>(.*?)</pre>", raw, re.S)]
    if len(blocks) != len(PROMPT_NAMES):
        raise SystemExit(f"guide has {len(blocks)} <pre> blocks; expected {len(PROMPT_NAMES)} — check the guide version")
    prompts = dict(zip(PROMPT_NAMES, blocks, strict=True))
    for name, head in EXPECTED_HEADS.items():
        if not prompts[name].startswith(head):
            raise SystemExit(f"prompt {name} does not start with {head!r} — guide layout changed")
    return prompts


def platform_catalog(version: str) -> str:
    rows = query(
        "SELECT domain, lever_code, applicability_hint FROM tmm_mi_model_impact_lever_m "
        "WHERE del_yn='N' AND catalog_version=%s "
        "ORDER BY FIELD(domain,'demand','supply','trade','price_only'), lever_code",
        (version,),
    )
    if not rows:
        raise SystemExit(f"catalog_version={version} not found")
    table = "\n".join(f"| {r['domain']} | `{r['lever_code']}` | {r['applicability_hint']} |" for r in rows)
    return (f"## 사용 가능한 Driver Tree Catalog\n### Catalog version\n- {version}\n\n"
            f"| domain | driverTreeCode | 사용 기준 |\n|---|---|---|\n{table}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--as-of", required=True, help="YYYY-MM-DD; also used as the workspace folder date")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--catalog", choices=["platform", "guide"], default="platform")
    parser.add_argument("--catalog-version", default="v4")
    parser.add_argument("--guide", default=DEFAULT_GUIDE)
    args = parser.parse_args()

    out = Path(args.out_dir)
    prompts = extract_prompts(Path(args.guide))
    (out / "prompts").mkdir(parents=True, exist_ok=True)
    for name, text in prompts.items():
        (out / "prompts" / f"{name}.txt").write_text(text, encoding="utf-8")

    template = prompts["00b_input_template"]
    if args.catalog == "platform":
        template = re.sub(r"## 사용 가능한 Driver Tree Catalog.*?(?=\n## 추가 제약)", platform_catalog(args.catalog_version),
                          template, flags=re.S)
    events = [p for p in Path(args.events_dir).glob("*.md") if not nfc(p.name).startswith("0")]
    folder = f"workshop_{args.as_of.replace('-', '')}"
    for index in range(1, args.runs + 1):
        ws = out / f"run_{index:02d}" / folder
        ws.mkdir(parents=True, exist_ok=True)
        for event in events:
            shutil.copy(event, ws / event.name)
        (ws / "00_input.md").write_text(template, encoding="utf-8")
        print(f"workspace: {ws}")
    catalog_line = re.search(r"### Catalog version\n- (\S+)", template)
    print(f"prompts: {out / 'prompts'} | catalog={catalog_line.group(1) if catalog_line else '?'} | events={len(events)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
