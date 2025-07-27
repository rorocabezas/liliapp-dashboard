# dashboard/pages/servicios_crud.py

import streamlit as st
import requests
import pandas as pd
from pathlib import Path
import sys
from datetime import datetime

# --- Patrón de Importación y Autenticación ---
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from dashboard.auth import check_login
from dashboard.menu import render_menu

# --- Configuración de Página y Autenticación ---
st.set_page_config(page_title="Gestión de Catálogo - LiliApp", layout="wide")
check_login()
render_menu()

# API URL base
API_URL = "http://127.0.0.1:8000/api/v1/crud"

# ===================================================================
# ===               FUNCIONES DE INTERACCIÓN CON API              ===
# ===================================================================

@st.cache_data(ttl=60)
def get_all_catalog_data():
    """Carga todos los servicios y categorías de una vez."""
    try:
        services_res = requests.get(f"{API_URL}/services")
        services_res.raise_for_status()
        categories_res = requests.get(f"{API_URL}/categories")
        categories_res.raise_for_status()
        return services_res.json(), categories_res.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error al cargar datos del catálogo: {e}")
        return [], []

@st.cache_data(ttl=30)
def get_service_components(service_id):
    """Obtiene las subcategorías y variantes de un servicio."""
    if not service_id: return [], []
    try:
        subcat_res = requests.get(f"{API_URL}/services/{service_id}/subcategories")
        variants_res = requests.get(f"{API_URL}/services/{service_id}/variants")
        return subcat_res.json() if subcat_res.ok else [], variants_res.json() if variants_res.ok else []
    except requests.exceptions.RequestException:
        return [], []

def handle_api_request(method, url, success_message, json_payload=None):
    """Función genérica para manejar peticiones y mostrar feedback."""
    try:
        response = method(url, json=json_payload)
        response.raise_for_status()
        st.toast(success_message, icon="✅")
        st.cache_data.clear() # Limpiamos todo el caché para forzar recarga
        st.rerun()
    except requests.exceptions.RequestException as e:
        error_detail = e.response.json().get('detail') if e.response else str(e)
        st.error(f"Error: {error_detail}")

# ===================================================================
# ===               CUERPO PRINCIPAL DEL DASHBOARD                ===
# ===================================================================

st.title("🛠️ Gestión de Catálogo de Servicios")
st.markdown("Administra servicios, categorías, subcategorías y variantes desde un solo lugar.")

services_data, categories_data = get_all_catalog_data()

if not categories_data:
    st.warning("No se pudieron cargar las categorías. Revisa la conexión con el backend.")
    st.stop()

# --- Diccionarios de mapeo para uso general ---
category_map = {cat['id']: cat['name'] for cat in categories_data}
service_map = {srv['id']: srv['name'] for srv in services_data}

# --- Definición de Pestañas (Tabs) ---
tab_services, tab_categories, tab_components = st.tabs(["📝 Servicios", "🗂️ Categorías", "🧬 Subcategorías y Variantes"])

# ==========================================================
# ===                    PESTAÑA DE SERVICIOS               ===
# ==========================================================
with tab_services:
    st.header("Gestión de Servicios")
    with st.expander("➕ Añadir Nuevo Servicio"):
        with st.form("create_service_form", clear_on_submit=True):
            selected_cat_id = st.selectbox(
                "Selecciona una Categoría Principal",
                options=list(category_map.keys()),
                format_func=lambda cat_id: category_map.get(cat_id, "N/A")
            )
            new_name = st.text_input("Nombre del Servicio")
            new_desc = st.text_area("Descripción")
            new_price = st.number_input("Precio Base (CLP)", min_value=0, step=1000)
            new_status = st.selectbox("Estado", options=["active", "inactive"])

            if st.form_submit_button("Guardar Servicio"):
                if new_name and selected_cat_id:
                    payload = {"name": new_name, "description": new_desc, "price": new_price, "status": new_status, "categoryId": selected_cat_id}
                    handle_api_request(requests.post, f"{API_URL}/services", "Servicio creado con éxito", json_payload=payload)
    
    st.markdown("---")
    st.header("Lista de Servicios Existentes")
    if services_data:
        df_services = pd.DataFrame(services_data)
        df_services['categoryName'] = df_services['categoryId'].map(category_map).fillna("Sin Categoría")
        
        # --- VISTA PRINCIPAL (SOLO LECTURA) ---
        display_columns = ["id", "name", "categoryName", "price", "status"]
        st.dataframe(
            df_services[display_columns],
            column_config={ "id": "ID", "name": "Nombre", "categoryName": "Categoría", "price": "Precio", "status": "Estado" },
            use_container_width=True, hide_index=True
        )

        # --- SECCIÓN DE EDICIÓN AVANZADA ---
        with st.expander("✏️ Editar Servicios (Vista Avanzada)"):
            st.warning("Los cambios en esta tabla se guardan directamente en la base de datos.", icon="⚠️")
            
            edited_df = st.data_editor(
                df_services,
                column_config={
                    "id": st.column_config.Column(disabled=True),
                    "name": st.column_config.TextColumn(required=True),
                    "price": st.column_config.NumberColumn(format="$ %d", required=True),
                    "status": st.column_config.SelectboxColumn(options=["active", "inactive"], required=True),
                    "categoryId": st.column_config.TextColumn(label="ID Categoría", required=True),
                    "description": st.column_config.TextColumn(width="large"),
                    # Ocultamos columnas que no deben ser editadas directamente
                    "createdAt": None, "hasVariants": None, "hasSubcategories": None,
                    "stats": None, "variants": None, "subcategories": None, "categoryName": None
                },
                use_container_width=True, hide_index=True, key="services_editor"
            )
            if st.button("Guardar Cambios", use_container_width=True):
                if not edited_df.empty:
                    for _, row in edited_df.iterrows():
                        payload = row.to_dict()
                        service_id = payload.pop("id")
                        handle_api_request(requests.put, f"{API_URL}/services/{service_id}", f"Servicio {service_id} actualizado", json_payload=payload)
                else:
                    st.warning("No hay cambios para guardar.")
            # TODO: Implementar lógica de guardado para st.data_editor
            # La lógica para 'edited_rows' se puede añadir aquí cuando se necesite.

    else:        
        st.info("No hay servicios disponibles. Por favor, añade uno nuevo.")

