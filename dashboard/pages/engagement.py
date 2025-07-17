# dashboard/pages/engagement.py
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

# --- Importaciones de nuestro propio proyecto ---
from dashboard.auth import check_login
from dashboard.menu import render_menu

# --- Configuración de Página y Autenticación ---
st.set_page_config(page_title="Conversión - LiliApp", layout="wide")
check_login()
render_menu()

# --- Función para Cargar Datos desde la API ---
@st.cache_data(ttl=3600)
def load_engagement_data(start_date, end_date):
    """Llama al endpoint /engagement de la API para obtener los datos."""
    api_url = "http://127.0.0.1:8000/api/v1/kpis/engagement"
    params = {"start_date": start_date, "end_date": end_date}
    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error al conectar con la API: {e}")
        return None

# --- Cuerpo del Dashboard ---
st.title("🛒 Engagement y Conversión")
st.markdown("Métricas clave del embudo de compra y comportamiento del usuario.")

start_date, end_date = st.session_state.get('date_range', (None, None))

if start_date and end_date:
    with st.spinner("Cargando datos de engagement..."):
        data = load_engagement_data(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))

    if data:
        # --- KPIs Principales en Columnas ---
        col1, col2, col3 = st.columns(3)
        col1.metric("Ticket Promedio (AOV)", f"${data.get('aov_clp', 0):,}")
        col2.metric("Tasa Abandono de Carrito", f"{data.get('abandonment_rate', 0)}%")
        col3.metric("Frecuencia de Compra", f"{data.get('purchase_frequency', 0)}")
        
        st.markdown("---")

        # --- Gráficos en Columnas ---
        col_graf_1, col_graf_2 = st.columns(2)

        with col_graf_1:
            st.subheader("Rendimiento de Servicios (Top 5)")
            service_data = data.get('service_performance', [])
            if service_data:
                df_services = pd.DataFrame(service_data)
                fig_bar = px.bar(
                    df_services, 
                    x='purchases', 
                    y='name', 
                    orientation='h',
                    title="Servicios más Comprados",
                    text='purchases'
                )
                fig_bar.update_layout(yaxis_title="Servicio", xaxis_title="N° de Compras")
                fig_bar.update_traces(marker_color='#6d28d9', textposition='outside')
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("No hay datos de rendimiento de servicios para mostrar.")

        with col_graf_2:
            st.subheader("Distribución de Métodos de Pago")
            payment_data = data.get('payment_method_distribution', {})
            if payment_data:
                df_payments = pd.DataFrame(list(payment_data.items()), columns=['Método de Pago', 'Cantidad'])
                fig_pie = px.pie(
                    df_payments, 
                    names='Método de Pago', 
                    values='Cantidad', 
                    title="Uso de Métodos de Pago en Órdenes Completadas",
                    hole=0.4
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("No hay datos de métodos de pago para mostrar.")
    else:
        st.error("No se pudieron cargar los datos para el período seleccionado.")
else:
    st.warning("Por favor, selecciona un rango de fechas para ver los datos.")