# dashboard/pages/segmentacion.py
import streamlit as st
import pandas as pd
import plotly.express as px

# --- Importaciones ---
from dashboard.auth import check_login
from dashboard.menu import render_menu
from dashboard.api_client import get_kpis

# --- Configuración de Página ---
st.set_page_config(page_title="Segmentación - LiliApp BI", layout="wide", initial_sidebar_state="expanded")
check_login()
render_menu()

st.title("🎯 Segmentación de Clientes (RFM)")
st.markdown("Análisis de Recencia, Frecuencia y Valor Monetario para agrupar clientes en segmentos accionables.")

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

# --- Visualización del Dashboard ---
st.subheader(f"Análisis sobre órdenes completadas entre el {start_date_obj.strftime('%d/%m/%Y')} y el {end_date_obj.strftime('%d/%m/%Y')}")

segment_dist = data.get("segment_distribution", {})

if not segment_dist:
    st.info("No hay suficientes datos de órdenes en este período para generar segmentos RFM.")
    st.stop()

# --- Gráfico de Distribución de Segmentos ---
st.subheader("Distribución de Clientes por Segmento")
df_dist = pd.DataFrame(list(segment_dist.items()), columns=['Segmento', 'Número de Clientes'])
fig = px.bar(df_dist, x='Segmento', y='Número de Clientes', 
             title="Clientes por Segmento RFM", text_auto=True,
             color='Segmento', color_discrete_map={
                 '🏆 Campeones': 'gold', '💖 Leales': 'royalblue',
                 '😮 En Riesgo': 'darkorange', '❄️ Hibernando': 'lightskyblue', 'Otros': 'grey'
             })
fig.update_layout(showlegend=False)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# --- Muestra de Clientes por Segmento ---
st.subheader("Muestra de Clientes por Segmento")
st.caption("Una vista detallada de algunos clientes en cada grupo para entender su comportamiento.")

sample_customers = data.get("sample_customers", {})
for segment, customers in sample_customers.items():
    with st.expander(f"**{segment}** ({segment_dist.get(segment, 0)} clientes)"):
        if customers:
            df_sample = pd.DataFrame(customers)
            st.dataframe(df_sample, use_container_width=True, hide_index=True)
        else:
            st.write("No hay clientes de muestra para este segmento.")

# --- Explicación de los Segmentos ---
st.markdown("---")
st.subheader("📖 ¿Qué significa cada segmento?")
st.markdown("""
- **🏆 Campeones:** Tus mejores clientes. Compraron recientemente, compran a menudo y gastan más. ¡Hay que fidelizarlos!
- **💖 Leales:** Clientes que compran con buena frecuencia. Responden bien a programas de lealtad.
- **😮 En Riesgo:** Compraron bastante y gastaron bien, pero **hace mucho tiempo que no vuelven**. ¡Necesitan una campaña de reactivación!
- **❄️ Hibernando:** Clientes de bajo valor que compraron hace mucho. Podrían perderse si no se les contacta.
- **Otros:** Clientes que no encajan claramente en los segmentos principales.
""")