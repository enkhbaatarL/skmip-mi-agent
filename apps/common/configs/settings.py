"""Backwards-compatible settings exports. """

from pydantic_settings import BaseSettings

from apps.common.configs.config import Settings, get_settings, settings

__all__ = ["BaseSettings", "Settings", "get_settings", "settings"]