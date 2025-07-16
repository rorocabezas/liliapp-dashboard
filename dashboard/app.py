# dashboard/app.py

import streamlit as st
from pathlib import Path
import sys

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from dashboard.auth import check_login
from dashboard.menu import render_menu
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os

st.set_page_config(page_title="Dashboard LiliApp", layout="wide")

check_login()
render_menu() 

with st.sidebar:
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(script_dir, "assets", "logo.png")
        st.image(logo_path, width=150)
    except Exception as e:
        st.error(f"Error al cargar el logo en app.py: {e}")
        
    st.markdown(f"#### Bienvenido, {st.session_state['username']}")
    st.markdown("---")
    
    # Filtro de fecha
    st.header("Filtros Disponibles")
    today = datetime.now()
    date_range = st.date_input(
        "Selecciona un rango de fechas",
        (today - timedelta(days=30), today), # Valor por defecto: últimos 30 días
        format="DD/MM/YYYY"
    )

    


@st.cache_data
def load_main_kpis(start_date, end_date):
    """
    Carga todos los KPIs principales desde la API de FastAPI.
    En el futuro, esto podría ser un único endpoint para eficiencia.
    """
    api_url = "http://127.0.0.1:8000"

    start_str = start_date.isoformat()
    end_str = end_date.isoformat()
    

    mock_data = {
        "new_users": 1250,
        "aov_clp": 58700,
        "conversion_rate": 25.5,
        "time_series_data": {
            "dates": pd.to_datetime([today - timedelta(days=i) for i in range(30)][::-1]),
            "sales": [100, 120, 110, 150, 130, 140, 160, 180, 170, 190, 200, 210, 220, 230, 240, 250, 260, 270, 280, 290, 300, 310, 320, 330, 340, 350, 360, 370, 380, 400]
        }
    }
    return mock_data
    # --------------------------------

# --- 4. CUERPO PRINCIPAL DEL DASHBOARD ---
st.title("📊 Dashboard de Business Intelligence - LiliApp")
st.markdown("### Resumen Ejecutivo")

# Verificamos que el rango de fechas sea válido
if len(date_range) == 2:
    start_date, end_date = date_range
    
    # Cargamos los datos usando nuestra función cacheada
    data = load_main_kpis(start_date, end_date)

    if data:
        # Layout de KPIs en columnas
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="Nuevos Usuarios", value=f"{data.get('new_users', 0):,}")
        with col2:
            st.metric(label="Ticket Promedio (AOV)", value=f"${data.get('aov_clp', 0):,.0f} CLP")
        with col3:
            st.metric(label="Tasa de Conversión", value=f"{data.get('conversion_rate', 0)}%")
        
        st.markdown("---")

        # Gráfico de series de tiempo
        st.subheader("Ventas en el Período Seleccionado")
        
        # Creamos un DataFrame de Pandas para el gráfico
        df_time_series = pd.DataFrame(data['time_series_data'])
        
        # Creamos la figura con Plotly Express
        fig = px.line(
            df_time_series, 
            x='dates', 
            y='sales', 
            title='Evolución de Ventas Diarias',
            labels={'dates': 'Fecha', 'sales': 'Ventas (CLP)'}
        )
        fig.update_traces(line_color='#FF4B4B', line_width=3) # Color corporativo
        
        # Mostramos el gráfico en Streamlit
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.error("No se pudieron cargar los datos desde la API.")
else:
    st.warning("Por favor, selecciona un rango de fechas válido en la barra lateral.")