# dashboard/pages/Mapeo_de_Ordenes.py
import streamlit as st
from etl.modules.transform import transform_single_order
from dashboard.auth import check_login
from dashboard.menu import render_menu
from dashboard.api_client import get_all_jumpseller_orders, get_jumpseller_order_details

# --- Configuración de Página y Autenticación ---
st.set_page_config(page_title="Mapeo de Órdenes (ETL) - LiliApp", layout="wide")
check_login()
render_menu()

# --- Carga de Datos en Caché (Paso 1: Lista Ligera) ---
@st.cache_data(ttl=3600)
def load_order_list_for_selector():
    """
    Carga una lista de órdenes con datos mínimos para poblar el selector.
    """
    with st.spinner("Cargando lista de órdenes..."):
        orders_raw = get_all_jumpseller_orders(status="paid")
    
    if not orders_raw:
        st.error("No se pudieron cargar órdenes. Verifica la conexión del backend.")
        return {}
    
    return {
        str(item['order']['id']): item['order'].get('customer') 
        for item in orders_raw if 'order' in item
    }

# --- Cuerpo del Dashboard ---
st.title("🔄 Herramienta de Mapeo y Diagnóstico de Órdenes (ETL)")
st.markdown("Valida cómo una orden **en vivo** de Jumpseller se deconstruye en documentos para las colecciones de Firestore.")

order_list_for_selector = load_order_list_for_selector()

if not order_list_for_selector:
    st.warning("No hay órdenes disponibles para mapear.")
    st.stop()

# --- 1. Selección de Orden ---
st.subheader("1. Selecciona una Orden para Analizar")

def format_order_option(order_id):
    """Formatea la etiqueta para el selector con protección contra None."""
    customer_data = order_list_for_selector.get(order_id)
    if customer_data:
        customer_identifier = customer_data.get('email', 'Cliente no identificado')
    else:
        customer_identifier = 'Sin cliente asociado'
    return f"Orden ID: {order_id} (Cliente: {customer_identifier})"

selected_order_id = st.selectbox(
    "Busca y elige una orden:",
    options=[""] + list(order_list_for_selector.keys()),
    format_func=lambda oid: "Selecciona una orden..." if oid == "" else format_order_option(oid),
    key="order_selector"
)

# --- Lógica de Carga de Detalles y Transformación ---
if selected_order_id:
    # --- PASO 2: OBTENER LOS DETALLES COMPLETOS DE LA ORDEN SELECCIONADA ---
    with st.spinner(f"Cargando detalles completos de la orden {selected_order_id}..."):
        # La API de detalle devuelve el objeto anidado en 'order'
        detailed_order_response = get_jumpseller_order_details(selected_order_id)
        source_order = detailed_order_response.get('order') if detailed_order_response else None

    if not source_order:
        st.error(f"No se pudieron cargar los detalles para la orden {selected_order_id}. Puede que ya no exista o haya un error de API.")
        st.stop()
        
    # --- PASO 3: TRANSFORMAR EL OBJETO DETALLADO Y RICO EN DATOS ---
    user_doc, profile_doc, address_doc, order_doc = transform_single_order(source_order)
    
    st.markdown("---")
    st.subheader("2. Visualización Comparativa: Jumpseller vs. Firestore")
    
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        st.markdown("#### Origen: Jumpseller (Datos Completos)")
        customer_info = source_order.get('customer', {})
        shipping_info = source_order.get('shipping_address', {})
        
        # Este bloque ahora se poblará correctamente con los datos ricos
        source_display_text = (
            f"ID Orden: {source_order.get('id')}\n"
            f"Estado: {source_order.get('status')}\n"
            f"Total: ${source_order.get('total', 0):,}\n"
            f"----------------------------------\n"
            f"ID Cliente: {customer_info.get('id')}\n"
            f"Nombre Cliente: {customer_info.get('fullname')}\n"
            f"Email Cliente: {customer_info.get('email')}\n"
            f"----------------------------------\n"
            f"Dirección: {shipping_info.get('address')}, {shipping_info.get('city')}"
        )
        st.text_area("Resumen de la Orden Fuente:", value=source_display_text, height=250)
        with st.expander("Ver JSON completo de la orden original"):
            st.json(source_order)
            
    with col2:
        st.markdown("#### Destino: Firestore (Simulación)")
        tab_user, tab_profile, tab_address, tab_order = st.tabs(["👤 User", "📋 Profile", "🏠 Address", "🛒 Order"])

        with tab_user:
            st.json(user_doc)
        with tab_profile:
            st.json(profile_doc)
        with tab_address:
            st.json(address_doc)
        with tab_order:
            st.json(order_doc)

    st.markdown("---")
    
    # --- Diagnóstico de Integridad (ahora funciona sobre datos correctos) ---
    st.subheader("3. Diagnóstico de Integridad de Claves")
    st.markdown("Verifica que los IDs generados se conecten correctamente entre los documentos.")

    all_docs_valid = user_doc and profile_doc and address_doc and order_doc
    if all_docs_valid:
        user_id_check = (user_doc.get('id') == profile_doc.get('userId') == order_doc.get('userId'))
        address_id_check = (address_doc.get('id') == order_doc.get('addressId'))

        if user_id_check:
            st.success(f"✅ **Conexión de Usuario Correcta:** El `userId` (`{user_doc.get('id')}`) es consistente en los documentos de perfil y orden.")
        else:
            st.error("🚨 **Error de Conexión de Usuario:** El `userId` no coincide. Revisa la lógica de `transform_single_order`.")

        if address_id_check:
            st.success(f"✅ **Conexión de Dirección Correcta:** El `addressId` (`{address_doc.get('id')}`) se ha enlazado correctamente a la orden.")
        else:
            st.error("🚨 **Error de Conexión de Dirección:** El `addressId` no coincide. Revisa la lógica de `transform_single_order`.")
    else:
        st.warning("No se pudieron generar todos los documentos necesarios para el análisis de integridad.")