# backend/services/jumpseller_service.py

import requests
from typing import List, Dict, Any, Literal
from backend.core.config import settings

# --- Configuración de la API ---
API_BASE_URL = settings.API_BASE_URL
LOGIN = settings.JUMPSELLER_LOGIN
AUTHTOKEN = settings.JUMPSELLER_AUTHTOKEN

# --- Función Genérica de Peticiones ---
def _make_request(
    endpoint: str,
    method: Literal["GET", "POST", "PUT", "DELETE"] = "GET",
    params: Dict = None,
    json_data: Dict = None
) -> Any:
    """
    Función genérica para realizar peticiones a la API de Jumpseller
    usando Autenticación Básica.
    """
    url = f"{API_BASE_URL}/{endpoint}.json"
    try:
        response = requests.request(
            method=method,
            url=url,
            params=params,
            json=json_data,
            auth=(LOGIN, AUTHTOKEN)
        )
        response.raise_for_status()
        # DELETE a veces no devuelve JSON, sino solo un status 200
        return response.json() if response.status_code != 204 else {"status": "success"}
    except requests.exceptions.RequestException as e:
        print(f"Error en API Jumpseller ({method} {url}): {e}")
        # Propagamos el error para que el endpoint lo maneje
        raise e

# ===================================================================
# ===               CATÁLOGO DE FUNCIONES DE ENDPOINT             ===
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

# --- Categories (NUEVO) ---
def get_categories(limit: int = 50, page: int = 1) -> List[Dict[str, Any]]:
    """Obtiene todas las categorías."""
    params = {"limit": limit, "page": page}
    return _make_request("categories", params=params)

def create_category(name: str, parent_id: int = None) -> Dict[str, Any]:
    """Crea una nueva categoría."""
    payload = {"category": {"name": name}}
    if parent_id is not None:
        payload["category"]["parent_id"] = parent_id
    return _make_request("categories", method="POST", json_data=payload)