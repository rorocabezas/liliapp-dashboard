# backend/api/v1/endpoints/jumpseller.py

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from backend.services import jumpseller_service



router = APIRouter()

# --- Pydantic Models ---
class CategoryCreate(BaseModel):
    name: str
    parent_id: int | None = None

# --- Endpoints ---
@router.get("/orders", summary="Obtener Órdenes", tags=["Jumpseller API"])
def get_orders_endpoint(
    status: str = Query("paid", description="Estado de la orden"),
    limit: int = Query(20, le=100),
    page: int = Query(1)
):
    try:
        return jumpseller_service.get_orders(limit=limit, page=page, status=status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/products",
            summary="Obtener todos los productos de Jumpseller (vía Streaming)",
            tags=["Jumpseller API Explorer"])
def stream_jumpseller_products(status: str = "available"):
    """
    Endpoint que obtiene todos los productos de Jumpseller usando una conexión
    de streaming para evitar timeouts en catálogos grandes.
    Devuelve los productos en formato JSON-Lines (un JSON por línea).
    """
    # Devolvemos una StreamingResponse que consume nuestro generador
    return StreamingResponse(
        jumpseller_service.stream_all_jumpseller_products(status),
        media_type="application/x-json-stream"
    )

@router.get("/categories", summary="Obtener Categorías", tags=["Jumpseller API"])
def get_categories_endpoint(limit: int = Query(50, le=100), page: int = 1):
    try:
        return jumpseller_service.get_categories(limit=limit, page=page)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/categories", summary="Crear una Categoría", tags=["Jumpseller API"])
def create_category_endpoint(category: CategoryCreate):
    try:
        return jumpseller_service.create_category(name=category.name, parent_id=category.parent_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

class CustomerUpdate(BaseModel):
    email: str | None = None
    fullname: str | None = None
    phone: str | None = None

@router.get("/customers", summary="Obtener Clientes", tags=["Jumpseller API"])
def get_customers_endpoint(limit: int = 20, page: int = 1):
    try:
        return jumpseller_service.get_customers(limit=limit, page=page)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/customers/{customer_id}", summary="Actualizar un Cliente", tags=["Jumpseller API"])
def update_customer_endpoint(customer_id: int, customer_data: CustomerUpdate):
    try:
        # Pydantic nos asegura que solo pasamos los campos permitidos
        return jumpseller_service.update_customer(customer_id, customer_data.dict(exclude_unset=True))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/customers/{customer_id}", summary="Eliminar un Cliente", tags=["Jumpseller API"])
def delete_customer_endpoint(customer_id: int):
    try:
        return jumpseller_service.delete_customer(customer_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/customers/{customer_id}",
            summary="Obtener un Cliente de Jumpseller por ID",
            tags=["Jumpseller API Explorer"])
def get_jumpseller_customer_by_id(customer_id: int):
    """
    Endpoint para obtener los detalles de un cliente específico desde Jumpseller.
    """
    customer_data = jumpseller_service.get_customer_by_id(customer_id)
    if not customer_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID {customer_id} not found in Jumpseller."
        )
    return customer_data

@router.get("/store-health-summary",
            summary="Obtener Resumen de Salud de la Tienda Jumpseller",
            tags=["Jumpseller API Explorer"])
def get_jumpseller_store_health():
    """
    Endpoint que agrega los conteos de recursos clave (órdenes, productos, clientes)
    de Jumpseller para un dashboard de salud.
    """
    summary_data = jumpseller_service.get_store_health_summary()
    return summary_data

@router.get("/stream-orders",
            summary="Obtener todas las Órdenes de Jumpseller (vía Streaming)",
            tags=["Jumpseller API Explorer"])
def stream_jumpseller_orders(status: str = "paid"):
    """
    Endpoint que obtiene todas las órdenes de Jumpseller usando una conexión
    de streaming para evitar timeouts. Devuelve en formato JSON-Lines.
    """
    return StreamingResponse(
        jumpseller_service.stream_all_jumpseller_orders(status),
        media_type="application/x-json-stream"
    )

@router.get("/orders/{order_id}",
            summary="Obtener una Orden de Jumpseller por ID",
            tags=["Jumpseller API Explorer"])
def get_jumpseller_order_by_id(order_id: int):
    """
    Endpoint para obtener los detalles completos de una orden específica.
    """
    try:
 
        order_data = jumpseller_service.get_orders(order_id=order_id) 
        return order_data
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Order not found or API error: {e}")
    

@router.get("/products/{product_id}",
            summary="Obtener un Producto de Jumpseller por ID",
            tags=["Jumpseller API Explorer"])
def get_jumpseller_product_by_id(product_id: int):
    """
    Endpoint para obtener los detalles completos de un producto específico desde Jumpseller.
    """
    try:
        product_data = jumpseller_service.get_product_by_id(product_id)
        return product_data
    except Exception as e:
        # Si _make_request lanza una excepción, la capturamos aquí
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Producto con ID {product_id} no encontrado en Jumpseller o error de API."
        )