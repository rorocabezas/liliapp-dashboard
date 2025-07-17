# dashboard/pages/segmentacion.py

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
st.set_page_config(page_title="Segmentación - LiliApp", layout="wide")
check_login()
render_menu()

# --- Función para Cargar Datos desde la API ---
@st.cache_data(ttl=3600)
def load_segmentation_data(end_date):
    """Llama al endpoint /segmentation de la API para obtener los datos."""
    api_url = "http://127.0.0.1:8000/api/v1/kpis/segmentation"
    params = {"end_date": end_date}
    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error al conectar con la API: {e}")
        return None

# --- Cuerpo del Dashboard ---
st.title("🎯 Segmentación y Marketing")
st.markdown("Análisis RFM para agrupar clientes según su comportamiento de compra.")

_, end_date = st.session_state.get('date_range', (None, None))

if end_date:
    with st.spinner("Realizando análisis RFM... Este proceso puede tardar un momento."):
        data = load_segmentation_data(end_date.strftime('%Y-%m-%d'))

    if data and data.get('segment_distribution'):
        # --- Gráfico de Distribución de Segmentos ---
        st.subheader("Distribución de Clientes por Segmento")
        
        segment_data = data.get('segment_distribution', {})
        df_segments = pd.DataFrame(list(segment_data.items()), columns=['Segmento', 'Número de Clientes'])
        
        fig = px.treemap(
            df_segments, 
            path=[px.Constant("Todos los Clientes"), 'Segmento'], 
            values='Número de Clientes',
            color='Número de Clientes',
            color_continuous_scale='Purples'
        )
        fig.update_layout(margin = dict(t=50, l=25, r=25, b=25))
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")

        # --- Explorador de Segmentos ---
        st.subheader("Explorar Segmentos de Clientes")
        
        sample_data = data.get('sample_customers', {})
        
        # Creamos un selectbox para que el usuario elija un segmento
        segment_to_show = st.selectbox(
            "Selecciona un segmento para ver una muestra de clientes:",
            options=list(sample_data.keys())
        )
        
        if segment_to_show:
            st.write(f"**Muestra de clientes en el segmento '{segment_to_show}':**")
            
            customers_in_segment = sample_data[segment_to_show]
            df_sample = pd.DataFrame(customers_in_segment)
            
            # Mostramos la tabla con los datos RFM
            st.dataframe(
                df_sample[['customerId', 'recency', 'frequency', 'monetary', 'segment']],
                use_container_width=True,
                column_config={
                    "customerId": "ID Cliente",
                    "recency": st.column_config.NumberColumn("Recencia (días)", help="Días desde la última compra"),
                    "frequency": st.column_config.NumberColumn("Frecuencia", help="Número total de compras"),
                    "monetary": st.column_config.NumberColumn("Valor Monetario (CLP)", format="$ %d")
                }
            )
            st.info("Utiliza esta lista para campañas de marketing dirigidas, como enviar un cupón de reactivación a los clientes 'En Riesgo'.", icon="💡")

    else:
        st.error("No se pudieron cargar los datos de segmentación.")
else:
    st.warning("Por favor, selecciona un rango de fechas para ver los datos.")