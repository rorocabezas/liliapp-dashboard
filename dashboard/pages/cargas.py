# dashboard/pages/cargas.py

import streamlit as st
import sys
from pathlib import Path
import firebase_admin
from firebase_admin import credentials

# --- Patrón de Importación Robusto ---
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from dashboard.auth import check_login
from dashboard.menu import render_menu

# --- Importamos nuestros módulos ETL genéricos ---
from etl.modules import extract, transform, load

# --- Configuración de Página y Autenticación ---
st.set_page_config(page_title="Panel ETL - LiliApp", layout="wide")
check_login()
render_menu()

# --- Restricción de Rol ---
# TODO: Habilitar esto para producción
# if st.session_state.get("user_role") != "admin":
#     st.error("🚫 Acceso Denegado")
#     st.stop()

# --- Cuerpo del Dashboard ---
st.title("⚙️ Panel de Control ETL (Extract, Transform, Load)")
st.markdown("Desde aquí puedes iniciar los procesos de carga y migración de datos hacia Firestore.")

# --- Formulario para Seleccionar el ETL ---
with st.form("etl_runner_form"):
    st.subheader("Seleccionar Proceso ETL")
    
    # --- CAMBIO 1: Añadir la nueva opción al selectbox ---
    etl_process = st.selectbox(
        "Elige el tipo de datos que deseas cargar:",
        ("Órdenes", "Productos y Categorías", "Usuarios (Próximamente)")
    )
    
    submitted = st.form_submit_button("🚀 Iniciar Proceso de Carga", use_container_width=True, type="primary")

    if submitted:
        # --- Lógica de Inicialización de Firebase (común para todos los ETLs) ---
        try:
            if not firebase_admin._apps:
                st.write("🔥 Inicializando conexión con Firebase...")
                # (Tu lógica de inicialización)
                firebase_admin.initialize_app(options={'projectId': 'liliapp-fe07b'}) # REEMPLAZA si es necesario
                st.write("✅ Conexión establecida.")
        except Exception as e:
            st.error(f"Error al inicializar Firebase: {e}")
            st.stop()

        # --- ORQUESTACIÓN DEL ETL ---
        if etl_process == "Órdenes":
            with st.status("Ejecutando ETL para Órdenes...", expanded=True) as status:
                source_file = project_root / "etl" / "data" / "source_orders.json"
                
                raw_data = extract.load_data_from_json(str(source_file), "order", logger=st.write)
                if raw_data:
                    transformed_data = transform.transform_orders(raw_data, logger=st.write)
                    if transformed_data:
                        load.load_data_to_firestore("orders", transformed_data, "id", logger=st.write)
                        status.update(label="¡ETL de Órdenes completado!", state="complete")

        # --- CAMBIO 2: Añadir el bloque 'elif' para el nuevo ETL ---
        elif etl_process == "Productos y Categorías":
            with st.status("Ejecutando ETL para Productos y Categorías...", expanded=True) as status:
                source_file = project_root / "etl" / "data" / "source_products.json"
                
                # 1. Extract
                raw_data = extract.load_data_from_json(str(source_file), "product", logger=st.write)
                if raw_data:
                    # 2. Transform (devuelve dos listas)
                    services, categories = transform.transform_products(raw_data, logger=st.write)
                    
                    # 3. Load (dos cargas separadas)
                    if categories:
                        load.load_data_to_firestore("categories", categories, "id", logger=st.write)
                    if services:
                        load.load_data_to_firestore("services", services, "id", logger=st.write)
                        
                    status.update(label="¡ETL de Productos y Categorías completado!", state="complete")

        else:
            st.info(f"El proceso ETL para '{etl_process}' aún no está implementado.")