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
    if isinstance(orders_by_commune, dict) and orders_by_commune:
        df_commune = pd.DataFrame(list(orders_by_commune.items()), columns=['Comuna', 'Nº de Órdenes']).sort_values('Nº de Órdenes', ascending=False).head(10)
        st.bar_chart(df_commune.set_index('Comuna'), use_container_width=True)
    else:
        st.info("No hay datos de órdenes por comuna en este período.")

    st.subheader("📄 Pedidos con Boleta Adjunta")
    boleta_pct = data.get('orders_with_boleta_pct', 0)
    boleta_pct_val = 0.0
    if boleta_pct is not None:
        try:
            boleta_pct_val = float(boleta_pct)
        except (TypeError, ValueError):
            boleta_pct_val = 0.0
    st.metric("% Pedidos con Boleta", f"{boleta_pct_val:.1f}%")

    st.subheader("🕒 Tiempo Promedio de Ejecución")
    avg_exec_time = data.get('avg_exec_time', None)
    avg_exec_time_val = None
    if avg_exec_time is not None:
        try:
            avg_exec_time_val = float(avg_exec_time)
        except (TypeError, ValueError):
            avg_exec_time_val = None
    if avg_exec_time_val is not None:
        st.metric("Promedio ejecución", f"{avg_exec_time_val:.2f} días")
    else:
        st.info("No hay datos de tiempo de ejecución.")

    st.subheader("🕒 Tiempo Promedio por Etapa")
    avg_stage_time = data.get('avg_stage_time', None)
    avg_stage_time_val = None
    if avg_stage_time is not None:
        try:
            avg_stage_time_val = float(avg_stage_time)
        except (TypeError, ValueError):
            avg_stage_time_val = None
    if avg_stage_time_val is not None:
        st.metric("Promedio por etapa", f"{avg_stage_time_val:.2f} hrs")
    else:
        st.info("No hay datos de etapas.")

with col2:
    st.subheader("⏰ Distribución de Órdenes por Hora del Día")
    orders_by_hour = data.get('orders_by_hour', [])
    if isinstance(orders_by_hour, list) and orders_by_hour and all(isinstance(x, (int, float)) for x in orders_by_hour):
        if sum(orders_by_hour) > 0:
            df_hour = pd.DataFrame({'Hora': range(len(orders_by_hour)), 'Nº de Órdenes': orders_by_hour})
            fig = px.line(df_hour, x='Hora', y='Nº de Órdenes', title="Demanda Horaria", markers=True)
            fig.update_layout(xaxis_title="Hora del día (0-23)", yaxis_title="Cantidad de Órdenes")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos de órdenes por hora en este período.")
    else:
        st.info("No hay datos de órdenes por hora en este período.")

    st.subheader("📊 Pedidos por Estado de Ejecución")
    exec_states = data.get('orders_by_exec_state', {})
    if isinstance(exec_states, dict) and exec_states:
        df_state = pd.DataFrame(list(exec_states.items()), columns=['Estado', 'Órdenes'])
        fig2 = px.pie(df_state, names='Estado', values='Órdenes', color_discrete_sequence=px.colors.sequential.RdBu)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No hay datos de estado de ejecución disponibles.")

    st.subheader("👨‍🔧 Pedidos por Profesional (Top 5)")
    by_prof = data.get('orders_by_professional', {})
    if isinstance(by_prof, dict) and by_prof:
        df_prof = pd.DataFrame(list(by_prof.items()), columns=['Profesional', 'Órdenes'])
        df_prof = df_prof.sort_values('Órdenes', ascending=False).head(5)
        st.table(df_prof)
    else:
        st.info("No hay datos de profesionales disponibles.")

    st.subheader("👤 Pedidos por Cliente (Top 5)")
    by_client = data.get('orders_by_client', {})
    if isinstance(by_client, dict) and by_client:
        df_client = pd.DataFrame(list(by_client.items()), columns=['Cliente', 'Órdenes'])
        df_client = df_client.sort_values('Órdenes', ascending=False).head(5)
        st.table(df_client)
    else:
        st.info("No hay datos de clientes disponibles.")