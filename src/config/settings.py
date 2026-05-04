"""
Central configuration for the Data Engineering pipeline.
Manages environment variables and project constants.
"""
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project base directory
BASE_DIR = Path(__file__).parent.parent.parent


class SnowflakeConfig(BaseModel):
    """Snowflake connection configuration."""
    account: str = Field(default_factory=lambda: os.getenv("SNOWFLAKE_ACCOUNT", ""))
    user: str = Field(default_factory=lambda: os.getenv("SNOWFLAKE_USER", ""))
    password: str = Field(default_factory=lambda: os.getenv("SNOWFLAKE_PASSWORD", ""))
    database: str = Field(default_factory=lambda: os.getenv("SNOWFLAKE_DATABASE", "DATA_WAREHOUSE"))
    schema_name: str = Field(default_factory=lambda: os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC"))
    warehouse: str = Field(default_factory=lambda: os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"))
    role: str = Field(default_factory=lambda: os.getenv("SNOWFLAKE_ROLE", "DATA_ENGINEER"))


class GCPConfig(BaseModel):
    """Google Cloud Platform configuration."""
    project_id: str = Field(default_factory=lambda: os.getenv("GCP_PROJECT_ID", ""))
    bucket_name: str = Field(default_factory=lambda: os.getenv("GCP_BUCKET_NAME", ""))
    vertex_datastore_id: str = Field(default_factory=lambda: os.getenv("GCP_VERTEX_DATASTORE_ID", ""))
    credentials_path: str = Field(
        default_factory=lambda: os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    )


class AzureConfig(BaseModel):
    """Azure configuration."""
    storage_connection_string: str = Field(
        default_factory=lambda: os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
    )
    container_name: str = Field(
        default_factory=lambda: os.getenv("AZURE_CONTAINER_NAME", "data-pipeline")
    )
    subscription_id: str = Field(
        default_factory=lambda: os.getenv("AZURE_SUBSCRIPTION_ID", "")
    )
    resource_group: str = Field(
        default_factory=lambda: os.getenv("AZURE_RESOURCE_GROUP", "")
    )


class PipelineConfig(BaseModel):
    """General pipeline configuration."""
    local_db_path: str = Field(
        default_factory=lambda: os.getenv("LOCAL_DB_PATH", "./data/warehouse.duckdb")
    )
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    batch_size: int = Field(default_factory=lambda: int(os.getenv("BATCH_SIZE", "10000")))
    data_source_path: Path = Field(
        default_factory=lambda: Path(os.getenv("DATA_SOURCE_PATH", BASE_DIR))
    )
    output_path: Path = Field(
        default_factory=lambda: Path(os.getenv("OUTPUT_PATH", BASE_DIR / "data" / "processed"))
    )

    class Config:
        arbitrary_types_allowed = True


class Settings(BaseModel):
    """Global project configuration."""
    snowflake: SnowflakeConfig = Field(default_factory=SnowflakeConfig)
    gcp: GCPConfig = Field(default_factory=GCPConfig)
    azure: AzureConfig = Field(default_factory=AzureConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)


# Global configuration instance
settings = Settings()


# Data paths
DATA_PATHS = {
    "despoblamiento": BASE_DIR / "raw_data" / "despoblamiento",
    "industria": BASE_DIR / "raw_data" / "industria",
    "poblacion": BASE_DIR / "raw_data" / "pob_x_munic_y_sexo",
}

# Warehouse table schemas
TABLE_SCHEMAS = {
    "dim_provincia": {
        "codigo_provincia": "INTEGER PRIMARY KEY",
        "nombre_provincia": "VARCHAR(100)",
        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    },
    "dim_municipio": {
        "id_municipio": "INTEGER PRIMARY KEY",
        "codigo_municipio": "VARCHAR(20)",
        "nombre_municipio": "VARCHAR(200)",
        "codigo_provincia": "INTEGER",
        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    },
    "fact_despoblamiento": {
        "id": "INTEGER PRIMARY KEY",
        "codigo_provincia": "INTEGER",
        "porcen_desp": "FLOAT",
        "pob_tot": "INTEGER",
        "pob_hom": "INTEGER",
        "pob_muj": "INTEGER",
        "tasa_actividad": "FLOAT",
        "tasa_empleo": "FLOAT",
        "tasa_paro": "FLOAT",
        "ipc_general": "FLOAT",
        "pib_total": "FLOAT",
        "anio": "INTEGER",
        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    },
    "fact_poblacion_municipio": {
        "id": "INTEGER PRIMARY KEY",
        "codigo_provincia": "INTEGER",
        "codigo_municipio": "VARCHAR(20)",
        "sexo": "VARCHAR(20)",
        "periodo": "INTEGER",
        "total_poblacion": "INTEGER",
        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    },
    "fact_industria": {
        "id": "INTEGER PRIMARY KEY",
        "codigo_provincia": "INTEGER",
        "nombre_provincia": "VARCHAR(100)",
        "sector": "VARCHAR(200)",
        "valor": "FLOAT",
        "anio": "INTEGER",
        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    }
}

