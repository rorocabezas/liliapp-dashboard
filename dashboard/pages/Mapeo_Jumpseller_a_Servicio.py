import streamlit as st

# --- Importaciones de Módulos del Proyecto ---
from dashboard.auth import check_login
from dashboard.menu import render_menu
from dashboard.api_client import get_all_jumpseller_products, get_jumpseller_product_details
from etl.modules.transform import transform_product_to_service_model

# --- Configuración de Página ---
st.set_page_config(page_title="Mapeo a Servicio - LiliApp", layout="wide", initial_sidebar_state="expanded")
check_login()
render_menu()

# --- Funciones de Carga de Datos ---
@st.cache_data(ttl=3600)
def load_jumpseller_product_list():
    """Carga una lista ligera de productos desde Jumpseller para el selector."""
    with st.spinner("Cargando lista de servicios desde Jumpseller..."):
        products_raw = get_all_jumpseller_products(status="available")
    if not products_raw: return {}
    return {str(item['product']['id']): item['product'] for item in products_raw if 'product' in item}

# --- Cuerpo del Dashboard ---
st.title("🗺️ Mapeo de Producto Jumpseller al Modelo `Service` Híbrido")
st.markdown(
    "Esta herramienta simula cómo un producto de Jumpseller se transforma en un documento `service` "
    "con referencias anidadas y en documentos separados para la colección `categories`."
)

jumpseller_products = load_jumpseller_product_list()

if not jumpseller_products:
    st.warning("No se pudieron cargar los servicios de Jumpseller.")
    st.stop()

# --- Selección de Producto ---
st.subheader("1. Selecciona un Producto de Jumpseller")

def format_option(product_id):
    product_data = jumpseller_products.get(product_id, {})
    return f"{product_data.get('name', 'N/A')} (ID: {product_id})"

selected_product_id = st.selectbox(
    "Busca un servicio:",
    options=[""] + list(jumpseller_products.keys()),
    format_func=lambda pid: "Selecciona un servicio..." if not pid else format_option(pid),
    key="service_map_selector"
)

if selected_product_id:
    with st.spinner(f"Cargando detalles del producto {selected_product_id}..."):
        source_product = get_jumpseller_product_details(int(selected_product_id)).get('product')

    if not source_product:
        st.error("No se pudieron cargar los detalles del producto.")
        st.stop()
    
    # --- Llamada a la Lógica de Transformación ---
    service_doc, categories_docs = transform_product_to_service_model(source_product)
    
    # --- Visualización ---
    st.markdown("---")
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.subheader("⬅️ Origen: Producto de Jumpseller")
        st.json(source_product, expanded=False)

    with col2:
        st.subheader("➡️ Destino: Documentos en Firestore")
        
        st.markdown("#### 📄 Documento para `services/{serviceId}`")
        st.info("Observa que `category` y `subcategories` solo contienen el **ID** de referencia.")
        st.json(service_doc)

        st.markdown("#### 🗂️ Documentos para `categories/{categoryId}`")
        st.info("Estos son los documentos completos que se crearían/actualizarían. Son la fuente de la verdad para los nombres.")
        if categories_docs:
            for cat_doc in categories_docs:
                st.json(cat_doc)
        else:
            st.write("No se extrajeron categorías de este producto.")

    st.markdown("---")
    st.subheader("💬 Nota del Arquitecto: Análisis del Modelo Híbrido")
    st.success(
        """
        **Análisis de la Arquitectura Híbrida (Recomendada):**

        - **Consistencia Garantizada:** Almacenar solo los **IDs** de las categorías en el documento del servicio asegura que si un nombre de categoría cambia, solo necesita ser actualizado en **un solo lugar** (la colección `categories`).
        
        - **Lecturas Eficientes:** Para mostrar una página de detalle, la aplicación leerá el documento del servicio y luego hará una segunda consulta muy rápida para obtener los nombres de las categorías usando la lista de IDs.
        
        **Esta arquitectura es el equilibrio perfecto entre rendimiento y mantenibilidad, y es el enfoque profesional para construir sistemas escalables con Firestore.**
        """,
        icon="✅"
    )