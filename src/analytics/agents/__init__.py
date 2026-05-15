"""
Spain Depopulation Analysis Agent
=================================
LangGraph-based AI agent for analyzing depopulation trends in Spain.

This agent can:
- Query Snowflake data warehouse for population/economic data
- Search INE (Instituto Nacional de Estadística) for live data
- Find academic papers on depopulation
- Analyze factors contributing to depopulation
- Compare historical population trends
"""

from .depopulation_agent import DepopulationAgent
from .graph import create_agent_graph

__all__ = ['DepopulationAgent', 'create_agent_graph']

