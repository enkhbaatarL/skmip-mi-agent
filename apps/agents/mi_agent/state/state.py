from pydantic import Field

from apps.agents.mi_agent.schemas.mari_agent_input import MariAgentInput
from apps.agents.mi_agent.schemas.schemas import TimeSeriesInsights
from apps.agents.mi_agent.schemas.search_output import SearchOutput
from apps.common.values.enums import AnalysisType


class MariAgentState(MariAgentInput):
    user_query_language: str | None = Field(
        default=None,
        description="사용자 입력 질의 언어(영어, 한국어)",
    )
    rewritten_query: str | None = Field(
        default=None,
        description="사용자 질의를 LLM에 의해 재작성해 얻은 보완 질의",
    )
    analysis_type: AnalysisType | None = Field(
        None,
        description="분석 유형",
        examples=["general_request"],
    )
    search_output: SearchOutput = Field(
        default_factory=SearchOutput,
        description="검색 결과",
    )
    analysis_content: str | None = Field(
        default=None,
        description="상세 분석 내용 (검색 결과 기반)",
    )
    suggested_questions: list[str] = Field(
        default_factory=list,
        description="추가로 궁금하실 수 있는 질문들",
    )
    analysis_summary: str | None = Field(
        default=None,
        description="핵심 인사이트 (2-3문장)",
    )
    timeseries_insights: TimeSeriesInsights | None = Field(
        default=None,
        description="시계열 인사이트 (주요 지표, 하이라이트, 차트 포함)",
    )
    current_node: str | None = Field(default=None, description="현재 실행 중인 노드")
    executed_nodes: list[str] | None = Field(
        default_factory=list,
        description="실행된 노드 목록",
    )
    usage: dict | None = Field(default=None, description="LLM 사용량 정보")
