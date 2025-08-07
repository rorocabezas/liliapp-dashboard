# dashboard/pages/retencion.py
import streamlit as st
import pandas as pd

# --- Importaciones de Módulos del Proyecto ---
from dashboard.auth import check_login
from dashboard.menu import render_menu
from dashboard.api_client import get_kpis
from dashboard.styles import load_custom_css, metric_card, COLOR_PRIMARY, COLOR_SECONDARY

# --- Configuración de Página ---
st.set_page_config(page_title="Retención - LiliApp BI", layout="wide", initial_sidebar_state="expanded")
check_login()
render_menu()
load_custom_css() # Inyectamos nuestros estilos personalizados

st.title("💖 Análisis de Retención y Lealtad")
st.markdown("Métricas que miden la capacidad de nuestro negocio para mantener a los clientes y maximizar su valor a lo largo del tiempo.")

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

# --- Visualización de KPIs con Tarjetas Personalizadas ---
st.subheader(f"Análisis sobre órdenes completadas entre el {start_date_obj.strftime('%d/%m/%Y')} y el {end_date_obj.strftime('%d/%m/%Y')}")

cols_kpi = st.columns(2)
with cols_kpi[0]:
    metric_card(
        icon="💰",
        title="Valor de Vida del Cliente (LTV)",
        value=f"${data.get('ltv_clp', 0):,.0f} CLP",
        background_color=COLOR_PRIMARY,
        key="card_ltv"
    )
with cols_kpi[1]:
    metric_card(
        icon="🔄",
        title="Tasa de Recompra",
        value=f"{data.get('repurchase_rate', 0)}%",
        background_color=COLOR_SECONDARY,
        key="card_repurchase"
    )

st.info(
    """
    - **LTV (Customer Lifetime Value):** Se calcula como el gasto total dividido por el número de clientes únicos que compraron en el período seleccionado. Representa el valor promedio que un cliente aporta al negocio.
    - **Tasa de Recompra:** Es el porcentaje de clientes (que compraron en el período) que han realizado más de una compra en total. Mide la lealtad y la recurrencia.
    """,
    icon="💡"
)

# --- Futuras Mejoras ---
st.markdown("---")
st.subheader("Próximamente: Análisis de Cohortes")
st.info("Aquí se podría visualizar un mapa de calor mostrando el porcentaje de clientes de un mes de registro que vuelven a comprar en los meses siguientes.")