from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.errors import ServiceUnavailableAppError
from app.models import AssetVersion
from app.schemas.seed import SeedDocument

REQUIRED_RUNTIME_ASSETS: tuple[tuple[str, str], ...] = (
    ("flow_profile", "lng_scenario_to_parameter_v1"),
    ("lever_catalog", "lng_levers"),
    ("parameter_catalog", "lng_parameters"),
    ("mapping_catalog", "lng_parameter_mappings"),
    ("dimension_rule", "lng_dimension_rules"),
    ("domain_rule", "lng_domain_rules"),
    ("evaluation_case", "lng_pressure_bands"),
    ("memory", "default_memory"),
    ("skill", "scenario_parameter_skill"),
)


def missing_runtime_assets(snapshot: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for asset_type, asset_key in REQUIRED_RUNTIME_ASSETS:
        snapshot_key = f"{asset_type}:{asset_key}"
        value = snapshot.get(snapshot_key)
        if (
            not isinstance(value, dict)
            or value.get("assetType") != asset_type
            or value.get("assetKey") != asset_key
            or not isinstance(value.get("version"), int)
            or not value.get("contentHash")
        ):
            missing.append(snapshot_key)
    return missing


def active_assets(session: Session, for_update: bool = False) -> list[AssetVersion]:
    statement: Select[tuple[AssetVersion]] = select(AssetVersion).where(AssetVersion.active.is_(True))
    if for_update:
        statement = statement.with_for_update()
    return list(session.scalars(statement.order_by(AssetVersion.asset_type, AssetVersion.asset_key)))


def asset_snapshot(session: Session) -> dict[str, Any]:
    return {
        f"{asset.asset_type}:{asset.asset_key}": {
            "assetType": asset.asset_type,
            "assetKey": asset.asset_key,
            "version": asset.version,
            "contentHash": asset.content_hash,
        }
        for asset in active_assets(session)
    }


def seed_for_snapshot(session: Session, snapshot: dict[str, Any], fallback: SeedDocument) -> SeedDocument:
    """Rebuild runtime catalogs from the exact asset versions captured by a Run."""
    missing = missing_runtime_assets(snapshot)
    if missing:
        raise ServiceUnavailableAppError(
            "필수 Active Asset Version Snapshot이 완전하지 않습니다.",
            {"missingAssets": missing, "seedRequired": True},
        )
    assets: dict[tuple[str, str], AssetVersion] = {}
    for asset_type, asset_key in REQUIRED_RUNTIME_ASSETS:
        value = snapshot[f"{asset_type}:{asset_key}"]
        asset_type = str(value.get("assetType") or "")
        asset_key = str(value.get("assetKey") or "")
        version = value.get("version")
        row = session.scalar(
            select(AssetVersion).where(
                AssetVersion.asset_type == asset_type,
                AssetVersion.asset_key == asset_key,
                AssetVersion.version == version,
            )
        )
        if row is None or row.content_hash != value.get("contentHash"):
            raise ServiceUnavailableAppError(
                "Snapshot이 가리키는 Asset Version을 복원할 수 없습니다.",
                {
                    "assetType": asset_type,
                    "assetKey": asset_key,
                    "version": version,
                    "contentHash": value.get("contentHash"),
                },
            )
        assets[(asset_type, asset_key)] = row

    def json_content(asset_type: str, asset_key: str) -> dict[str, Any]:
        row = assets.get((asset_type, asset_key))
        if row is None or not isinstance(row.content_json, dict):
            raise ServiceUnavailableAppError(
                "JSON Asset Content가 유효하지 않습니다.",
                {"assetType": asset_type, "assetKey": asset_key},
            )
        return row.content_json

    def text_content(asset_type: str, asset_key: str) -> str:
        row = assets.get((asset_type, asset_key))
        if row is None or not isinstance(row.content_text, str) or not row.content_text.strip():
            raise ServiceUnavailableAppError(
                "Text Asset Content가 유효하지 않습니다.",
                {"assetType": asset_type, "assetKey": asset_key},
            )
        return row.content_text

    mapping_catalog = json_content("mapping_catalog", "lng_parameter_mappings")
    domain_rules = json_content("domain_rule", "lng_domain_rules")
    pressure_bands = json_content("evaluation_case", "lng_pressure_bands")
    runtime = fallback.model_copy(
        update={
            "flow_profile": json_content("flow_profile", "lng_scenario_to_parameter_v1"),
            "levers": json_content("lever_catalog", "lng_levers"),
            "parameters": json_content("parameter_catalog", "lng_parameters"),
            "mappings": mapping_catalog.get("mappings"),
            "dimension_rules": json_content("dimension_rule", "lng_dimension_rules"),
            "domain_rules": domain_rules.get("rules"),
            "pressure_bands": pressure_bands.get("pressureBands"),
            "memory_v2": text_content("memory", "default_memory"),
            "skill_v1": text_content("skill", "scenario_parameter_skill"),
        }
    )
    try:
        return SeedDocument.model_validate(runtime.model_dump(by_alias=True))
    except Exception as exc:
        raise ServiceUnavailableAppError(
            "Snapshot Asset Content가 Runtime Catalog Schema를 만족하지 않습니다.",
            {"error": str(exc)},
        ) from exc


def get_active_asset(
    session: Session, asset_type: str, asset_key: str, for_update: bool = False
) -> AssetVersion | None:
    statement = select(AssetVersion).where(
        AssetVersion.asset_type == asset_type,
        AssetVersion.asset_key == asset_key,
        AssetVersion.active.is_(True),
    )
    if for_update:
        statement = statement.with_for_update()
    return session.scalar(statement)


def list_assets(session: Session) -> list[dict[str, Any]]:
    rows = list(
        session.scalars(
            select(AssetVersion).order_by(AssetVersion.asset_type, AssetVersion.asset_key, AssetVersion.version.desc())
        )
    )
    groups: dict[tuple[str, str], list[AssetVersion]] = defaultdict(list)
    for row in rows:
        groups[(row.asset_type, row.asset_key)].append(row)
    return [
        {
            "assetType": asset_type,
            "assetKey": asset_key,
            "learnable": versions[0].learnable,
            "locked": versions[0].locked,
            "activeVersion": next((item.version for item in versions if item.active), None),
            "versionCount": len(versions),
            "updatedAt": versions[0].updated_at.isoformat(),
        }
        for (asset_type, asset_key), versions in groups.items()
    ]


def asset_to_dict(asset: AssetVersion, include_content: bool = True) -> dict[str, Any]:
    result: dict[str, Any] = {
        "assetVersionId": asset.asset_version_id,
        "assetType": asset.asset_type,
        "assetKey": asset.asset_key,
        "version": asset.version,
        "contentHash": asset.content_hash,
        "learnable": asset.learnable,
        "locked": asset.locked,
        "active": asset.active,
        "sourceCandidateId": asset.source_candidate_id,
        "createdAt": asset.created_at.isoformat(),
    }
    if include_content:
        result["content"] = asset.content_text if asset.content_text is not None else asset.content_json
    return result
