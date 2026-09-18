from __future__ import annotations

from apps.persistence.model_impact_lever.repository import ModelImpactLeverRepository
from apps.persistence.model_impact_lever.schema import ModelImpactLeverPayload
from apps.persistence.model_impact_lever.service import (
    ModelImpactLeverService as SharedModelImpactLeverService,
    resolve_binding_support,
)


_resolve_binding_support = resolve_binding_support


class ModelImpactLeverService:
    def load_display_labels(
        self,
        *,
        catalog_version: str,
        catalog_checksum: str,
    ) -> dict[str, str]:
        """Load labels only when the complete Scenario Group catalog pin is current."""
        from apps.common.configs.database.sync_database.connection import get_sync_session

        requested_version = catalog_version.strip()
        requested_checksum = catalog_checksum.strip()
        if not requested_version or not requested_checksum:
            return {}
        session = get_sync_session()
        try:
            _catalog, active_version, active_checksum = SharedModelImpactLeverService(
                session=session,
            ).load_active_catalog(catalog_version=requested_version)
            if active_version != requested_version or active_checksum != requested_checksum:
                return {}
            return ModelImpactLeverRepository(session=session).fetch_display_labels(
                catalog_version=requested_version,
            )
        finally:
            session.close()

    def load_active_catalog(
        self,
        *,
        catalog_version: str,
    ) -> tuple[list[ModelImpactLeverPayload], str, str]:
        return SharedModelImpactLeverService().load_active_catalog(
            catalog_version=catalog_version,
        )
