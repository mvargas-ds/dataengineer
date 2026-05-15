"""
INE Tool (Instituto Nacional de Estadística)
=============================================
Tool for fetching live data from Spain's National Statistics Institute.

The INE provides APIs and data services for:
- Population statistics
- Economic indicators
- Labor market data
- Regional statistics
"""

import os
from typing import Optional, Dict, Any, List
from langchain.tools import tool
from pydantic import BaseModel, Field
from loguru import logger
import httpx
from bs4 import BeautifulSoup
import json


class INETool:
    """
    Tool for querying INE (Instituto Nacional de Estadística) data.
    Uses both the official INE API and web scraping when needed.
    """

    # INE API Base URLs
    INE_API_BASE = "https://servicios.ine.es/wstempus/js"
    INE_WEB_BASE = "https://www.ine.es"

    # Common INE operation codes
    OPERATION_CODES = {
        'population': '2861',           # Cifras de población
        'continuous_census': '2903',     # Padrón continuo
        'labor_force': '4212',          # EPA (Encuesta Población Activa)
        'gdp_regional': '3010',         # PIB regional
        'cpi': '2501',                  # IPC
        'mortality': '6546',            # Defunciones
        'births': '6566',               # Nacimientos
    }

    def __init__(self):
        self.client = httpx.Client(timeout=30.0)

    def get_operation_data(self, operation_code: str, series_code: Optional[str] = None) -> Dict:
        """
        Fetch data from INE API for a specific operation.

        Args:
            operation_code: INE operation code
            series_code: Specific series within the operation
        """
        try:
            # Get operation metadata
            url = f"{self.INE_API_BASE}/ES/OPERACION/{operation_code}"
            response = self.client.get(url)

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"INE API returned status {response.status_code}")
                return {"error": f"API returned status {response.status_code}"}

        except Exception as e:
            logger.error(f"Error fetching INE data: {e}")
            return {"error": str(e)}

    def search_tables(self, query: str) -> List[Dict]:
        """
        Search for tables in INE that match a query.

        Args:
            query: Search term (e.g., "población municipio", "despoblación")
        """
        try:
            # Search endpoint
            url = f"{self.INE_API_BASE}/ES/DATOS_TABLA"
            params = {"tip": "AM", "nult": 10}  # Get recent data

            response = self.client.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                # Filter results containing the query
                filtered = [
                    item for item in data
                    if query.lower() in str(item).lower()
                ]
                return filtered[:10]  # Limit results

            return []

        except Exception as e:
            logger.error(f"Error searching INE tables: {e}")
            return []

    def get_municipal_population(self, province: Optional[str] = None) -> str:
        """
        Get municipal population data from INE.
        """
        try:
            # Continuous Census data
            url = f"{self.INE_API_BASE}/ES/DATOS_TABLA/2909"
            response = self.client.get(url)

            if response.status_code == 200:
                data = response.json()
                return json.dumps(data[:50], indent=2, ensure_ascii=False)

            return "No data available"

        except Exception as e:
            return f"Error: {str(e)}"

    def scrape_depopulation_news(self) -> List[Dict]:
        """
        Scrape recent news and reports about depopulation from INE.
        """
        try:
            # INE notes de prensa
            url = f"{self.INE_WEB_BASE}/dyngs/INEbase/es/operacion.htm?c=Estadistica_C&cid=1254736176951&menu=ultiDatos&idp=1254735572981"

            response = self.client.get(url)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Extract news items
                news = []
                for item in soup.find_all('div', class_='noticia')[:5]:
                    title = item.find('a')
                    if title:
                        news.append({
                            'title': title.get_text(strip=True),
                            'url': self.INE_WEB_BASE + title.get('href', '')
                        })

                return news

            return []

        except Exception as e:
            logger.error(f"Error scraping INE: {e}")
            return []

    def get_unemployment_data(self, province: Optional[str] = None) -> Dict:
        """
        Get unemployment data from EPA (Encuesta de Población Activa).
        """
        try:
            url = f"{self.INE_API_BASE}/ES/DATOS_TABLA/4212"
            response = self.client.get(url)

            if response.status_code == 200:
                return response.json()

            return {"error": "Could not fetch unemployment data"}

        except Exception as e:
            return {"error": str(e)}

    def close(self):
        """Close the HTTP client."""
        self.client.close()


# LangChain Tool Definition
class INEQueryInput(BaseModel):
    """Input schema for INE query tool."""
    query_type: str = Field(
        description="""Type of INE data to fetch:
        - 'population': Get latest population figures
        - 'unemployment': Get unemployment rates by region
        - 'gdp': Get regional GDP data
        - 'demographics': Get demographic indicators (births, deaths)
        - 'news': Get recent INE news about population/depopulation
        - 'search': Search INE tables for a topic
        """
    )
    search_term: Optional[str] = Field(
        default=None,
        description="Search term when query_type='search' (e.g., 'despoblación', 'municipios')"
    )
    province: Optional[str] = Field(
        default=None,
        description="Filter by province name (optional)"
    )


@tool("query_ine", args_schema=INEQueryInput)
def query_ine(
    query_type: str,
    search_term: Optional[str] = None,
    province: Optional[str] = None
) -> str:
    """
    Query the INE (Instituto Nacional de Estadística) for live Spanish demographic data.

    Use this tool when you need:
    - The most up-to-date population figures
    - Official unemployment rates
    - Regional GDP and economic indicators
    - Recent news and reports about demographics

    This complements the Snowflake data with real-time official statistics.
    """
    tool = INETool()

    try:
        if query_type == 'population':
            result = tool.get_municipal_population(province)
            return f"## INE Population Data\n\n{result}"

        elif query_type == 'unemployment':
            data = tool.get_unemployment_data(province)
            if 'error' in data:
                return f"Error: {data['error']}"
            return f"## INE Unemployment Data\n\n{json.dumps(data[:20], indent=2, ensure_ascii=False)}"

        elif query_type == 'news':
            news = tool.scrape_depopulation_news()
            if not news:
                return "No recent news found."

            result = "## Recent INE News on Demographics\n\n"
            for item in news:
                result += f"- [{item['title']}]({item['url']})\n"
            return result

        elif query_type == 'search' and search_term:
            tables = tool.search_tables(search_term)
            if not tables:
                return f"No INE tables found matching '{search_term}'"

            result = f"## INE Tables matching '{search_term}'\n\n"
            for table in tables:
                result += f"- {json.dumps(table, ensure_ascii=False)}\n"
            return result

        elif query_type == 'demographics':
            # Get multiple demographic indicators
            result = "## INE Demographic Data\n\n"

            births = tool.get_operation_data('6566')
            deaths = tool.get_operation_data('6546')

            result += f"**Births data:** Available operations = {len(births) if isinstance(births, list) else 1}\n"
            result += f"**Deaths data:** Available operations = {len(deaths) if isinstance(deaths, list) else 1}\n"

            return result

        else:
            return f"Unknown query type: {query_type}. Use: population, unemployment, news, search, demographics"

    except Exception as e:
        return f"Error querying INE: {str(e)}"

    finally:
        tool.close()

