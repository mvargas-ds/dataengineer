# 🇪🇸 Data Engineering Pipeline - Spain Data

Data Engineering pipeline for extraction, transformation, and loading (ETL) of demographic, economic, and industrial data from Spain, with **AI-powered analysis** using LangGraph + Groq.

## 📋 Description

This project implements a modern Data Engineering architecture similar to production pipelines:

- **Extraction**: Depopulation, population by municipality, and industry data by province
- **Transformation**: Data cleaning, normalization, and enrichment
- **Loading**: Local Data Warehouse (DuckDB) or Cloud (Snowflake)
- **AI Agent**: LangGraph-powered conversational agent for depopulation analysis
- **AI-Assisted Development**: GitHub Copilot for code generation and queries

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA SOURCES                                    │
├────────────────┬────────────────────┬───────────────────────────────────────┤
│  Depopulation  │     Population     │              Industry                  │
│    (4 CSV)     │   by Municipality  │            by Province                 │
│                │     (52 CSV)       │           (44 Excel)                   │
└───────┬────────┴─────────┬──────────┴──────────────┬────────────────────────┘
        │                  │                         │
        ▼                  ▼                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          EXTRACTION (Python)                                 │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────────────────┐ │
│  │DepopulationExt.  │ │  PopulationExt.  │ │      IndustryExt.            │ │
│  └──────────────────┘ └──────────────────┘ └──────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      TRANSFORMATION (Python/Pandas)                          │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────────────────┐ │
│  │ Data Cleaning    │ │  Normalization   │ │  Enrichment                  │ │
│  │ Validation       │ │  Standardization │ │  Derived Metrics             │ │
│  └──────────────────┘ └──────────────────┘ └──────────────────────────────┘ │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
            ┌───────────────────┼───────────────────┐
            ▼                   ▼                   ▼
┌───────────────────┐ ┌─────────────────┐ ┌─────────────────────────────────┐
│   DuckDB (Local)  │ │    Snowflake    │ │   GCP (Vertex AI Datastore)     │
│   Data Warehouse  │ │  (Production)   │ │      For AI/ML                  │
└───────────────────┘ └────────┬────────┘ └─────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     🤖 AI AGENT (LangGraph + Groq)                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       Router Node                                    │   │
│  │              Analyzes question type and routes to tools              │   │
│  └───────────────────────────┬─────────────────────────────────────────┘   │
│                              │                                              │
│    ┌─────────────┬───────────┼───────────┬────────────────┐                │
│    ▼             ▼           ▼           ▼                ▼                │
│ ┌──────┐   ┌──────────┐ ┌──────────┐ ┌──────────┐  ┌──────────────┐       │
│ │ SQL  │   │   INE    │ │   Web    │ │ Scholar  │  │  Analysis    │       │
│ │ Tool │   │   Tool   │ │  Search  │ │   Tool   │  │    Tool      │       │
│ └──────┘   └──────────┘ └──────────┘ └──────────┘  └──────────────┘       │
│                     │                                                       │
│                     ▼                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │               Synthesis Node (Groq LLM - Llama/Qwen)                │   │
│  │                 Combines results + Expert insights                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
          ┌─────────────────┐ ┌─────────────────────────────────┐
          │   FastAPI REST  │ │     Command Line Interface      │
          │  localhost:8000 │ │        python -m ...            │
          └─────────────────┘ └─────────────────────────────────┘

                    ORCHESTRATION: Apache Airflow
                    CONTAINERIZATION: Docker
                    AI ASSISTANT: GitHub Copilot
