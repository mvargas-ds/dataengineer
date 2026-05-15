"""
Snowflake Tool
==============
Tool for querying the Snowflake data warehouse with population,
depopulation, and industrial data from Spain.

Tables available:
- FACT_DESPOBLAMIENTO: Depopulation indicators by province
- FACT_POBLACION: Population by municipality and sex (1996-2023)
- FACT_INDUSTRIA: Industrial data by province (2019)
"""

import os
from typing import Optional, Dict, Any, List
from langchain.tools import tool
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from loguru import logger
from dotenv import load_dotenv
import pandas as pd

load_dotenv()


class SnowflakeConfig:
    """Snowflake connection configuration."""

    def __init__(self):
        self.account = os.getenv('SNOWFLAKE_ACCOUNT')
        self.user = os.getenv('SNOWFLAKE_USER')
        self.password = os.getenv('SNOWFLAKE_PASSWORD')
        self.database = os.getenv('SNOWFLAKE_DATABASE', 'SPAIN_DATA')
        self.warehouse = os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH')
        self.schema = os.getenv('SNOWFLAKE_SCHEMA', 'PUBLIC')
        self.role = os.getenv('SNOWFLAKE_ROLE', 'ACCOUNTADMIN')

    def is_configured(self) -> bool:
        """Check if Snowflake is properly configured."""
        return all([self.account, self.user, self.password])


