# dashboard/pages/cargas.py

import streamlit as st
import firebase_admin
from firebase_admin import credentials
import datetime

from dashboard.auth import check_login
from dashboard.menu import render_menu
# --- Importaciones Limpias y Precisas ---
from dashboard.api_client import get_all_jumpseller_orders, get_all_jumpseller_products
from etl.modules import transform, load
from backend.services import firestore_service

# --- Configuración de Página y Autenticación ---
st.set_page_config(page_title="Panel ETL - LiliApp", layout="wide")
check_login()
render_menu()

# --- Helpers de UI ---
def log_message(container, message):
    """Función para escribir mensajes en el contenedor de logs con un timestamp."""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    container.write(f"[{timestamp}] {message}")

# --- Funciones de Orquestación del ETL ---
def run_orders_etl(is_test_run, logger_container):
    """Orquesta el proceso ETL completo para Órdenes, Usuarios, Perfiles y Direcciones."""
    with st.status("Ejecutando ETL de Órdenes...", expanded=True) as status:
        try:
            log_message(logger_container, "🚀 Proceso iniciado para Órdenes.")
            
            # 1. EXTRACT: Desde la API en vivo
            log_message(logger_container, "Fase 1: EXTRACCIÓN de datos de órdenes desde Jumpseller...")
            raw_data_nested = get_all_jumpseller_orders(status="paid") # Obtenemos los datos anidados
            if not raw_data_nested:
                log_message(logger_container, "⚠️ No se encontraron órdenes para procesar.")
                status.update(label="Extracción fallida: No se encontraron datos.", state="warning")
                return
            
            # --- CORRECCIÓN: Desanidar los datos aquí ---
            raw_data = [item['order'] for item in raw_data_nested if 'order' in item]
            log_message(logger_container, f"✅ Se extrajeron y desempaquetaron {len(raw_data)} órdenes.")

            if is_test_run:
                log_message(logger_container, f"🧪 MODO PRUEBA: Se procesarán solo los primeros 10 registros.")
                raw_data = raw_data[:10]

            # 2. TRANSFORM (Ahora recibe el formato correcto)
            log_message(logger_container, "Fase 2: TRANSFORMACIÓN de datos...")
            log_message(logger_container, "🔍 Obteniendo usuarios existentes para evitar duplicados...")
            existing_users = firestore_service.get_all_documents("users")
            existing_user_emails = {user.get('email') for user in existing_users if user.get('email')}
            log_message(logger_container, f"✅ Se encontraron {len(existing_user_emails)} emails existentes en Firestore.")
            
            users, profiles, addresses, orders = transform.transform_orders(raw_data, existing_user_emails, logger=lambda msg: log_message(logger_container, msg))

            # 3. LOAD
            log_message(logger_container, "Fase 3: CARGA de datos a Firestore...")
            if users: load.load_data_to_firestore("users", users, "id", logger=lambda msg: log_message(logger_container, msg))
            if profiles: load.load_customer_profiles(profiles, logger=lambda msg: log_message(logger_container, msg))
            if addresses: load.load_addresses(addresses, logger=lambda msg: log_message(logger_container, msg))
            if orders: load.load_data_to_firestore("orders", orders, "id", logger=lambda msg: log_message(logger_container, msg))
                            
            status.update(label="¡ETL de Órdenes completado con éxito!", state="complete")
            log_message(logger_container, "🎉 Proceso finalizado.")

        except Exception as e:
            status.update(label="Ocurrió un error en el ETL de Órdenes", state="error")
            st.exception(e)

