# dashboard/pages/cargas.py
import streamlit as st
import firebase_admin
import datetime

# --- Importaciones ---
from dashboard.auth import check_login
from dashboard.menu import render_menu
from dashboard.api_client import clean_services_subcollections_api

from dashboard.api_client import (
    get_all_jumpseller_orders, 
    get_all_jumpseller_products, 
    get_all_jumpseller_categories
)
from etl.modules import transform, load
from backend.services import firestore_service

# --- Configuración y Autenticación ---
st.set_page_config(page_title="Panel ETL - LiliApp", layout="wide", initial_sidebar_state="expanded")
check_login()
render_menu()

# --- Helpers ---
def log_message(container, message):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    container.write(f"[{timestamp}] {message}")

# ==========================================================
# ===         ORQUESTADORES DE PROCESOS ETL              ===
# ==========================================================

def run_categories_etl(is_test_run, logger_container):
    """Orquesta el proceso ETL completo para Categorías."""
    with st.status("Ejecutando ETL de Categorías...", expanded=True) as status:
        try:
            log_message(logger_container, "🚀 Proceso iniciado para Categorías.")
            log_message(logger_container, "Fase 1: EXTRACCIÓN...")
            raw_data = get_all_jumpseller_categories()
            if not raw_data: 
                log_message(logger_container, "⚠️ No se encontraron categorías.")
                status.update(label="Extracción fallida.", state="warning"); return
            log_message(logger_container, f"✅ Se extrajeron {len(raw_data)} categorías.")
            data_to_process = raw_data[:10] if is_test_run else raw_data
            if is_test_run: log_message(logger_container, f"🧪 MODO PRUEBA: Procesando {len(data_to_process)} registros.")

            log_message(logger_container, "Fase 2: TRANSFORMACIÓN...")
            categories = transform.transform_categories(data_to_process, logger=lambda msg: log_message(logger_container, msg))
            
            log_message(logger_container, "Fase 3: CARGA (Idempotente)...")
            if categories: load.load_data_to_firestore("categories", categories, "id", logger=lambda msg: log_message(logger_container, msg), merge=True)
            
            status.update(label="¡ETL de Categorías completado!", state="complete")
            log_message(logger_container, "🎉 Proceso finalizado.")
        except Exception as e:
            status.update(label="Ocurrió un error en el ETL", state="error"); st.exception(e)

def run_orders_etl_normalized(is_test_run, logger_container):
    """Orquesta el proceso ETL original para Órdenes, creando usuarios y perfiles normalizados."""
    with st.status("Ejecutando ETL de Órdenes (Modelo Normalizado)...", expanded=True) as status:
        try:
            log_message(logger_container, "🚀 Proceso iniciado para Órdenes (Modelo Normalizado).")
            log_message(logger_container, "Fase 1: EXTRACCIÓN...")
            raw_data_nested = get_all_jumpseller_orders(status="paid")
            if not raw_data_nested:
                log_message(logger_container, "⚠️ No se encontraron órdenes."); status.update(label="Extracción fallida.", state="warning"); return
            raw_data = [item['order'] for item in raw_data_nested if 'order' in item and item.get('order') is not None]
            log_message(logger_container, f"✅ Se extrajeron {len(raw_data)} órdenes.")
            data_to_process = raw_data[:10] if is_test_run else raw_data
            if is_test_run: log_message(logger_container, f"🧪 MODO PRUEBA: Procesando {len(data_to_process)} registros.")
            log_message(logger_container, "Fase 2: TRANSFORMACIÓN...")
            existing_users = firestore_service.get_all_documents("users")
            existing_user_emails = {user.get('email') for user in existing_users if user.get('email')}
            users, profiles, addresses, orders = transform.transform_orders(data_to_process, existing_user_emails, logger=lambda msg: log_message(logger_container, msg))
            log_message(logger_container, "Fase 3: CARGA...")
            if users: load.load_data_to_firestore("users", users, "id", logger=lambda msg: log_message(logger_container, msg))
            if profiles: load.load_customer_profiles(profiles, logger=lambda msg: log_message(logger_container, msg))
            if addresses: load.load_addresses(addresses, logger=lambda msg: log_message(logger_container, msg))
            if orders: load.load_data_to_firestore("orders", orders, "id", logger=lambda msg: log_message(logger_container, msg))
            status.update(label="¡ETL (Modelo Normalizado) completado!", state="complete")
            log_message(logger_container, "🎉 Proceso finalizado.")
        except Exception as e:
            status.update(label="Ocurrió un error en el ETL", state="error"); st.exception(e)

