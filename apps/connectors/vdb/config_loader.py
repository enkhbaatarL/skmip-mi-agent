from __future__ import annotations

from functools import lru_cache
import pathlib

import yaml

from apps.connectors.vdb.schemas import RetrievalOptions


_CONFIGS_DIR = pathlib.Path(__file__).parent / "configs"
_PROVIDER_FIELDS = {
    "retrieval_mode",
    "text_search_fields",
    "semantic_configuration_name",
    "scoring_profile",
    "scoring_parameters",
    "top_k",
}


@lru_cache(maxsize=None)
def _load_yaml_raw(provider: str) -> dict:
    path = _CONFIGS_DIR / f"{provider}.yaml"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_retrieval_options(provider: str | None) -> RetrievalOptions:
    from apps.agents.mi_agent.schemas.mari_agent_input import ContentProvider

    defaults = dict(_load_yaml_raw(provider or ContentProvider.LSEG))
    if provider == ContentProvider.OMDIA:
        overrides = _load_yaml_raw(provider)
        for field in _PROVIDER_FIELDS:
            if field in overrides:
                defaults[field] = overrides[field]
    return RetrievalOptions(**defaults)