```

## 📁 Project Structure

```
dataengineer/
├── 📂 src/                              # Source code
│   ├── 📂 config/                       # Configuration
│   │   ├── __init__.py
│   │   └── settings.py                  # Environment variables and constants
│   ├── 📂 etl/                          # ETL Pipeline
│   │   ├── __init__.py
│   │   ├── extractors.py                # Data extractors
│   │   ├── transformers.py              # Transformers
│   │   └── loaders.py                   # Loaders (DuckDB, Snowflake, GCS)
│   ├── 📂 pipeline/                     # Orchestration
│   │   ├── __init__.py
│   │   └── main.py                      # Main pipeline
│   ├── 📂 analytics/                    # Analysis tools
│   │   ├── chatbot.py                   # Text-to-SQL chatbot
│   │   └── 📂 agents/                   # 🤖 AI Agent System
│   │       ├── __init__.py
│   │       ├── depopulation_agent.py    # Main agent orchestrator
│   │       ├── graph.py                 # LangGraph workflow definition
│   │       ├── 📂 tools/                # Agent tools
│   │       │   ├── snowflake_tool.py    # SQL queries to Snowflake
│   │       │   ├── ine_tool.py          # INE official statistics API
│   │       │   ├── web_search_tool.py   # Web + academic search
│   │       │   └── analysis_tool.py     # Expert analysis tool
│   │       ├── 📂 prompts/              # LLM prompts
│   │       │   └── expert_prompts.py    # Domain expert prompts
│       └── 📂 memory/               # Conversation memory
│           └── conversation.py      # Memory management
│   └── 📂 api/                          # REST API (FastAPI)
│       └── main.py
├── 📂 airflow/                          # Apache Airflow
│   ├── 📂 dags/
│   │   └── spain_data_pipeline_dag.py   # Orchestration DAG
│   ├── 📂 logs/                         # Airflow logs
│   └── 📂 plugins/                      # Custom plugins
├── 📂 tests/                            # Unit tests
│   ├── __init__.py
│   └── test_pipeline.py
├── 📂 data/                             # Processed data (generated)
│   └── warehouse.duckdb                 # DuckDB database
├── 📂 raw_data/                         # Raw data sources
│   ├── 📂 despoblamiento/               # Depopulation data (4 CSV)
│   ├── 📂 industria/                    # Industry data (44 Excel)
│   └── 📂 pob_x_munic_y_sexo/           # Population data (52 CSV)
├── 📂 notebooks/                        # Jupyter notebooks
│   └── data_exploration.ipynb
├── 📄 Dockerfile                        # Pipeline container
├── 📄 Dockerfile.airflow                # Airflow container
├── 📄 docker-compose.yml                # Services orchestration
├── 📄 requirements.txt                  # Python dependencies
├── 📄 .env                              # Environment variables (not versioned)
└── 📄 README.md                         # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git

### 1. Clone and Configure

```bash
# Clone the repository
git clone https://github.com/mvargas-ds/dataengineer.git
cd dataengineer

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
copy .env.example .env
# Edit .env with your credentials
```

### 2. Run Pipeline Locally

```bash
# Run complete pipeline (uses DuckDB by default)
python -m src.pipeline.main --target duckdb --log-level INFO

# Run extraction only
python -m src.pipeline.main --phase extract

# Run transformation only
python -m src.pipeline.main --phase transform

# Load to Snowflake (requires credentials)
python -m src.pipeline.main --target snowflake
```

### 3. Run with Docker

```bash
# Build image
docker build -t dataengineer-pipeline .

# Run pipeline
docker run -v ${PWD}/data:/app/data dataengineer-pipeline

# Or with docker-compose (pipeline only)
docker-compose --profile pipeline up
```

### 4. Run with Airflow

```bash
# Create .env file with AIRFLOW_UID
echo "AIRFLOW_UID=50000" > .env

# Initialize Airflow (first time)
docker-compose --profile airflow up airflow-init

# Start all Airflow services
docker-compose --profile airflow up -d

# Access Airflow UI
# URL: http://localhost:8081
# User: admin
# Password: admin

# View logs
docker-compose --profile airflow logs -f airflow-webserver

# Stop services
docker-compose --profile airflow down
```

## 📊 Datasets