def run_orders_etl_customer_centric(is_test_run, logger_container):
    """Orquesta el proceso ETL para Órdenes, creando documentos 'customer' denormalizados."""
    with st.status("Ejecutando ETL de Órdenes (Modelo Customer-Centric)...", expanded=True) as status:
        try:
            log_message(logger_container, "🚀 Proceso iniciado para Órdenes (Modelo Customer-Centric).")
            log_message(logger_container, "Fase 1: EXTRACCIÓN...")
            raw_data_nested = get_all_jumpseller_orders(status="paid")
            if not raw_data_nested:
                log_message(logger_container, "⚠️ No se encontraron órdenes."); status.update(label="Extracción fallida.", state="warning"); return
            raw_data = [item['order'] for item in raw_data_nested if 'order' in item and item.get('order') is not None]
            log_message(logger_container, f"✅ Se extrajeron {len(raw_data)} órdenes.")
            data_to_process = raw_data
            if is_test_run:
                log_message(logger_container, f"🧪 MODO PRUEBA: Buscando los primeros 10 registros VÁLIDOS...")
                valid_orders = [order for order in raw_data if isinstance(order.get("customer"), dict) and order["customer"].get("id")]
                data_to_process = valid_orders[:10]
                log_message(logger_container, f"✅ Se encontraron {len(data_to_process)} órdenes válidas para procesar.")
                if not data_to_process:
                    log_message(logger_container, "🚫 No se encontraron órdenes válidas en el lote inicial."); status.update(label="Modo prueba fallido.", state="error"); return
            log_message(logger_container, "Fase 2: TRANSFORMACIÓN...")
            customers, orders = transform.transform_orders_for_customer_model(data_to_process)
            log_message(logger_container, f"✅ Transformación completada: {len(customers)} clientes únicos y {len(orders)} órdenes generadas.")
            log_message(logger_container, "Fase 3: CARGA...")
            if customers: load.load_customers_denormalized(customers, logger=lambda msg: log_message(logger_container, msg))
            if orders: load.load_data_to_firestore("orders", orders, "id", logger=lambda msg: log_message(logger_container, msg))
            status.update(label="¡ETL (Modelo Customer-Centric) completado!", state="complete")
            log_message(logger_container, "🎉 Proceso finalizado.")
        except Exception as e:
            status.update(label="Ocurrió un error en el ETL", state="error"); st.exception(e)

def run_products_etl_normalized(is_test_run, logger_container):
    """Orquesta el proceso ETL original para Productos, con subcolecciones."""
    with st.status("Ejecutando ETL de Servicios (Modelo Normalizado)...", expanded=True) as status:
        try:
            log_message(logger_container, "🚀 Proceso iniciado...")
            log_message(logger_container, "Fase 1: EXTRACCIÓN...")
            raw_data_nested = get_all_jumpseller_products(status="available")
            if not raw_data_nested: status.update(label="Extracción fallida.", state="warning"); return
            raw_data = [item['product'] for item in raw_data_nested if item.get('product')]
            log_message(logger_container, f"✅ Se extrajeron {len(raw_data)} productos.")
            data_to_process = raw_data[:10] if is_test_run else raw_data
            if is_test_run: log_message(logger_container, f"🧪 MODO PRUEBA: Procesando {len(data_to_process)} registros.")
            log_message(logger_container, "Fase 2: TRANSFORMACIÓN...")
            services, categories, variants, subcategories = transform.transform_products(data_to_process, logger=lambda msg: log_message(logger_container, msg))
            log_message(logger_container, "Fase 3: CARGA...")
            if categories: load.load_data_to_firestore("categories", categories, "id", logger=lambda msg: log_message(logger_container, msg))
            if services: load.load_data_to_firestore("services", services, "id", logger=lambda msg: log_message(logger_container, msg))
            if variants: load.load_variants_to_firestore(variants, logger=lambda msg: log_message(logger_container, msg))
            if subcategories: load.load_subcategories_to_firestore(subcategories, logger=lambda msg: log_message(logger_container, msg))
            status.update(label="¡ETL (Modelo Normalizado) completado!", state="complete")
            log_message(logger_container, "🎉 Proceso finalizado.")
        except Exception as e:
            status.update(label="Ocurrió un error en el ETL", state="error"); st.exception(e)

