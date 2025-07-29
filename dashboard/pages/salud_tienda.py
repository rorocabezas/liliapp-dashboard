import streamlit as st
from pathlib import Path
import sys

# --- Patrón de Importación y Autenticación ---
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))
from dashboard.auth import check_login
from dashboard.menu import render_menu
from dashboard.api_client import get_store_health_summary

st.set_page_config(page_title="Salud de la Tienda - LiliApp", layout="wide")
check_login()
render_menu()

st.title("🩺 Dashboard de Salud de la Tienda Jumpseller")
st.markdown("Métricas clave obtenidas en tiempo real desde la API de Jumpseller.")

# Función para cargar datos con cache
@st.cache_data(ttl=300) # Cache por 5 minutos
def load_health_data():
    summary_response = get_store_health_summary()
    if summary_response and 'health_summary' in summary_response:
        return summary_response['health_summary']
    return None

if st.button("Recargar Datos"):
    st.cache_data.clear()

data = load_health_data()

if data:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(label="🛍️ Órdenes Totales", value=f"{data.get('orders', 0):,}")
    col2.metric(label="📦 Productos Activos", value=f"{data.get('products', 0):,}")
    col3.metric(label="👥 Clientes Registrados", value=f"{data.get('customers', 0):,}")
    col4.metric(label="📚 Categorías Definidas", value=f"{data.get('categories', 0):,}")
    
    st.info("Los datos se actualizan automáticamente cada 5 minutos o al presionar 'Recargar Datos'.")
else:
    st.warning("No se pudo cargar el resumen de salud de la tienda. Asegúrate de que el backend esté funcionando.")