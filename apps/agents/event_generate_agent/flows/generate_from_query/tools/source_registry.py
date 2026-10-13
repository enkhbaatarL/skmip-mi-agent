"""웹 검색 1차 대상 도메인을 정의한 source registry 를 읽는 툴.

registry(`resources/source_registry.json`)는 신뢰도 높은 공식·1차 자료 출처 목록이다.
search_web 은 여기 모인 도메인으로 먼저 검색하고, 근거가 비면 도메인 제한 없이 다시 검색한다.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

from apps.common.logging.logger_config import logger


SOURCE_REGISTRY_PATH = Path(__file__).resolve().parents[3] / "resources" / "source_registry.json"


class SourceEntry(BaseModel, frozen=True):
    source_id: str
    domains: list[str] = Field(default_factory=list)
    type: str = ""
    default_priority: int = 0


class SourceRegistry(BaseModel, frozen=True):
    registry_version: str = ""
    sources: list[SourceEntry] = Field(default_factory=list)

    @property
    def domains(self) -> list[str]:
        """등록된 모든 도메인. 등록 순서를 유지하고 중복은 제거"""
        seen: set[str] = set()
        unique: list[str] = []
        for source in self.sources:
            for raw_domain in source.domains:
                domain = raw_domain.strip().lower()
                if domain and domain not in seen:
                    seen.add(domain)
                    unique.append(domain)
        return unique


@lru_cache(maxsize=1)
def load_source_registry() -> SourceRegistry:
    """Registry 파일을 1회 읽어 캐싱"""
    registry = SourceRegistry.model_validate_json(SOURCE_REGISTRY_PATH.read_text(encoding="utf-8"))
    logger.info(
        f"[TOOL][load_source_registry] LOADED | version={registry.registry_version} "
        f"| sources={len(registry.sources)} | domains={len(registry.domains)}",
    )
    return registry


def registry_domains() -> list[str]:
    """1차 검색에 쓸 도메인 목록. registry 를 읽지 못하면 빈 목록(=도메인 제한 없음)을 반환"""
    try:
        return load_source_registry().domains
    except Exception:
        # registry 는 검색 범위를 좁히는 보조 설정이다. 읽지 못해도 검색 자체는 계속한다.
        logger.exception(f"[TOOL][registry_domains] LOAD_FAILED | path={SOURCE_REGISTRY_PATH}")
        return []
