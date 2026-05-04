"""
🌐 API REST para el Data Warehouse de España
============================================
Proporciona endpoints para consultar los datos de población,
despoblamiento e industria.

Ejecutar con:
    uvicorn src.api.main:app --reload
    
Documentación disponible en:
    http://localhost:8000/docs
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import duckdb
from pathlib import Path
from datetime import datetime

# Ruta al warehouse
DB_PATH = Path(__file__).parent.parent.parent / "data" / "warehouse.duckdb"

# Crear la aplicación FastAPI
app = FastAPI(
    title="Data Warehouse España API",
    description="API para consultar datos de población, despoblamiento e industria de España",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================
# Modelos Pydantic
# =============================================

class SQLQuery(BaseModel):
    """Modelo para consultas SQL personalizadas."""
    query: str
    
class QueryResult(BaseModel):
    """Modelo para resultados de consultas."""
    success: bool
    data: List[Dict[str, Any]]
    row_count: int
    execution_time_ms: float
    error: Optional[str] = None

class TableInfo(BaseModel):
    """Información de una tabla."""
    name: str
    columns: List[Dict[str, str]]
    row_count: int
    sample_data: List[Dict[str, Any]]


# =============================================
# Funciones de utilidad
# =============================================

def get_db_connection():
    """Obtiene una conexión a la base de datos."""
    return duckdb.connect(str(DB_PATH), read_only=True)


def execute_query(sql: str) -> QueryResult:
    """Ejecuta una consulta SQL y retorna los resultados."""
    start_time = datetime.now()
    try:
        conn = get_db_connection()
        df = conn.execute(sql).fetchdf()
        conn.close()
        
        # Convertir a lista de diccionarios
        data = df.to_dict('records')
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return QueryResult(
            success=True,
            data=data,
            row_count=len(data),
            execution_time_ms=execution_time
        )
    except Exception as e:
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        return QueryResult(
            success=False,
            data=[],
            row_count=0,
            execution_time_ms=execution_time,
            error=str(e)
        )


# =============================================
# Endpoints
# =============================================

@app.get("/", tags=["Root"])
async def root():
    """Endpoint raíz con información de la API."""
    return {
        "message": "🗄️ Data Warehouse España API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "schema": "/schema",
            "tables": "/tables",
            "poblacion": "/poblacion",
            "despoblamiento": "/despoblamiento",
            "industria": "/industria",
            "query": "/query (POST)"
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Verifica el estado de la API y la base de datos."""
    try:
        conn = get_db_connection()
        tables = conn.execute("SHOW TABLES").fetchall()
        conn.close()
        return {
            "status": "healthy",
            "database": "connected",
            "tables_count": len(tables)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }


@app.get("/schema", tags=["Schema"], response_model=List[TableInfo])
async def get_schema():
    """Obtiene información del esquema de la base de datos."""
    conn = get_db_connection()
    tables = conn.execute("SHOW TABLES").fetchall()
    
    schema_info = []
    for table in tables:
        table_name = table[0]
        columns = conn.execute(f"DESCRIBE {table_name}").fetchdf()
        sample = conn.execute(f"SELECT * FROM {table_name} LIMIT 3").fetchdf()
        count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        
        schema_info.append(TableInfo(
            name=table_name,
            columns=columns.to_dict('records'),
            row_count=count,
            sample_data=sample.to_dict('records')
        ))
    
    conn.close()
    return schema_info


@app.get("/tables", tags=["Schema"])
async def list_tables():
    """Lista todas las tablas disponibles."""
    conn = get_db_connection()
    tables = conn.execute("SHOW TABLES").fetchall()
    conn.close()
    
    return {"tables": [t[0] for t in tables]}


# =============================================
# Endpoints de Población
# =============================================

@app.get("/poblacion", tags=["Población"])
async def get_poblacion(
    provincia: Optional[str] = Query(None, description="Filtrar por provincia"),
    municipio: Optional[str] = Query(None, description="Filtrar por municipio"),
    año: Optional[int] = Query(None, description="Filtrar por año"),
    limit: int = Query(100, description="Límite de resultados", le=10000)
):
    """Obtiene datos de población."""
    sql = "SELECT * FROM fact_poblacion WHERE 1=1"
    
    if provincia:
        sql += f" AND lower(nombre_provincia) LIKE lower('%{provincia}%')"
    if municipio:
        sql += f" AND lower(nombre_municipio) LIKE lower('%{municipio}%')"
    if año:
        sql += f" AND periodo = {año}"
    
    sql += f" LIMIT {limit}"
    
    return execute_query(sql)


@app.get("/poblacion/provincias", tags=["Población"])
async def get_poblacion_provincias(año: int = Query(2023, description="Año de los datos")):
    """Obtiene población agregada por provincia."""
    sql = f"""
        SELECT 
            nombre_provincia,
            SUM(CASE WHEN sexo = 'Total' THEN total END) as poblacion_total,
            SUM(CASE WHEN sexo = 'Hombres' THEN total END) as hombres,
            SUM(CASE WHEN sexo = 'Mujeres' THEN total END) as mujeres
        FROM fact_poblacion
        WHERE periodo = {año}
        GROUP BY nombre_provincia
        ORDER BY poblacion_total DESC
    """
    return execute_query(sql)


@app.get("/poblacion/evolucion", tags=["Población"])
async def get_evolucion_poblacion(
    provincia: Optional[str] = Query(None, description="Filtrar por provincia")
):
    """Obtiene la evolución de la población a lo largo del tiempo."""
    sql = """
        SELECT 
            periodo as año,
            SUM(total) as poblacion_total
        FROM fact_poblacion
        WHERE sexo = 'Total'
    """
    
    if provincia:
        sql += f" AND lower(nombre_provincia) LIKE lower('%{provincia}%')"
    
    sql += " GROUP BY periodo ORDER BY periodo"
    
    return execute_query(sql)


