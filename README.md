# 🇪🇸 Data Engineering Pipeline - Spain Data

Data Engineering pipeline for extraction, transformation, and loading (ETL) of demographic, economic, and industrial data from Spain.

## 📋 Description

This project implements a modern Data Engineering architecture similar to production pipelines:

- **Extraction**: Depopulation, population by municipality, and industry by province data
- **Transformation**: Data cleaning, normalization, and enrichment
- **Loading**: Local Data Warehouse (DuckDB) or cloud (Snowflake)
- **AI/ML Ready**: Export to Vertex AI Datastore format
- **AI-Assisted Development**: GitHub Copilot for code generation and queries

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          DATA SOURCES                                   │
├────────────────┬────────────────────┬───────────────────────────────────┤
│  Depopulation  │     Population     │            Industry               │
│    (4 CSV)     │   by Municipality  │         by Province               │
│                │    (52 CSV)        │          (44 Excel)               │
└───────┬────────┴─────────┬──────────┴──────────────┬────────────────────┘
        │                  │                         │
        ▼                  ▼                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        EXTRACTION (Python)                              │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────────────┐ │
│  │ DepopulationExt. │ │  PopulationExt.  │ │     IndustryExt.         │ │
│  └──────────────────┘ └──────────────────┘ └──────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      TRANSFORMATION (Python/Pandas)                     │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────────────┐ │
│  │ Data Cleaning    │ │  Normalization   │ │  Enrichment              │ │
│  │ Validation       │ │  Standardization │ │  Derived Metrics         │ │
│  └──────────────────┘ └──────────────────┘ └──────────────────────────┘ │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
            ┌───────────────────┼───────────────────┐
            ▼                   ▼                   ▼
┌───────────────────┐ ┌─────────────────┐ ┌─────────────────────────────┐
│   DuckDB (Local)  │ │    Snowflake    │ │   GCP (Vertex AI Datastore) │
│   Data Warehouse  │ │  (Production)   │ │      For AI/ML              │
└───────────────────┘ └─────────────────┘ └─────────────────────────────┘

                    ORCHESTRATION: Apache Airflow
                    CONTAINERIZATION: Docker
                    AI ASSISTANT: GitHub Copilot
```

## 📁 Project Structure

```
dataengineer/
├── 📂 src/                          # Source code
│   ├── 📂 config/                   # Configuration
│   │   ├── __init__.py
│   │   └── settings.py              # Environment variables and constants
│   ├── 📂 etl/                      # ETL Pipeline
│   │   ├── __init__.py
│   │   ├── extractors.py            # Data extractors
│   │   ├── transformers.py          # Transformers
│   │   └── loaders.py               # Loaders (DuckDB, Snowflake, GCS)
│   ├── 📂 pipeline/                 # Orchestration
│   │   ├── __init__.py
│   │   └── main.py                  # Main pipeline
│   ├── 📂 analytics/                # Analysis tools
│   │   └── chatbot.py               # Text-to-SQL Chatbot
│   ├── 📂 dashboard/                # Streamlit Dashboard
│   │   └── app.py
│   └── 📂 api/                      # FastAPI REST API
│       └── main.py
├── 📂 airflow/                      # Apache Airflow
│   ├── 📂 dags/
│   │   └── spain_data_pipeline_dag.py  # Orchestration DAG
│   ├── 📂 logs/                     # Airflow logs
│   └── 📂 plugins/                  # Custom plugins
├── 📂 tests/                        # Unit tests
│   ├── __init__.py
│   └── test_pipeline.py
├── 📂 data/                         # Processed data (generated)
│   └── warehouse.duckdb             # DuckDB database
├── 📂 raw_data/                     # Raw data sources
│   ├── 📂 despoblamiento/           # Depopulation data (4 CSV)
│   ├── 📂 industria/                # Industry data (44 Excel)
│   └── 📂 pob_x_munic_y_sexo/       # Population data (52 CSV)
├── 📂 notebooks/                    # Jupyter notebooks
│   └── data_exploration.ipynb
├── 📄 Dockerfile                    # Pipeline container
├── 📄 Dockerfile.airflow            # Airflow container
├── 📄 docker-compose.yml            # Service orchestration
├── 📄 requirements.txt              # Python dependencies
├── 📄 .env                          # Environment variables (not versioned)
├── 📄 .env.example                  # Environment variables example
└── 📄 README.md                     # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git
- GitHub Copilot (recommended for assisted development)

