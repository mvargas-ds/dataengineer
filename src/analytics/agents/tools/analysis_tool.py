"""
Analysis Tool
=============
Tool for performing statistical analysis on depopulation data.
Analyzes correlations, trends, and factors contributing to depopulation.
"""

from typing import Optional, List, Dict, Any
from langchain.tools import tool
from pydantic import BaseModel, Field
from loguru import logger
import json


class AnalysisTool:
    """
    Tool for statistical analysis of depopulation data.
    """

    # Depopulation threshold in Spain
    DEPOPULATION_THRESHOLD = 2000  # inhabitants

    # Known factors and their typical correlations
    KNOWN_FACTORS = {
        'unemployment': {
            'correlation': 'positive',
            'description': 'Higher unemployment correlates with higher depopulation',
            'mechanism': 'Lack of job opportunities drives migration to urban areas'
        },
        'gdp_per_capita': {
            'correlation': 'negative',
            'description': 'Lower GDP correlates with higher depopulation',
            'mechanism': 'Economic opportunities attract and retain population'
        },
        'distance_to_city': {
            'correlation': 'positive',
            'description': 'Greater distance from cities correlates with higher depopulation',
            'mechanism': 'Access to services and employment decreases with distance'
        },
        'aging_index': {
            'correlation': 'positive',
            'description': 'Higher aging index correlates with higher depopulation',
            'mechanism': 'Young people migrate, leaving elderly population'
        },
        'service_availability': {
            'correlation': 'negative',
            'description': 'Better services correlate with lower depopulation',
            'mechanism': 'Healthcare, education, and transport retain population'
        },
        'industrial_activity': {
            'correlation': 'negative',
            'description': 'More industrial activity correlates with lower depopulation',
            'mechanism': 'Industry provides stable employment'
        },
        'connectivity': {
            'correlation': 'negative',
            'description': 'Better connectivity (internet, roads) correlates with lower depopulation',
            'mechanism': 'Enables remote work and access to markets'
        },
        'gender_imbalance': {
            'correlation': 'positive',
            'description': 'Higher male/female ratio (more men) correlates with depopulation',
            'mechanism': 'Women tend to migrate first seeking education/employment'
        }
    }

    # Repopulation success factors
    REPOPULATION_FACTORS = {
        'remote_work': 'Availability of high-speed internet enabling remote work',
        'quality_of_life': 'Lower cost of living, less pollution, better environment',
        'local_initiatives': 'Municipal programs to attract new residents',
        'tourism': 'Rural tourism creating economic opportunities',
        'agriculture_innovation': 'Modern, profitable agricultural practices',
        'renewable_energy': 'Wind/solar farms creating jobs and income',
        'proximity_to_city': 'Within commuting distance of employment centers',
        'housing_availability': 'Affordable housing stock in good condition'
    }

    def analyze_factors(self, province: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze factors contributing to depopulation.
        """
        analysis = {
            'depopulation_threshold': self.DEPOPULATION_THRESHOLD,
            'key_factors': self.KNOWN_FACTORS,
            'repopulation_enablers': self.REPOPULATION_FACTORS,
            'analysis_type': 'factor_analysis',
            'province_filter': province
        }

        if province:
            analysis['note'] = f"Analysis focused on {province} province"
        else:
            analysis['note'] = "General analysis for all of Spain"

        return analysis

    def compare_periods(self, start_year: int, end_year: int) -> Dict[str, Any]:
        """
        Generate analysis framework for comparing two time periods.
        """
        period_length = end_year - start_year

        return {
            'comparison_type': 'temporal',
            'start_year': start_year,
            'end_year': end_year,
            'period_length_years': period_length,
            'analysis_points': [
                f'Change in number of depopulated municipalities (<{self.DEPOPULATION_THRESHOLD})',
                'Change in total rural population',
                'Municipalities that crossed the depopulation threshold',
                'Provinces with highest population loss',
                'Provinces with population gain (if any)',
                'Economic indicators evolution (unemployment, GDP)',
            ],
            'context': {
                '1996-2006': 'Economic boom period in Spain',
                '2006-2013': 'Financial crisis and recession',
                '2013-2023': 'Recovery and COVID-19 impact'
            }
        }

    def suggest_repopulation_strategies(self, characteristics: Dict) -> List[str]:
        """
        Suggest repopulation strategies based on area characteristics.
        """
        strategies = []

        # Base strategies applicable to most areas
        strategies.append("Digital infrastructure: High-speed internet to enable remote work")
        strategies.append("Housing rehabilitation: Restore abandoned properties for new residents")

        # Conditional strategies
        if characteristics.get('near_city', False):
            strategies.append("Promote as bedroom community for city workers")

        if characteristics.get('natural_beauty', False):
            strategies.append("Develop sustainable rural tourism")

        if characteristics.get('agricultural_land', False):
            strategies.append("Support modern, profitable agriculture and agritech")

        if characteristics.get('renewable_potential', False):
            strategies.append("Develop renewable energy projects for local employment")

        strategies.append("Incentive programs: Tax benefits for new residents and businesses")
        strategies.append("Service guarantees: Ensure healthcare, education, and transport")

        return strategies


# LangChain Tool Definition
class AnalysisInput(BaseModel):
    """Input schema for analysis tool."""
    analysis_type: str = Field(
        description="""Type of analysis to perform:
        - 'factors': Analyze factors contributing to depopulation
        - 'comparison': Compare depopulation between time periods
        - 'strategies': Get repopulation strategies
        - 'correlation': Explain correlations between variables
        - 'threshold': Explain depopulation threshold and classification
        """
    )
    province: Optional[str] = Field(
        default=None,
        description="Province to focus analysis on (optional)"
    )
    start_year: Optional[int] = Field(
        default=None,
        description="Start year for temporal comparison"
    )
    end_year: Optional[int] = Field(
        default=None,
        description="End year for temporal comparison"
    )
    factor: Optional[str] = Field(
        default=None,
        description="Specific factor to analyze (unemployment, gdp, aging, etc.)"
    )


@tool("analyze_depopulation_factors", args_schema=AnalysisInput)
def analyze_depopulation_factors(
    analysis_type: str,
    province: Optional[str] = None,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    factor: Optional[str] = None
) -> str:
    """
    Analyze factors and patterns related to rural depopulation in Spain.

    Use this tool to:
    - Understand what factors cause depopulation
    - Compare depopulation trends across time periods
    - Get strategies for repopulation
    - Explain correlations between economic/social indicators and population decline

    This provides analytical context to complement the data from Snowflake and INE.
    """
    tool = AnalysisTool()

    try:
        if analysis_type == 'factors':
            result = tool.analyze_factors(province)

            output = "## Depopulation Factor Analysis\n\n"
            output += f"**Depopulation threshold:** Municipalities with less than {result['depopulation_threshold']} inhabitants\n\n"

            output += "### Key Factors Contributing to Depopulation\n\n"
            for factor_name, info in result['key_factors'].items():
                output += f"**{factor_name.replace('_', ' ').title()}**\n"
                output += f"- Correlation: {info['correlation']} with depopulation\n"
                output += f"- Description: {info['description']}\n"
                output += f"- Mechanism: {info['mechanism']}\n\n"

            return output

        elif analysis_type == 'comparison':
            if not start_year or not end_year:
                return "Error: Please provide start_year and end_year for comparison analysis"

            result = tool.compare_periods(start_year, end_year)

            output = f"## Temporal Comparison: {start_year} vs {end_year}\n\n"
            output += f"**Period length:** {result['period_length_years']} years\n\n"

            output += "### Key Analysis Points\n\n"
            for point in result['analysis_points']:
                output += f"- {point}\n"

            output += "\n### Historical Context\n\n"
            for period, context in result['context'].items():
                output += f"- **{period}:** {context}\n"

            return output

        elif analysis_type == 'strategies':
            # Default characteristics for general analysis
            characteristics = {
                'near_city': True,
                'natural_beauty': True,
                'agricultural_land': True,
                'renewable_potential': True
            }

            strategies = tool.suggest_repopulation_strategies(characteristics)

            output = "## Repopulation Strategies\n\n"
            output += "### Recommended Strategies for Rural Revitalization\n\n"

            for i, strategy in enumerate(strategies, 1):
                output += f"{i}. {strategy}\n"

            output += "\n### Enabling Factors for Successful Repopulation\n\n"
            for factor_name, description in tool.REPOPULATION_FACTORS.items():
                output += f"- **{factor_name.replace('_', ' ').title()}:** {description}\n"

            return output

        elif analysis_type == 'correlation':
            if factor and factor.lower() in tool.KNOWN_FACTORS:
                info = tool.KNOWN_FACTORS[factor.lower()]

                output = f"## Correlation Analysis: {factor.title()} and Depopulation\n\n"
                output += f"**Correlation type:** {info['correlation'].title()}\n\n"
                output += f"**Finding:** {info['description']}\n\n"
                output += f"**Mechanism:** {info['mechanism']}\n"

                return output
            else:
                output = "## Available Correlation Analyses\n\n"
                output += "Specify one of these factors:\n\n"
                for f in tool.KNOWN_FACTORS.keys():
                    output += f"- {f}\n"
                return output

        elif analysis_type == 'threshold':
            output = "## Depopulation Threshold in Spain\n\n"
            output += f"**Official threshold:** {tool.DEPOPULATION_THRESHOLD} inhabitants\n\n"
            output += "### Classification\n\n"
            output += "- **Depopulated:** < 2,000 inhabitants\n"
            output += "- **At risk:** 2,000 - 5,000 inhabitants\n"
            output += "- **Small town:** 5,000 - 10,000 inhabitants\n"
            output += "- **Medium town:** 10,000 - 50,000 inhabitants\n\n"
            output += "### Legal Framework\n\n"
            output += "Spain's Law 45/2007 for Sustainable Development of Rural Areas "
            output += "establishes policies for areas affected by depopulation.\n"

            return output

        else:
            return f"Unknown analysis type: {analysis_type}. Use: factors, comparison, strategies, correlation, threshold"

    except Exception as e:
        return f"Error performing analysis: {str(e)}"

