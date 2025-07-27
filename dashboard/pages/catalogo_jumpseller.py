# dashboard/pages/catalogo_jumpseller.py

import streamlit as st
import requests
from pathlib import Path
import sys
import pandas as pd

# --- Patrón de Importación y Autenticación ---
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))
from dashboard.auth import check_login
from dashboard.menu import render_menu

st.set_page_config(page_title="Catálogo Jumpseller - LiliApp", layout="wide")
check_login()
render_menu()

API_URL = "http://127.0.0.1:8000/api/v1/jumpseller"

# --- Función genérica para mostrar datos ---
def display_data(title: str, data: list, key_to_expand: str):
    st.header(title)
    if data:
        st.success(f"Se encontraron {len(data)} registros.")
        for item in data:
            main_object = item.get(key_to_expand, {})
            # Usamos el nombre si existe, si no el ID
            expander_title = f"{main_object.get('name', 'ID: ' + str(main_object.get('id')))}"
            with st.expander(expander_title):
                st.json(main_object)
    else:
        st.info("No se encontraron registros para los filtros seleccionados.")

# --- Cuerpo del Dashboard ---
st.title("📦 Explorador de Datos de Jumpseller")
st.markdown("Visualiza y gestiona los datos en crudo directamente desde la API de Jumpseller.")

tab_orders, tab_products, tab_categories = st.tabs(["🛍️ Órdenes", "🛠️ Productos", "🗂️ Categorías"])

# --- Pestaña de Órdenes ---
with tab_orders:
    page_orders = st.number_input("Página de Órdenes", min_value=1, value=1, key="page_orders")
    try:
        response = requests.get(f"{API_URL}/orders", params={"page": page_orders, "status": "paid"})
        response.raise_for_status()
        display_data("Últimas Órdenes Pagadas", response.json(), "order")
    except requests.RequestException as e:
        st.error(f"Error al obtener las órdenes: {e}")

# --- Pestaña de Productos ---
with tab_products:
    page_products = st.number_input("Página de Productos", min_value=1, value=1, key="page_products")
    try:
        response = requests.get(f"{API_URL}/products", params={"page": page_products, "status": "available"})
        response.raise_for_status()
        display_data("Productos Disponibles", response.json(), "product")
    except requests.RequestException as e:
        st.error(f"Error al obtener los productos: {e}")

# --- Pestaña de Categorías ---
with tab_categories:
    st.header("Gestión de Categorías en Jumpseller")
    with st.expander("➕ Crear Nueva Categoría"):
        with st.form("create_cat_form", clear_on_submit=True):
            cat_name = st.text_input("Nombre de la Nueva Categoría")
            if st.form_submit_button("Crear Categoría"):
                if cat_name:
                    try:
                        res = requests.post(f"{API_URL}/categories", json={"name": cat_name})
                        res.raise_for_status()
                        st.success(f"Categoría '{cat_name}' creada con éxito.")
                    except requests.RequestException as e:
                        st.error(f"Error al crear categoría: {e}")
    
    st.markdown("---")
    st.header("Lista de Categorías")
    page_categories = st.number_input("Página de Categorías", min_value=1, value=1, key="page_cats")
    try:
        response = requests.get(f"{API_URL}/categories", params={"page": page_categories})
        response.raise_for_status()
        categories_data = response.json()
        if categories_data:
            # Mostramos las categorías en una tabla para una mejor visualización
            df_cats = pd.DataFrame([item.get('category', {}) for item in categories_data])
            st.dataframe(df_cats, use_container_width=True, hide_index=True)
        else:
            st.info("No se encontraron más categorías.")
    except requests.RequestException as e:
        st.error(f"Error al obtener las categorías: {e}")