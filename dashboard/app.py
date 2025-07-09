# dashboard/app.py

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from auth import check_login
import os

st.set_page_config(page_title="Dashboard LiliApp", layout="wide")

# --- 1. VERIFICACIÓN DE LOGIN ---
# Esta línea protege toda la página. Si no está logueado, se detiene aquí.
check_login()

# --- 2. LAYOUT DEL SIDEBAR (BARRA LATERAL) ---
# Aquí pondremos los filtros y el botón de logout.
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
    st.header("Filtros")
    today = datetime.now()
    date_range = st.date_input(
        "Selecciona un rango de fechas",
        (today - timedelta(days=30), today), # Valor por defecto: últimos 30 días
        format="DD/MM/YYYY"
    )

    st.markdown("---")
    if st.button("Cerrar Sesión"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# --- 3. FUNCIÓN PARA CARGAR DATOS (CON CACHÉ) ---
# Usamos el decorador de caché de Streamlit para evitar llamar a la API repetidamente.
@st.cache_data
def load_main_kpis(start_date, end_date):
    """
    Carga todos los KPIs principales desde la API de FastAPI.
    En el futuro, esto podría ser un único endpoint para eficiencia.
    """
    api_url = "http://127.0.0.1:8000"
    
    # Convertimos las fechas a string en formato ISO para la API
    start_str = start_date.isoformat()
    end_str = end_date.isoformat()
    
    # Aquí irían las llamadas a tu API. Por ahora, usamos datos de ejemplo.
    # response_kpis = requests.get(f"{api_url}/api/v1/kpis/summary?start_date={start_str}&end_date={end_str}")
    # if response_kpis.status_code == 200:
    #     return response_kpis.json()
    
    # --- Datos de Ejemplo (MOCK) ---
    # Reemplaza esto con la llamada real a tu API cuando esté lista.
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