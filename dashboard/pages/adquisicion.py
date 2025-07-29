import streamlit as st
import pandas as pd
from datetime import datetime

# --- Importaciones de Módulos del Proyecto ---
from dashboard.auth import check_login
from dashboard.menu import render_menu
from dashboard.api_client import get_kpis_acquisition

# --- Configuración de Página y Autenticación ---
st.set_page_config(page_title="Adquisición - LiliApp BI", layout="wide")
check_login()
render_menu()

st.title("📈 Análisis de Adquisición de Clientes")
st.markdown("Métricas clave sobre cómo los nuevos clientes se unen a la plataforma.")

# --- Procesamiento de Filtros Globales ---
if 'date_range' not in st.session_state or len(st.session_state.date_range) != 2:
    st.warning("El rango de fechas no está disponible. Por favor, selecciónalo en el menú lateral.")
    st.stop()

start_date_obj, end_date_obj = st.session_state.date_range
start_date_str = start_date_obj.strftime('%Y-%m-%d')
end_date_str = end_date_obj.strftime('%Y-%m-%d')

# --- Carga de Datos desde la API ---
@st.cache_data(ttl=300)
def load_data(start_str, end_str):
    return get_kpis_acquisition(start_str, end_str)

data = load_data(start_date_str, end_date_str)

# --- Visualización del Dashboard ---
if not data:
    st.error("No se pudieron cargar los datos para el análisis. Verifica el backend y la base de datos.")
    st.stop()

# --- KPIs Principales ---
st.subheader(f"Resumen del Período: {start_date_obj.strftime('%d/%m/%Y')} al {end_date_obj.strftime('%d/%m/%Y')}")
col1, col2 = st.columns(2)
col1.metric("👤 Nuevos Usuarios Registrados", f"{data.get('new_users', 0):,}")
col2.metric("✅ Tasa de Onboarding Completado", f"{data.get('onboarding_rate', 0)}%")
st.markdown("---")

# --- Gráfico de Tendencia Diaria ---
st.subheader("Tendencia de Nuevos Usuarios por Día")
daily_data = data.get('daily_new_users', {})
if daily_data and daily_data.get('dates'):
    df_daily = pd.DataFrame(daily_data)
    df_daily['dates'] = pd.to_datetime(df_daily['dates'])
    df_daily.set_index('dates', inplace=True)
    st.line_chart(df_daily, use_container_width=True)
else:
    st.info("No hay datos diarios para mostrar en este período.")

# --- Gráfico de Distribución por Región con Insight Accionable ---
st.subheader("Distribución de Nuevos Usuarios por Región")
acquisition_by_region = data.get('acquisition_by_region', {})

if acquisition_by_region:
    # --- Lógica para el Insight ---
    total_region_users = sum(acquisition_by_region.values())
    unspecified_users = acquisition_by_region.get('No especificada', 0)
    
    if total_region_users > 0:
        unspecified_percentage = (unspecified_users / total_region_users) * 100
        if unspecified_percentage > 20: # Umbral configurable
            st.warning(
                f"**Insight Accionable:** ¡El **{unspecified_percentage:.0f}%** de los nuevos usuarios no tienen una región definida! "
                "Considera hacer este campo obligatorio durante el onboarding para mejorar la calidad de los datos y la segmentación.",
                icon="🎯"
            )
            
    # --- Visualización del Gráfico ---
    df_region = pd.DataFrame(
        list(acquisition_by_region.items()),
        columns=['Región', 'Nuevos Usuarios']
    ).sort_values('Nuevos Usuarios', ascending=False)
    
    st.bar_chart(df_region.set_index('Región'), use_container_width=True)
else:
    st.info("No hay datos de región disponibles para el período seleccionado.")