def run_products_etl_hybrid(is_test_run, logger_container):
    """Orquesta el nuevo proceso ETL para Servicios, con arreglos de referencias."""
    with st.status("Ejecutando ETL de Servicios (Modelo Híbrido)...", expanded=True) as status:
        try:
            log_message(logger_container, "🚀 Proceso iniciado...")
            log_message(logger_container, "Fase 1: EXTRACCIÓN...")
            raw_data_nested = get_all_jumpseller_products(status="available")
            if not raw_data_nested: status.update(label="Extracción fallida.", state="warning"); return
            raw_data = [item['product'] for item in raw_data_nested if item.get('product')]
            log_message(logger_container, f"✅ Se extrajeron {len(raw_data)} productos.")
            data_to_process = raw_data[:10] if is_test_run else raw_data
            if is_test_run: log_message(logger_container, f"🧪 MODO PRUEBA: Procesando {len(data_to_process)} registros.")
            log_message(logger_container, "Fase 2: TRANSFORMACIÓN...")
            services, categories = transform.transform_products_for_service_model(data_to_process, logger=lambda msg: log_message(logger_container, msg))
            log_message(logger_container, "Fase 3: CARGA...")
            load.load_services_hybrid(services, categories, logger=lambda msg: log_message(logger_container, msg))
            status.update(label="¡ETL (Modelo Híbrido) completado!", state="complete")
            log_message(logger_container, "🎉 Proceso finalizado.")
        except Exception as e:
            status.update(label="Ocurrió un error en el ETL", state="error"); st.exception(e)

# --- Cuerpo del Dashboard ---
st.title("⚙️ Panel de Control ETL (Extract, Transform, Load)")
st.markdown("Inicia los procesos de carga y migración de datos desde Jumpseller hacia Firestore.")

try:
    if not firebase_admin._apps: firebase_admin.initialize_app()
except Exception as e:
    st.error(f"Error crítico al inicializar Firebase: {e}"); st.stop()

log_container = st.expander("Ver registro detallado del proceso", expanded=True)
with st.form("etl_runner_form"):
    st.subheader("Seleccionar Proceso ETL")
    
    etl_process = st.selectbox(
        "Elige el tipo de datos que deseas cargar:",
        (
            "Sincronizar Categorías",
            "Órdenes (Modelo Normalizado: users/profiles)",
            "Órdenes (Modelo Desnormalizado: customers)",
            "Servicios (Modelo Normalizado: subcolecciones)",
            "Servicios (Modelo Híbrido: arreglos de refs)"
        ),
        key="etl_process_selector"
    )

    is_test_run = st.checkbox("Carga de prueba (primeros 10 registros)", value=True)
    if not is_test_run: st.warning("⚠️ **MODO REAL ACTIVADO:** Se cargarán TODOS los registros.", icon="🔥")

    if st.form_submit_button("🚀 Iniciar Proceso de Carga", use_container_width=True, type="primary"):
        log_container.empty()
        
        if etl_process == "Sincronizar Categorías":
            run_categories_etl(is_test_run, log_container)
        elif etl_process == "Órdenes (Modelo Normalizado: users/profiles)":
            run_orders_etl_normalized(is_test_run, log_container)
        elif etl_process == "Órdenes (Modelo Desnormalizado: customers)":
            run_orders_etl_customer_centric(is_test_run, log_container)
        elif etl_process == "Servicios (Modelo Normalizado: subcolecciones)":
            run_products_etl_normalized(is_test_run, log_container)
        elif etl_process == "Servicios (Modelo Híbrido: arreglos de refs)":
            run_products_etl_hybrid(is_test_run, log_container)


# ==========================================================
# ===                 HERRAMIENTAS DE MANTENIMIENTO        ===
# ==========================================================
st.markdown("---")
st.subheader("🛠️ Herramientas de Mantenimiento de Datos")
st.warning("PRECAUCIÓN: Las siguientes operaciones modifican o eliminan datos de forma masiva.", icon="⚠️")

if st.button("🧹 Iniciar Limpieza de Subcolecciones de Servicios", 
             help="Elimina las subcolecciones 'variants' y 'subcategories' de TODOS los servicios. Este proceso se ejecuta en segundo plano y puede tardar varios minutos.",
             type="secondary"):
    
    # La interacción con el usuario ahora es instantánea
    st.info("Enviando solicitud para iniciar el proceso de limpieza...")
    result = clean_services_subcollections_api()
    
    if result and result.get("status") == "accepted":
        st.success("✅ ¡Solicitud aceptada! El proceso de limpieza ha comenzado en el servidor.")
        st.caption("Puedes monitorear el progreso en la consola del backend. La limpieza puede tardar varios minutos en completarse.")
    else:
        st.error("Ocurrió un error al intentar iniciar el proceso. Revisa los logs del backend.")