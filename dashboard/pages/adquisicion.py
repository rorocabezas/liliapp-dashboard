# dashboard/pages/adquisicion.py

# --- Importaciones de la librería estándar ---
import sys
from pathlib import Path

# --- Importaciones de terceros ---
import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# --- Patrón de importación para encontrar módulos locales ---
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# --- Importaciones de nuestro propio proyecto ---
from dashboard.auth import check_login
from dashboard.menu import render_menu

# --- Configuración de Página y Autenticación ---
st.set_page_config(page_title="Adquisición - LiliApp", layout="wide")
check_login() # Protege la página
render_menu() # Renderiza el menú


# --- Función para Cargar Datos desde la API ---
@st.cache_data(ttl=3600) # El caché dura 1 hora
def load_acquisition_data(start_date, end_date):
    """Llama al endpoint /acquisition de la API para obtener los datos."""
    api_url = "http://127.0.0.1:8000/api/v1/kpis/acquisition"
    params = {"start_date": start_date, "end_date": end_date}
    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status() # Lanza un error para códigos 4xx/5xx
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error al conectar con la API: {e}")
        return None


# --- Cuerpo del Dashboard - Título ---
st.title("📈 Adquisición y Crecimiento")
st.markdown("Análisis del flujo de nuevos usuarios y su activación en la plataforma.")


# --- Gráficos y Tablas ---
# Como menu.py garantiza que date_range siempre existe, podemos usarlo directamente.
start_date, end_date = st.session_state['date_range']

with st.spinner("Cargando datos de adquisición..."):
    data = load_acquisition_data(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))

if data:
    # --- KPIs Principales en Columnas ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Nuevos Usuarios", f"{data.get('new_users_count', 0):,}")
    col2.metric("Tasa de Onboarding", f"{data.get('onboarding_rate', 0)}%")
    col3.metric("Tasa de Validación RUT", f"{data.get('rut_validation_rate', 0)}%")

    st.markdown("---")

    # --- Gráficos en Columnas ---
    col_graf_1, col_graf_2 = st.columns(2)

    with col_graf_1:
        st.subheader("Canales de Adquisición")
        channel_data = data.get('channel_distribution', {})
        if channel_data:  # <-- Verificación específica para este gráfico
            df_channels = pd.DataFrame(list(channel_data.items()), columns=['Canal', 'Usuarios'])
            fig_bar = px.bar(df_channels, x='Usuarios', y='Canal', orientation='h', text_auto=True)
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No hay datos de canales de adquisición para mostrar en este período.")

    with col_graf_2:
        st.subheader("Registros por Región")
        region_data = data.get('region_distribution', {})
        if region_data:  # <-- Verificación específica para este gráfico
            df_regions = pd.DataFrame(list(region_data.items()), columns=['Región', 'Usuarios'])
            fig_pie = px.pie(df_regions, names='Región', values='Usuarios', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No hay datos de registros por región para mostrar en este período.")
else:
    st.error("No se pudieron cargar los datos desde la API. Revisa la conexión con el backend.")