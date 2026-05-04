# 🇪🇸 Data Engineering Pipeline - Datos de España

Pipeline de Data Engineering para extracción, transformación y carga (ETL) de datos demográficos, económicos e industriales de España.

## 📋 Descripción

Este proyecto implementa una arquitectura moderna de Data Engineering similar a pipelines de producción:

- **Extracción**: Datos de despoblamiento, población por municipio e industria por provincia
- **Transformación**: Limpieza, normalización y enriquecimiento de datos
- **Carga**: Data Warehouse local (DuckDB) o cloud (Snowflake)
- **AI/ML Ready**: Exportación a formato Vertex AI Datastore
- **Desarrollo asistido por IA**: GitHub Copilot para generación de código y consultas

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          FUENTES DE DATOS                               │
├────────────────┬────────────────────┬───────────────────────────────────┤
│  Despoblamiento│     Población      │            Industria              │
│    (4 CSV)     │   por Municipio    │         por Provincia             │
│                │    (52 CSV)        │          (44 Excel)               │
└───────┬────────┴─────────┬──────────┴──────────────┬────────────────────┘
        │                  │                         │
        ▼                  ▼                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        EXTRACCIÓN (Python)                              │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────────────┐ │
│  │DespoblamientoExt.│ │  PoblacionExt.   │ │     IndustriaExt.        │ │
│  └──────────────────┘ └──────────────────┘ └──────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      TRANSFORMACIÓN (Python/Pandas)                     │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────────────┐ │
│  │ Limpieza Datos   │ │  Normalización   │ │  Enriquecimiento         │ │
│  │ Validación       │ │  Estandarización │ │  Métricas Derivadas      │ │
│  └──────────────────┘ └──────────────────┘ └──────────────────────────┘ │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
            ┌───────────────────┼───────────────────┐
            ▼                   ▼                   ▼
┌───────────────────┐ ┌─────────────────┐ ┌─────────────────────────────┐
│   DuckDB (Local)  │ │    Snowflake    │ │   GCP (Vertex AI Datastore) │
│   Data Warehouse  │ │  (Producción)   │ │      Para AI/ML             │
└───────────────────┘ └─────────────────┘ └─────────────────────────────┘

                    ORQUESTACIÓN: Apache Airflow
                    CONTAINERIZACIÓN: Docker
                    ASISTENTE IA: GitHub Copilot
```

## 📁 Estructura del Proyecto

```
dataengineer/
├── 📂 src/                          # Código fuente
│   ├── 📂 config/                   # Configuración
│   │   ├── __init__.py
│   │   └── settings.py              # Variables de entorno y constantes
│   ├── 📂 etl/                      # Pipeline ETL
│   │   ├── __init__.py
│   │   ├── extractors.py            # Extractores de datos
│   │   ├── transformers.py          # Transformadores
│   │   └── loaders.py               # Cargadores (DuckDB, Snowflake, GCS)
│   ├── 📂 pipeline/                 # Orquestación
│   │   ├── __init__.py
│   │   └── main.py                  # Pipeline principal
│   ├── 📂 analytics/                # Herramientas de análisis
│   │   └── chatbot.py               # Chatbot Text-to-SQL
│   ├── 📂 dashboard/                # Dashboard Streamlit
│   │   └── app.py
│   └── 📂 api/                      # API REST FastAPI
│       └── main.py
├── 📂 airflow/                      # Apache Airflow
│   ├── 📂 dags/
│   │   └── spain_data_pipeline_dag.py  # DAG de orquestación
│   ├── 📂 logs/                     # Logs de Airflow
│   └── 📂 plugins/                  # Plugins personalizados
├── 📂 tests/                        # Tests unitarios
│   ├── __init__.py
│   └── test_pipeline.py
├── 📂 data/                         # Datos procesados (generado)
│   └── warehouse.duckdb             # Base de datos DuckDB
docker-compose --profile airflow down -v├── 📂 raw_data/                     # Fuentes de datos crudos
│   ├── 📂 despoblamiento/           # Datos de despoblamiento (4 CSV)
│   ├── 📂 industria/                # Datos de industria (44 Excel)
│   └── 📂 pob_x_munic_y_sexo/       # Datos de población (52 CSV)
├── 📂 notebooks/                    # Jupyter notebooks
│   └── data_exploration.ipynb
├── 📄 Dockerfile                    # Container del pipeline
├── 📄 Dockerfile.airflow            # Container de Airflow
├── 📄 docker-compose.yml            # Orquestación de servicios
├── 📄 requirements.txt              # Dependencias Python
├── 📄 .env                          # Variables de entorno (no versionado)
├── 📄 .env.example                  # Variables de entorno ejemplo
└── 📄 README.md                     # Este archivo
```

## 🚀 Inicio Rápido

### Prerrequisitos

- Python 3.11+
- Docker & Docker Compose
- Git
- GitHub Copilot (recomendado para desarrollo asistido)

### 1. Clonar y Configurar

```bash
# Clonar el repositorio
git clone https://github.com/your-org/dataengineer.git
cd dataengineer

# Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
copy .env.example .env
# Editar .env con tus credenciales
```

### 2. Ejecutar Pipeline Localmente

```bash
# Ejecutar pipeline completo (usa DuckDB por defecto)
python -m src.pipeline.main --target duckdb --log-level INFO

# Ejecutar solo extracción
python -m src.pipeline.main --phase extract

# Ejecutar solo transformación
python -m src.pipeline.main --phase transform
```

### 3. Ejecutar con Docker

```bash
# Construir imagen
docker build -t dataengineer-pipeline .

# Ejecutar pipeline
docker run -v ${PWD}/data:/app/data dataengineer-pipeline

# O con docker-compose (solo pipeline)
docker-compose --profile pipeline up
```

### 4. Ejecutar con Airflow

```bash
# Crear archivo .env con AIRFLOW_UID
echo "AIRFLOW_UID=50000" > .env

# Inicializar Airflow (primera vez)
docker-compose --profile airflow up airflow-init

# Iniciar todos los servicios de Airflow
docker-compose --profile airflow up -d

# Acceder a Airflow UI
# http://localhost:8081
# Usuario: admin
# Contraseña: admin

# Ver logs
docker-compose --profile airflow logs -f airflow-webserver

# Detener servicios
docker-compose --profile airflow down
```

## 📊 Datasets

### Despoblamiento (4 archivos CSV)
Indicadores económicos y demográficos por provincia:
- `despob_pob_actividad_activos_ipc_pib_2023_clusters.csv` - Datos con clustering
- `despob_pob_actividad_ocupados_ipc_pib_2023_despobl_desc.csv` - Datos descriptivos
- `Despoblamiento_tasaActividad_2023.csv` - Tasas de actividad
- Indicadores: despoblamiento, población, tasas de actividad/empleo/paro, IPC, PIB

### Población por Municipio (52 archivos CSV)
Series temporales de población (1996-2023):
- Código y nombre de provincia
- Código y nombre de municipio
- Población por sexo (Total, Hombres, Mujeres)
- Datos históricos anuales

### Industria (44 archivos Excel)
Datos industriales por provincia (2019):
- Un archivo Excel por cada provincia española
- Información por sectores industriales
- Métricas de empleo y producción

## ⚙️ Configuración

### Variables de Entorno (.env)

```bash
# Airflow
AIRFLOW_UID=50000

# Base de datos local
LOCAL_DB_PATH=./data/warehouse.duckdb

# Snowflake (producción)
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_DATABASE=DATA_WAREHOUSE
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_SCHEMA=PUBLIC
SNOWFLAKE_ROLE=ACCOUNTADMIN