class SnowflakeTool:
    """
    Tool for querying Snowflake data warehouse.
    Contains predefined queries for common depopulation analysis scenarios.
    """

    # Schema information for the LLM
    SCHEMA_INFO = """
    ## Available Tables in Snowflake

    ### FACT_DESPOBLAMIENTO (Depopulation Indicators)
    Columns:
    - NOMBRE_PROVINCIA: Province name
    - PORCENTAJE_DESPOBLAMIENTO: Depopulation percentage
    - POBLACION_TOTAL: Total population
    - TASA_PARO_TOTAL: Unemployment rate
    - TASA_EMPLEO_TOTAL: Employment rate
    - TASA_ACTIVIDAD_TOTAL: Activity rate
    - PIB_PRECIOS_CORRIENTES: GDP at current prices
    - CATEGORIA_DESPOBLAMIENTO: Category (Very High, High, Medium, Low)

    ### FACT_POBLACION (Population by Municipality)
    Columns:
    - COD_PROVINCIA: Province code
    - NOMBRE_PROVINCIA: Province name
    - COD_MUNICIPIO: Municipality code
    - NOMBRE_MUNICIPIO: Municipality name
    - SEXO: Sex (Total, Hombres, Mujeres)
    - PERIODO: Year (1996-2023)
    - TOTAL: Population count

    ### FACT_INDUSTRIA (Industrial Data)
    Columns:
    - PROVINCIA: Province name
    - MUNICIPIO: Municipality name
    - VAB_CORREGIDO_2016: Value Added Gross
    - PIB_MUNICIPIOS_2016: Municipal GDP
    - AFILIADOS_DICIEMBRE_DE_2016: Social Security affiliates
    - AAEE_SECCIN_CNAE09: Economic activity sector (CNAE)
    
    ## Important Notes
    - Depopulated municipality = population < 2000 inhabitants
    - Data covers years 1996-2023 for population
    - Use PERIODO to filter by year
    - Use SEXO = 'Total' for total population (not by gender)
    """

    # Predefined queries for common scenarios
    PREDEFINED_QUERIES = {
        'current_depopulated_count': """
            SELECT 
                COUNT(DISTINCT NOMBRE_MUNICIPIO) as total_municipalities,
                SUM(CASE WHEN TOTAL < 2000 THEN 1 ELSE 0 END) as depopulated_count,
                ROUND(SUM(CASE WHEN TOTAL < 2000 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as depopulated_percentage
            FROM FACT_POBLACION
            WHERE SEXO = 'Total' AND PERIODO = 2023
        """,

        'depopulation_by_province': """
            SELECT 
                NOMBRE_PROVINCIA,
                COUNT(DISTINCT NOMBRE_MUNICIPIO) as total_municipalities,
                SUM(CASE WHEN TOTAL < 2000 THEN 1 ELSE 0 END) as depopulated_count,
                ROUND(SUM(CASE WHEN TOTAL < 2000 THEN 1 ELSE 0 END) * 100.0 / COUNT(DISTINCT NOMBRE_MUNICIPIO), 2) as depopulated_pct
            FROM FACT_POBLACION
            WHERE SEXO = 'Total' AND PERIODO = 2023
            GROUP BY NOMBRE_PROVINCIA
            ORDER BY depopulated_pct DESC
            LIMIT 15
        """,

        'historical_comparison': """
            WITH yearly_stats AS (
                SELECT 
                    PERIODO,
                    COUNT(DISTINCT NOMBRE_MUNICIPIO) as total_muni,
                    SUM(CASE WHEN TOTAL < 2000 THEN 1 ELSE 0 END) as depopulated
                FROM FACT_POBLACION
                WHERE SEXO = 'Total' 
                    AND PERIODO IN (1996, 2006, 2013, 2023)
                GROUP BY PERIODO
            )
            SELECT 
                PERIODO as year,
                total_muni,
                depopulated,
                ROUND(depopulated * 100.0 / total_muni, 2) as depopulated_pct
            FROM yearly_stats
            ORDER BY PERIODO
        """,

        'growing_municipalities': """
            WITH pop_change AS (
                SELECT 
                    NOMBRE_PROVINCIA,
                    NOMBRE_MUNICIPIO,
                    MAX(CASE WHEN PERIODO = 2008 THEN TOTAL END) as pop_2008,
                    MAX(CASE WHEN PERIODO = 2023 THEN TOTAL END) as pop_2023
                FROM FACT_POBLACION
                WHERE SEXO = 'Total' AND PERIODO IN (2008, 2023)
                GROUP BY NOMBRE_PROVINCIA, NOMBRE_MUNICIPIO
            )
            SELECT 
                NOMBRE_PROVINCIA,
                NOMBRE_MUNICIPIO,
                pop_2008,
                pop_2023,
                pop_2023 - pop_2008 as absolute_change,
                ROUND((pop_2023 - pop_2008) * 100.0 / NULLIF(pop_2008, 0), 2) as growth_pct
            FROM pop_change
            WHERE pop_2008 IS NOT NULL AND pop_2023 IS NOT NULL
                AND pop_2008 < 2000  -- Was depopulated
                AND pop_2023 >= pop_2008  -- Has grown
            ORDER BY growth_pct DESC
            LIMIT 20
        """,

        'declining_municipalities': """
            WITH pop_change AS (
                SELECT 
                    NOMBRE_PROVINCIA,
                    NOMBRE_MUNICIPIO,
                    MAX(CASE WHEN PERIODO = 2008 THEN TOTAL END) as pop_2008,
                    MAX(CASE WHEN PERIODO = 2023 THEN TOTAL END) as pop_2023
                FROM FACT_POBLACION
                WHERE SEXO = 'Total' AND PERIODO IN (2008, 2023)
                GROUP BY NOMBRE_PROVINCIA, NOMBRE_MUNICIPIO
            )
            SELECT 
                NOMBRE_PROVINCIA,
                NOMBRE_MUNICIPIO,
                pop_2008,
                pop_2023,
                pop_2023 - pop_2008 as absolute_change,
                ROUND((pop_2023 - pop_2008) * 100.0 / NULLIF(pop_2008, 0), 2) as decline_pct
            FROM pop_change
            WHERE pop_2008 IS NOT NULL AND pop_2023 IS NOT NULL
            ORDER BY decline_pct ASC
            LIMIT 20
        """,

        'depopulation_factors': """
            SELECT 
                CATEGORIA_DESPOBLAMIENTO,
                COUNT(*) as count,
                ROUND(AVG(TASA_PARO_TOTAL), 2) as avg_unemployment,
                ROUND(AVG(TASA_EMPLEO_TOTAL), 2) as avg_employment,
                ROUND(AVG(PIB_PRECIOS_CORRIENTES), 0) as avg_gdp,
                ROUND(AVG(PORCENTAJE_DESPOBLAMIENTO), 2) as avg_depopulation_pct
            FROM FACT_DESPOBLAMIENTO
            WHERE CATEGORIA_DESPOBLAMIENTO IS NOT NULL
            GROUP BY CATEGORIA_DESPOBLAMIENTO
            ORDER BY avg_depopulation_pct DESC
        """,

        'province_economic_profile': """
            SELECT 
                NOMBRE_PROVINCIA,
                ROUND(PORCENTAJE_DESPOBLAMIENTO, 2) as depop_pct,
                ROUND(TASA_PARO_TOTAL, 2) as unemployment,
                ROUND(PIB_PRECIOS_CORRIENTES, 0) as gdp,
                CATEGORIA_DESPOBLAMIENTO
            FROM FACT_DESPOBLAMIENTO
            WHERE PORCENTAJE_DESPOBLAMIENTO IS NOT NULL
            ORDER BY PORCENTAJE_DESPOBLAMIENTO DESC
            LIMIT 15
        """,

        'gender_distribution': """
            SELECT 
                NOMBRE_PROVINCIA,
                SUM(CASE WHEN SEXO = 'Hombres' THEN TOTAL ELSE 0 END) as men,
                SUM(CASE WHEN SEXO = 'Mujeres' THEN TOTAL ELSE 0 END) as women,
                SUM(CASE WHEN SEXO = 'Total' THEN TOTAL ELSE 0 END) as total,
                ROUND(SUM(CASE WHEN SEXO = 'Hombres' THEN TOTAL ELSE 0 END) * 100.0 / 
                      NULLIF(SUM(CASE WHEN SEXO = 'Total' THEN TOTAL ELSE 0 END), 0), 2) as men_pct
            FROM FACT_POBLACION
            WHERE PERIODO = 2023
            GROUP BY NOMBRE_PROVINCIA
            ORDER BY total DESC
            LIMIT 15
        """
    }

    def __init__(self):
        self.config = SnowflakeConfig()
        self.conn = None

    def connect(self):
        """Establish connection to Snowflake."""
        if not self.config.is_configured():
            raise ValueError("Snowflake credentials not configured. Set environment variables.")

        try:
            import snowflake.connector

            self.conn = snowflake.connector.connect(
                account=self.config.account,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                warehouse=self.config.warehouse,
                schema=self.config.schema,
                role=self.config.role
            )


            logger.info(f"Connected to Snowflake: {self.config.database}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Snowflake: {e}")
            return False

    def execute_query(self, sql: str) -> pd.DataFrame:
        """Execute a SQL query and return results as DataFrame."""
        if self.conn is None:
            self.connect()

        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)
            df = cursor.fetch_pandas_all()
            cursor.close()
            return df
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            raise

    def get_predefined_query(self, query_name: str) -> Optional[str]:
        """Get a predefined query by name."""
        return self.PREDEFINED_QUERIES.get(query_name)

    def close(self):
        """Close the connection."""
        if self.conn:
            self.conn.close()
            logger.info("Snowflake connection closed")


