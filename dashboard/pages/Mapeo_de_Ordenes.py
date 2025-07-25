# dashboard/pages/Mapeo_de_Ordenes.py


import streamlit as st
import sys
from pathlib import Path
import json

# --- Patrón de Importación Robusto ---
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from dashboard.auth import check_login
from dashboard.menu import render_menu
from etl.modules.transform import transform_single_order

# --- Configuración de Página y Autenticación ---
st.set_page_config(page_title="Mapeo de Órdenes - LiliApp", layout="wide")
check_login()
render_menu()

# --- Carga de Datos en Caché ---
@st.cache_data
def load_source_orders():
    """Carga las órdenes desde el archivo JSON de origen."""
    source_file = project_root / "etl" / "data" / "source_orders.json"
    try:
        with open(source_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        orders = {str(item['order']['id']): item['order'] for item in raw_data if 'order' in item}
        return orders
    except Exception as e:
        st.error(f"Error al cargar source_orders.json: {e}")
        return {}

# --- Cuerpo del Dashboard ---
st.title("🔄 Herramienta de Mapeo de Órdenes (ETL)")
st.markdown("Usa esta herramienta para validar cómo una orden de Jumpseller se transforma en documentos para **cuatro** colecciones de Firestore.")

all_orders = load_source_orders()

if not all_orders:
    st.stop()

# --- 1. Selección de Orden ---
st.subheader("1. Selecciona una Orden para Analizar")

def format_order_option(order_id):
    order_data = all_orders[order_id]
    customer_name = order_data.get('customer', {}).get('fullname', 'N/A')
    return f"Orden ID: {order_id} (Cliente: {customer_name})"

selected_order_id = st.selectbox(
    "Elige una orden por su ID o cliente:",
    options=list(all_orders.keys()),
    format_func=format_order_option
)

if selected_order_id:
    source_order = all_orders[selected_order_id]
    
    # --- CAMBIO 1: Ahora esperamos 4 valores de retorno ---
    user, profile, address, order = transform_single_order(source_order)
    
    st.markdown("---")
    st.subheader("2. Visualiza la Transformación")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Datos de Origen (Jumpseller)")
        with st.expander("Ver JSON completo de la orden original"):
            st.json(source_order, expanded=False)
            
        st.write("Principales campos de origen:")
        st.text_area(
            "Fuente",
            f"ID Orden: {source_order.get('id')}\n"
            f"ID Cliente: {source_order.get('customer', {}).get('id')}\n"
            f"Cliente: {source_order.get('customer', {}).get('fullname')}\n"
            f"Email: {source_order.get('customer', {}).get('email')}\n"
            f"Total (CLP): {source_order.get('total')}\n"
            f"Dirección: {source_order.get('shipping_address', {}).get('address')}, {source_order.get('shipping_address', {}).get('municipality')}",
            height=200
        )
        
    with col2:
        st.markdown("#### Datos Transformados (Para Firestore)")

        # --- CAMBIO 2: Mostramos los 4 objetos transformados ---
        st.write("➡️ **Documento para la colección `users`**")
        st.json(user)
        
        st.write("➡️ **Documento para la subcolección `customer_profiles`**")
        st.json(profile)
        
        st.write("➡️ **Documento para la subcolección `addresses`**")
        st.json(address)
        
        st.write("➡️ **Documento para la colección `orders`**")
        st.json(order)

    st.markdown("---")
    
    # --- 3. Análisis y Siguientes Pasos ---
    st.subheader("3. Análisis y Siguientes Pasos")
    st.info(
        "Verifica que los datos de cliente y dirección se hayan extraído correctamente y que la orden tenga la estructura final deseada. "
        "Si todo se ve bien, puedes proceder con la carga masiva usando el **Panel ETL**.",
        icon="✅"
    )