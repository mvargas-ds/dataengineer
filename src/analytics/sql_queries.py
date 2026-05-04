"""
Consultas Analíticas sobre el Data Warehouse.
Ejemplos de análisis de datos de España (despoblamiento, población, industria).
"""
import duckdb
from pathlib import Path
import pandas as pd
from tabulate import tabulate

# Conexión al warehouse
DB_PATH = Path(__file__).parent.parent.parent / "data" / "warehouse.duckdb"


class AnalyticsEngine:
    """Motor de consultas analíticas sobre el Data Warehouse."""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
        self.conn = duckdb.connect(self.db_path, read_only=True)
        print(f"✅ Conectado a: {self.db_path}")
        self._show_tables()
    
    def _show_tables(self):
        """Muestra las tablas disponibles."""
        tables = self.conn.execute("SHOW TABLES").fetchall()
        print(f"📊 Tablas disponibles: {[t[0] for t in tables]}")
    
    def query(self, sql: str) -> pd.DataFrame:
        """Ejecuta una consulta SQL y retorna DataFrame."""
        return self.conn.execute(sql).fetchdf()
    
    def print_query(self, sql: str, title: str = "Resultado"):
        """Ejecuta y muestra una consulta con formato."""
        print(f"\n{'='*60}")
        print(f"📈 {title}")
        print(f"{'='*60}")
        print(f"SQL: {sql[:100]}..." if len(sql) > 100 else f"SQL: {sql}")
        print("-"*60)
        df = self.query(sql)
        print(tabulate(df.head(15), headers='keys', tablefmt='psql', showindex=False))
        print(f"\nTotal filas: {len(df)}")
        return df
    
    def close(self):
        """Cierra la conexión."""
        self.conn.close()


