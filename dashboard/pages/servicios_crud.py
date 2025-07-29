import streamlit as st
import pandas as pd

# --- Importaciones Limpias y Centralizadas ---
from dashboard.auth import check_login
from dashboard.menu import render_menu
from dashboard.api_client import (
    get_services, get_categories, get_service_components,
    create_document, update_service
)

# --- Configuración de Página y Autenticación ---
st.set_page_config(page_title="Gestión de Catálogo - LiliApp", layout="wide")
check_login()
render_menu()

# --- Funciones de Utilidad ---
@st.cache_data(ttl=60)
def load_catalog_data():
    """Carga servicios y categorías usando el api_client."""
    services = get_services()
    categories = get_categories()
    return services or [], categories or []

@st.cache_data(ttl=30)
def load_service_components(service_id):
    """Carga componentes (subcategorías y variantes) de un servicio específico."""
    if not service_id: return [], []
    return get_service_components(service_id)

def refresh_data(toast_message=""):
    """Limpia el caché, muestra un mensaje y recarga la página."""
    if toast_message:
        st.toast(toast_message, icon="✅")
    st.cache_data.clear()
    st.rerun()

# --- Cuerpo Principal del Dashboard ---
st.title("🛠️ Gestión de Catálogo de Servicios")
st.markdown("Administra servicios, categorías y sus componentes.")

services_data, categories_data = load_catalog_data()

if not categories_data:
    st.warning("No se pudieron cargar las categorías. Revisa la conexión con el backend.")
    st.stop()

# --- Diccionarios de Mapeo (Con Corrección a String) ---
category_map = {str(cat['id']): cat.get('name') for cat in categories_data}
service_map = {str(srv['id']): srv.get('name') for srv in services_data}

# --- Definición de Pestañas (Tabs) ---
tab_services, tab_categories, tab_components = st.tabs(["📝 Servicios", "🗂️ Categorías", "🧬 Componentes"])

# ==========================================================
# ===                    PESTAÑA DE SERVICIOS               ===
# ==========================================================
with tab_services:
    st.header("Gestión de Servicios")
    with st.expander("➕ Añadir Nuevo Servicio"):
        with st.form("create_service_form"):
            # Usamos una función de formato defensiva aquí también
            selected_cat_id = st.selectbox(
                "Selecciona una Categoría Principal",
                options=list(category_map.keys()),
                format_func=lambda cat_id: category_map.get(cat_id) or f"ID: {cat_id} (Sin Nombre)",
                key="new_service_cat"
            )
            new_name = st.text_input("Nombre del Servicio")
            new_desc = st.text_area("Descripción")
            new_price = st.number_input("Precio Base (CLP)", min_value=0, step=1000)
            new_status = st.selectbox("Estado", options=["active", "inactive"])

            if st.form_submit_button("Guardar Servicio", use_container_width=True):
                if new_name and selected_cat_id:
                    payload = {"name": new_name, "description": new_desc, "price": new_price, "status": new_status, "categoryId": selected_cat_id}
                    response = create_document("/crud/services", payload)
                    if response:
                        refresh_data("Servicio creado con éxito!")

    st.markdown("---")
    st.header("Lista de Servicios Existentes")
    if services_data:
        df_services = pd.DataFrame(services_data)
        df_services['categoryId'] = df_services['categoryId'].astype(str)
        # Usamos una función lambda para el mapeo seguro
        df_services['categoryName'] = df_services['categoryId'].apply(lambda x: category_map.get(x, "Sin Categoría"))
        
        display_columns = ["id", "name", "categoryName", "price", "status"]
        st.dataframe(
            df_services[display_columns],
            column_config={"id": "ID", "name": "Nombre", "categoryName": "Categoría", "price": "Precio", "status": "Estado"},
            use_container_width=True, hide_index=True
        )
    else:
        st.info("No hay servicios disponibles. Por favor, añade uno nuevo.")


# ==========================================================
# ===                   PESTAÑA DE CATEGORÍAS             ===
# ==========================================================
with tab_categories:
    st.header("Gestión de Categorías Principales")
    with st.expander("➕ Añadir Nueva Categoría"):
        with st.form("create_category_form"):
            cat_name = st.text_input("Nombre de la Nueva Categoría")
            if st.form_submit_button("Guardar Categoría", use_container_width=True):
                if cat_name:
                    response = create_document("/crud/categories", {"name": cat_name})
                    if response:
                        refresh_data("Categoría creada con éxito!")
    
    st.markdown("---")
    st.header("Lista de Categorías Existentes")
    if categories_data:
        st.dataframe(pd.DataFrame(categories_data)[['id', 'name']], column_config={"id": "ID", "name": "Nombre"}, use_container_width=True, hide_index=True)
    else:
        st.info("No hay categorías creadas.")


# ==========================================================
# ===         PESTAÑA DE COMPONENTES DE SERVICIO           ===
# ==========================================================
with tab_components:
    st.header("Gestión de Subcategorías y Variantes")

    # --- CORRECCIÓN DEFINITIVA EN LA FUNCIÓN DE FORMATO ---
    selected_service_id = st.selectbox(
        "Selecciona un servicio para gestionar sus componentes:",
        options=[""] + list(service_map.keys()),
        format_func=lambda srv_id: "Elige un servicio..." if not srv_id else service_map.get(srv_id) or f"ID: {srv_id} (Sin Nombre)",
        key="service_components_selector"
    )
    
    if selected_service_id:
        # El resto del código de esta pestaña no necesita cambios
        st.markdown(f"### Gestionando: **{service_map.get(selected_service_id) or 'Servicio sin nombre'}**")
        subcategories, variants = load_service_components(selected_service_id)
        col_sub, col_var = st.columns(2)
        
        with col_sub:
            st.subheader("🗂️ Subcategorías")
            with st.expander("➕ Añadir Nueva"):
                with st.form("add_subcat_form"):
                    subcat_name = st.text_input("Nombre de la Subcategoría")
                    if st.form_submit_button("Guardar Subcategoría", use_container_width=True):
                        if subcat_name:
                            res = create_document(f"/crud/services/{selected_service_id}/subcategories", {"name": subcat_name})
                            if res: refresh_data(f"Subcategoría '{subcat_name}' creada!")
            if subcategories:
                st.dataframe(pd.DataFrame(subcategories)[['id', 'name']], use_container_width=True, hide_index=True)
            else:
                st.info("Este servicio no tiene subcategorías.")

        with col_var:
            st.subheader("🧬 Variantes")
            with st.expander("➕ Añadir Nueva"):
                with st.form("add_variant_form"):
                    v_col1, v_col2 = st.columns(2)
                    with v_col1:
                        var_option_name = st.text_input("Nombre Opción", placeholder="Ej: Tamaño")
                        var_price = st.number_input("Precio (CLP)", min_value=0)
                    with v_col2:
                        var_option_value = st.text_input("Valor Opción", placeholder="Ej: Grande")
                        var_stock = st.number_input("Stock", min_value=0, value=99)
                    if st.form_submit_button("Guardar Variante", use_container_width=True):
                        if var_option_name and var_option_value:
                            payload = {"price": var_price, "options": {"name": var_option_name, "value": var_option_value}, "stock": var_stock}
                            res = create_document(f"/crud/services/{selected_service_id}/variants", payload)
                            if res: refresh_data("Variante creada con éxito!")
            if variants:
                df_variants = pd.json_normalize(variants, sep='_')
                st.dataframe(df_variants, use_container_width=True, hide_index=True)
            else:
                st.info("Este servicio no tiene variantes.")