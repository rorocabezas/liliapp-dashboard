# dashboard/pages/operaciones.py

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
st.set_page_config(page_title="Operaciones - LiliApp", layout="wide")
check_login()
render_menu()

# --- Función para Cargar Datos desde la API ---
@st.cache_data(ttl=3600)
def load_operations_data(start_date, end_date):
    """Llama al endpoint /operations de la API para obtener los datos."""
    api_url = "http://127.0.0.1:8000/api/v1/kpis/operations"
    params = {"start_date": start_date, "end_date": end_date}
    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error al conectar con la API: {e}")
        return None

# --- Cuerpo del Dashboard ---
st.title("⚙️ Operaciones y Calidad del Servicio")
st.markdown("Métricas sobre la eficiencia y la calidad de la ejecución de servicios.")

start_date, end_date = st.session_state.get('date_range', (None, None))

if start_date and end_date:
    with st.spinner("Cargando datos de operaciones..."):
        data = load_operations_data(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))

    if data:
        # --- KPIs Principales en Columnas ---
        col1, col2, col3 = st.columns(3)
        col1.metric("Tiempo de Ciclo Promedio", f"{data.get('avg_cycle_time_days', 0)} días", help="Desde el pago hasta la finalización del servicio.")
        col2.metric("Tasa de Cancelación", f"{data.get('cancellation_rate', 0)}%")
        col3.metric("Satisfacción Promedio", f"{data.get('avg_rating', 0)} ⭐")
        
        st.markdown("---")

        # --- Gráficos en Columnas ---
        col_graf_1, col_graf_2 = st.columns(2)

        with col_graf_1:
            st.subheader("Distribución de Órdenes por Comuna (Top 10)")
            commune_data = data.get('orders_by_commune', {})
            if commune_data:
                df_communes = pd.DataFrame(list(commune_data.items()), columns=['Comuna', 'Órdenes']).sort_values(by='Órdenes', ascending=False).head(10)
                fig_bar = px.bar(df_communes, x='Órdenes', y='Comuna', orientation='h', text_auto=True)
                fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
                fig_bar.update_traces(marker_color='#6d28d9')
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("No hay datos de órdenes por comuna para mostrar.")

        with col_graf_2:
            st.subheader("Distribución de Órdenes por Hora del Día")
            hour_data = data.get('orders_by_hour', [])
            if any(h > 0 for h in hour_data): # Comprueba si hay algún dato
                df_hours = pd.DataFrame({'Hora': range(24), 'Órdenes': hour_data})
                fig_line = px.line(df_hours, x='Hora', y='Órdenes', title="Horas Pico de Creación de Órdenes")
                fig_line.update_traces(line_color='#FF4B4B', line_width=3)
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.info("No hay datos de órdenes por hora para mostrar.")
    else:
        st.error("No se pudieron cargar los datos para el período seleccionado.")
else:
    st.warning("Por favor, selecciona un rango de fechas para ver los datos.")