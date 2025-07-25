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
                # Lógica para usar ADC o service account
                cred_path = project_root / "serviceAccountKey.json"
                if cred_path.exists():
                     cred = credentials.Certificate(str(cred_path))
                     firebase_admin.initialize_app(cred)
                else:
                    firebase_admin.initialize_app(options={'projectId': 'liliapp-fe07b'}) # REEMPLAZA si es necesario
                st.write("✅ Conexión establecida.")
        except Exception as e:
            st.error(f"Error al inicializar Firebase: {e}")
            st.stop()

        # --- ORQUESTACIÓN DEL ETL ---
        if etl_process == "Órdenes":
            with st.status("Ejecutando ETL completo para Órdenes...", expanded=True) as status:
                source_file = project_root / "etl" / "data" / "source_orders.json"
                
                raw_data = extract.load_data_from_json(str(source_file), "order", logger=st.write)
                if raw_data:
                    # 1. Transform (ahora devuelve CUATRO listas)
                    users, profiles, addresses, orders = transform.transform_orders(raw_data, logger=st.write)
                    
                    # 2. Load (cuatro cargas separadas y en orden)
                    if users:
                        load.load_data_to_firestore("users", users, "id", logger=st.write)
                    if profiles:
                        load.load_customer_profiles(profiles, logger=st.write)
                    if addresses:
                        load.load_addresses(addresses, logger=st.write)
                    if orders:
                        load.load_data_to_firestore("orders", orders, "id", logger=st.write)
                        
                    status.update(label="¡ETL de Órdenes, Usuarios y Direcciones completado!", state="complete")

        elif etl_process == "Productos y Categorías":
            with st.status("Ejecutando ETL para Productos...", expanded=True) as status:
                source_file = project_root / "etl" / "data" / "source_products.json"
                
                raw_data = extract.load_data_from_json(str(source_file), "product", logger=st.write)
                if raw_data:
                    # 1. Transform (ahora devuelve CUATRO listas)
                    services, categories, variants, subcategories = transform.transform_products(raw_data, logger=st.write)
                    
                    # 2. Load (cuatro cargas separadas y en orden)
                    if categories:
                        load.load_data_to_firestore("categories", categories, "id", logger=st.write)
                    if services:
                        load.load_data_to_firestore("services", services, "id", logger=st.write)
                    if variants:
                        load.load_variants_to_firestore(variants, logger=st.write)
                    if subcategories: # <-- NUEVA CARGA
                        load.load_subcategories_to_firestore(subcategories, logger=st.write)
                        
                    status.update(label="¡ETL de Productos, Categorías, Variantes y Subcategorías completado!", state="complete")

        else:
            st.info(f"El proceso ETL para '{etl_process}' aún no está implementado.")