# dashboard/pages/auditoria.py
import streamlit as st

# --- Importaciones de Módulos del Proyecto ---
from dashboard.auth import check_login
from dashboard.menu import render_menu
from dashboard.api_client import (
    get_all_jumpseller_orders, get_audit_data_for_order,
    get_all_jumpseller_products, get_audit_data_for_service # <-- Nuevas importaciones
)

# --- Configuración de Página ---
st.set_page_config(page_title="Auditoría de Datos - LiliApp", layout="wide", initial_sidebar_state="expanded")
check_login()
render_menu()

# --- Funciones de Carga de Datos ---
@st.cache_data(ttl=3600)
def load_list_for_selector(entity_type: str):
    """Carga una lista ligera de órdenes o productos para los selectores."""
    with st.spinner(f"Cargando lista de {entity_type} desde Jumpseller..."):
        if entity_type == "órdenes":
            raw_data = get_all_jumpseller_orders(status="paid")
            if not raw_data: return {}
            return {str(item['order']['id']): item['order'].get('customer', {}) for item in raw_data if 'order' in item}
        elif entity_type == "servicios":
            raw_data = get_all_jumpseller_products(status="available")
            if not raw_data: return {}
            return {str(item['product']['id']): item['product'].get('name', 'Sin Nombre') for item in raw_data if 'product' in item}
    return {}

# --- Cuerpo del Dashboard ---
st.title("🔬 Herramienta de Auditoría de Datos")
st.markdown("Compara los datos de origen (Jumpseller) con los datos cargados en Firestore para verificar la integridad del ETL.")

tab_orders, tab_services = st.tabs(["🛒 Auditoría de Órdenes", "🛠️ Auditoría de Servicios"])

# ==========================================================
# ===                PESTAÑA DE ÓRDENES                  ===
# ==========================================================
with tab_orders:
    order_list = load_list_for_selector("órdenes")
    if not order_list:
        st.warning("No se pudieron cargar las órdenes para auditar.")
    else:
        st.subheader("1. Selecciona una Orden para Auditar")
        def format_order_option(order_id):
            customer_data = order_list.get(order_id)
            if customer_data and isinstance(customer_data, dict):
                email = customer_data.get('email', 'N/A')
            else:
                email = 'Sin cliente'
            return f"Orden ID: {order_id} (Cliente: {email})"

        selected_order_id = st.selectbox(
            "Busca una orden:",
            options=[""] + list(order_list.keys()),
            format_func=lambda oid: "Selecciona una orden..." if not oid else format_order_option(oid),
            key="order_audit_selector"
        )
        if selected_order_id:
            with st.spinner(f"Cargando datos de auditoría para la orden {selected_order_id}..."):
                audit_data = get_audit_data_for_order(int(selected_order_id))
            if audit_data:
                col1, col2 = st.columns(2, gap="large")
                with col1:
                    st.markdown("#### Origen: Jumpseller")
                    st.json(audit_data.get("jumpseller_data", {}), expanded=True)
                with col2:
                    st.markdown("#### Destino: Firestore")
                    firestore_data = audit_data.get("firestore_data", {})
                    tabs = st.tabs(["Order", "User", "Profile", "Address"])
                    with tabs[0]: st.json(firestore_data.get("order"))
                    with tabs[1]: st.json(firestore_data.get("user"))
                    with tabs[2]: st.json(firestore_data.get("profile"))
                    with tabs[3]: st.json(firestore_data.get("address"))

# ==========================================================
# ===                PESTAÑA DE SERVICIOS                ===
# ==========================================================
with tab_services:
    service_list = load_list_for_selector("servicios")
    if not service_list:
        st.warning("No se pudieron cargar los servicios para auditar.")
    else:
        st.subheader("1. Selecciona un Servicio para Auditar")
        def format_service_option(service_id):
            name = service_list.get(service_id, "Nombre no disponible")
            return f"{name} (ID: {service_id})"

        selected_service_id = st.selectbox(
            "Busca un servicio:",
            options=[""] + list(service_list.keys()),
            format_func=lambda sid: "Selecciona un servicio..." if not sid else format_service_option(sid),
            key="service_audit_selector"
        )
        if selected_service_id:
            with st.spinner(f"Cargando datos de auditoría para el servicio {selected_service_id}..."):
                audit_data = get_audit_data_for_service(int(selected_service_id))
            if audit_data:
                col1, col2 = st.columns(2, gap="large")
                with col1:
                    st.markdown("#### Origen: Jumpseller")
                    st.json(audit_data.get("jumpseller_data", {}), expanded=True)
                with col2:
                    st.markdown("#### Destino: Firestore")
                    firestore_data = audit_data.get("firestore_data", {})
                    tabs = st.tabs(["Service", "Category", "Variants", "Subcategories"])
                    with tabs[0]: st.json(firestore_data.get("service"))
                    with tabs[1]: st.json(firestore_data.get("category"))
                    with tabs[2]: st.json(firestore_data.get("variants"))
                    with tabs[3]: st.json(firestore_data.get("subcategories"))