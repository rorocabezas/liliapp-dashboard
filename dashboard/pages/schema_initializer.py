# dashboard/pages/schema_initializer.py

import streamlit as st
import requests
from pathlib import Path
import sys

# --- Patrón de Importación y Autenticación ---
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))
from dashboard.auth import check_login
from dashboard.menu import render_menu

st.set_page_config(page_title="Inicializador de Esquema - LiliApp", layout="wide")
check_login()
render_menu()

# --- Restringir acceso solo a Clientes ---
if st.session_state.get("user_role") != "customer":
    st.error("🚫 Acceso Denegado. Esta herramienta es solo para clientes.")
    st.stop()

# API URL base
API_URL = "http://127.0.0.1:8000/api/v1/crud"

# --- Cuerpo del Dashboard ---
st.title("🏗️ Inicializador de Esquema de Base de Datos")
st.markdown("Herramienta para crear las nuevas colecciones de **Presupuestos Personalizados** y poblarlas con datos de ejemplo.")

st.warning(
    """
    **¡ADVERTENCIA!** Esta acción creará nuevas colecciones y documentos en tu base de datos de Firestore.
    - **Colecciones a crear:** `quote_requests`, `quotes`, `custom_services`.
    - **Colecciones a modificar:** `orders`.
    - **Uso:** Ideal para una primera configuración o para entornos de prueba. No ejecutes esto en producción si ya tienes datos.
    """,
    icon="⚠️"
)

if st.button("🚀 Crear Colecciones y Datos de Ejemplo", type="primary", use_container_width=True):
    with st.spinner("Creando esquema y documentos de ejemplo en Firestore..."):
        try:
            response = requests.post(f"{API_URL}/admin/initialize-quote-schema")
            response.raise_for_status()
            
            data = response.json()
            st.success(data.get("message"))
            
            st.markdown("---")
            st.subheader("Documentos Creados:")
            st.json(data.get("created_ids"))
            
            st.info(
                "Ahora puedes ir a tu Consola de Firebase para ver las nuevas colecciones "
                "y verificar que los documentos de ejemplo se hayan creado con las relaciones correctas."
            )

        except requests.exceptions.RequestException as e:
            error_detail = e.response.json().get('detail') if e.response else str(e)
            st.error(f"Ocurrió un error: {error_detail}")