# LangChain Tool Definition
class SnowflakeQueryInput(BaseModel):
    """Input schema for Snowflake query tool."""
    query_type: str = Field(
        description="""Type of query to execute. Options:
        - 'current_depopulated_count': Get count of depopulated municipalities (<2000 inhabitants)
        - 'depopulation_by_province': Get depopulation stats by province
        - 'historical_comparison': Compare depopulation across years (1996, 2006, 2013, 2023)
        - 'growing_municipalities': Find municipalities that have grown (repopulated)
        - 'declining_municipalities': Find municipalities with biggest population decline
        - 'depopulation_factors': Analyze factors (unemployment, GDP) by depopulation category
        - 'province_economic_profile': Economic profile of provinces
        - 'gender_distribution': Population by gender per province
        - 'custom': Execute a custom SQL query (provide in 'custom_sql' parameter)
        """
    )
    custom_sql: Optional[str] = Field(
        default=None,
        description="Custom SQL query to execute (only used when query_type='custom')"
    )
    province: Optional[str] = Field(
        default=None,
        description="Filter by province name (optional)"
    )
    year: Optional[int] = Field(
        default=None,
        description="Filter by year (optional, 1996-2023)"
    )


@tool("query_snowflake", args_schema=SnowflakeQueryInput)
def query_snowflake(
    query_type: str,
    custom_sql: Optional[str] = None,
    province: Optional[str] = None,
    year: Optional[int] = None
) -> str:
    """
    Query the Snowflake data warehouse for Spanish population and depopulation data.

    Use this tool to get statistical data about:
    - Depopulated municipalities (< 2000 inhabitants)
    - Historical population trends
    - Economic factors (unemployment, GDP)
    - Industrial activity
    - Comparison across provinces and years

    Returns data as formatted text suitable for analysis.
    """
    tool = SnowflakeTool()

    try:
        if not tool.connect():
            return "Error: Could not connect to Snowflake. Check credentials."

        # Get the SQL query
        if query_type == 'custom' and custom_sql:
            sql = custom_sql
        else:
            sql = tool.get_predefined_query(query_type)
            if not sql:
                return f"Error: Unknown query type '{query_type}'. Available: {list(tool.PREDEFINED_QUERIES.keys())}"

        # Execute query
        df = tool.execute_query(sql)
        tool.close()

        # Format results
        if df.empty:
            return "Query returned no results."

        # Create summary
        result = f"## Query Results: {query_type}\n\n"
        result += f"**Rows returned:** {len(df)}\n\n"
        result += "### Data:\n"
        result += df.to_markdown(index=False)

        return result

    except Exception as e:
        return f"Error executing query: {str(e)}"
    finally:
        tool.close()


# Convenience function for direct usage
def get_schema_info() -> str:
    """Get schema information for the LLM."""
    return SnowflakeTool.SCHEMA_INFO

