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
_DEFAULT_PROVIDER = "LSEG"
_OMDIA_PROVIDER = "OMDIA"


@lru_cache(maxsize=None)
def _load_yaml_raw(provider: str) -> dict:
    path = _CONFIGS_DIR / f"{provider}.yaml"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_retrieval_options(provider: str | None) -> RetrievalOptions:
    provider_name = provider or _DEFAULT_PROVIDER
    defaults = dict(_load_yaml_raw(provider_name))
    if provider_name == _OMDIA_PROVIDER:
        overrides = _load_yaml_raw(provider_name)
        for field in _PROVIDER_FIELDS:
            if field in overrides:
                defaults[field] = overrides[field]
    return RetrievalOptions(**defaults)
