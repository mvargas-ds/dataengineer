"""
🤖 Data Analysis Chatbot with AI
=================================
Allows natural language queries on the Data Warehouse.

This is a very common pattern in modern Data Science projects:
- Text-to-SQL: Convert natural language questions to SQL
- RAG (Retrieval Augmented Generation): Use data as context
- Data Agents: LLMs that interact with databases

Supports multiple backends:
- OpenAI GPT-4
- Local LLMs (Ollama)
- No-LLM mode (predefined templates)
"""
import duckdb
import os
import json
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime

# Path to warehouse
DB_PATH = Path(__file__).parent.parent.parent / "data" / "warehouse.duckdb"


@dataclass
class ChatMessage:
    """Message in the chat."""
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: datetime = None
    sql_query: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class DataChatbot:
    """
    Intelligent chatbot for data analysis.
    Converts natural language questions to SQL queries.
    """
    
    def __init__(self, db_path: str = None, llm_provider: str = "template", database_type: str = "duckdb"):

        print("--------------      INIT    ----------------")
        """
        Initializes the chatbot.

        Args:
            db_path: Path to DuckDB database
            llm_provider: 'github', 'openai', 'anthropic', 'ollama', 'template'
            database_type: 'duckdb' or 'snowflake'
        """
        self.database_type = database_type
        self.llm_provider = llm_provider
        self.conversation_history: List[ChatMessage] = []
        self.db_path = None

        if database_type == "snowflake":
            self._connect_snowflake()
        else:
            self.db_path = db_path or str(DB_PATH)
            self.conn = duckdb.connect(self.db_path, read_only=True)

        self.schema_info = self._get_schema_info()
        
        print("🤖 Data Analysis Chatbot Initialized")
        print(f"📊 Database: {self.db_path}")
        print(f"🧠 LLM Provider: {llm_provider}")
        self._print_available_data()

    def _connect_snowflake(self):
        print("--------------      CONNECT SNOWFLAKE    ----------------")
        """Connects to Snowflake."""
        import snowflake.connector
        from dotenv import load_dotenv

        load_dotenv()

        account = os.getenv('SNOWFLAKE_ACCOUNT', 'fj69748.sa-east-1.aws')
        user = os.getenv('SNOWFLAKE_USER')
        password = os.getenv('SNOWFLAKE_PASSWORD')
        warehouse = os.getenv('SNOWFLAKE_WAREHOUSE')
        database = os.getenv('SNOWFLAKE_DATABASE')
        schema = os.getenv('SNOWFLAKE_SCHEMA', 'PUBLIC')

        self.conn = snowflake.connector.connect(
            account=account,
            user=user,
            password=password,
            warehouse=warehouse,
            database=database,
            schema=schema
        )
        print(f"❄️ Connected to Snowflake: {database}.{schema}")
    
    def _get_schema_info(self) -> Dict:
        print("--------------      GET SCHEMA INFO    ----------------")
        """Gets database schema information."""
        schema = {}
        if self.database_type == "snowflake":
            cursor = self.conn.cursor()
            cursor.execute("SHOW TABLES")
            tables = [(row[1],) for row in cursor.fetchall()]

            for table in tables:
                table_name = table[0]
                cursor.execute(f"DESCRIBE TABLE {table_name}")
                columns = [{"column_name": row[0], "column_type": row[1]} for row in cursor.fetchall()]
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                sample = cursor.fetchall()
                col_names = [desc[0] for desc in cursor.description]
                sample_data = [dict(zip(col_names, row)) for row in sample]
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]

                schema[table_name] = {
                    'columns': columns,
                    'sample_data': sample_data,
                    'row_count': count
                }
            cursor.close()
        else:
            # DuckDB original logic
            tables = self.conn.execute("SHOW TABLES").fetchall()
            for table in tables:
                table_name = table[0]
                columns = self.conn.execute(f"DESCRIBE {table_name}").fetchdf()
                sample = self.conn.execute(f"SELECT * FROM {table_name} LIMIT 3").fetchdf()
                count = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]

                schema[table_name] = {
                    'columns': columns.to_dict('records'),
                    'sample_data': sample.to_dict('records'),
                    'row_count': count
                }

        return schema
    
    def _print_available_data(self):
        """Shows information about available data."""
        print("\n📋 Available data:")
        for table, info in self.schema_info.items():
            cols = [c['column_name'] for c in info['columns'][:5]]
            print(f"   • {table}: {info['row_count']:,} rows")
            print(f"     Columns: {', '.join(cols)}...")
        print()
    
    def _build_system_prompt(self) -> str:
        print("--------------      BUILD SYSTEM PROMPT    ----------------")
        """Builds the system prompt with data context."""
        schema_text = ""
        for table, info in self.schema_info.items():
            cols = ", ".join([f"{c['column_name']} ({c['column_type']})" 
                            for c in info['columns']])
            schema_text += f"\nTable: {table}\n  Columns: {cols}\n  Rows: {info['row_count']}\n"

        db_note = ""
        if self.database_type == "snowflake":
            db_note = """
        ⚠️ CRITICAL: Use EXACTLY these column names (case-sensitive in Snowflake):
        - CODIGO_PROVINCIA (NOT CODIGO_PROVINCIO)
        - NOMBRE_PROVINCIA
        - Use uppercase for all column and table names in Snowflake
        """

        return f"""You are an expert data analysis assistant for Spain data.
You have access to a DuckDB database with the following data:

{schema_text}

AVAILABLE DATA:
- fact_despoblamiento: Depopulation indicators by province (population, employment rates, GDP, CPI)
- fact_poblacion: Population by municipality and sex from 1996 to 2023
- fact_industria: Industrial data by province (GVA, GDP, affiliates by sector)

INSTRUCTIONS:
1. When the user asks a question, generate a valid SQL query for DuckDB
2. Always respond in English
3. If you cannot answer with the available data, indicate it
4. Include the SQL query in your response between ```sql and ```
5. Explain the results clearly and concisely

EXAMPLE QUESTIONS:
- "What are the provinces with the highest depopulation?"
- "What is the population evolution of Madrid?"
- "Which industrial sectors have the most employment?"
"""
    
    def _query_with_openai(self, user_message: str) -> Tuple[str, Optional[str]]:
        """Generates response using OpenAI."""
        try:
            from openai import OpenAI
            from dotenv import load_dotenv
            import os
            
            # Load environment variables from .env
            load_dotenv()
            
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return """❌ **Error: OPENAI_API_KEY not configured**

Configure your API key in the `.env` file:
```
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
```

Or use template mode: --provider template""", None

            client = OpenAI(api_key=api_key)
            
            messages = [
                {"role": "system", "content": self._build_system_prompt()},
                {"role": "user", "content": user_message}
            ]
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Model accessible for all accounts
                messages=messages,
                temperature=0
            )
            
            return response.choices[0].message.content, None
        except Exception as e:
            return f"Error with OpenAI: {e}", None

    def _query_with_github(self, user_message: str) -> Tuple[str, Optional[str]]:
        """Generates response using GitHub Models (GitHub Copilot)."""
        try:
            from openai import OpenAI
            from dotenv import load_dotenv
            import os
            
            # Load environment variables from .env
            load_dotenv()
            
            # GitHub Models uses a GitHub token
            github_token = os.getenv("GITHUB_TOKEN")
            if not github_token:
                return """❌ **Error: GITHUB_TOKEN not configured**

To use GitHub Models (Copilot), you need to configure your GitHub token:

1. Go to https://github.com/settings/tokens
2. Generate a new token (classic) with 'read:user' permissions
3. Configure it in the `.env` file:
   ```
   GITHUB_TOKEN=ghp_xxxxxxxxxxxxx
   ```

Or use template mode: --provider template""", None

            # GitHub Models endpoint
            client = OpenAI(
                base_url="https://models.inference.ai.azure.com",
                api_key=github_token
            )
            
            messages = [
                {"role": "system", "content": self._build_system_prompt()},
                {"role": "user", "content": user_message}
            ]
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Available models: gpt-4o, gpt-4o-mini, Phi-3, Llama, etc.
                messages=messages,
                temperature=0
            )
            
            return response.choices[0].message.content, None
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "unauthorized" in error_msg.lower():
                return """❌ **GitHub authentication error**

Your GitHub token doesn't have permissions or is invalid.

1. Make sure you have access to GitHub Models
2. Generate a new token at: https://github.com/settings/tokens
3. The token needs minimum permissions (read:user)

You can also try template mode: --provider template""", None
            return f"Error with GitHub Models: {e}", None

    def _build_advanced_claude_prompt(self) -> str:
        """Builds an advanced prompt specifically for Claude."""
        schema_text = ""
        for table, info in self.schema_info.items():
            cols = "\n      ".join([f"- {c['column_name']}: {c['column_type']}" 
                            for c in info['columns']])
            schema_text += f"\n### Table: `{table}` ({info['row_count']:,} rows)\n    Columns:\n      {cols}\n"

        return f"""You are an expert data analyst specialized in demographic and economic data from Spain.
Your goal is to help users get insights from a Data Warehouse using SQL queries.

## 📊 DATABASE SCHEMA (DuckDB)
{schema_text}

## 📋 TABLE DESCRIPTIONS

### fact_despoblamiento
Contains depopulation indicators by province/region of Spain:
- Population data, employment/unemployment/activity rates
- Economic indicators: GDP, CPI
- Depopulation categories: 'Very High', 'High', 'Medium', 'Low'

### fact_poblacion  
Spain population by municipality and sex (1996-2023):
- Breakdown by province, municipality, sex (Men/Women/Total)
- Annual time series ('periodo' column)

### fact_industria
Industrial data by municipality (2016):
- GVA (Gross Value Added), municipal GDP
- Affiliates by CNAE sector
- Classification by sectors: agriculture, industry, construction, services

## 🎯 INSTRUCTIONS

1. **ALWAYS** generate a valid DuckDB SQL query between ```sql blocks
2. **ALWAYS** respond in English
3. Use appropriate aggregation functions (SUM, AVG, COUNT, etc.)
4. Use ROUND() for decimal numbers (2 decimal places)
5. Limit results with LIMIT (maximum 20 rows by default)
6. Order results logically (DESC for rankings)
7. Handle NULL values with COALESCE or WHERE filters
8. Explain the results after the SQL

## 📝 SQL QUERY EXAMPLES

**Example 1: Top provinces by population**
```sql
SELECT 
    nombre_provincia,
    SUM(total) as total_population
FROM fact_poblacion
WHERE sexo = 'Total' AND periodo = 2023
GROUP BY nombre_provincia
ORDER BY total_population DESC
LIMIT 10
```

**Example 2: Temporal comparison**
```sql
SELECT 
    periodo as year,
    SUM(total) as total_population,
    LAG(SUM(total)) OVER (ORDER BY periodo) as previous_year,
    ROUND((SUM(total) - LAG(SUM(total)) OVER (ORDER BY periodo)) * 100.0 / 
          NULLIF(LAG(SUM(total)) OVER (ORDER BY periodo), 0), 2) as growth_pct
FROM fact_poblacion
WHERE sexo = 'Total' AND periodo >= 2010
GROUP BY periodo
ORDER BY periodo
```

**Example 3: Depopulation-unemployment correlation**
```sql
SELECT 
    categoria_despoblamiento,
    COUNT(*) as num_records,
    ROUND(AVG(tasa_paro_total), 2) as avg_unemployment,
    ROUND(AVG(tasa_empleo_total), 2) as avg_employment
FROM fact_despoblamiento
WHERE categoria_despoblamiento IS NOT NULL
GROUP BY categoria_despoblamiento
ORDER BY avg_unemployment DESC
```

## ⚠️ IMPORTANT NOTES
- The most recent period is 2023
- 'sexo' can be: 'Total', 'Hombres', 'Mujeres'
- Use exact column names from the schema
- If the question is unclear, ask for clarification
"""

    def _query_with_anthropic(self, user_message: str) -> Tuple[str, Optional[str]]:
        """Generates response using Anthropic Claude with advanced prompts."""
        try:
            import anthropic
            from dotenv import load_dotenv
            load_dotenv()
            
            client = anthropic.Anthropic()
            
            # Build conversation history for context
            messages = []
            
            # Add last 4 messages from history for context
            recent_history = self.conversation_history[-4:] if len(self.conversation_history) > 0 else []
            for msg in recent_history:
                if msg.role in ['user', 'assistant']:
                    messages.append({
                        "role": msg.role,
                        "content": msg.content[:500]  # Limit size
                    })
            
            # Add current message
            messages.append({"role": "user", "content": user_message})
            
            response = client.messages.create(
                model="claude-sonnet-4-20250514",  # Most recent model
                max_tokens=4000,
                system=self._build_advanced_claude_prompt(),
                messages=messages,
                temperature=0  # More consistent responses
            )
            
            return response.content[0].text, None
        except anthropic.AuthenticationError:
            return """❌ **Anthropic authentication error**

To use Claude, you need to configure your API key:

1. Get your API key at: https://console.anthropic.com/
2. Configure it in the `.env` file:
   ```
   ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxx
   ```
3. Or export it as an environment variable:
   ```powershell
   $env:ANTHROPIC_API_KEY = "sk-ant-api03-xxxxxxxxxxxxx"
   ```

Meanwhile, you can use template mode (--provider template) which doesn't require an API key.""", None
        except Exception as e:
            return f"Error with Anthropic: {e}", None

    def _query_with_ollama(self, user_message: str) -> Tuple[str, Optional[str]]:
        """Generates response using Ollama (local LLM)."""
        try:
            import requests
            
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3",
                    "prompt": f"{self._build_system_prompt()}\n\nUser: {user_message}\n\nAssistant:",
                    "stream": False
                }
            )
            
            return response.json()["response"], None
        except Exception as e:
            return f"Error with Ollama: {e}. Is Ollama running?", None

    def _query_with_template(self, user_message: str) -> Tuple[str, Optional[str]]:
        """Generates responses using predefined templates (no LLM)."""
        message_lower = user_message.lower()
        
        # Define query templates
        templates = {
            "depopulation": {
                "keywords": ["depopulation", "depopulated", "empty", "abandoned", "despoblamiento", "despobladas"],
                "sql": """
                    SELECT 
                        ROUND(porcentaje_despoblamiento, 1) as depopulation_pct,
                        poblacion_total as total_population,
                        ROUND(tasa_paro_total, 2) as unemployment_rate,
                        categoria_despoblamiento as depopulation_category
                    FROM fact_despoblamiento
                    WHERE porcentaje_despoblamiento IS NOT NULL
                    ORDER BY porcentaje_despoblamiento DESC
                    LIMIT 10
                """,
                "description": "Areas with highest depopulation index"
            },
            "population_province": {
                "keywords": ["population", "inhabitants", "people", "province", "poblacion", "habitantes"],
                "sql": """
                    SELECT 
                        nombre_provincia as province_name,
                        SUM(CASE WHEN sexo = 'Total' THEN total END) as total_population,
                        SUM(CASE WHEN sexo = 'Hombres' THEN total END) as men,
                        SUM(CASE WHEN sexo = 'Mujeres' THEN total END) as women
                    FROM fact_poblacion
                    WHERE periodo = 2023
                    GROUP BY nombre_provincia
                    ORDER BY total_population DESC
                    LIMIT 10
                """,
                "description": "Population by province in 2023"
            },
            "evolution": {
                "keywords": ["evolution", "trend", "historical", "years", "change", "evolucion", "tendencia"],
                "sql": """
                    SELECT 
                        periodo as year,
                        SUM(total) as total_population
                    FROM fact_poblacion
                    WHERE sexo = 'Total' AND periodo >= 2000
                    GROUP BY periodo
                    ORDER BY periodo
                """,
                "description": "Evolution of total population in Spain"
            },
            "industry": {
                "keywords": ["industry", "industrial", "sectors", "economic", "gdp", "industria", "pib"],
                "sql": """
                    SELECT 
                        provincia as province,
                        ROUND(SUM(pib_municipios_2016), 0) as total_gdp,
                        COUNT(DISTINCT municipio) as municipalities
                    FROM fact_industria
                    WHERE pib_municipios_2016 IS NOT NULL
                    GROUP BY provincia
                    ORDER BY total_gdp DESC
                    LIMIT 10
                """,
                "description": "Industrial activity by province"
            },
            "sectors": {
                "keywords": ["sector", "cnae", "activity", "employment", "empleo", "actividad"],
                "sql": """
                    SELECT 
                        aaee_seccin_cnae09 as sector,
                        ROUND(SUM(vab_corregido_2016), 0) as gross_value_added,
                        ROUND(SUM(afiliados_diciembre_de_2016), 0) as affiliates
                    FROM fact_industria
                    WHERE aaee_seccin_cnae09 IS NOT NULL
                    GROUP BY sector
                    ORDER BY gross_value_added DESC
                    LIMIT 10
                """,
                "description": "Economic sectors with highest activity"
            },
            "unemployment": {
                "keywords": ["unemployment", "jobless", "work", "employment", "paro", "desempleo", "trabajo"],
                "sql": """
                    SELECT 
                        categoria_despoblamiento as depopulation_category,
                        ROUND(AVG(tasa_paro_total), 2) as avg_unemployment_rate,
                        ROUND(AVG(tasa_empleo_total), 2) as avg_employment_rate,
                        ROUND(AVG(tasa_actividad_total), 2) as avg_activity_rate
                    FROM fact_despoblamiento
                    WHERE tasa_paro_total IS NOT NULL
                    GROUP BY categoria_despoblamiento
                    ORDER BY avg_unemployment_rate DESC
                """,
                "description": "Employment and unemployment rates by depopulation level"
            },
            "municipalities": {
                "keywords": ["municipality", "town", "city", "locality", "municipio", "pueblo", "ciudad"],
                "sql": """
                    SELECT 
                        nombre_provincia as province_name,
                        nombre_municipio as municipality_name,
                        MAX(total) as population_2023
                    FROM fact_poblacion
                    WHERE sexo = 'Total' AND periodo = 2023
                    GROUP BY nombre_provincia, nombre_municipio
                    ORDER BY population_2023 DESC
                    LIMIT 15
                """,
                "description": "Most populated municipalities in Spain"
            },
            "growth": {
                "keywords": ["growth", "grow", "increase", "rise", "crecimiento", "crecer", "aumentar"],
                "sql": """
                    SELECT 
                        nombre_provincia as province_name,
                        nombre_municipio as municipality_name,
                        MAX(CASE WHEN periodo = 2023 THEN total END) as pop_2023,
                        MAX(CASE WHEN periodo = 2013 THEN total END) as pop_2013,
                        ROUND(
                            (MAX(CASE WHEN periodo = 2023 THEN total END) - 
                             MAX(CASE WHEN periodo = 2013 THEN total END)) * 100.0 / 
                            NULLIF(MAX(CASE WHEN periodo = 2013 THEN total END), 0), 2
                        ) as growth_pct
                    FROM fact_poblacion
                    WHERE sexo = 'Total' AND periodo IN (2013, 2023)
                    GROUP BY nombre_provincia, nombre_municipio
                    HAVING MAX(CASE WHEN periodo = 2013 THEN total END) > 5000
                    ORDER BY growth_pct DESC
                    LIMIT 10
                """,
                "description": "Municipalities with highest population growth (2013-2023)"
            }
        }
        
        # Find the most relevant template
        best_match = None
        best_score = 0
        
        for key, template in templates.items():
            score = sum(1 for kw in template["keywords"] if kw in message_lower)
            if score > best_score:
                best_score = score
                best_match = template
        
        if best_match and best_score > 0:
            return best_match["description"], best_match["sql"]
        
        # Default response
        return """I couldn't find a specific query for your question. 
        
I can help you with:
• **Depopulation** data: "What are the most depopulated areas?"
• **Population** by province/municipality: "How many inhabitants does each province have?"
• Population **evolution**: "How has the population evolved?"
• **Industry** data: "Which provinces have the most industrial activity?"
• Economic **sectors**: "Which sectors have the most employment?"
• **Unemployment/employment** rates: "What is the unemployment rate by region?"

What would you like to know?""", None

    def _extract_sql_from_response(self, response: str) -> Optional[str]:
        """Extracts SQL from the LLM response."""
        import re
        
        # Search for SQL between ```sql and ```
        sql_match = re.search(r'```sql\s*(.*?)\s*```', response, re.DOTALL | re.IGNORECASE)
        if sql_match:
            return sql_match.group(1).strip()
        
        # Search for SQL between ``` and ```
        sql_match = re.search(r'```\s*(SELECT.*?)\s*```', response, re.DOTALL | re.IGNORECASE)
        if sql_match:
            return sql_match.group(1).strip()
        
        return None
    
    def _execute_sql(self, sql: str) -> Tuple[bool, str]:
        """Executes a SQL query and returns formatted result."""
        try:
            if self.database_type == "snowflake":
                cursor = self.conn.cursor()
                cursor.execute(sql)
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                cursor.close()

                if len(rows) == 0:
                    return True, "The query returned no results."

                # Format as simple table
                import pandas as pd
                df = pd.DataFrame(rows, columns=columns)
                result = df.to_string(index=False)
                return True, f"\n📊 Results ({len(df)} rows):\n\n{result}"
            else:
                df = self.conn.execute(sql).fetchdf()
                if len(df) == 0:
                    return True, "The query returned no results."
                result = df.to_string(index=False)
                return True, f"\n📊 Results ({len(df)} rows):\n\n{result}"
        except Exception as e:
            return False, f"Error executing SQL: {e}"

    def chat(self, user_message: str) -> str:
        """
        Processes a user message and returns the response.
        """
        # Save user message
        self.conversation_history.append(ChatMessage(role="user", content=user_message))
        
        # Get response according to provider
        if self.llm_provider == "github":
            llm_response, sql = self._query_with_github(user_message)
        elif self.llm_provider == "openai":
            llm_response, sql = self._query_with_openai(user_message)
        elif self.llm_provider == "anthropic":
            llm_response, sql = self._query_with_anthropic(user_message)
        elif self.llm_provider == "ollama":
            llm_response, sql = self._query_with_ollama(user_message)
        else:
            llm_response, sql = self._query_with_template(user_message)
        
        # If no SQL was provided, try to extract it from the response
        if sql is None:
            sql = self._extract_sql_from_response(llm_response)
        
        # Execute SQL if it exists
        final_response = llm_response
        if sql:
            success, result = self._execute_sql(sql)
            if success:
                final_response = f"{llm_response}\n\n🔍 **SQL Query:**\n```sql\n{sql}\n```\n{result}"
            else:
                final_response = f"{llm_response}\n\n⚠️ {result}"
        
        # Save response
        self.conversation_history.append(
            ChatMessage(role="assistant", content=final_response, sql_query=sql)
        )
        
        return final_response
    
    def run_interactive(self):
        print("--------------      RUN INTERACTIVE    ----------------")
        """Runs the chatbot in interactive mode."""
        print("\n" + "="*70)
        print("🤖 DATA ANALYSIS CHATBOT - SPAIN")
        print("="*70)
        
        if self.llm_provider in ["github", "anthropic", "openai"]:
            print(f"\n✨ AI mode active ({self.llm_provider.upper()})")
            print("You can ask complex questions in natural language.\n")
        else:
            print(f"\n📝 Template mode active")
            print("For more advanced queries use: --provider github\n")

        print("📊 Example questions:")
        print("  • What are the 10 most populated provinces?")
        print("  • How has Madrid's population evolved since 2010?")
        print("  • Is there a correlation between depopulation and unemployment rate?")
        print("  • Which industrial sectors generate the most employment?")
        print("  • Compare male vs female population by province")
        print("  • Which municipalities have grown the most in the last 10 years?")
        print("\n💡 Special commands:")
        print("  • 'tables' - View available tables")
        print("  • 'schema' - View table structure")
        print("  • 'example' - View example questions")
        print("  • 'exit' - End session")
        print("\n" + "-"*70)
        
        while True:
            try:
                user_input = input("\n👤 You: ").strip()

                if user_input.lower() in ['exit', 'quit', 'q', 'salir']:
                    print("\n👋 Goodbye!")
                    break
                
                if not user_input:
                    continue
                
                # Special commands
                if user_input.lower() in ['tables', 'tablas']:
                    self._print_available_data()
                    continue
                    
                if user_input.lower() in ['schema', 'esquema']:
                    self._print_schema_details()
                    continue
                    
                if user_input.lower() in ['example', 'ejemplo']:
                    self._print_examples()
                    continue
                
                print("\n🤖 Assistant: ", end="")
                if self.llm_provider in ["github", "anthropic", "openai"]:
                    print("Analyzing your question...\n")

                response = self.chat(user_input)
                print(response)
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}\n")
    
    def _print_schema_details(self):
        """Shows table schema details."""
        print("\n📋 TABLE SCHEMA")
        print("="*50)
        for table, info in self.schema_info.items():
            print(f"\n🗄️ {table} ({info['row_count']:,} rows)")
            print("-"*40)
            for col in info['columns']:
                print(f"   • {col['column_name']}: {col['column_type']}")
    
    def _print_examples(self):
        """Shows example questions."""
        print("\n💡 ADVANCED QUESTION EXAMPLES")
        print("="*50)
        examples = [
            "What are the provinces with the highest depopulation rate?",
            "Show me the evolution of Spain's population since 2000",
            "What is the relationship between GDP and depopulation level?",
            "Which municipalities have lost the most population in the last 10 years?",
            "Compare unemployment rates between areas with high and low depopulation",
            "Which CNAE sectors have the most affiliates in Madrid?",
            "Give me a statistical summary of population by sex",
            "How many municipalities does each province have?"
        ]
        for i, ex in enumerate(examples, 1):
            print(f"  {i}. {ex}")
    
    def close(self):
        """Closes the connection."""
        self.conn.close()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Data Analysis Chatbot")
    parser.add_argument(
        "--provider", 
        choices=["github", "openai", "anthropic", "ollama", "template"],
        default="openai",
        help="LLM provider (default: template)"
    )
    parser.add_argument(
        "--database",
        choices=["duckdb", "snowflake"],
        default="duckdb",
        help="Database to query (default: duckdb)"
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Execute a single query and exit"
    )
    
    args = parser.parse_args()
    
    chatbot = DataChatbot(llm_provider=args.provider, database_type=args.database)
    
    if args.query:
        response = chatbot.chat(args.query)
        print(response)
    else:
        chatbot.run_interactive()
    
    chatbot.close()


if __name__ == "__main__":
    main()