### Depopulation (4 CSV files)
Economic and demographic indicators by province:
- `despob_pob_actividad_activos_ipc_pib_2023_clusters.csv` - Data with clustering
- `despob_pob_actividad_ocupados_ipc_pib_2023_despobl_desc.csv` - Descriptive data
- `Despoblamiento_tasaActividad_2023.csv` - Activity rates
- Indicators: despopulation, population, activity/employment/unemployment rates, CPI, GDP

### Population by Municipality (52 CSV files)
Population time series (1996-2023):
- Province code and name
- Municipality code and name
- Population by sex (Total, Male, Female)
- Annual historical data

### Industry (44 Excel files)
Industrial data by province (2019):
- One Excel file per Spanish province
- Information by industrial sectors
- Employment and production metrics

## ⚙️ Configuration

### Environment Variables (.env)

```bash
# Airflow
AIRFLOW_UID=50000

# Local database
LOCAL_DB_PATH=./data/warehouse.duckdb

# Snowflake (production)
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_DATABASE=SPAIN_DATA
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_SCHEMA=PUBLIC
SNOWFLAKE_ROLE=ACCOUNTADMIN

# Groq LLM (FREE - required for AI agent)
GROQ_API_KEY=gsk_your_groq_api_key

# Web Search (optional)
TAVILY_API_KEY=tvly_your_tavily_key

# Google Cloud Platform (optional)
GCP_PROJECT_ID=your-project
GCP_BUCKET_NAME=your-bucket
GOOGLE_APPLICATION_CREDENTIALS=./credentials/gcp-sa.json
```

### Change Load Target in Airflow

In Airflow UI (Admin → Variables):
- `target_warehouse`: `duckdb` or `snowflake`
- `enable_gcp_export`: `true` or `false`

## 🔄 Pipeline DAG (Airflow)

```
start
  │
  ├──► extract_depopulation ──┬──► transform_depopulation ──┐
  ├──► extract_population ────┼──► transform_population ────┼──► load_to_warehouse
  └──► extract_industry ──────┴──► transform_industry ──────┘          │
                                                                       ▼
                                                                export_to_gcp
                                                                       │
                                                                       ▼
                                                                quality_check
                                                                       │
                                                                       ▼
                                                               send_notification
                                                                       │
                                                                       ▼
                                                                      end
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=src --cov-report=html

# Specific tests
pytest tests/test_pipeline.py::TestExtractors -v
```

---

## 🤖 AI Agent: Depopulation Analysis

### Overview

The project includes an **AI Agent** powered by **LangGraph + Groq** that can answer complex questions about rural depopulation in Spain ("España Vaciada").

**Depopulation Threshold:** Municipalities with **< 2,000 inhabitants**

**Target Users:**
- 🏛️ Government officials and policymakers
- 🎓 University professors and researchers
- 📖 Master's and PhD students
- 🏙️ Urban planners (smart cities, repopulation strategies)

### Features

| Feature | Description |
|---------|-------------|
| **Multi-tool Reasoning** | Queries Snowflake, INE, academic papers, web |
| **Conversational Memory** | Remembers context for follow-up questions |
| **Expert Analysis** | Explains correlations, factors, and trends |
| **Bilingual** | Responds in Spanish or English |
| **Multiple LLM Models** | Qwen3-32B, Llama 3.1, Llama 3.3 70B |

### Quick Start - AI Agent

```bash
# 1. Get your FREE Groq API key at: https://console.groq.com/

# 2. Add to .env file
GROQ_API_KEY=gsk_your_key_here
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_DATABASE=SPAIN_DATA

# 3. Run the agent in interactive mode
python -m src.analytics.agents.depopulation_agent

# 4. Or use the REST API
uvicorn src.api.main:app --reload --port 8000
```

### Example Questions

```
👤 How many depopulated municipalities are there in Spain?
👤 Which provinces have the highest depopulation rates?
👤 What factors contribute to rural depopulation in Teruel?
👤 Compare population trends between 2003 and 2023
👤 What strategies can help repopulate rural areas?
👤 Are there academic papers about "España vaciada"?
👤 Show me the relationship between unemployment and depopulation
```

### Available Tools