# Google Cloud Platform (opcional)
GCP_PROJECT_ID=your-project
GCP_BUCKET_NAME=your-bucket
GOOGLE_APPLICATION_CREDENTIALS=./credentials/gcp-sa.json

# LLM APIs (opcional para chatbot)
OPENAI_API_KEY=tu_api_key
ANTHROPIC_API_KEY=tu_api_key
```

### Cambiar destino de carga en Airflow

En la UI de Airflow (Admin → Variables):
- `target_warehouse`: `duckdb` o `snowflake`
- `enable_gcp_export`: `true` o `false`

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
# Ejecutar todos los tests
pytest tests/ -v

# Con cobertura
pytest tests/ -v --cov=src --cov-report=html

# Tests específicos
pytest tests/test_pipeline.py::TestExtractors -v
```

## 🤖 Desarrollo con GitHub Copilot

Este proyecto utiliza **GitHub Copilot** como asistente de IA para:

- Generación de código ETL
- Consultas SQL y Text-to-SQL
- Debugging y optimización
- Documentación automática

### Configuración recomendada en VS Code / PyCharm:
1. Instalar extensión GitHub Copilot
2. Autenticarse con cuenta GitHub
3. Usar Copilot Chat para consultas sobre el código

---

## 🔍 Herramientas de Análisis de Datos

### 1. Chatbot con IA (Text-to-SQL)

Permite hacer consultas en **lenguaje natural** sobre los datos:

```bash
# Modo interactivo (sin LLM - usa plantillas)
python -m src.analytics.chatbot

# Con OpenAI GPT-4
export OPENAI_API_KEY=tu_api_key
python -m src.analytics.chatbot --provider openai

# Con Anthropic Claude
export ANTHROPIC_API_KEY=tu_api_key
python -m src.analytics.chatbot --provider anthropic
```

**Ejemplos de preguntas:**
- "¿Cuáles son las provincias más despobladas?"
- "¿Cuántos habitantes tiene cada provincia?"
- "¿Qué sectores industriales tienen más empleo?"

### 2. Dashboard Interactivo (Streamlit)

```bash
streamlit run src/dashboard/app.py
```

Accede a `http://localhost:8501` para explorar visualizaciones interactivas.

### 3. API REST (FastAPI)

```bash
uvicorn src.api.main:app --reload --port 8000
```

**Endpoints:**
- `GET /tables` - Lista de tablas
- `POST /query` - Ejecutar SQL
- `GET /analytics/despoblamiento` - Análisis de despoblamiento
- `GET /analytics/poblacion` - Análisis de población

Documentación Swagger en `http://localhost:8000/docs`

### 4. Consultas SQL Directas

```python
import duckdb

conn = duckdb.connect('./data/warehouse.duckdb', read_only=True)

# Consulta de ejemplo
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

## 📈 Monitoreo

### Métricas del Pipeline

- Filas extraídas por fuente
- Filas transformadas
- Filas cargadas exitosamente
- Tiempo de ejecución por fase
- Reportes de calidad de datos

### Health Checks

```bash
# Verificar estado de servicios
docker-compose --profile airflow ps

# Ver logs del webserver
docker-compose --profile airflow logs airflow-webserver
```

## 🐳 Puertos de Servicios

| Servicio | Puerto | URL |
|----------|--------|-----|
| Airflow UI | 8081 | http://localhost:8081 |
| Streamlit Dashboard | 8501 | http://localhost:8501 |
| FastAPI | 8000 | http://localhost:8000 |

## 🤝 Contribuir

1. Fork el repositorio
2. Crear rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -m 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abrir Pull Request

## 📄 Licencia

MIT License - ver [LICENSE](LICENSE) para detalles.

---

## 👥 Autores

- Data Engineering Team

## 🙏 Agradecimientos

- Instituto Nacional de Estadística (INE) por los datos
- Apache Airflow y DuckDB communities
- GitHub Copilot por la asistencia en desarrollo
