# dashboard/pages/segmentacion.py
import streamlit as st
import pandas as pd
import plotly.express as px

# --- Importaciones de Módulos del Proyecto ---
from dashboard.auth import check_login
from dashboard.menu import render_menu
from dashboard.api_client import get_kpis
from dashboard.styles import load_custom_css # Solo necesitamos el CSS aquí

# --- Configuración de Página ---
st.set_page_config(page_title="Segmentación - LiliApp BI", layout="wide", initial_sidebar_state="expanded")
check_login()
render_menu()
load_custom_css()

st.title("🎯 Métricas de Segmentación y Marketing")
st.markdown("KPIs para agrupar clientes por especialidad, región, antigüedad, ticket promedio, RFM, campañas y referidos.")

# --- Filtros y Carga de Datos ---
if 'date_range' not in st.session_state or len(st.session_state.date_range) != 2:
    st.warning("Selecciona un rango de fechas en el menú."); st.stop()

start_date_obj, end_date_obj = st.session_state.date_range
start_date_str, end_date_str = start_date_obj.strftime('%Y-%m-%d'), end_date_obj.strftime('%Y-%m-%d')

@st.cache_data(ttl=300)
def load_data(start, end):
    return get_kpis("segmentation", start, end)

data = load_data(start_date_str, end_date_str)

if not data:
    st.error("No se pudieron cargar los datos. Verifica el backend y la base de datos."); st.stop()

st.subheader(f"Análisis sobre órdenes completadas entre el {start_date_obj.strftime('%d/%m/%Y')} y el {end_date_obj.strftime('%d/%m/%Y')}")

# --- Segmentación por Especialidad ---
st.subheader("🔧 Segmentación por Especialidad")
specialties = data.get('specialties_distribution', {})
if specialties:
    df_spec = pd.DataFrame(list(specialties.items()), columns=['Especialidad', 'Pedidos'])
    st.bar_chart(df_spec.set_index('Especialidad'), use_container_width=True)
else:
    st.info("No hay datos de especialidades.")

# --- Segmentación por Región/Comuna ---
st.subheader("🌎 Segmentación por Región/Comuna")
region_dist = data.get('region_distribution', {})
if region_dist:
    df_region = pd.DataFrame(list(region_dist.items()), columns=['Región/Comuna', 'Pedidos'])
    st.bar_chart(df_region.set_index('Región/Comuna'), use_container_width=True)
else:
    st.info("No hay datos de región/comuna.")

# --- Segmentación por Antigüedad ---
st.subheader("📅 Segmentación por Antigüedad")
cohort_dist = data.get('cohort_distribution', {})
if cohort_dist:
    df_cohort = pd.DataFrame(list(cohort_dist.items()), columns=['Cohorte', 'Clientes'])
    st.line_chart(df_cohort.set_index('Cohorte'), use_container_width=True)
else:
    st.info("No hay datos de cohortes de registro.")

# --- Segmentación por Ticket Promedio ---
st.subheader("💸 Segmentación por Ticket Promedio")
ticket_dist = data.get('ticket_distribution', {})
if ticket_dist:
    df_ticket = pd.DataFrame(list(ticket_dist.items()), columns=['Nivel de Gasto', 'Clientes'])
    st.bar_chart(df_ticket.set_index('Nivel de Gasto'), use_container_width=True)
else:
    st.info("No hay datos de ticket promedio.")

# --- Segmentación RFM ---
st.subheader("🎯 Segmentación RFM")
rfm_segments = data.get('rfm_segments', pd.DataFrame())
if isinstance(rfm_segments, pd.DataFrame) and not rfm_segments.empty:
    fig_rfm = px.bar(rfm_segments, x='Segmento', y='Clientes', color='Segmento', title="Distribución de Segmentos RFM")
    st.plotly_chart(fig_rfm, use_container_width=True)
else:
    st.info("No hay datos de RFM disponibles.")

# --- Efectividad de Campañas ---
st.subheader("📢 Efectividad de Campañas")
campaign_dist = data.get('campaign_distribution', {})
if campaign_dist:
    df_campaign = pd.DataFrame(list(campaign_dist.items()), columns=['Campaña', 'Pedidos'])
    st.bar_chart(df_campaign.set_index('Campaña'), use_container_width=True)
else:
    st.info("No hay datos de campañas.")

# --- Programa de Referidos ---
st.subheader("🤝 Programa de Referidos")
referred_pct = data.get('referred_pct', None)
if referred_pct is not None:
    st.metric("% Clientes Referidos", f"{referred_pct:.1f}%")
else:
    st.info("No hay datos de referidos.")

# --- Predicción de Churn ---
st.subheader("⚠️ Predicción de Churn (Riesgo de Abandono)")
churn_dist = data.get('churn_distribution', {})
if churn_dist:
    df_churn = pd.DataFrame(list(churn_dist.items()), columns=['Nivel de Riesgo', 'Clientes'])
    st.bar_chart(df_churn.set_index('Nivel de Riesgo'), use_container_width=True)
else:
    st.info("No hay datos de churn.")

# Si no hay datos de segmentación relevantes, mostrar KPIs básicos de pedidos
if not any([
    specialties,
    region_dist,
    cohort_dist,
    ticket_dist,
    isinstance(rfm_segments, pd.DataFrame) and not rfm_segments.empty,
    campaign_dist,
    referred_pct,
    churn_dist
]):
    st.subheader(f"KPIs básicos de pedidos entre el {start_date_obj.strftime('%d/%m/%Y')} y el {end_date_obj.strftime('%d/%m/%Y')}")
    cols_kpi = st.columns(3)
    with cols_kpi[0]:
        st.metric("Total de Pedidos", f"{data.get('total_pedidos', 0):,}")
    with cols_kpi[1]:
        st.metric("Monto Total Vendido", f"${data.get('monto_total', 0):,.0f}")
    with cols_kpi[2]:
        st.metric("Calificación Promedio", f"{data.get('calificacion_promedio', 0):.2f}")
    st.markdown("### Pedidos por Estado")
    st.write(data.get('pedidos_por_estado', {}))
    st.markdown("### Top 5 Clientes por Pedidos")
    pedidos_por_cliente = data.get('pedidos_por_cliente', {})
    if isinstance(pedidos_por_cliente, dict):
        top_clientes = sorted(pedidos_por_cliente.items(), key=lambda x: x[1], reverse=True)[:5]
        st.write(top_clientes)
    else:
        st.write(pedidos_por_cliente)
    st.markdown("### Métodos de Pago")
    st.write(data.get('metodos_pago', {}))
    st.markdown("### Pedidos por Comuna")
    st.write(data.get('pedidos_por_comuna', {}))

# --- Explicación de los Segmentos ---
st.markdown("---")
st.subheader("📖 ¿Qué significa cada segmento?")
st.markdown("""
- **🏆 Campeones:** Tus mejores clientes. Compraron recientemente, compran a menudo y gastan más. **Acción:** Fidelizarlos con beneficios exclusivos.
- **💖 Leales:** Clientes que compran con buena frecuencia, pero podrían gastar más. **Acción:** Ofrecerles productos complementarios (cross-selling).
- **😮 En Riesgo:** Gastaron bien, pero **hace mucho tiempo que no vuelven**. **Acción:** ¡Campaña de reactivación urgente con un descuento atractivo!
- **❄️ Hibernando:** Clientes de bajo valor que compraron hace mucho. **Acción:** Incluirlos en newsletters generales para mantener el contacto sin invertir demasiado.
- **Otros:** Clientes que no encajan claramente en los segmentos principales, a menudo nuevos. **Acción:** Observar y guiar hacia la lealtad.
""")