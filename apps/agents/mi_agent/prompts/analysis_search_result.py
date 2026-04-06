"""분석 프롬프트 모듈.

복잡한 로직이 필요하므로 builders/analysis.py에서 구현을 가져옵니다.
"""
from apps.agents.mi_agent.prompts.builders.analysis import build_analysis_prompt

__all__ = ["build_analysis_prompt"]
