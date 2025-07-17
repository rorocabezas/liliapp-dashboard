# dashboard/pages/retencion.py

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from pathlib import Path
import sys

# --- Patrón de Importación Robusto ---
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from dashboard.auth import check_login
from dashboard.menu import render_menu

# --- Configuración de Página y Autenticación ---
st.set_page_config(page_title="Retención - LiliApp", layout="wide")
check_login()
render_menu()

# --- Función para Cargar Datos desde la API ---
@st.cache_data(ttl=3600)
def load_retention_data(end_date):
    """Llama al endpoint /retention de la API para obtener los datos."""
    api_url = "http://127.0.0.1:8000/api/v1/kpis/retention"
    params = {"end_date": end_date}
    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error al conectar con la API: {e}")
        return None

# --- Cuerpo del Dashboard ---
st.title("💖 Retención y Lealtad de Clientes")
st.markdown("Métricas que miden el valor a largo plazo y la recurrencia de los clientes.")

# Usamos solo la fecha de fin del filtro global
_, end_date = st.session_state.get('date_range', (None, None))

if end_date:
    with st.spinner("Calculando KPIs de retención... Este proceso puede tardar un momento."):
        data = load_retention_data(end_date.strftime('%Y-%m-%d'))

    if data:
        # --- KPIs Principales en Columnas ---
        col1, col2, col3 = st.columns(3)
        col1.metric("Usuarios Activos Mensuales (MAU)", f"{data.get('mau', 0):,}")
        col2.metric("Valor de Vida del Cliente (LTV)", f"${data.get('ltv_clp', 0):,}")
        col3.metric("Tasa de Recompra", f"{data.get('repurchase_rate', 0)}%")
        
        st.markdown("---")

        # --- Gráfico de Cohortes ---
        st.subheader("Análisis de Cohortes de Retención Mensual")
        st.info("Este mapa de calor muestra el porcentaje de usuarios de un mes de registro (cohorte) que regresaron a comprar en los meses siguientes.", icon="ℹ️")
        
        cohort_data = data.get('cohort_data')
        if cohort_data and cohort_data['data']:
            # Reconstruimos el DataFrame desde el formato JSON 'split'
            df_retention = pd.DataFrame(cohort_data['data'], index=cohort_data['index'], columns=cohort_data['columns'])
            
            fig = px.imshow(
                df_retention,
                text_auto=".1f", # Formato del texto dentro de las celdas
                aspect="auto",
                labels=dict(x="Meses desde el Registro", y="Cohorte de Registro", color="Retención (%)"),
                color_continuous_scale=px.colors.sequential.Purples # Usamos la paleta de colores de LiliApp
            )
            fig.update_xaxes(side="top")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay suficientes datos para generar el análisis de cohortes.")
    else:
        st.error("No se pudieron cargar los datos para el período seleccionado.")
else:
    st.warning("Por favor, selecciona un rango de fechas para ver los datos.")