# ==========================================================
# ===                   PESTAÑA DE CATEGORÍAS             ===
# ==========================================================
with tab_categories:
    st.header("Gestión de Categorías Principales")
    with st.expander("➕ Añadir Nueva Categoría"):
        with st.form("create_category_form", clear_on_submit=True):
            cat_name = st.text_input("Nombre de la Nueva Categoría")
            if st.form_submit_button("Guardar Categoría"):
                if cat_name:
                    handle_api_request(requests.post, f"{API_URL}/categories", "Categoría creada", json_payload={"name": cat_name})
    
    st.markdown("---")
    st.header("Lista de Categorías Existentes")
    if categories_data:
        df_categories = pd.DataFrame(categories_data)
        st.dataframe(df_categories, use_container_width=True, hide_index=True)
        # TODO: Implementar lógica de edición para categorías

# ==========================================================
# ===         PESTAÑA DE COMPONENTES DE SERVICIO           ===
# ==========================================================
with tab_components:
    st.header("Gestión de Subcategorías y Variantes")
    
    # Manejo de estado para el selectbox
    if 'selected_service_id_components' not in st.session_state:
        st.session_state.selected_service_id_components = None

    selected_service_id = st.selectbox(
        "Selecciona un servicio para gestionar sus componentes:",
        options=[None] + list(service_map.keys()),
        format_func=lambda srv_id: service_map.get(srv_id, "Elige un servicio..."),
        key="selected_service_id_components"
    )
    
    if st.session_state.selected_service_id_components:
        service_details = next((s for s in services_data if s['id'] == st.session_state.selected_service_id_components), {})
        st.markdown(f"### Gestionando: **{service_details.get('name', '')}**")
        
        subcategories, variants = get_service_components(st.session_state.selected_service_id_components)
        
        col_sub, col_var = st.columns(2)
        
        with col_sub:
            st.subheader("🗂️ Subcategorías")
            with st.expander("➕ Añadir Nueva Subcategoría"):
                with st.form("create_subcategory_form", clear_on_submit=True):
                    subcat_name = st.text_input("Nombre de la Subcategoría")
                    if st.form_submit_button("Guardar Subcategoría"):
                        if subcat_name:
                            handle_api_request(requests.post, f"{API_URL}/services/{st.session_state.selected_service_id_components}/subcategories", "Subcategoría creada", json_payload={"name": subcat_name})
            
            if subcategories:
                st.dataframe(pd.DataFrame(subcategories), use_container_width=True, hide_index=True)
            else:
                st.info("Este servicio no tiene subcategorías.")

        with col_var:
            st.subheader("🧬 Variantes")
            with st.expander("➕ Añadir Nueva Variante"):
                with st.form("create_variant_form", clear_on_submit=True):
                    v_col1, v_col2 = st.columns(2)
                    with v_col1:
                        var_option_name = st.text_input("Nombre Opción", placeholder="Ej: Tamaño")
                        var_price = st.number_input("Precio (CLP)", min_value=0)
                    with v_col2:
                        var_option_value = st.text_input("Valor Opción", placeholder="Ej: Grande")
                        var_stock = st.number_input("Stock", min_value=0, value=99)
                    
                    if st.form_submit_button("Guardar Variante"):
                        if var_option_name and var_option_value:
                            payload = {"price": var_price, "options": {"name": var_option_name, "value": var_option_value}, "stock": var_stock}
                            handle_api_request(requests.post, f"{API_URL}/services/{st.session_state.selected_service_id_components}/variants", "Variante creada", json_payload=payload)

            if variants:
                st.dataframe(pd.DataFrame(variants), use_container_width=True, hide_index=True)
            else:
                st.info("Este servicio no tiene variantes.")