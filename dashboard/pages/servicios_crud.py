# dashboard/pages/servicios_crud.py
import streamlit as st
import pandas as pd
import uuid

# --- Importaciones Limpias y Centralizadas ---
from dashboard.auth import check_login
from dashboard.menu import render_menu
from dashboard.api_client import (
    get_services, get_categories, create_document,
    add_subcategory_to_service, add_variant_to_service
)

# --- Configuración de Página y Autenticación ---
st.set_page_config(page_title="Gestión de Catálogo - LiliApp", layout="wide", initial_sidebar_state="expanded")
check_login()
render_menu()

# --- Funciones de Utilidad ---
@st.cache_data(ttl=60)
def load_catalog_data():
    """Carga servicios y categorías usando el api_client."""
    services = get_services()
    categories = get_categories()
    return services or [], categories or []

def refresh_data(toast_message=""):
    """Limpia el caché, muestra un mensaje y recarga la página."""
    if toast_message: st.toast(toast_message, icon="✅")
    st.cache_data.clear()
    st.rerun()

# --- Cuerpo Principal del Dashboard ---
st.title("🛠️ Gestión de Catálogo de Servicios (Modelo Híbrido)")
st.markdown("Administra servicios, categorías y sus componentes anidados.")

services_data, categories_data = load_catalog_data()

if not categories_data and not services_data:
    st.warning("No se pudieron cargar los datos del catálogo. Revisa la conexión con el backend."); st.stop()

# --- Diccionarios de Mapeo ---
category_map = {str(cat['id']): cat.get('name') for cat in categories_data}
service_map = {str(srv['id']): srv.get('name') for srv in services_data}

# --- Definición de Pestañas (Tabs) ---
tab_services, tab_categories, tab_components = st.tabs(["📝 Servicios", "🗂️ Categorías", "🧬 Componentes"])

with tab_services:
    st.header("Gestión de Servicios")
    with st.expander("➕ Añadir Nuevo Servicio"):
        with st.form("create_service_form"):
            if not category_map:
                st.warning("Primero debes crear al menos una categoría.")
            else:
                selected_cat_id = st.selectbox("Categoría Principal", options=list(category_map.keys()), format_func=lambda cid: category_map.get(cid, "N/A"))
                new_name = st.text_input("Nombre del Servicio")
                new_desc = st.text_area("Descripción")
                new_price = st.number_input("Precio Base (CLP)", min_value=0)
                new_status = st.selectbox("Estado", options=["active", "inactive"])

                if st.form_submit_button("Guardar Servicio", use_container_width=True):
                    if new_name and selected_cat_id:
                        payload = {
                            "name": new_name, "description": new_desc, "price": new_price, "status": new_status,
                            "category": {"id": selected_cat_id},
                            "subcategories": [], "variants": [], "stats": {"viewCount": 0, "purchaseCount": 0, "averageRating": 0.0}
                        }
                        # Usamos un ID autogenerado por Firestore, por lo que llamamos al POST en la colección
                        response = create_document("/crud/services", payload)
                        if response: refresh_data("Servicio creado con éxito!")

    st.markdown("---")
    st.header("Lista de Servicios Existentes")
    if services_data:
        df_services = pd.DataFrame(services_data)
        df_services['categoryName'] = df_services['category'].apply(lambda cat: category_map.get(str(cat.get('id'))) if isinstance(cat, dict) and cat.get('id') else "Sin Categoría")
        display_columns = ["id", "name", "categoryName", "price", "status"]
        st.dataframe(df_services[display_columns], use_container_width=True, hide_index=True)
    else:
        st.info("No hay servicios disponibles.")

