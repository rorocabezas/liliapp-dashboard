import streamlit as st
from etl.modules.transform import transform_single_product
from dashboard.auth import check_login
from dashboard.menu import render_menu
from dashboard.api_client import get_all_jumpseller_products

# --- Configuración de Página y Autenticación ---
st.set_page_config(page_title="Mapeo de Servicios (ETL) - LiliApp", layout="wide")
check_login()
render_menu()

# --- Carga de Datos en Vivo desde la API con Caché ---
@st.cache_data(ttl=3600)  # Cachea los datos por 1 hora
def load_live_products_from_api():
    """
    Carga todos los productos 'disponibles' desde la API de Jumpseller.
    """
    with st.spinner("Conectando con Jumpseller y cargando catálogo de productos... Esto puede tardar un momento."):
        live_products_raw = get_all_jumpseller_products(status="available")
    
    if not live_products_raw:
        st.error("No se pudieron cargar productos desde Jumpseller. Verifica la conexión del backend.")
        return {}
    
    products_dict = {
        str(item['product']['id']): item['product'] 
        for item in live_products_raw if 'product' in item
    }
    return products_dict

# --- Cuerpo Principal del Dashboard ---
st.title("🛠️ Herramienta de Mapeo y Diagnóstico de Servicios (ETL)")
st.markdown(
    "Selecciona un producto **en vivo** desde Jumpseller para simular su transformación al esquema de Firestore. "
    "Ideal para validar cambios en el ETL antes de una carga masiva."
)

all_products_dict = load_live_products_from_api()

if not all_products_dict:
    st.warning("No hay productos disponibles para mapear.")
    st.stop()

# --- 1. Selección de Producto ---
st.subheader("1. Selecciona un Producto para Analizar")
product_options = {
    pid: f"{pdata.get('name')} (ID: {pid})" 
    for pid, pdata in all_products_dict.items()
}
selected_product_id = st.selectbox(
    "Busca y elige un producto:",
    options=[""] + list(product_options.keys()),
    format_func=lambda pid: "Selecciona un producto..." if pid == "" else product_options[pid]
)

if selected_product_id:
    source_product = all_products_dict[selected_product_id]
    transformed_service, transformed_category, transformed_variants, transformed_subcategories = transform_single_product(source_product)
    
    st.markdown("---")
    st.subheader("2. Visualización Comparativa: Jumpseller vs. Firestore")
    
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        st.markdown("#### Datos de Origen (Jumpseller)")

        # --- INICIO DE LA MODIFICACIÓN BASADA EN TU FEEDBACK ---
        
        # 1. Re-establecemos la lógica para diferenciar categoría principal y subcategorías
        jumpseller_categories = source_product.get('categories', [])
        main_category_name = jumpseller_categories[0].get('name') if jumpseller_categories else "Ninguna"
        subcategory_names = [cat.get('name') for cat in jumpseller_categories[1:]] if len(jumpseller_categories) > 1 else []

        # 2. Re-introducimos el st.text_area para una visualización clara y contenida
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
        
        st.text_area("Resumen del Producto Fuente:", value=source_display_text, height=250, key="source_summary")

        with st.expander("Ver JSON completo del producto original"):
            st.json(source_product)
        
        # --- FIN DE LA MODIFICACIÓN ---
            
    with col2:
        st.markdown("#### Destino: Firestore (Simulación)")
        tab_service, tab_cat, tab_subcat, tab_variants = st.tabs(["Servicio Principal", "Categoría", "Subcategorías", "Variantes"])

        with tab_service:
            st.write("📄 **Colección `services`**")
            st.json(transformed_service)
        
        with tab_cat:
            st.write("🗂️ **Colección `categories`**")
            st.json(transformed_category)

        with tab_subcat:
            st.write("📁 **Subcolección `subcategories`**")
            if transformed_subcategories:
                st.json(transformed_subcategories)
            else:
                st.info("Este producto no genera subcategorías.")

        with tab_variants:
            st.write("🎨 **Subcolección `variants`**")
            if transformed_variants:
                st.json(transformed_variants)
            else:
                st.info("Este producto no genera variantes.")

    st.markdown("---")
    
    # --- 3. Análisis de Integridad y Diagnóstico ---
    st.subheader("3. Diagnóstico del Mapeo")
    ideal_service_schema = {
        "id", "name", "description", "categoryId", "price", "discount", 
        "stats", "status", "createdAt", "hasVariants", "hasSubcategories"
    }
    
    if transformed_service:
        transformed_keys = set(transformed_service.keys())
        missing_keys = ideal_service_schema - transformed_keys
        extra_keys = transformed_keys - ideal_service_schema
        
        st.write("Análisis contra el esquema ideal de la colección `services`:")
        if not missing_keys and not extra_keys:
            st.success("✅ ¡Mapeo perfecto! Todos los campos del esquema `services` están presentes y no hay campos sobrantes.")
        else:
            if missing_keys:
                st.warning(f"**Campos Faltantes:** `{', '.join(missing_keys)}`")
            if extra_keys:
                st.info(f"**Campos Adicionales:** `{', '.join(extra_keys)}`")
            
    st.markdown("**Recomendación:** Si la transformación es correcta, puedes proceder con confianza al **Panel ETL**.")