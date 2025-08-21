# dashboard/pages/retencion.py
import streamlit as st
import pandas as pd
# --- Importaciones de Módulos del Proyecto ---
from dashboard.auth import check_login
from dashboard.menu import render_menu
from dashboard.api_client import get_kpis, get_basic_pedidos_kpis
from dashboard.api_client import get_kpis
from dashboard.styles import load_custom_css, metric_card, COLOR_PRIMARY, COLOR_SUCCESS
# --- Configuración de Página ---
st.set_page_config(page_title="Retención - LiliApp BI", layout="wide", initial_sidebar_state="expanded")
st.set_page_config(page_title="Retención y Lealtad - LiliApp BI", layout="wide", initial_sidebar_state="expanded")
render_menu()
load_custom_css() # Inyectamos nuestros estilos personalizados
load_custom_css()
st.title("💖 Análisis de Retención y Lealtad")
st.markdown("KPIs para analizar la fidelidad, recompra y valor de los clientes. Incluye cohortes y referidos si hay datos disponibles.")
# --- Filtros y Carga de Datos ---
if 'date_range' not in st.session_state or len(st.session_state.date_range) != 2:
    st.warning("Selecciona un rango de fechas en el menú."); st.stop()

start_date_obj, end_date_obj = st.session_state.date_range
start_date_str, end_date_str = start_date_obj.strftime('%Y-%m-%d'), end_date_obj.strftime('%Y-%m-%d')

@st.cache_data(ttl=300)

@st.cache_data(ttl=300)
def load_data(start, end):
    return get_kpis("retention", start, end)

data = load_data(start_date_str, end_date_str)

if not data:
    st.error("No se pudieron cargar los datos. Verifica el backend y la base de datos."); st.stop()

st.subheader(f"Resumen del Período: {start_date_obj.strftime('%d/%m/%Y')} al {end_date_obj.strftime('%d/%m/%Y')}")

cols_kpi = st.columns(3)
with cols_kpi[0]:
    metric_card(
        icon="🔁",
        title="Retención 30 días",
        value=f"{data.get('retention_30d', 0)}%",
        background_color=COLOR_PRIMARY,
        key="card_ret30"
    )
with cols_kpi[1]:
    metric_card(
        icon="💰",
        title="Valor Vida Cliente (CLV)",
        value=f"${data.get('clv', 0):,.0f}",
        background_color=COLOR_SUCCESS,
        key="card_clv"
    )
with cols_kpi[2]:
    metric_card(
        icon="👥",
        title="Usuarios Activos Mensuales (MAU)",
        value=f"{data.get('mau', 0):,}",
        background_color=COLOR_PRIMARY,
        key="card_mau"
    )
st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    st.subheader("📈 Tasa de Recompra")
    repurchase_rate = data.get('repurchase_rate', 0)
    st.metric("% Clientes Recurrentes", f"{repurchase_rate:.1f}%")

    st.subheader("📊 Pedidos Promedio por Cliente (por Comuna)")
    avg_orders_commune = data.get('avg_orders_by_commune', {})
    if isinstance(avg_orders_commune, dict) and avg_orders_commune:
        df_commune = pd.DataFrame(list(avg_orders_commune.items()), columns=['Comuna', 'Promedio Pedidos'])
        st.bar_chart(df_commune.set_index('Comuna'), use_container_width=True)
    else:
        st.info("No hay datos de pedidos por comuna.")

    st.subheader("🔥 Cohortes de Retención")
    cohort_data = data.get('retention_cohorts', None)
    if isinstance(cohort_data, pd.DataFrame) and not cohort_data.empty:
        st.dataframe(cohort_data, use_container_width=True)
    else:
        st.info("No hay datos de cohortes disponibles.")

with col2:
    st.subheader("🎯 Segmentación RFM")
    rfm_data = data.get('rfm_segments', None)
    if isinstance(rfm_data, pd.DataFrame) and not rfm_data.empty:
        import plotly.express as px
        fig_rfm = px.bar(rfm_data, x='Segmento', y='Clientes', color='Segmento', title="Distribución de Segmentos RFM")
        st.plotly_chart(fig_rfm, use_container_width=True)
    else:
        st.info("No hay datos de RFM disponibles.")

    st.subheader("🤝 Programa de Referidos")
    referred_pct = data.get('referred_pct', None)
    if referred_pct is not None:
        st.metric("% Clientes Referidos", f"{referred_pct:.1f}%")
    else:
        st.info("No hay datos de referidos.")

# --- Futuras Mejoras ---
st.markdown("---")
st.subheader("Próximamente: Análisis de Cohortes")
st.info("Aquí se podría visualizar un mapa de calor mostrando el porcentaje de clientes de un mes de registro que vuelven a comprar en los meses siguientes.")