def run_analytics_examples():
    """Ejecuta ejemplos de consultas analíticas."""
    
    engine = AnalyticsEngine()
    
    # =========================================================================
    # 1. RESUMEN GENERAL DEL WAREHOUSE
    # =========================================================================
    print("\n" + "🏠 RESUMEN DEL DATA WAREHOUSE ".center(60, "="))
    
    engine.print_query("""
        SELECT 
            'fact_despoblamiento' as tabla,
            COUNT(*) as registros
        FROM fact_despoblamiento
        UNION ALL
        SELECT 'fact_poblacion', COUNT(*) FROM fact_poblacion
        UNION ALL
        SELECT 'fact_industria', COUNT(*) FROM fact_industria
    """, "Conteo de Registros por Tabla")
    
    # =========================================================================
    # 2. ANÁLISIS DE DESPOBLAMIENTO
    # =========================================================================
    print("\n" + "📉 ANÁLISIS DE DESPOBLAMIENTO ".center(60, "="))
    
    engine.print_query("""
        SELECT 
            categoria_despoblamiento,
            COUNT(*) as provincias,
            ROUND(AVG(poblacion_total), 0) as poblacion_promedio,
            ROUND(AVG(tasa_paro_total), 2) as tasa_paro_promedio,
            ROUND(AVG(pib_precios_corrientes), 0) as pib_promedio
        FROM fact_despoblamiento
        WHERE categoria_despoblamiento IS NOT NULL
        GROUP BY categoria_despoblamiento
        ORDER BY 
            CASE categoria_despoblamiento 
                WHEN 'Bajo' THEN 1 
                WHEN 'Medio' THEN 2 
                WHEN 'Alto' THEN 3 
                WHEN 'Muy Alto' THEN 4 
            END
    """, "Indicadores por Nivel de Despoblamiento")
    
    engine.print_query("""
        SELECT 
            ROUND(porcentaje_despoblamiento, 1) as pct_despoblamiento,
            poblacion_total,
            ROUND(tasa_actividad_total, 2) as tasa_actividad,
            ROUND(tasa_empleo_total, 2) as tasa_empleo,
            ROUND(tasa_paro_total, 2) as tasa_paro,
            categoria_despoblamiento
        FROM fact_despoblamiento
        WHERE porcentaje_despoblamiento IS NOT NULL
        ORDER BY porcentaje_despoblamiento DESC
        LIMIT 10
    """, "Top 10 - Mayor Despoblamiento")
    
    # =========================================================================
    # 3. ANÁLISIS DE POBLACIÓN
    # =========================================================================
    print("\n" + "👥 ANÁLISIS DE POBLACIÓN ".center(60, "="))
    
    engine.print_query("""
        SELECT 
            nombre_provincia,
            periodo as año,
            SUM(total) as poblacion_total,
            SUM(CASE WHEN sexo = 'Hombres' THEN total ELSE 0 END) as hombres,
            SUM(CASE WHEN sexo = 'Mujeres' THEN total ELSE 0 END) as mujeres
        FROM fact_poblacion
        WHERE sexo != 'Total' AND periodo = 2023
        GROUP BY nombre_provincia, periodo
        ORDER BY poblacion_total DESC
        LIMIT 10
    """, "Top 10 Provincias por Población (2023)")
    
    engine.print_query("""
        SELECT 
            periodo as año,
            SUM(total) as poblacion_total,
            COUNT(DISTINCT codigo_municipio) as num_municipios
        FROM fact_poblacion
        WHERE sexo = 'Total' AND periodo >= 2010
        GROUP BY periodo
        ORDER BY periodo DESC
    """, "Evolución de Población Total por Año")
    
    engine.print_query("""
        SELECT 
            nombre_provincia,
            nombre_municipio,
            MAX(CASE WHEN periodo = 2023 THEN total END) as pob_2023,
            MAX(CASE WHEN periodo = 2010 THEN total END) as pob_2010,
            ROUND(
                (MAX(CASE WHEN periodo = 2023 THEN total END) - 
                 MAX(CASE WHEN periodo = 2010 THEN total END)) * 100.0 / 
                NULLIF(MAX(CASE WHEN periodo = 2010 THEN total END), 0), 2
            ) as variacion_pct
        FROM fact_poblacion
        WHERE sexo = 'Total' AND periodo IN (2010, 2023)
        GROUP BY nombre_provincia, nombre_municipio
        HAVING MAX(CASE WHEN periodo = 2010 THEN total END) > 10000
        ORDER BY variacion_pct DESC
        LIMIT 10
    """, "Municipios con Mayor Crecimiento (2010-2023)")
    
    # =========================================================================
    # 4. ANÁLISIS DE INDUSTRIA
    # =========================================================================
    print("\n" + "🏭 ANÁLISIS DE INDUSTRIA ".center(60, "="))
    
    engine.print_query("""
        SELECT 
            provincia,
            COUNT(DISTINCT municipio) as num_municipios,
            ROUND(SUM(pib_municipios_2016), 0) as pib_total,
            ROUND(AVG(pib_municipios_2016), 0) as pib_promedio
        FROM fact_industria
        WHERE pib_municipios_2016 IS NOT NULL
        GROUP BY provincia
        ORDER BY pib_total DESC
        LIMIT 10
    """, "Top 10 Provincias por PIB Industrial")
    
    engine.print_query("""
        SELECT 
            aaee_seccin_cnae09 as sector,
            COUNT(*) as num_registros,
            ROUND(SUM(vab_corregido_2016), 0) as vab_total,
            ROUND(SUM(afiliados_diciembre_de_2016), 0) as total_afiliados
        FROM fact_industria
        WHERE aaee_seccin_cnae09 IS NOT NULL
        GROUP BY aaee_seccin_cnae09
        ORDER BY vab_total DESC
        LIMIT 10
    """, "Top Sectores por Valor Añadido Bruto")
    
    # =========================================================================
    # 5. ANÁLISIS CRUZADO
    # =========================================================================
    print("\n" + "🔗 ANÁLISIS CRUZADO ".center(60, "="))
    
    engine.print_query("""
        WITH industria_prov AS (
            SELECT 
                provincia,
                ROUND(SUM(pib_municipios_2016), 0) as pib_industrial
            FROM fact_industria
            WHERE pib_municipios_2016 IS NOT NULL
            GROUP BY provincia
        )
        SELECT 
            d.categoria_despoblamiento,
            COUNT(*) as num_registros,
            ROUND(AVG(d.poblacion_total), 0) as poblacion_promedio,
            ROUND(AVG(d.pib_precios_corrientes), 0) as pib_promedio,
            ROUND(AVG(d.tasa_paro_total), 2) as tasa_paro_promedio
        FROM fact_despoblamiento d
        WHERE d.categoria_despoblamiento IS NOT NULL
        GROUP BY d.categoria_despoblamiento
    """, "Relación Despoblamiento - Indicadores Económicos")
    
    engine.close()
    print("\n" + "✅ ANÁLISIS COMPLETADO ".center(60, "="))


if __name__ == "__main__":
    try:
        from tabulate import tabulate
    except ImportError:
        print("Instalando tabulate...")
        import subprocess
        subprocess.run(["pip", "install", "tabulate", "-q"])
        from tabulate import tabulate
    
    run_analytics_examples()

