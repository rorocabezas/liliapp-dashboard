import streamlit as st

# --- Importaciones ---
from dashboard.auth import check_login
from dashboard.menu import render_menu
from dashboard.api_client import get_all_jumpseller_orders, get_jumpseller_order_details
# Importamos la nueva función de transformación
from etl.modules.transform import transform_order_to_customer_model

# --- Configuración de Página ---
st.set_page_config(page_title="Mapeo a Cliente - LiliApp", layout="wide", initial_sidebar_state="expanded")
check_login()
render_menu()

# --- Funciones de Carga ---
@st.cache_data(ttl=3600)
def load_jumpseller_order_list():
    """Carga una lista ligera de órdenes desde Jumpseller para el selector."""
    with st.spinner("Cargando lista de órdenes desde Jumpseller..."):
        orders_raw = get_all_jumpseller_orders(status="paid")
    if not orders_raw: return {}
    return {str(item['order']['id']): item['order'] for item in orders_raw if 'order' in item}

# --- Cuerpo del Dashboard ---
st.title("🗺️ Mapeo de Orden Jumpseller al Modelo `Customer`")
st.markdown(
    "Esta herramienta simula cómo una orden de Jumpseller se transforma en un único documento denormalizado para la colección `customers`."
)

jumpseller_orders = load_jumpseller_order_list()

if not jumpseller_orders:
    st.warning("No se pudieron cargar las órdenes de Jumpseller.")
    st.stop()

# --- Selección de Orden ---
st.subheader("1. Selecciona una Orden de Jumpseller")

def format_option(order_id):
    order_data = jumpseller_orders.get(order_id, {})
    customer = order_data.get('customer') or {}
    return f"Orden ID: {order_id} (Cliente: {customer.get('fullname', 'N/A')})"

selected_order_id = st.selectbox(
    "Busca una orden:",
    options=[""] + list(jumpseller_orders.keys()),
    format_func=lambda oid: "Selecciona una orden..." if not oid else format_option(oid),
    key="customer_map_selector"
)

if selected_order_id:
    with st.spinner(f"Cargando detalles de la orden {selected_order_id}..."):
        source_order = get_jumpseller_order_details(int(selected_order_id)).get('order')

    if not source_order:
        st.error("No se pudieron cargar los detalles de la orden.")
        st.stop()
    
    # --- Llamada a la Nueva Lógica de Transformación ---
    customer_doc, order_doc = transform_order_to_customer_model(source_order)
    
    # --- Visualización ---
    st.markdown("---")
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.subheader("⬅️ Origen: Orden de Jumpseller")
        st.json(source_order, expanded=False)

    with col2:
        st.subheader("➡️ Destino: Documentos en Firestore")

        st.markdown("#### 📄 Documento para `customers/{customerId}`")
        st.info("Este documento fusiona datos de usuario, perfil y direcciones.")
        st.json(customer_doc)

        st.markdown("#### 📦 Documento para `orders/{orderId}`")
        st.info("La colección de órdenes se mantiene separada por escalabilidad.")
        st.json(order_doc)

    st.markdown("---")
    st.subheader("💬 Nota del Arquitecto: Análisis del Modelo")
    st.info(
        """
        **Ventajas de este Modelo Desnormalizado:**
        - **Lecturas Simples:** Obtener el perfil completo de un cliente y todas sus direcciones requiere **una sola lectura** de la base de datos, lo que es muy eficiente para renderizar páginas de perfil.
        - **Separación de Lógica:** Mantiene los datos de autenticación (colección `users`) separados de los datos de negocio (colección `customers`).

        **Consideraciones a Largo Plazo:**
        - **Límite de 1MB:** Aunque poco probable para direcciones, debemos monitorizar el tamaño de los documentos de clientes con muchas direcciones o datos adicionales.
        - **Actualizaciones de Direcciones:** Para añadir/modificar una dirección, el ETL deberá leer el documento del cliente, modificar el arreglo `addresses` y reescribir el documento completo. Se recomienda usar operaciones atómicas como `firestore.ArrayUnion`.
        """,
        icon="💡"
    )