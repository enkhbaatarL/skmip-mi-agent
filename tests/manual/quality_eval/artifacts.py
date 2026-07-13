from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import sqlite3
from typing import Any


@dataclass(frozen=True)
class RunArtifacts:
    mi_event_id: int
    scenario_group_id: int | None
    status: str
    step1: dict[str, Any] | None
    step2: dict[str, Any] | None
    step3: dict[str, Any] | None
    step4: dict[str, Any] | None
    event_detail: dict[str, Any] | None


@dataclass(frozen=True)
class BatchArtifacts:
    batch_id: str
    batch_dir: Path
    runs: list[RunArtifacts]


def load_batch(output_root: Path, batch_id: str | None) -> BatchArtifacts:
    """Load a pipeline batch, selecting the newest artifact directory by default."""
    batch_dir = _resolve_batch_dir(output_root, batch_id)
    run_metadata = _load_run_metadata(output_root / "sync_pipeline_metrics.sqlite3", batch_dir.name)
    event_ids = _event_ids(batch_dir, run_metadata)
    runs = [
        RunArtifacts(
            mi_event_id=event_id,
            scenario_group_id=run_metadata.get(event_id, (None, "unknown"))[0],
            status=run_metadata.get(event_id, (None, "unknown"))[1],
            step1=_read_json_dict(batch_dir / f"{event_id}_step1_create_response.json"),
            step2=_read_json_dict(batch_dir / f"{event_id}_step2_validate_response.json"),
            step3=_read_json_dict(batch_dir / f"{event_id}_step3_signposts_response.json"),
            step4=_read_json_dict(batch_dir / f"{event_id}_step4_confirmation_response.json"),
            event_detail=_read_json_dict(batch_dir / f"{event_id}_event_detail.json"),
        )
        for event_id in event_ids
    ]
    return BatchArtifacts(batch_id=batch_dir.name, batch_dir=batch_dir, runs=runs)


def _resolve_batch_dir(output_root: Path, batch_id: str | None) -> Path:
    if batch_id is not None:
        batch_dir = output_root / batch_id
        if not batch_dir.is_dir():
            raise FileNotFoundError(f"Batch directory not found: {batch_dir}")
        return batch_dir
    candidates = _recorded_batch_dirs(output_root)
    if not candidates:
        candidates = _artifact_batch_dirs(output_root)
    if not candidates:
        raise FileNotFoundError(f"No pipeline batch directories found under: {output_root}")
    return max(candidates, key=lambda path: path.name)


def _recorded_batch_dirs(output_root: Path) -> list[Path]:
    """Prefer IDs recorded by the pipeline runner over arbitrary output subdirectories."""
    db_path = output_root / "sync_pipeline_metrics.sqlite3"
    if not db_path.is_file():
        return []
    with sqlite3.connect(db_path) as connection:
        try:
            rows = connection.execute("SELECT DISTINCT batch_id FROM pipeline_runs").fetchall()
        except sqlite3.OperationalError:
            return []
    return [output_root / str(row[0]) for row in rows if row[0] is not None and (output_root / str(row[0])).is_dir()]


def _artifact_batch_dirs(output_root: Path) -> list[Path]:
    """Support copied artifacts without metrics while excluding helper folders such as live_logs."""
    if not output_root.is_dir():
        return []
    batch_id_pattern = re.compile(r"^\d{8}_\d{6}$")
    return [
        path
        for path in output_root.iterdir()
        if path.is_dir() and batch_id_pattern.fullmatch(path.name) and (path / "selected_events.json").is_file()
    ]


def _read_json(path: Path) -> Any:
    if not path.is_file():
        return None
    with path.open(encoding="utf-8") as file:
        payload = json.load(file)
    return payload


def _read_json_dict(path: Path) -> dict[str, Any] | None:
    payload = _read_json(path)
    return payload if isinstance(payload, dict) else None


def _load_run_metadata(db_path: Path, batch_id: str) -> dict[int, tuple[int | None, str]]:
    if not db_path.is_file():
        return {}
    with sqlite3.connect(db_path) as connection:
        try:
            rows = connection.execute(
                "SELECT mi_event_id, scenario_group_id, status FROM pipeline_runs WHERE batch_id = ?",
                (batch_id,),
            ).fetchall()
        except sqlite3.OperationalError:
            return {}
    return {int(event_id): (int(group_id) if group_id is not None else None, str(status)) for event_id, group_id, status in rows}


def _event_ids(batch_dir: Path, run_metadata: dict[int, tuple[int | None, str]]) -> list[int]:
    event_ids = set(run_metadata)
    selected = _read_json(batch_dir / "selected_events.json")
    if isinstance(selected, list):
        for item in selected:
            if isinstance(item, dict) and item.get("mi_event_id") is not None:
                event_ids.add(int(item["mi_event_id"]))
    for path in batch_dir.glob("*_step1_create_response.json"):
        prefix = path.name.removesuffix("_step1_create_response.json")
        if prefix.isdigit():
            event_ids.add(int(prefix))
    return sorted(event_ids)
