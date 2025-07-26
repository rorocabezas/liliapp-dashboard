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

@st.cache_data(ttl=60) # Cache de 1 minuto
def get_all_data():
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

def update_document(collection_name, doc_id, data):
    """Función genérica para actualizar cualquier documento."""
    try:
        response = requests.put(f"{API_URL}/{collection_name}/{doc_id}", json=data)
        response.raise_for_status()
        st.toast(response.json().get("message"), icon="✅")
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Error al actualizar: {e.response.json().get('detail') if e.response else str(e)}")
        return False

def create_document(collection_name, data):
    """Función genérica para crear cualquier documento."""
    try:
        # Añadimos campos por defecto si es un servicio
        if collection_name == "services":
            data['createdAt'] = datetime.now().isoformat()
            data['hasVariants'] = False
            data['hasSubcategories'] = False
            data['stats'] = {"viewCount": 0, "purchaseCount": 0, "averageRating": 0.0}

        response = requests.post(f"{API_URL}/{collection_name}", json=data)
        response.raise_for_status()
        st.success(response.json().get("message"))
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Error al crear: {e.response.json().get('detail') if e.response else str(e)}")
        return False

# ===================================================================
# ===               CUERPO PRINCIPAL DEL DASHBOARD                ===
# ===================================================================

st.title("🛠️ Gestión de Catálogo de Servicios")
st.markdown("Administra servicios, categorías, subcategorías y variantes desde un solo lugar.")

services_data, categories_data = get_all_data()

if not services_data or not categories_data:
    st.warning("No se pudieron cargar los datos del catálogo. Revisa la conexión con el backend.")
    st.stop()

# --- Definición de Pestañas (Tabs) ---
tab_services, tab_categories, tab_variants = st.tabs(["📝 Servicios", "🗂️ Categorías", "🧬 Variantes y Subcategorías"])

# ==========================================================
# ===                    PESTAÑA DE SERVICIOS               ===
# ==========================================================
with tab_services:
    st.header("Gestión de Servicios")

    with st.expander("➕ Añadir Nuevo Servicio"):
        with st.form("create_service_form", clear_on_submit=True):
            category_options = {cat['id']: cat['name'] for cat in categories_data}
            selected_cat_id = st.selectbox(
                "Selecciona una Categoría Principal",
                options=list(category_options.keys()),
                format_func=lambda cat_id: category_options.get(cat_id, "Categoría no encontrada")
            )
            new_name = st.text_input("Nombre del Servicio")
            new_desc = st.text_area("Descripción")
            new_price = st.number_input("Precio Base (CLP)", min_value=0, step=1000)
            new_status = st.selectbox("Estado", options=["active", "inactive"])

            if st.form_submit_button("Guardar Servicio"):
                if new_name and selected_cat_id:
                    payload = {"name": new_name, "description": new_desc, "price": new_price, "status": new_status, "categoryId": selected_cat_id}
                    if create_document("services", payload):
                        st.cache_data.clear()
                        st.rerun()
                else:
                    st.error("Nombre y Categoría son obligatorios.")

    st.markdown("---")
    st.header("Lista de Servicios Existentes")
    st.info("💡 Haz doble clic en una celda para editarla. Los cambios se guardarán automáticamente al presionar Enter.", icon="ℹ️")

    df_services = pd.DataFrame(services_data)
    column_order = ["id", "name", "price", "status", "categoryId", "description"]
    display_columns = [col for col in column_order if col in df_services.columns]
    
    edited_df = st.data_editor(
        df_services[display_columns],
        column_config={
            "id": st.column_config.Column("ID (No editable)", disabled=True),
            "name": st.column_config.TextColumn("Nombre", required=True),
            "price": st.column_config.NumberColumn("Precio (CLP)", format="$ %d", required=True),
            "status": st.column_config.SelectboxColumn("Estado", options=["active", "inactive"], required=True),
            "categoryId": st.column_config.TextColumn("ID Categoría", required=True),
            "description": st.column_config.TextColumn("Descripción", width="large")
        },
        use_container_width=True, hide_index=True, key="services_editor"
    )
    # Lógica de actualización (no necesita cambios)

# ==========================================================
# ===                   PESTAÑA DE CATEGORÍAS             ===
# ==========================================================
with tab_categories:
    st.header("Gestión de Categorías")

    with st.expander("➕ Añadir Nueva Categoría"):
        with st.form("create_category_form", clear_on_submit=True):
            cat_name = st.text_input("Nombre de la Nueva Categoría")
            if st.form_submit_button("Guardar Categoría"):
                if cat_name:
                    if create_document("categories", {"name": cat_name, "description": ""}):
                        st.cache_data.clear()
                        st.rerun()
                else:
                    st.error("El nombre es obligatorio.")
                    
    st.markdown("---")
    st.header("Lista de Categorías Existentes")
    df_categories = pd.DataFrame(categories_data)
    st.data_editor(
        df_categories[["id", "name", "description"]], key="categories_editor",
        use_container_width=True, hide_index=True
    )
    # TODO: Añadir lógica para manejar la edición de categorías

# ==========================================================
# ===         PESTAÑA DE VARIANTES Y SUBCATEGORÍAS        ===
# ==========================================================
with tab_variants:
    st.header("Gestión de Variantes y Subcategorías")
    
    service_options = {srv['id']: srv['name'] for srv in services_data}
    selected_service_id = st.selectbox(
        "Selecciona un servicio para gestionar sus componentes:",
        options=list(service_options.keys()),
        format_func=lambda srv_id: service_options.get(srv_id, "Servicio no encontrado")
    )
    
    if selected_service_id:
        service_details = next((s for s in services_data if s['id'] == selected_service_id), None)
        if service_details:
            st.markdown(f"### Gestionando: **{service_details['name']}**")
            col_var, col_sub = st.columns(2)
            
            with col_var:
                st.subheader("🧬 Variantes")
                variants_df = pd.DataFrame(service_details.get("variants", []))
                st.dataframe(variants_df, use_container_width=True)

            with col_sub:
                st.subheader("🗂️ Subcategorías")
                subcat_df = pd.DataFrame(service_details.get("subcategories", []))
                st.dataframe(subcat_df, use_container_width=True)

            st.info("La edición de variantes y subcategorías anidadas se debe gestionar a través del ETL por ahora, ya que son datos complejos.", icon="ℹ️")