#   apps/common/values/enums.py

from enum import StrEnum


class ModelPreference(StrEnum):
    QUALITY = "quality"
    SPEED = "speed"


class SemaphoreName(StrEnum):
    HTTP = "HTTP"
    LLM = "LLM"