| Tool | Purpose |
|------|---------|
| `snowflake_tool` | Query population, economic, and industrial data from Snowflake |
| `ine_tool` | Fetch live data from INE (official Spanish statistics) |
| `web_search_tool` | Search news, reports, government documents |
| `analysis_tool` | Expert analysis on depopulation factors and correlations |

### Agent Architecture

```
User Question
     │
     ▼
┌─────────────────────────────────────────┐
│           LangGraph Agent               │
│  ┌─────────────────────────────────┐   │
│  │         Router Node             │   │
│  │   Analyzes question type        │   │
│  └─────────────┬───────────────────┘   │
│                │                        │
│    ┌───────────┼───────────┐           │
│    ▼           ▼           ▼           │
│ ┌──────┐  ┌──────┐  ┌──────────┐       │
│ │ SQL  │  │ INE  │  │ Web/     │       │
│ │ Tool │  │ Tool │  │ Scholar  │       │
│ └──────┘  └──────┘  └──────────┘       │
│    │           │           │           │
│    └───────────┼───────────┘           │
│                ▼                        │
│  ┌─────────────────────────────────┐   │
│  │    Synthesis Node (Groq LLM)    │   │
│  │    Combines results + insights  │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
     │
     ▼
  Response
```

---

## 🔍 Data Analysis Tools

### 1. REST API (FastAPI)

```bash
uvicorn src.api.main:app --reload --port 8000
```

**Endpoints:**
- `GET /tables` - List of tables
- `POST /query` - Execute SQL
- `GET /analytics/depopulation` - Depopulation analysis
- `GET /analytics/population` - Population analysis

Swagger documentation at `http://localhost:8000/docs`

### 2. Text-to-SQL Chatbot

```bash
# Interactive mode (template-based, no LLM)
python -m src.analytics.chatbot

# With OpenAI GPT-4
export OPENAI_API_KEY=your_api_key
python -m src.analytics.chatbot --provider openai

# With Anthropic Claude
export ANTHROPIC_API_KEY=your_api_key
python -m src.analytics.chatbot --provider anthropic
```

### 3. Direct SQL Queries

```python
import duckdb

conn = duckdb.connect('./data/warehouse.duckdb', read_only=True)

# Example query
df = conn.execute("""
    SELECT nombre_provincia, SUM(total) as poblacion
    FROM fact_poblacion
    WHERE sexo = 'Total' AND periodo = 2023
    GROUP BY nombre_provincia
    ORDER BY poblacion DESC
    LIMIT 10
""").fetchdf()

print(df)
conn.close()
```

---

## 📈 Monitoring

### Pipeline Metrics

- Rows extracted per source
- Rows transformed
- Rows loaded successfully
- Execution time per phase
- Data quality reports

### Health Checks

```bash
# Check service status
docker-compose --profile airflow ps

# View webserver logs
docker-compose --profile airflow logs airflow-webserver
```

## 🐳 Service Ports

| Service | Port | URL |
|---------|------|-----|
| Airflow UI | 8081 | http://localhost:8081 |
| FastAPI | 8000 | http://localhost:8000 |

---

## 🤖 Development with GitHub Copilot

This project uses **GitHub Copilot** as an AI assistant for:

- ETL code generation
- SQL queries and Text-to-SQL
- Debugging and optimization
- Automatic documentation

### Recommended Setup in VS Code / PyCharm:
1. Install GitHub Copilot extension
2. Authenticate with GitHub account
3. Use Copilot Chat for code queries

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/new-functionality`)
3. Commit changes (`git commit -m 'Add new functionality'`)
4. Push to branch (`git push origin feature/new-functionality`)
5. Open Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 👥 Authors

- Data Engineering Team
- GitHub: [@mvargas-ds](https://github.com/mvargas-ds)

## 🙏 Acknowledgments

- Instituto Nacional de Estadística (INE) for the data
- Apache Airflow, DuckDB, Snowflake, LangChain communities
- Groq for free LLM inference
- GitHub Copilot for development assistance
