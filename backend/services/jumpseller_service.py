import requests
import json
from typing import List, Dict, Any, Literal, Generator
from backend.core.config import settings

# --- Configuración de la API ---
API_BASE_URL = settings.API_BASE_URL
LOGIN = settings.JUMPSELLER_LOGIN
AUTHTOKEN = settings.JUMPSELLER_AUTHTOKEN

# --- Función Genérica de Peticiones (Centralizada) ---
def _make_request(
    endpoint: str,
    method: Literal["GET", "POST", "PUT", "DELETE"] = "GET",
    params: Dict = None,
    json_data: Dict = None
) -> Any:
    """
    Función genérica para realizar peticiones a la API de Jumpseller
    usando Autenticación Básica. TODAS las demás funciones deben usar esta.
    """
    url = f"{API_BASE_URL}/{endpoint}.json"
    try:
        response = requests.request(
            method=method,
            url=url,
            auth=(LOGIN, AUTHTOKEN),
            params=params,
            json=json_data,
        )
        response.raise_for_status()
        return response.json() if response.content else {"status": "success", "code": response.status_code}
    except requests.exceptions.RequestException as e:
        print(f"Error en API Jumpseller ({method} {url}): {e}")
        raise e

# ===================================================================
# ===               CATÁLOGO DE FUNCIONES DE SERVICIO             ===
# ===================================================================

# --- Products ---
def get_products(limit: int = 50, page: int = 1, status: str = 'available') -> List[Dict[str, Any]]:
    params = {"limit": limit, "page": page}
    endpoint = f"products/status/{status}" if status else "products"
    return _make_request(endpoint, params=params)

# --- Orders ---
def get_orders(limit: int = 50, page: int = 1, status: str = 'paid') -> List[Dict[str, Any]]:
    params = {"limit": limit, "page": page}
    endpoint = f"orders/status/{status}" if status else "orders"
    return _make_request(endpoint, params=params)

# --- Categories ---
def get_categories(limit: int = 50, page: int = 1) -> List[Dict[str, Any]]:
    params = {"limit": limit, "page": page}
    return _make_request("categories", params=params)

def create_category(name: str, parent_id: int = None) -> Dict[str, Any]:
    payload = {"category": {"name": name}}
    if parent_id is not None:
        payload["category"]["parent_id"] = parent_id
    return _make_request("categories", method="POST", json_data=payload)

# --- Customers ---
def get_customers(limit: int = 50, page: int = 1) -> List[Dict[str, Any]]:
    params = {"limit": limit, "page": page}
    return _make_request("customers", params=params)

def get_customer_by_id(customer_id: int) -> Dict[str, Any]:
    """Obtiene un cliente por su ID. (Versión Única y Correcta)"""
    return _make_request(f"customers/{customer_id}")

def update_customer(customer_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    payload = {"customer": data}
    return _make_request(f"customers/{customer_id}", method="PUT", json_data=payload)

def delete_customer(customer_id: int):
    return _make_request(f"customers/{customer_id}", method="DELETE")

# --- Health Summary (Refactorizado) ---
def get_resource_count(resource: str) -> int:
    """Función genérica para obtener el conteo de un recurso. (Refactorizada)"""
    try:
        # El endpoint de count no lleva / al principio y no necesita .json aquí
        response = _make_request(f"{resource}/count")
        return response.get('count', 0)
    except requests.exceptions.RequestException:
        return 0

def get_store_health_summary() -> Dict[str, Any]:
    """Obtiene un resumen de las métricas clave. (Refactorizada)"""
    resources_to_count = ["orders", "products", "customers", "categories"]
    summary = {resource: get_resource_count(resource) for resource in resources_to_count}
    return {"health_summary": summary}

# ===================================================================
# ===               NUEVA FUNCIÓN DE STREAMING                   ===
# ===================================================================

def stream_all_jumpseller_products(status: str = "available") -> Generator[str, None, None]:
    """
    Generador que obtiene TODOS los productos de Jumpseller y los "produce" (yield)
    en formato JSON-line, manejando la paginación.
    """
    page = 1
    limit = 50 # Un límite razonable por página
    while True:
        try:
            params = {"limit": limit, "page": page, "status": status}
            # Llama al endpoint de productos. La API de Jumpseller no tiene un endpoint específico por status.
            # Se usa como parámetro.
            products_page = _make_request("products", params=params)

            if not products_page:
                break  # No hay más productos, terminamos el bucle

            for product_item in products_page:
                yield json.dumps(product_item) + "\n"

            if len(products_page) < limit:
                break  # Era la última página

            page += 1
        except requests.exceptions.RequestException as e:
            print(f"Error durante el streaming de productos en la página {page}: {e}")
            break 

def stream_all_jumpseller_orders(status: str = "paid") -> Generator[str, None, None]:
    """
    Generador que obtiene TODAS las órdenes de Jumpseller y las "produce" (yield)
    en formato JSON-line, manejando la paginación.
    """
    page = 1
    limit = 50
    while True:
        try:
            params = {"limit": limit, "page": page, "status": status}
            # El endpoint de Jumpseller es 'orders' con un parámetro de status
            orders_page = _make_request("orders", params=params)

            if not orders_page:
                break

            for order_item in orders_page:
                yield json.dumps(order_item) + "\n"

            if len(orders_page) < limit:
                break

            page += 1
        except requests.exceptions.RequestException as e:
            print(f"Error durante el streaming de órdenes en la página {page}: {e}")
            break

def get_orders(limit: int = 50, page: int = 1, status: str = 'paid', order_id: int = None) -> Any:
    if order_id:
        # Petición para un solo objeto
        endpoint = f"orders/{order_id}"
        return _make_request(endpoint)
    else:
        # Petición para una lista
        params = {"limit": limit, "page": page, "status": status}
        endpoint = "orders" # El status se pasa como param, no en el path para órdenes
        return _make_request(endpoint, params=params)
    
# en backend/services/jumpseller_service.py
def get_product_by_id(product_id: int) -> Dict[str, Any]:
    """Obtiene un producto por su ID."""
    return _make_request(f"products/{product_id}")


def stream_all_jumpseller_categories() -> Generator[str, None, None]:
    """
    Generador que obtiene TODAS las categorías de Jumpseller y las "produce" (yield)
    en formato JSON-line, manejando la paginación.
    """
    page = 1
    limit = 100
    while True:
        try:
            params = {"limit": limit, "page": page}
            categories_page = _make_request("categories", params=params)

            if not categories_page:
                break

            for category_item in categories_page:
                yield json.dumps(category_item) + "\n"

            if len(categories_page) < limit:
                break
            
            page += 1
        except requests.exceptions.RequestException as e:
            print(f"Error durante el streaming de categorías en la página {page}: {e}")
            break