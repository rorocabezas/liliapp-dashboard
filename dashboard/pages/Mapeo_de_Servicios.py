# dashboard/pages/Mapeo_de_servicios.py

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
from etl.modules.transform import transform_single_product

# --- Configuración de Página y Autenticación ---
st.set_page_config(page_title="Mapeo de Productos - LiliApp", layout="wide")
check_login()
render_menu()

# --- Carga de Datos en Caché ---
@st.cache_data
def load_source_products():
    """Carga los productos desde el archivo JSON de origen."""
    source_file = project_root / "etl" / "data" / "source_products.json"
    try:
        with open(source_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        products = {str(item['product']['id']): item['product'] for item in raw_data if 'product' in item}
        return products
    except Exception as e:
        st.error(f"Error al cargar source_products.json: {e}")
        return {}

# --- Cuerpo del Dashboard ---
st.title("🛠️ Herramienta de Mapeo de Servicios (ETL)")
st.markdown("Usa esta herramienta para seleccionar un producto de Jumpseller, ver su transformación y validar los campos contra el esquema de Firestore.")

all_products = load_source_products()

if not all_products:
    st.stop()

# --- 1. Selección de Producto ---
st.subheader("1. Selecciona un Producto para Analizar")
product_options = {pid: f"{pdata.get('name')} (ID: {pid})" for pid, pdata in all_products.items()}
selected_product_id = st.selectbox(
    "Elige un producto por su nombre o ID:",
    options=list(product_options.keys()),
    format_func=lambda pid: product_options[pid]
)

if selected_product_id:
    source_product = all_products[selected_product_id]
    
    # --- LA CORRECCIÓN ESTÁ AQUÍ ---
    # Ahora esperamos y recibimos CUATRO valores de la función
    transformed_service, transformed_category, transformed_variants, transformed_subcategories = transform_single_product(source_product)
    
    st.markdown("---")
    st.subheader("2. Visualiza la Transformación")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Datos de Origen (Jumpseller)")
        with st.expander("Ver JSON completo del producto original"):
            st.json(source_product, expanded=False)
            
        st.write("Principales campos de origen:")
        # Extraemos las categorías para mostrarlas de forma más clara
        jumpseller_categories = source_product.get('categories', [])
        
        main_category_name = jumpseller_categories[0].get('name') if jumpseller_categories else "Ninguna"
        
        subcategory_names = [cat.get('name') for cat in jumpseller_categories[1:]] if len(jumpseller_categories) > 1 else []

        source_display_text = (
            f"ID: {source_product.get('id')}\n"
            f"Nombre: {source_product.get('name')}\n"
            f"Precio: {source_product.get('price')}\n"
            f"Estado: {source_product.get('status')}\n"
            f"----------------------------------\n"
            f"Categoría Principal: {main_category_name}\n"
            f"Subcategorías: {subcategory_names}\n"
            f"Nº de Variantes: {len(source_product.get('variants', []))}"
        )
        
        st.text_area("Fuente", source_display_text, height=220)
        
    with col2:
        st.markdown("#### Datos Transformados (Para Firestore)")
        
        st.write("➡️ **Colección `services`**")
        st.json(transformed_service)
        
        st.write("➡️ **Colección `categories` (Categoría Principal)**")
        st.json(transformed_category)

        st.write("➡️ **Subcolección `subcategories`**")
        if transformed_subcategories:
            st.json(transformed_subcategories)
        else:
            st.info("Este producto no tiene subcategorías definidas.")

        st.write("➡️ **Subcolección `variants`**")
        if transformed_variants:
            st.json(transformed_variants)
        else:
            st.info("Este producto no tiene variantes definidas.")

    st.markdown("---")
    
    # --- 3. Análisis de Campos Faltantes ---
    st.subheader("3. Análisis de Campos y Siguientes Pasos")
    
    # Se añade 'hasSubcategories' al esquema ideal para validación
    ideal_service_schema = {
        "id", "name", "description", "categoryId", "price", "discount", 
        "stats", "status", "createdAt", "hasVariants", "hasSubcategories"
    }
    
    if transformed_service:
        transformed_keys = set(transformed_service.keys())
        missing_keys = ideal_service_schema - transformed_keys
        
        st.write("Comparando con el esquema ideal de la colección `services`:")
        if missing_keys:
            st.warning(f"**Campos Faltantes:** `{', '.join(missing_keys)}`")
            st.info("Estos campos no se encontraron o no se generaron en la transformación.")
        else:
            st.success("¡Excelente! Todos los campos del esquema `services` están presentes.")
            
    st.markdown("**Recomendación:** Si la transformación es correcta, usa el **Panel ETL** para la carga masiva.")