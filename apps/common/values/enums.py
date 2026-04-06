from enum import StrEnum


class ModelPreference(StrEnum):
    QUALITY = "quality"
    SPEED = "speed"


class MCPServerCallMode(StrEnum):
    RDB_READ = ("rdb_read",)
    RDB_EXECUTE = ("rdb_execute",)


class SemaphoreName(StrEnum):
    HTTP = "HTTP"
    MCP = "MCP"
    LLM = "LLM"
    RDB_EXEC = "rdb_exec"
    WEB = "web"


class SearchSource(StrEnum):
    RDB = "rdb"
    VDB = "vdb"
    WEB = "web"


class AnalysisType(StrEnum):
    GENERAL_REQUEST = "general_request"
    SINGLE_METRIC = "single_metric"
    TIMESERIES_TREND = "timeseries_trend"
    ITEM_COMPARISON = "item_comparison"
    SIMILARITY_PATTERN = "similarity_pattern"
    MARKET_IMPACT = "market_impact"
    EVENT_IMPACT = "event_impact"
