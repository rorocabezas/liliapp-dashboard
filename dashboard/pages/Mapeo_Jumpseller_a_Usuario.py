import streamlit as st
from etl.modules.transform import transform_single_order
from dashboard.auth import check_login
from dashboard.menu import render_menu
from dashboard.api_client import get_all_jumpseller_orders, get_jumpseller_order_details
from backend.services import firestore_service # Necesitaremos leer usuarios existentes

# --- Configuración de Página y Autenticación ---
st.set_page_config(page_title="Mapeo Jumpseller a Usuario - LiliApp", layout="wide", initial_sidebar_state="expanded")
check_login()
render_menu()

# --- Funciones de Carga de Datos ---
@st.cache_data(ttl=3600)
def load_jumpseller_order_list():
    """Carga una lista ligera de órdenes desde Jumpseller para el selector."""
    with st.spinner("Cargando lista de órdenes desde Jumpseller..."):
        orders_raw = get_all_jumpseller_orders(status="paid")
    if not orders_raw: return {}
    return {str(item['order']['id']): item['order'] for item in orders_raw if 'order' in item}

@st.cache_data(ttl=60)
def load_existing_firestore_users():
    """Carga los usuarios existentes desde Firestore para la comparación."""
    try:
        users = firestore_service.get_all_documents("users")
        return {user['id']: user for user in users}
    except Exception as e:
        st.error(f"No se pudieron cargar los usuarios de Firestore: {e}")
        return {}

# --- Cuerpo del Dashboard ---
st.title("🗺️ Mapeo de Orden Jumpseller a Modelo de Usuario Firestore")
st.markdown(
    "Esta herramienta simula cómo se procesa una orden de Jumpseller para crear o actualizar los datos de un usuario "
    "en las colecciones y subcolecciones de Firestore, siguiendo las **mejores prácticas de escalabilidad**."
)

jumpseller_orders = load_jumpseller_order_list()
firestore_users = load_existing_firestore_users()

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
    format_func=lambda oid: "Selecciona una orden..." if not oid else format_option(oid)
)

if selected_order_id:
    # --- Carga y Transformación ---
    with st.spinner(f"Cargando detalles de la orden {selected_order_id}..."):
        source_order = get_jumpseller_order_details(int(selected_order_id)).get('order')

    if not source_order:
        st.error("No se pudieron cargar los detalles de la orden.")
        st.stop()
    
    user_doc, profile_doc, address_doc, order_doc = transform_single_order(source_order)
    user_id = user_doc.get('id')

    # --- Visualización ---
    st.markdown("---")
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.subheader("⬅️ Origen: Orden de Jumpseller")
        st.json(source_order, expanded=False)

    with col2:
        st.subheader("➡️ Destino: Modelo de Usuario en Firestore")
        
        # Comprobar si el usuario ya existe en Firestore
        if user_id in firestore_users:
            st.info(f"El usuario **{user_doc.get('email')}** ya existe en Firestore. El ETL actualizaría sus datos y añadiría una nueva orden/dirección.", icon="🔄")
        else:
            st.success(f"El usuario **{user_doc.get('email')}** es nuevo. El ETL crearía los siguientes documentos:", icon="✨")

        st.markdown("#### Documento en `users/{userId}`")
        st.json(user_doc)

        st.markdown(f"#### Documento en `users/{user_id}/customer_profiles/{user_id}`")
        st.json(profile_doc)
        
        address_id = address_doc.get("id")
        st.markdown(f"#### Documento en `users/{user_id}/customer_profiles/{user_id}/addresses/{address_id}`")
        st.json(address_doc)
        
        st.markdown("#### Documento en `orders/{orderId}` (relacionado por `userId`)")
        st.json(order_doc)

    st.markdown("---")
    st.subheader("💬 Explicación del Arquitecto")
    st.warning(
        """
        **¿Por qué usamos Subcolecciones y no Arreglos Anidados?**

        1.  **Escalabilidad:** Las subcolecciones permiten que un usuario tenga un número ilimitado de órdenes y direcciones sin riesgo de exceder el límite de 1MB por documento de Firestore.
        2.  **Eficiencia:** Para leer una sola dirección, solo se lee ese pequeño documento, no el perfil de usuario completo con todo su historial de órdenes.
        3.  **Consultas Potentes:** Este modelo nos permite hacer consultas globales, como "buscar todas las órdenes completadas en Santiago", lo cual es imposible si las órdenes están anidadas dentro de cada usuario.
        
        **Esta arquitectura es la recomendada por Google y es el estándar de la industria para garantizar que LiliApp pueda crecer sin problemas.**
        """,
        icon="🛡️"
    )