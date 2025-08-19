# dashboard/api_client.py
import requests
import streamlit as st
import json

API_BASE_URL = "http://127.0.0.1:8000/api/v1"

def _handle_request(method: str, endpoint: str, **kwargs):
    """
    Función de ayuda interna para manejar todas las llamadas a la API,
    con manejo de errores mejorado para depuración.
    """
    url = f"{API_BASE_URL}{endpoint}"
    try:
        response = requests.request(method, url, timeout=10, **kwargs)
        response.raise_for_status()
        return response.json() if response.content else {"status": "success"}
    except requests.exceptions.HTTPError as e:
        st.error(f"Error de API: {e.response.status_code} - {e.response.text}")
    except requests.exceptions.ConnectionError as e:
        st.error(f"🔌 Error de Conexión: No se pudo conectar a {url}.")
        st.error(f"   Detalle técnico: {repr(e)}")
        st.warning("   ACCIÓN: Verifica que el servidor backend (FastAPI) esté corriendo y que tu Firewall/Antivirus no esté bloqueando la conexión al puerto 8000.")
    except requests.exceptions.Timeout:
        st.error(f"🔌 Error de Timeout: El servidor en {url} tardó demasiado en responder.")
    except requests.exceptions.RequestException as e:
        st.error(f"Ocurrió un error de red inesperado: {e}")
    return None

# --- Funciones de KPIs ---
def get_kpis(endpoint: str, start_date: str, end_date: str):
    """Función genérica para obtener todos los KPIs."""
    params = {"start_date": start_date, "end_date": end_date}
    return _handle_request("GET", f"/kpis/{endpoint}", params=params)

# --- Jumpseller API ---
def get_all_jumpseller_orders(status: str = "paid"):
    endpoint = "/jumpseller/stream-orders"
    url, params = f"{API_BASE_URL}{endpoint}", {"status": status}
    all_orders = []
    try:
        with requests.get(url, params=params, stream=True, timeout=300) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if line: all_orders.append(json.loads(line))
        return all_orders
    except Exception as e: st.error(f"Error de API al cargar órdenes: {e}"); return None

def get_all_jumpseller_products(status: str = "available"):
    endpoint = "/jumpseller/products"
    url, params = f"{API_BASE_URL}{endpoint}", {"status": status}
    all_products = []
    try:
        with requests.get(url, params=params, stream=True, timeout=300) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if line: all_products.append(json.loads(line))
        return all_products
    except Exception as e: st.error(f"Error de API al cargar productos: {e}"); return None
        
def get_all_jumpseller_categories():
    endpoint = "/jumpseller/stream-categories"
    url = f"{API_BASE_URL}{endpoint}"
    all_categories = []
    try:
        with requests.get(url, stream=True, timeout=120) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line: all_categories.append(json.loads(line))
        return all_categories
    except Exception as e: st.error(f"Error de API al cargar categorías: {e}"); return None

def get_jumpseller_order_details(order_id: int):
    return _handle_request("GET", f"/jumpseller/orders/{order_id}")

def get_jumpseller_product_details(product_id: int):
    return _handle_request("GET", f"/jumpseller/products/{product_id}")

# --- CRUD (Alineado con el nuevo modelo) ---
def get_customers():
    return _handle_request("GET", "/crud/customers")

def get_services():
    return _handle_request("GET", "/crud/services")

def get_categories():
    return _handle_request("GET", "/crud/categories")
    
def create_document(endpoint: str, payload: dict):
    # Asumimos que el endpoint ya incluye el prefijo /crud
    return _handle_request("POST", endpoint, json=payload)

def update_customer_fields(customer_id: str, payload: dict):
    return _handle_request("PUT", f"/crud/customers/{customer_id}", json=payload)

def add_address(customer_id: str, payload: dict):
    return _handle_request("POST", f"/crud/customers/{customer_id}/addresses", json=payload)

def update_address(customer_id: str, address_id: str, payload: dict):
    return _handle_request("PUT", f"/crud/customers/{customer_id}/addresses/{address_id}", json=payload)

def add_subcategory_to_service(service_id: str, payload: dict):
    return _handle_request("POST", f"/crud/services/{service_id}/subcategories", json=payload)

def add_variant_to_service(service_id: str, payload: dict):
    return _handle_request("POST", f"/crud/services/{service_id}/variants", json=payload)

# --- Auditoría y Salud ---
def get_audit_data_for_order(order_id: int):
    return _handle_request("GET", f"/audit/order/{order_id}")

def get_audit_data_for_service(service_id: int):
    return _handle_request("GET", f"/audit/service/{service_id}")
    
def get_firestore_health_summary():
    return _handle_request("GET", "/audit/firestore-health")

# --- Mantenimiento / Limpieza ---
def clean_services_subcollections_api():
    """Llama al endpoint para limpiar las subcolecciones de servicios."""
    return _handle_request("POST", "/crud/services/clean-subcollections")

def clean_collection_api(collection_name: str):
    """
    Llama al endpoint para limpiar todos los documentos de una colección completa.
    """
    return _handle_request("POST", f"/crud/collections/{collection_name}/clean")