### 1. Clone and Setup

```bash
# Clone repository
git clone https://github.com/your-org/dataengineer.git
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

# Run complete pipeline (uses github as provider and Snowflake database)
python -m src.analytics.chatbot --provider github --database snowflake

# Run extraction only
python -m src.pipeline.main --phase extract

# Run transformation only
python -m src.pipeline.main --phase transform
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
# http://localhost:8081
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
- Indicators: depopulation, population, activity/employment/unemployment rates, CPI, GDP

### Population by Municipality (52 CSV files)
Population time series (1996-2023):
- Province code and name
- Municipality code and name
- Population by sex (Total, Men, Women)
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
SNOWFLAKE_DATABASE=DATA_WAREHOUSE
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_SCHEMA=PUBLIC
SNOWFLAKE_ROLE=ACCOUNTADMIN

# Google Cloud Platform (optional)
GCP_PROJECT_ID=your-project
GCP_BUCKET_NAME=your-bucket
GOOGLE_APPLICATION_CREDENTIALS=./credentials/gcp-sa.json

# LLM APIs (optional for chatbot)
OPENAI_API_KEY=your_api_key
ANTHROPIC_API_KEY=your_api_key
```

### Change loading destination in Airflow

In Airflow UI (Admin → Variables):
- `target_warehouse`: `duckdb` or `snowflake`
- `enable_gcp_export`: `true` or `false`

## 🔄 Pipeline DAG (Airflow)

```
start
  │
  ├──► extract_despoblamiento ──┬──► transform_despoblamiento ──┐
  ├──► extract_poblacion ───────┼──► transform_poblacion ───────┼──► load_to_warehouse
  └──► extract_industria ───────┴──► transform_industria ───────┘          │
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

## 🤖 Development with GitHub Copilot

This project uses **GitHub Copilot** as an AI assistant for:

- ETL code generation
- SQL queries and Text-to-SQL
- Debugging and optimization
- Automatic documentation

### Recommended configuration in VS Code / PyCharm:
1. Install GitHub Copilot extension
2. Authenticate with GitHub account
3. Use Copilot Chat for code queries

---

## 🔍 Data Analysis Tools

### 1. AI Chatbot (Text-to-SQL)

Allows **natural language** queries on the data:

```bash
# Interactive mode (without LLM - uses templates)
python -m src.analytics.chatbot

# With OpenAI GPT-4
export OPENAI_API_KEY=your_api_key
python -m src.analytics.chatbot --provider openai

# With Anthropic Claude
export ANTHROPIC_API_KEY=your_api_key
python -m src.analytics.chatbot --provider anthropic
```

**Example questions:**
- "What are the most depopulated provinces?"
- "How many inhabitants does each province have?"
- "Which industrial sectors have the most employment?"

### 2. Interactive Dashboard (Streamlit)

```bash
streamlit run src/dashboard/app.py
```

Access `http://localhost:8501` to explore interactive visualizations.

### 3. REST API (FastAPI)

```bash
uvicorn src.api.main:app --reload --port 8000
```

**Endpoints:**
- `GET /tables` - List of tables
- `POST /query` - Execute SQL
- `GET /analytics/despoblamiento` - Depopulation analysis
- `GET /analytics/poblacion` - Population analysis

Swagger documentation at `http://localhost:8000/docs`

### 4. Direct SQL Queries

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
# Check services status
docker-compose --profile airflow ps

# View webserver logs
docker-compose --profile airflow logs airflow-webserver
```

## 🐳 Service Ports

| Service | Port | URL |
|---------|------|-----|
| Airflow UI | 8081 | http://localhost:8081 |
| Streamlit Dashboard | 8501 | http://localhost:8501 |
| FastAPI | 8000 | http://localhost:8000 |

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/new-feature`)
3. Commit changes (`git commit -m 'Add new feature'`)
4. Push to branch (`git push origin feature/new-feature`)
5. Open Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 👥 Authors

- Data Engineering Team

## 🙏 Acknowledgments

- Instituto Nacional de Estadística (INE) for the data
- Apache Airflow and DuckDB communities
- GitHub Copilot for development assistance

