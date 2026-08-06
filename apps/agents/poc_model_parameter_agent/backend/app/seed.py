from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import session_scope
from app.models import AssetVersion
from app.schemas.seed import SeedDocument


def load_seed_document(path: Path | None = None) -> SeedDocument:
    seed_path = path or get_settings().seed_path
    return SeedDocument.model_validate_json(seed_path.read_text(encoding="utf-8"))


def stable_content_hash(content_json: dict[str, Any] | None, content_text: str | None) -> str:
    payload = content_text if content_text is not None else json.dumps(content_json, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _asset_specs(seed: SeedDocument) -> list[dict[str, Any]]:
    return [
        {
            "asset_type": "flow_profile",
            "asset_key": seed.flow_profile["assetKey"],
            "version": 1,
            "content_json": seed.flow_profile,
            "learnable": False,
            "locked": True,
            "active": True,
        },
        {
            "asset_type": "lever_catalog",
            "asset_key": "lng_levers",
            "version": 1,
            "content_json": seed.levers,
            "learnable": False,
            "locked": True,
            "active": True,
        },
        {
            "asset_type": "parameter_catalog",
            "asset_key": "lng_parameters",
            "version": 1,
            "content_json": seed.parameters,
            "learnable": False,
            "locked": True,
            "active": True,
        },
        {
            "asset_type": "mapping_catalog",
            "asset_key": "lng_parameter_mappings",
            "version": 1,
            "content_json": {"mappings": seed.mappings},
            "learnable": False,
            "locked": True,
            "active": True,
        },
        {
            "asset_type": "dimension_rule",
            "asset_key": "lng_dimension_rules",
            "version": 1,
            "content_json": seed.dimension_rules,
            "learnable": False,
            "locked": True,
            "active": True,
        },
        {
            "asset_type": "domain_rule",
            "asset_key": "lng_domain_rules",
            "version": 1,
            "content_json": {"rules": seed.domain_rules},
            "learnable": False,
            "locked": True,
            "active": True,
        },
        {
            "asset_type": "evaluation_case",
            "asset_key": "lng_pressure_bands",
            "version": 1,
            "content_json": {"pressureBands": seed.pressure_bands},
            "learnable": False,
            "locked": True,
            "active": True,
        },
        {
            "asset_type": "memory",
            "asset_key": "default_memory",
            "version": 1,
            "content_text": seed.memory_v1,
            "learnable": True,
            "locked": False,
            "active": False,
        },
        {
            "asset_type": "memory",
            "asset_key": "default_memory",
            "version": 2,
            "content_text": seed.memory_v2,
            "learnable": True,
            "locked": False,
            "active": True,
        },
        {
            "asset_type": "skill",
            "asset_key": "scenario_parameter_skill",
            "version": 1,
            "content_text": seed.skill_v1,
            "learnable": True,
            "locked": False,
            "active": True,
        },
    ]


def seed_assets(session: Session, seed: SeedDocument | None = None) -> dict[str, int]:
    document = seed or load_seed_document()
    inserted = 0
    skipped = 0
    for spec in _asset_specs(document):
        identity = (spec["asset_type"], spec["asset_key"], spec["version"])
        existing = session.scalar(
            select(AssetVersion).where(
                AssetVersion.asset_type == identity[0],
                AssetVersion.asset_key == identity[1],
                AssetVersion.version == identity[2],
            )
        )
        if existing is not None:
            skipped += 1
            continue
        content_json = spec.get("content_json")
        content_text = spec.get("content_text")
        session.add(
            AssetVersion(
                asset_version_id=str(uuid.uuid4()),
                content_hash=stable_content_hash(content_json, content_text),
                content_json=content_json,
                content_text=content_text,
                **{key: value for key, value in spec.items() if key not in {"content_json", "content_text"}},
            )
        )
        inserted += 1
    session.flush()
    return {"inserted": inserted, "skipped": skipped}


def main() -> None:
    with session_scope() as session:
        result = seed_assets(session)
    logger.info("Asset seed completed: {}", result)


if __name__ == "__main__":
    main()
