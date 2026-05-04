"""
📊 Dashboard Interactivo con Streamlit
======================================
Aplicación web para exploración visual de datos.

Uso:
    streamlit run src/dashboard/app.py
"""
import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# Configuración de página
st.set_page_config(
    page_title="Data Warehouse España",
    page_icon="🇪🇸",
    layout="wide"
)

# Conexión
DB_PATH = Path(__file__).parent.parent.parent / "data" / "warehouse.duckdb"

@st.cache_resource
def get_connection():
    return duckdb.connect(str(DB_PATH), read_only=True)

@st.cache_data
def query(sql):
    conn = get_connection()
    return conn.execute(sql).fetchdf()

# Título principal
st.title("🇪🇸 Data Warehouse - España")
st.markdown("Exploración interactiva de datos de **despoblamiento**, **población** e **industria**")

# Sidebar
st.sidebar.title("📊 Navegación")
page = st.sidebar.radio("Selecciona sección:", 
    ["🏠 Inicio", "📉 Despoblamiento", "👥 Población", "🏭 Industria", "🔍 Consultas SQL"])

if page == "🏠 Inicio":
    st.header("Resumen del Data Warehouse")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        count = query("SELECT COUNT(*) as n FROM fact_despoblamiento")['n'][0]
        st.metric("📉 Despoblamiento", f"{count:,} registros")
    
    with col2:
        count = query("SELECT COUNT(*) as n FROM fact_poblacion")['n'][0]
        st.metric("👥 Población", f"{count:,} registros")
    
    with col3:
        count = query("SELECT COUNT(*) as n FROM fact_industria")['n'][0]
        st.metric("🏭 Industria", f"{count:,} registros")
    
    st.markdown("---")
    st.subheader("📋 Tablas Disponibles")
    st.dataframe(query("SHOW TABLES"))

elif page == "📉 Despoblamiento":
    st.header("Análisis de Despoblamiento")
    
    df = query("""
        SELECT porcentaje_despoblamiento, poblacion_total, 
               tasa_paro_total, tasa_empleo_total, categoria_despoblamiento
        FROM fact_despoblamiento
        WHERE porcentaje_despoblamiento IS NOT NULL
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.histogram(df, x='porcentaje_despoblamiento', 
                          title='Distribución del Despoblamiento')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        by_cat = df.groupby('categoria_despoblamiento').agg({
            'tasa_paro_total': 'mean',
            'poblacion_total': 'mean'
        }).reset_index()
        fig = px.bar(by_cat, x='categoria_despoblamiento', y='tasa_paro_total',
                    title='Tasa de Paro por Nivel de Despoblamiento')
        st.plotly_chart(fig, use_container_width=True)
    
    fig = px.scatter(df, x='tasa_empleo_total', y='tasa_paro_total',
                    color='porcentaje_despoblamiento',
                    title='Empleo vs Paro (color = despoblamiento)')
    st.plotly_chart(fig, use_container_width=True)

elif page == "👥 Población":
    st.header("Análisis de Población")
    
    year = st.slider("Selecciona año:", 2000, 2023, 2023)
    
    df_prov = query(f"""
        SELECT nombre_provincia, SUM(total) as poblacion
        FROM fact_poblacion
        WHERE sexo = 'Total' AND periodo = {year}
        GROUP BY nombre_provincia
        ORDER BY poblacion DESC
    """)
    
    fig = px.bar(df_prov.head(15), x='nombre_provincia', y='poblacion',
                title=f'Top 15 Provincias por Población ({year})')
    st.plotly_chart(fig, use_container_width=True)
    
    # Evolución
    df_evol = query("""
        SELECT periodo, SUM(total) as poblacion
        FROM fact_poblacion
        WHERE sexo = 'Total' AND periodo >= 2000
        GROUP BY periodo ORDER BY periodo
    """)
    
    fig = px.line(df_evol, x='periodo', y='poblacion',
                 title='Evolución de la Población Total')
    st.plotly_chart(fig, use_container_width=True)

elif page == "🏭 Industria":
    st.header("Análisis Industrial")
    
    df_ind = query("""
        SELECT provincia, SUM(pib_municipios_2016) as pib
        FROM fact_industria
        WHERE pib_municipios_2016 IS NOT NULL
        GROUP BY provincia ORDER BY pib DESC
    """)
    
    fig = px.bar(df_ind.head(15), x='provincia', y='pib',
                title='PIB Industrial por Provincia')
    st.plotly_chart(fig, use_container_width=True)
    
    df_sect = query("""
        SELECT aaee_seccin_cnae09 as sector, SUM(vab_corregido_2016) as vab
        FROM fact_industria
        WHERE aaee_seccin_cnae09 IS NOT NULL
        GROUP BY sector ORDER BY vab DESC LIMIT 10
    """)
    
    fig = px.pie(df_sect, values='vab', names='sector',
                title='Distribución por Sector')
    st.plotly_chart(fig, use_container_width=True)

elif page == "🔍 Consultas SQL":
    st.header("Ejecutar Consultas SQL")
    
    st.markdown("""
    Escribe una consulta SQL para explorar los datos.
    
    **Tablas disponibles:**
    - `fact_despoblamiento`
    - `fact_poblacion`  
    - `fact_industria`
    """)
    
    default_query = """SELECT nombre_provincia, SUM(total) as poblacion
FROM fact_poblacion
WHERE sexo = 'Total' AND periodo = 2023
GROUP BY nombre_provincia
ORDER BY poblacion DESC
LIMIT 10"""
    
    sql = st.text_area("Consulta SQL:", value=default_query, height=150)
    
    if st.button("▶️ Ejecutar"):
        try:
            df = query(sql)
            st.success(f"✅ {len(df)} filas retornadas")
            st.dataframe(df)
            
            # Opción de descargar
            csv = df.to_csv(index=False)
            st.download_button("📥 Descargar CSV", csv, "resultado.csv", "text/csv")
        except Exception as e:
            st.error(f"❌ Error: {e}")

# Footer
st.sidebar.markdown("---")
st.sidebar.info("🤖 Data Engineering Pipeline\nv1.0.0")

