from __future__ import annotations

"""Golden-case Markdown parsing for judge recall review.

Matching is deliberately not automated: semantic matching of an expert finding to
a judge violation is a review decision.  The evaluator surfaces both sets, and the
operator records the reviewed outcome through ``--golden-record``.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml


@dataclass(frozen=True)
class GoldenLabel:
    label_id: str
    type: Literal["A", "B", "C", "D"]
    target: str
    expected_judge: str
    note: str
    quote: str | None


@dataclass(frozen=True)
class GoldenCase:
    mi_event_id: int
    scenario_group_id: int | None
    event_title: str
    artifacts: str | None
    labels: list[GoldenLabel]
    path: Path


_REQUIRED_FRONTMATTER = ("mi_event_id", "event_title")
_LABEL_START = "### GC-"


def _frontmatter_and_body(path: Path) -> tuple[dict[str, object], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"Golden case must begin with YAML frontmatter: {path}")
    frontmatter_text, separator, body = text[len("---\n") :].partition("\n---\n")
    if not separator:
        raise ValueError(f"Golden case has unclosed YAML frontmatter: {path}")
    loaded = yaml.safe_load(frontmatter_text)
    if not isinstance(loaded, dict):
        raise ValueError(f"Golden case frontmatter must be a mapping: {path}")
    missing = [key for key in _REQUIRED_FRONTMATTER if not loaded.get(key)]
    if missing:
        raise ValueError(f"Golden case missing frontmatter {missing}: {path}")
    return loaded, body


def _parse_label_block(label_id: str, block: str, path: Path) -> GoldenLabel:
    fields: dict[str, str] = {}
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line.startswith("-") or ":" not in line:
            continue
        key, value = line[1:].split(":", 1)
        fields[key.strip()] = value.strip()

    required = ("type", "target", "expected_judge", "지적")
    missing = [field for field in required if not fields.get(field)]
    if missing:
        raise ValueError(f"Golden label {label_id} missing {missing}: {path}")
    label_type = fields["type"]
    if label_type not in {"A", "B", "C", "D"}:
        raise ValueError(f"Golden label {label_id} has invalid type {label_type!r}: {path}")
    return GoldenLabel(
        label_id=label_id,
        type=label_type,  # type: ignore[arg-type]
        target=fields["target"],
        expected_judge=fields["expected_judge"],
        note=fields["지적"],
        quote=fields.get("인용"),
    )


def _parse_labels(body: str, path: Path) -> list[GoldenLabel]:
    blocks = body.split(_LABEL_START)
    labels: list[GoldenLabel] = []
    for block in blocks[1:]:
        heading, separator, remainder = block.partition("\n")
        if not separator:
            raise ValueError(f"Golden label has no body: {path}")
        label_id = "GC-" + heading.strip()
        label_body = remainder.split(_LABEL_START, 1)[0]
        labels.append(_parse_label_block(label_id, label_body, path))
    if not labels:
        raise ValueError(f"Golden case has no GC-xx labels: {path}")
    return labels


def _as_optional_int(value: object, field: str, path: Path) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(str(value))
    except ValueError as exc:
        raise ValueError(f"Golden case {field} must be an integer: {path}") from exc


def load_golden_cases(dir_: Path) -> list[GoldenCase]:
    """Load every version-controlled ``gc_*.md`` case in deterministic order."""
    if not dir_.exists():
        return []
    cases: list[GoldenCase] = []
    for path in sorted(dir_.glob("gc_*.md")):
        frontmatter, body = _frontmatter_and_body(path)
        event_id = _as_optional_int(frontmatter["mi_event_id"], "mi_event_id", path)
        if event_id is None:
            raise ValueError(f"Golden case mi_event_id cannot be empty: {path}")
        cases.append(
            GoldenCase(
                mi_event_id=event_id,
                scenario_group_id=_as_optional_int(frontmatter.get("scenario_group_id"), "scenario_group_id", path),
                event_title=str(frontmatter["event_title"]),
                artifacts=str(frontmatter["artifacts"]) if frontmatter.get("artifacts") else None,
                labels=_parse_labels(body, path),
                path=path,
            )
        )
    return cases


def find_incidental_matches(event_ids: list[int], cases: list[GoldenCase]) -> list[GoldenCase]:
    """Return cases that share an evaluated event ID; no matching judgment is made."""
    event_id_set = set(event_ids)
    return [case for case in cases if case.mi_event_id in event_id_set]
