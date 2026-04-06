from pydantic import BaseModel, Field

from apps.agents.mi_agent.subgraphs.rdb_search.schemas import RDBSearchOutput
from apps.agents.mi_agent.subgraphs.vdb_search.schemas import VDBSearchOutput
from apps.agents.mi_agent.subgraphs.web_search.schemas import WebSearchOutput


class SearchOutput(BaseModel):
    rewritten_query: str = Field(
        default="",
        description="사용자 질의를 LLM에 의해 재작성해 얻은 보완 질의",
    )
    histories: list[dict] | None = Field(default=None, description="대화 히스토리")
    web_search_enabled: bool | None = Field(default=True, description="웹 검색 사용 여부")

    rdb_search_output: RDBSearchOutput | None = Field(default=None, description="RDB검색 결과")
    vdb_search_output: VDBSearchOutput | None = Field(default=None, description="VDB검색 결과")
    web_search_output: WebSearchOutput | None = Field(default=None, description="WEB검색 결과")
