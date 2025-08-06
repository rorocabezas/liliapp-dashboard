# dashboard/pages/retencion.py
import streamlit as st
import pandas as pd

# --- Importaciones ---
from dashboard.auth import check_login
from dashboard.menu import render_menu
from dashboard.api_client import get_kpis

# --- Configuración de Página ---
st.set_page_config(page_title="Retención - LiliApp BI", layout="wide", initial_sidebar_state="expanded")
check_login()
render_menu()

st.title("💖 Análisis de Retención y Lealtad")
st.markdown("Métricas que miden la capacidad de nuestro negocio para mantener a los clientes a lo largo del tiempo.")

# --- Filtros y Carga de Datos ---
if 'date_range' not in st.session_state or len(st.session_state.date_range) != 2:
    st.warning("Selecciona un rango de fechas en el menú."); st.stop()

start_date_obj, end_date_obj = st.session_state.date_range
start_date_str, end_date_str = start_date_obj.strftime('%Y-%m-%d'), end_date_obj.strftime('%Y-%m-%d')

@st.cache_data(ttl=300)
def load_data(start, end):
    return get_kpis("retention", start, end)

data = load_data(start_date_str, end_date_str)

if not data:
    st.error("No se pudieron cargar los datos. Verifica el backend y la base de datos."); st.stop()

# --- Visualización de KPIs ---
st.subheader(f"Análisis sobre órdenes completadas entre el {start_date_obj.strftime('%d/%m/%Y')} y el {end_date_obj.strftime('%d/%m/%Y')}")

cols_kpi = st.columns(2)
cols_kpi[0].metric("💰 Valor de Vida del Cliente (LTV)", f"${data.get('ltv_clp', 0):,.0f} CLP")
cols_kpi[1].metric("🔄 Tasa de Recompra", f"{data.get('repurchase_rate', 0)}%")

st.info("El LTV se calcula como el gasto total dividido por el número de clientes únicos en el período. La Tasa de Recompra es el % de clientes con más de una compra.")