# =============================================
# Endpoints de Despoblamiento
# =============================================

@app.get("/despoblamiento", tags=["Despoblamiento"])
async def get_despoblamiento(
    categoria: Optional[str] = Query(None, description="Filtrar por categoría"),
    limit: int = Query(100, description="Límite de resultados", le=1000)
):
    """Obtiene datos de despoblamiento."""
    sql = "SELECT * FROM fact_despoblamiento WHERE 1=1"
    
    if categoria:
        sql += f" AND lower(categoria_despoblamiento) LIKE lower('%{categoria}%')"
    
    sql += f" ORDER BY porcentaje_despoblamiento DESC NULLS LAST LIMIT {limit}"
    
    return execute_query(sql)


@app.get("/despoblamiento/ranking", tags=["Despoblamiento"])
async def get_ranking_despoblamiento(top: int = Query(10, description="Top N resultados")):
    """Obtiene el ranking de zonas más despobladas."""
    sql = f"""
        SELECT 
            porcentaje_despoblamiento,
            poblacion_total,
            tasa_paro_total,
            tasa_empleo_total,
            categoria_despoblamiento
        FROM fact_despoblamiento
        WHERE porcentaje_despoblamiento IS NOT NULL
        ORDER BY porcentaje_despoblamiento DESC
        LIMIT {top}
    """
    return execute_query(sql)


@app.get("/despoblamiento/estadisticas", tags=["Despoblamiento"])
async def get_estadisticas_despoblamiento():
    """Obtiene estadísticas agregadas de despoblamiento."""
    sql = """
        SELECT 
            categoria_despoblamiento,
            COUNT(*) as num_registros,
            ROUND(AVG(poblacion_total), 0) as poblacion_promedio,
            ROUND(AVG(tasa_paro_total), 2) as tasa_paro_promedio,
            ROUND(AVG(tasa_empleo_total), 2) as tasa_empleo_promedio,
            ROUND(AVG(porcentaje_despoblamiento), 2) as despoblamiento_promedio
        FROM fact_despoblamiento
        WHERE categoria_despoblamiento IS NOT NULL
        GROUP BY categoria_despoblamiento
        ORDER BY despoblamiento_promedio DESC
    """
    return execute_query(sql)


# =============================================
# Endpoints de Industria
# =============================================

@app.get("/industria", tags=["Industria"])
async def get_industria(
    provincia: Optional[str] = Query(None, description="Filtrar por provincia"),
    sector: Optional[str] = Query(None, description="Filtrar por sector CNAE"),
    limit: int = Query(100, description="Límite de resultados", le=10000)
):
    """Obtiene datos de industria."""
    sql = "SELECT * FROM fact_industria WHERE 1=1"
    
    if provincia:
        sql += f" AND lower(provincia) LIKE lower('%{provincia}%')"
    if sector:
        sql += f" AND lower(aaee_seccin_cnae09) LIKE lower('%{sector}%')"
    
    sql += f" LIMIT {limit}"
    
    return execute_query(sql)


@app.get("/industria/provincias", tags=["Industria"])
async def get_industria_provincias():
    """Obtiene datos de industria agregados por provincia."""
    sql = """
        SELECT 
            provincia,
            COUNT(DISTINCT municipio) as num_municipios,
            ROUND(SUM(pib_municipios_2016), 0) as pib_total,
            ROUND(SUM(vab_corregido_2016), 0) as valor_añadido_total,
            ROUND(SUM(afiliados_diciembre_de_2016), 0) as afiliados_total
        FROM fact_industria
        WHERE provincia IS NOT NULL
        GROUP BY provincia
        ORDER BY pib_total DESC NULLS LAST
    """
    return execute_query(sql)


@app.get("/industria/sectores", tags=["Industria"])
async def get_industria_sectores():
    """Obtiene datos de industria agregados por sector económico."""
    sql = """
        SELECT 
            aaee_seccin_cnae09 as sector,
            COUNT(*) as num_registros,
            ROUND(SUM(vab_corregido_2016), 0) as valor_añadido_total,
            ROUND(SUM(afiliados_diciembre_de_2016), 0) as afiliados_total,
            ROUND(AVG(vab_corregido_2016), 2) as valor_añadido_promedio
        FROM fact_industria
        WHERE aaee_seccin_cnae09 IS NOT NULL
        GROUP BY aaee_seccin_cnae09
        ORDER BY valor_añadido_total DESC NULLS LAST
    """
    return execute_query(sql)


# =============================================
# Consultas SQL personalizadas
# =============================================

@app.post("/query", tags=["SQL"], response_model=QueryResult)
async def execute_custom_query(query: SQLQuery):
    """
    Ejecuta una consulta SQL personalizada (solo SELECT).
    
    ⚠️ Solo se permiten consultas SELECT por seguridad.
    """
    # Validar que sea una consulta SELECT
    query_lower = query.query.strip().lower()
    if not query_lower.startswith("select"):
        raise HTTPException(
            status_code=400,
            detail="Solo se permiten consultas SELECT"
        )
    
    # Prohibir palabras peligrosas
    dangerous_words = ["drop", "delete", "update", "insert", "alter", "create", "truncate"]
    for word in dangerous_words:
        if word in query_lower:
            raise HTTPException(
                status_code=400,
                detail=f"Operación no permitida: {word}"
            )
    
    return execute_query(query.query)


# =============================================
# Main
# =============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

