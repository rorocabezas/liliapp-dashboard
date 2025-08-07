# dashboard/pages/operaciones.py
import streamlit as st
import pandas as pd
import plotly.express as px

# --- Importaciones de Módulos del Proyecto ---
from dashboard.auth import check_login
from dashboard.menu import render_menu
from dashboard.api_client import get_kpis
from dashboard.styles import load_custom_css, metric_card, COLOR_PRIMARY, COLOR_SUCCESS

# --- Configuración de Página ---
st.set_page_config(page_title="Operaciones - LiliApp BI", layout="wide", initial_sidebar_state="expanded")
check_login()
render_menu()
load_custom_css()

st.title("⚙️ Análisis de Operaciones y Calidad")
st.markdown("Métricas sobre la eficiencia de nuestros procesos, la carga de trabajo y la satisfacción del cliente.")

# --- Filtros y Carga de Datos ---
if 'date_range' not in st.session_state or len(st.session_state.date_range) != 2:
    st.warning("Selecciona un rango de fechas en el menú."); st.stop()

start_date_obj, end_date_obj = st.session_state.date_range
start_date_str, end_date_str = start_date_obj.strftime('%Y-%m-%d'), end_date_obj.strftime('%Y-%m-%d')

@st.cache_data(ttl=300)
def load_data(start, end):
    return get_kpis("operations", start, end)

data = load_data(start_date_str, end_date_str)

if not data:
    st.error("No se pudieron cargar los datos. Verifica el backend y la base de datos."); st.stop()

# --- Visualización de KPIs con tus Tarjetas Personalizadas ---
st.subheader(f"Resumen del Período: {start_date_obj.strftime('%d/%m/%Y')} al {end_date_obj.strftime('%d/%m/%Y')}")

cols_kpi = st.columns(2)
with cols_kpi[0]:
    metric_card(
        icon="🚫",
        title="Tasa de Cancelación",
        value=f"{data.get('cancellation_rate', 0)}%",
        background_color=COLOR_PRIMARY, # Usando tus colores definidos
        key="card_cancel"
    )
with cols_kpi[1]:
    metric_card(
        icon="⭐",
        title="Calificación Promedio",
        value=f"{data.get('avg_rating', 0):.2f} / 5.0",
        background_color=COLOR_SUCCESS, # Usando tus colores definidos
        key="card_rating"
    )
st.markdown("---")

# --- Gráficos Detallados de Operaciones ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("📍 Órdenes Completadas por Comuna (Top 10)")
    orders_by_commune = data.get('orders_by_commune', {})
    if orders_by_commune:
        df_commune = pd.DataFrame(list(orders_by_commune.items()), columns=['Comuna', 'Nº de Órdenes']).sort_values('Nº de Órdenes', ascending=False).head(10)
        st.bar_chart(df_commune.set_index('Comuna'), use_container_width=True)
    else:
        st.info("No hay datos de órdenes por comuna en este período.")

with col2:
    st.subheader("⏰ Distribución de Órdenes por Hora del Día")
    orders_by_hour = data.get('orders_by_hour', [])
    if orders_by_hour and sum(orders_by_hour) > 0:
        df_hour = pd.DataFrame({'Hora': range(24), 'Nº de Órdenes': orders_by_hour})
        fig = px.line(df_hour, x='Hora', y='Nº de Órdenes', title="Demanda Horaria", markers=True)
        fig.update_layout(xaxis_title="Hora del día (0-23)", yaxis_title="Cantidad de Órdenes")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay datos de órdenes por hora en este período.")