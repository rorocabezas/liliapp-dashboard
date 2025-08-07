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

st.title("🎯 Segmentación de Clientes (RFM)")
st.markdown("Análisis de **R**ecencia, **F**recuencia y Valor **M**onetario para agrupar clientes en segmentos accionables.")

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
fig = px.bar(df_dist.sort_values('Número de Clientes', ascending=False), 
             x='Segmento', y='Número de Clientes', 
             title="Clientes por Segmento RFM", text_auto=True,
             color='Segmento', color_discrete_map={
                 '🏆 Campeones': '#FFD700', # Oro
                 '💖 Leales': '#1E90FF',    # Azul
                 '😮 En Riesgo': '#FF8C00', # Naranja oscuro
                 '❄️ Hibernando': '#ADD8E6', # Azul claro
                 'Otros': '#D3D3D3'     # Gris
             })
fig.update_layout(showlegend=False)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# --- Muestra de Clientes por Segmento ---
st.subheader("Muestra de Clientes por Segmento")
st.caption("Una vista detallada de algunos clientes en cada grupo para entender su comportamiento.")

sample_customers = data.get("sample_customers", {})
# Ordenar los segmentos para una visualización consistente
sorted_segments = sorted(sample_customers.keys(), key=lambda x: segment_dist.get(x, 0), reverse=True)

for segment in sorted_segments:
    customers = sample_customers.get(segment)
    with st.expander(f"**{segment}** ({segment_dist.get(segment, 0)} clientes)"):
        if customers:
            df_sample = pd.DataFrame(customers)
            # Formatear columnas para una mejor lectura
            df_sample['monetary'] = df_sample['monetary'].apply(lambda x: f"${x:,.0f}")
            st.dataframe(df_sample.rename(columns={
                'customerId': 'ID Cliente', 'email': 'Email', 'recency': 'Recencia (días)', 
                'frequency': 'Frecuencia', 'monetary': 'Valor Monetario (CLP)'
            }), use_container_width=True, hide_index=True)
        else:
            st.write("No hay clientes de muestra para este segmento.")

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