def run_products_etl(is_test_run, logger_container):
    """Orquesta el proceso ETL completo para Productos y Catálogo."""
    with st.status("Ejecutando ETL de Productos...", expanded=True) as status:
        try:
            log_message(logger_container, "🚀 Proceso iniciado para Productos y Catálogo.")
            
            # 1. EXTRACT: Desde la API en vivo
            log_message(logger_container, "Fase 1: EXTRACCIÓN de datos de productos desde Jumpseller...")
            raw_data_nested = get_all_jumpseller_products(status="available")
            if not raw_data_nested:
                log_message(logger_container, "⚠️ No se encontraron productos para procesar.")
                status.update(label="Extracción fallida: No se encontraron datos.", state="warning")
                return
            
            # --- CORRECCIÓN: Desanidar los datos aquí ---
            raw_data = [item['product'] for item in raw_data_nested if 'product' in item]
            log_message(logger_container, f"✅ Se extrajeron y desempaquetaron {len(raw_data)} productos.")

            if is_test_run:
                log_message(logger_container, f"🧪 MODO PRUEBA: Se procesarán solo los primeros 10 registros.")
                raw_data = raw_data[:10]

            # 2. TRANSFORM (Ahora recibe el formato correcto)
            log_message(logger_container, "Fase 2: TRANSFORMACIÓN de datos...")
            services, categories, variants, subcategories = transform.transform_products(raw_data, logger=lambda msg: log_message(logger_container, msg))
            
            # 3. LOAD
            log_message(logger_container, "Fase 3: CARGA de datos a Firestore...")
            if categories: load.load_data_to_firestore("categories", categories, "id", logger=lambda msg: log_message(logger_container, msg))
            if services: load.load_data_to_firestore("services", services, "id", logger=lambda msg: log_message(logger_container, msg))
            if variants: load.load_variants_to_firestore(variants, logger=lambda msg: log_message(logger_container, msg))
            if subcategories: load.load_subcategories_to_firestore(subcategories, logger=lambda msg: log_message(logger_container, msg))
                            
            status.update(label="¡ETL de Catálogo completado con éxito!", state="complete")
            log_message(logger_container, "🎉 Proceso finalizado.")

        except Exception as e:
            status.update(label="Ocurrió un error en el ETL de Productos", state="error")
            st.exception(e)

# --- Cuerpo del Dashboard ---
st.title("⚙️ Panel de Control ETL (Extract, Transform, Load)")
st.markdown("Inicia los procesos de carga y migración de datos desde Jumpseller hacia Firestore.")

# --- Inicialización Segura de Firebase ---
try:
    if not firebase_admin._apps:
        # Usamos ADC. Asegúrate de tener las credenciales configuradas en tu entorno.
        firebase_admin.initialize_app()
except Exception as e:
    st.error(f"Error crítico al inicializar Firebase: {e}")
    st.info("Asegúrate de haber configurado las credenciales de servicio (Application Default Credentials) en tu entorno de ejecución.")
    st.stop()


# --- Formulario de Control y Contenedor de Logs ---
log_container = st.expander("Ver registro detallado del proceso", expanded=False)
with st.form("etl_runner_form"):
    st.subheader("Seleccionar Proceso ETL")
    
    etl_process = st.selectbox(
        "Elige el tipo de datos que deseas cargar:",
        ("Órdenes (con Usuarios y Direcciones)", "Productos y Categorías"),
        key="etl_process_selector"
    )

    is_test_run = st.checkbox(
        "Realizar una carga de prueba (solo los primeros 10 registros)", 
        value=True, # Marcado por defecto por seguridad
        help="Si desmarcas esta opción, se procesarán TODOS los registros de Jumpseller. Úsalo con precaución."
    )
    
    if not is_test_run:
        st.warning("⚠️ **MODO REAL ACTIVADO:** Se intentará cargar TODOS los registros. Este proceso puede tardar y es irreversible.", icon="🔥")

    submitted = st.form_submit_button("🚀 Iniciar Proceso de Carga", use_container_width=True, type="primary")

    if submitted:
        log_container.empty() # Limpiamos los logs de ejecuciones anteriores
        if etl_process == "Órdenes (con Usuarios y Direcciones)":
            run_orders_etl(is_test_run, log_container)
        elif etl_process == "Productos y Categorías":
            run_products_etl(is_test_run, log_container)