from pydantic import BaseModel, Field


class SearchInput(BaseModel):
    rewritten_query: str = Field(description="사용자 질의를 LLM에 의해 재작성해 얻은 보완 질의")
    histories: list[dict] | None = Field(default=None, description="대화 히스토리")
    web_search_enabled: bool | None = Field(default=True, description="웹 검색 사용 여부")
