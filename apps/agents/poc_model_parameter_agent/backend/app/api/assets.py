from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import NotFoundAppError
from app.models import AssetVersion
from app.persistence.asset_repository import asset_to_dict, get_active_asset, list_assets

router = APIRouter(tags=["assets"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/assets")
def get_assets(session: DbSession) -> dict[str, object]:
    items = list_assets(session)
    return {"items": items, "total": len(items)}


@router.get("/assets/{asset_type}/{asset_key}")
def get_asset(asset_type: str, asset_key: str, session: DbSession) -> dict[str, object]:
    row = get_active_asset(session, asset_type, asset_key)
    if row is None:
        raise NotFoundAppError("Asset", f"{asset_type}:{asset_key}")
    return asset_to_dict(row)


@router.get("/assets/{asset_type}/{asset_key}/versions")
def get_asset_versions(asset_type: str, asset_key: str, session: DbSession) -> dict[str, object]:
    rows = list(
        session.scalars(
            select(AssetVersion)
            .where(AssetVersion.asset_type == asset_type, AssetVersion.asset_key == asset_key)
            .order_by(AssetVersion.version.desc())
        )
    )
    if not rows:
        raise NotFoundAppError("Asset", f"{asset_type}:{asset_key}")
    return {"items": [asset_to_dict(item) for item in rows], "total": len(rows)}