# ==========================================================
# ===                   PESTAÑA DE CATEGORÍAS             ===
# ==========================================================
with tab_categories:
    # --- CÓDIGO RESTAURADO Y FUNCIONAL ---
    st.header("Gestión de Categorías Principales")
    with st.expander("➕ Añadir Nueva Categoría"):
        with st.form("create_category_form"):
            cat_name = st.text_input("Nombre de la Nueva Categoría")
            if st.form_submit_button("Guardar Categoría", use_container_width=True):
                if cat_name:
                    # Usamos el endpoint POST de /crud/categories
                    response = create_document("/crud/categories", {"name": cat_name})
                    if response:
                        refresh_data("Categoría creada con éxito!")
    
    st.markdown("---")
    st.header("Lista de Categorías Existentes")
    if categories_data:
        df_categories = pd.DataFrame(categories_data)
        st.dataframe(df_categories[['id', 'name']], column_config={"id": "ID", "name": "Nombre"}, use_container_width=True, hide_index=True)
    else:
        st.info("No hay categorías creadas.")
    # --- FIN DEL CÓDIGO RESTAURADO ---

with tab_components:
    st.header("Gestión de Subcategorías y Variantes (Anidadas)")
    if not service_map:
        st.info("No hay servicios creados para gestionar.")
    else:
        selected_service_id = st.selectbox(
            "Selecciona un servicio para gestionar sus componentes:",
            options=[""] + list(service_map.keys()),
            format_func=lambda srv_id: "Elige un servicio..." if not srv_id else service_map.get(srv_id) or f"ID: {srv_id}",
            key="service_components_selector"
        )
    
        if selected_service_id:
            selected_service = next((s for s in services_data if str(s['id']) == selected_service_id), None)
            
            if selected_service:
                st.markdown(f"### Gestionando: **{selected_service.get('name', '')}**")
                subcategories = selected_service.get('subcategories', [])
                variants = selected_service.get('variants', [])
                
                col_sub, col_var = st.columns(2)
                
                with col_sub:
                    st.subheader("🗂️ Subcategorías")
                    with st.expander("➕ Añadir Nueva"):
                        with st.form("add_subcat_form"):
                            available_cats = {k: v for k, v in category_map.items() if k != str(selected_service.get('category', {}).get('id'))}
                            if not available_cats:
                                st.info("No hay otras categorías disponibles para añadir como subcategoría.")
                            else:
                                new_subcat_id = st.selectbox("Selecciona una categoría para añadir como subcategoría", options=list(available_cats.keys()), format_func=lambda cid: available_cats.get(cid))
                                if st.form_submit_button("Añadir Subcategoría"):
                                    if new_subcat_id:
                                        payload = {"id": new_subcat_id, "name": available_cats[new_subcat_id]}
                                        res = add_subcategory_to_service(selected_service_id, payload)
                                        if res: refresh_data("Subcategoría añadida!")
                    if subcategories:
                        st.dataframe(pd.DataFrame(subcategories), use_container_width=True, hide_index=True)
                    else:
                        st.info("Este servicio no tiene subcategorías.")

                with col_var:
                    st.subheader("🧬 Variantes")
                    with st.expander("➕ Añadir Nueva"):
                        with st.form("add_variant_form"):
                            var_option_name = st.text_input("Nombre Opción", placeholder="Ej: Tamaño")
                            var_option_value = st.text_input("Valor Opción", placeholder="Ej: Grande")
                            var_price = st.number_input("Precio de la Variante (CLP)", min_value=0)
                            var_stock = st.number_input("Stock", min_value=0, value=99)
                            if st.form_submit_button("Añadir Variante"):
                                if var_option_name and var_option_value:
                                    payload = {"id": str(uuid.uuid4()), "price": var_price, "options": {"name": var_option_name, "value": var_option_value}, "stock": var_stock}
                                    res = add_variant_to_service(selected_service_id, payload)
                                    if res: refresh_data("Variante añadida!")
                    if variants:
                        st.dataframe(pd.json_normalize(variants, sep='_'), use_container_width=True, hide_index=True)
                    else:
                        st.info("Este servicio no tiene variantes.")