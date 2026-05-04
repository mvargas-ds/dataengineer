# =============================================================================
# Dockerfile para el Pipeline de Data Engineering
# =============================================================================
# Este Dockerfile crea una imagen containerizada del pipeline ETL
# que puede ser ejecutada en Azure Container Instances, GCP Cloud Run,
# o cualquier plataforma que soporte containers Docker.
#
# Uso:
#   docker build -t dataengineer-pipeline .
#   docker run -e TARGET=duckdb dataengineer-pipeline
# =============================================================================

# Imagen base con Python
FROM python:3.11-slim

# Metadatos de la imagen
LABEL maintainer="Data Engineering Team"
LABEL description="Pipeline ETL para datos de España"
LABEL version="1.0.0"

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Argumento para el target por defecto
ARG TARGET=duckdb
ENV TARGET=${TARGET}

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivos de requisitos
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copiar código fuente
COPY src/ ./src/
COPY raw_data/ ./raw_data/

# Copiar configuración
COPY .env.example ./.env

# Crear directorios necesarios
RUN mkdir -p /app/data /app/logs /app/data/processed

# Usuario no-root para seguridad
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from src.config import settings; print('OK')" || exit 1

# Comando por defecto: ejecutar el pipeline
ENTRYPOINT ["python", "-m", "src.pipeline.main"]
CMD ["--target", "duckdb", "--log-level", "INFO"]

