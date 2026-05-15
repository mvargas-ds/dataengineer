"""
Web Search Tool
===============
Tool for searching the web for academic papers, news, and reports
about depopulation in Spain.

Uses Tavily for web search and scholarly for academic papers.
"""

import os
from typing import Optional, List, Dict
from langchain.tools import tool
from pydantic import BaseModel, Field
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


class WebSearchTool:
    """
    Tool for web search including academic papers.
    """

    def __init__(self):
        self.tavily_key = os.getenv('TAVILY_API_KEY')

    def search_web(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Search the web using Tavily API.

        Args:
            query: Search query
            max_results: Maximum number of results
        """
        if not self.tavily_key:
            return self._fallback_search(query)

        try:
            from tavily import TavilyClient

            client = TavilyClient(api_key=self.tavily_key)
            response = client.search(
                query=query,
                search_depth="advanced",
                max_results=max_results,
                include_domains=["ine.es", "csic.es", "edu", "gov.es", "scholar.google"]
            )

            results = []
            for item in response.get('results', []):
                results.append({
                    'title': item.get('title', ''),
                    'url': item.get('url', ''),
                    'content': item.get('content', '')[:500],
                    'score': item.get('score', 0)
                })

            return results

        except Exception as e:
            logger.error(f"Tavily search error: {e}")
            return self._fallback_search(query)

    def _fallback_search(self, query: str) -> List[Dict]:
        """
        Fallback search when Tavily is not available.
        Returns guidance on where to search manually.
        """
        return [{
            'title': 'Manual Search Recommended',
            'url': f'https://www.google.com/search?q={query.replace(" ", "+")}',
            'content': f'Tavily API not configured. Search manually for: {query}',
            'score': 0
        }]

    def search_academic_papers(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Search for academic papers using Google Scholar.

        Args:
            query: Search query
            max_results: Maximum number of papers
        """
        try:
            from scholarly import scholarly

            search_query = scholarly.search_pubs(query)

            papers = []
            for i, paper in enumerate(search_query):
                if i >= max_results:
                    break

                bib = paper.get('bib', {})
                papers.append({
                    'title': bib.get('title', 'Unknown'),
                    'authors': ', '.join(bib.get('author', ['Unknown'])),
                    'year': bib.get('pub_year', 'Unknown'),
                    'venue': bib.get('venue', 'Unknown'),
                    'abstract': bib.get('abstract', '')[:300] if bib.get('abstract') else '',
                    'citations': paper.get('num_citations', 0),
                    'url': paper.get('pub_url', '')
                })

            return papers

        except Exception as e:
            logger.error(f"Scholar search error: {e}")
            return [{
                'title': 'Search Error',
                'authors': '',
                'year': '',
                'abstract': f'Could not search academic papers: {str(e)}',
                'url': f'https://scholar.google.com/scholar?q={query.replace(" ", "+")}'
            }]

    def search_dialnet(self, query: str) -> List[Dict]:
        """
        Search Dialnet (Spanish academic database).
        Note: Dialnet doesn't have a public API, returns search URL.
        """
        search_url = f"https://dialnet.unirioja.es/buscar/documentos?querysDismax.DOCUMENTAL_TODO={query.replace(' ', '+')}"

        return [{
            'title': f'Dialnet Search: {query}',
            'url': search_url,
            'content': 'Search Dialnet for Spanish academic publications on this topic.',
            'source': 'dialnet'
        }]


# LangChain Tool Definitions
class WebSearchInput(BaseModel):
    """Input schema for web search tool."""
    query: str = Field(
        description="Search query (e.g., 'despoblación rural España causas')"
    )
    search_type: str = Field(
        default="web",
        description="""Type of search:
        - 'web': General web search (news, reports, government sites)
        - 'academic': Academic papers from Google Scholar
        - 'spanish_academic': Spanish academic sources (Dialnet)
        - 'all': Search all sources
        """
    )
    max_results: int = Field(
        default=5,
        description="Maximum number of results to return"
    )


@tool("search_web", args_schema=WebSearchInput)
def search_web(
    query: str,
    search_type: str = "web",
    max_results: int = 5
) -> str:
    """
    Search the web and academic sources for information about Spanish depopulation.

    Use this tool when you need:
    - Recent news and reports about rural depopulation
    - Academic papers and research on "España vaciada"
    - Government reports and policy documents
    - Smart city initiatives for repopulation

    Supports general web search and academic paper search.
    """
    tool = WebSearchTool()
    results = []

    try:
        if search_type in ['web', 'all']:
            web_results = tool.search_web(query, max_results)
            results.extend([('Web', r) for r in web_results])

        if search_type in ['academic', 'all']:
            academic_results = tool.search_academic_papers(query, max_results)
            results.extend([('Academic', r) for r in academic_results])

        if search_type in ['spanish_academic', 'all']:
            dialnet_results = tool.search_dialnet(query)
            results.extend([('Dialnet', r) for r in dialnet_results])

        if not results:
            return f"No results found for: {query}"

        # Format output
        output = f"## Search Results for: '{query}'\n\n"

        current_type = None
        for source_type, item in results:
            if source_type != current_type:
                output += f"\n### {source_type} Results\n\n"
                current_type = source_type

            if 'authors' in item:  # Academic paper
                output += f"**{item['title']}**\n"
                output += f"- Authors: {item['authors']}\n"
                output += f"- Year: {item['year']}\n"
                if item.get('citations'):
                    output += f"- Citations: {item['citations']}\n"
                if item.get('abstract'):
                    output += f"- Abstract: {item['abstract']}...\n"
                output += f"- URL: {item.get('url', 'N/A')}\n\n"
            else:  # Web result
                output += f"**{item['title']}**\n"
                output += f"- URL: {item['url']}\n"
                if item.get('content'):
                    output += f"- Summary: {item['content'][:200]}...\n"
                output += "\n"

        return output

    except Exception as e:
        return f"Error performing search: {str(e)}"


# Specialized search function for depopulation topics
@tool("search_depopulation_research")
def search_depopulation_research(topic: str) -> str:
    """
    Search for academic research specifically about Spanish rural depopulation.

    Use this for:
    - Academic papers on "España vaciada"
    - Research on rural-urban migration in Spain
    - Studies on repopulation strategies
    - Smart village/city initiatives

    Args:
        topic: Specific aspect of depopulation (e.g., "causas", "soluciones", "smart villages")
    """
    search_queries = {
        'causas': 'causas despoblación rural España factores',
        'soluciones': 'soluciones despoblación rural repoblación estrategias España',
        'smart_village': 'smart village pueblo inteligente España rural',
        'migracion': 'migración rural urbana España jóvenes',
        'envejecimiento': 'envejecimiento población rural España',
        'empleo': 'empleo rural teletrabajo España despoblación',
        'servicios': 'servicios públicos zonas rurales España despoblación',
        'general': 'españa vaciada despoblación rural investigación'
    }

    query = search_queries.get(topic.lower(), f'despoblación rural España {topic}')

    # Use the main search tool
    return search_web(query, search_type='all', max_results=5)

