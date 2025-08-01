import requests
import streamlit as st
import json

# Usamos una constante para la URL base de la API.
API_BASE_URL = "http://127.0.0.1:8000/api/v1"

def _handle_request(method: str, endpoint: str, **kwargs):
    """
    Función de ayuda interna para manejar las llamadas a la API, 
    incluyendo la gestión de errores.
    """
    url = f"{API_BASE_URL}{endpoint}"
    try:
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()  # Lanza un error para códigos 4xx/5xx
        return response.json()
    except requests.exceptions.HTTPError as e:
        st.error(f"Error de API: {e.response.status_code} - {e.response.text}")
    except requests.exceptions.RequestException as e:
        st.error(f"Error de conexión con el backend: {e}")
    return None

# --- Funciones para el Explorador de Jumpseller ---

def get_jumpseller_orders(page: int, status: str):
    return _handle_request("GET", "/jumpseller/orders", params={"page": page, "status": status})

def get_jumpseller_products(page: int, status: str):
    return _handle_request("GET", "/jumpseller/products", params={"page": page, "status": status})

def get_jumpseller_categories(page: int):
    return _handle_request("GET", "/jumpseller/categories", params={"page": page})

def get_jumpseller_customers():
    return _handle_request("GET", "/jumpseller/customers")

def post_jumpseller_category(name: str):
    return _handle_request("POST", "/jumpseller/categories", json={"name": name})

def update_jumpseller_customer(customer_id: int, data: dict):
    return _handle_request("PUT", f"/jumpseller/customers/{customer_id}", json=data)

def delete_jumpseller_customer(customer_id: int):
    return _handle_request("DELETE", f"/jumpseller/customers/{customer_id}")

# --- NUEVAS FUNCIONES PARA LAS TAREAS PENDIENTES ---

def get_jumpseller_customer_details(customer_id: int):
    """
    Llama al nuevo endpoint para obtener los detalles de un cliente específico.
    """
    return _handle_request("GET", f"/jumpseller/customers/{customer_id}")

def get_store_health_summary():
    """
    Llama al nuevo endpoint de agregación para el dashboard de salud.
    """
    return _handle_request("GET", "/jumpseller/store-health-summary")



def get_all_jumpseller_products(status: str = "available"):
    """
    Obtiene TODOS los productos desde el endpoint de streaming del backend.
    """
    all_products = []
    endpoint = f"/jumpseller/products"
    url = f"{API_BASE_URL}{endpoint}"
    params = {"status": status}
    
    try:
        # ¡La clave está en stream=True!
        with requests.get(url, params=params, stream=True, timeout=300) as response:
            response.raise_for_status()
            # Iteramos sobre las líneas de la respuesta
            for line in response.iter_lines():
                if line: # Filtramos líneas vacías
                    # Decodificamos cada línea (que es un JSON) y la añadimos a la lista
                    all_products.append(json.loads(line))
        return all_products
    except requests.exceptions.HTTPError as e:
        st.error(f"Error de API al cargar productos: {e.response.status_code} - {e.response.text}")
    except requests.exceptions.RequestException as e:
        st.error(f"Error de conexión con el backend: {e}")
    
    return None # Devolvemos None si hubo un error


def get_all_jumpseller_orders(status: str = "paid"):
    """
    Obtiene TODAS las órdenes desde el endpoint de streaming del backend.
    """
    all_orders = []
    # Apuntamos al nuevo endpoint de streaming
    endpoint = "/jumpseller/stream-orders"
    url = f"{API_BASE_URL}{endpoint}"
    params = {"status": status}
    
    try:
        with requests.get(url, params=params, stream=True, timeout=300) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    all_orders.append(json.loads(line))
        return all_orders
    except requests.exceptions.HTTPError as e:
        st.error(f"Error de API al cargar órdenes: {e.response.status_code} - {e.response.text}")
    except requests.exceptions.RequestException as e:
        st.error(f"Error de conexión con el backend: {e}")
    
    return None

def get_jumpseller_order_details(order_id: int):
    """
    Obtiene los detalles completos de una única orden desde el backend.
    """
    return _handle_request("GET", f"/jumpseller/orders/{order_id}")


def get_services():
    return _handle_request("GET", "/crud/services")

def get_categories():
    return _handle_request("GET", "/crud/categories")

# get_service_components YA NO ES NECESARIA, la información viene en get_services()

def create_document(endpoint: str, payload: dict):
    return _handle_request("POST", endpoint, json=payload)

def add_subcategory_to_service(service_id: str, payload: dict):
    """Añade una subcategoría a un servicio."""
    return _handle_request("POST", f"/crud/services/{service_id}/subcategories", json=payload)

def add_variant_to_service(service_id: str, payload: dict):
    """Añade una variante a un servicio."""
    return _handle_request("POST", f"/crud/services/{service_id}/variants", json=payload)


def get_kpis_acquisition(start_date, end_date):
    """Obtiene los KPIs de adquisición desde el backend."""
    params = {"start_date": start_date, "end_date": end_date}
    return _handle_request("GET", "/kpis/acquisition", params=params)



def get_kpis_acquisition(start_date, end_date):
    """Obtiene los KPIs de adquisición desde el backend."""
    params = {"start_date": start_date, "end_date": end_date}
    return _handle_request("GET", "/kpis/acquisition", params=params)

# ==========================================================
# ===         NUEVA FUNCIÓN PARA LA AUDITORÍA            ===
# ==========================================================

def get_audit_data_for_order(order_id: int):
    """
    Obtiene los datos de auditoría comparativos (Jumpseller vs. Firestore)
    para una orden específica desde el backend.
    """
    return _handle_request("GET", f"/audit/order/{order_id}")



def get_audit_data_for_service(service_id: int):
    """Obtiene los datos de auditoría para un servicio específico."""
    return _handle_request("GET", f"/audit/service/{service_id}")


def get_firestore_health_summary():
    """Obtiene el resumen de salud de datos de Firestore desde el backend."""
    return _handle_request("GET", "/audit/firestore-health")


def get_jumpseller_product_details(product_id: int):
    """
    Obtiene los detalles completos de un único producto desde el backend.
    """
    return _handle_request("GET", f"/jumpseller/products/{product_id}")


# --- Funciones para el CRUD de Clientes (Modelo Desnormalizado) ---
def get_customers():
    """Obtiene todos los clientes de la colección 'customers'."""
    return _handle_request("GET", "/crud/customers")

def update_customer_fields(customer_id: str, payload: dict):
    """Actualiza los campos principales de un cliente."""
    return _handle_request("PUT", f"/crud/customers/{customer_id}", json=payload)

def add_address(customer_id: str, payload: dict):
    """Añade una nueva dirección al arreglo de un cliente."""
    return _handle_request("POST", f"/crud/customers/{customer_id}/addresses", json=payload)

def update_address(customer_id: str, address_id: str, payload: dict):
    """Actualiza una dirección existente en el arreglo de un cliente."""
    return _handle_request("PUT", f"/crud/customers/{customer_id}/addresses/{address_id}", json=payload)


def get_all_jumpseller_categories():
    """Obtiene TODAS las categorías desde el endpoint de streaming del backend."""
    all_categories = []
    endpoint = "/jumpseller/stream-categories"
    url = f"{API_BASE_URL}{endpoint}"
    try:
        with requests.get(url, stream=True, timeout=120) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    all_categories.append(json.loads(line))
        return all_categories
    except Exception as e:
        st.error(f"Error de API al cargar categorías: {e}")
    return None