# dashboard/pages/1_📈_Adquisición_y_Crecimiento.py
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

import streamlit as st
from dashboard.auth import check_login
from dashboard.menu import render_menu
import plotly.express as px
import pandas as pd
from dashboard.auth import check_login



st.set_page_config(page_title="Adquisición - LiliApp", layout="wide")
check_login() # Protege la página
render_menu() # Renderiza el menú

# --- Función de Carga de Datos ---
@st.cache_data(ttl=600)
def load_data(start_date, end_date):
    # En un futuro, llamarías al endpoint /acquisition
    # Por ahora, usamos datos de ejemplo
    mock_data = {
        "new_users": 1345,
        "onboarding_rate": 78.2,
        "acquisition_channels": {"Google Ads": 550, "Referidos": 400, "Facebook": 395},
        "rut_validation_rate": 62.1
    }
    return mock_data


# --- Título y Filtros ---
st.title("📈 Adquisición y Crecimiento")
st.subheader("Nuevos Usuarios y Activación")
st.markdown("Análisis del flujo de nuevos usuarios y su activación en la plataforma.")

# Reutilizamos el filtro de fecha de la página principal
if 'date_range' in st.session_state:
    start_date, end_date = st.session_state['date_range']
    data = load_data(start_date, end_date)

    if data:
        # --- KPIs Principales ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Nuevos Usuarios", f"{data['new_users']:,}")
        col2.metric("Tasa de Onboarding", f"{data['onboarding_rate']}%")
        col3.metric("Tasa de Validación RUT", f"{data['rut_validation_rate']}%")

        st.markdown("---")

        # --- Visualizaciones ---
        st.subheader("Canales de Adquisición")
        
        channels_df = pd.DataFrame(
            list(data['acquisition_channels'].items()), 
            columns=['Canal', 'Nuevos Usuarios']
        )
        
        fig = px.bar(
            channels_df, 
            x='Canal', 
            y='Nuevos Usuarios', 
            title='Distribución de Nuevos Usuarios por Canal',
            text_auto=True
        )
        fig.update_traces(marker_color='#6d28d9')
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("No se pudieron cargar los datos.")
else:
    st.warning("Por favor, selecciona un rango de fechas en la página principal.")