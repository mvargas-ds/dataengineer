"""
Agent Tools
===========
Tools available to the depopulation analysis agent.
"""

from .snowflake_tool import SnowflakeTool, query_snowflake
from .ine_tool import INETool, query_ine
from .web_search_tool import WebSearchTool, search_web
from .analysis_tool import AnalysisTool, analyze_depopulation_factors

__all__ = [
    'SnowflakeTool',
    'query_snowflake',
    'INETool',
    'query_ine',
    'WebSearchTool',
    'search_web',
    'AnalysisTool',
    'analyze_depopulation_factors'
]

