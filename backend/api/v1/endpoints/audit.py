from fastapi import APIRouter, HTTPException
from backend.services import jumpseller_service, firestore_service

router = APIRouter()

@router.get("/order/{order_id}", summary="Auditar datos de una orden entre Jumpseller y Firestore")
def audit_order_data(order_id: int):
    """
    Obtiene los datos de una orden desde Jumpseller y los documentos
    correspondientes desde Firestore para una comparación lado a lado.
    """
    # 1. Obtener datos de Jumpseller
    try:
        jumpseller_data = jumpseller_service.get_orders(order_id=order_id)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Orden ID {order_id} no encontrada en Jumpseller.")

    # 2. Obtener datos de Firestore (el ID es un string en Firestore)
    firestore_data = firestore_service.get_firestore_data_for_audit(str(order_id))

    if firestore_data.get("error"):
        raise HTTPException(status_code=404, detail=firestore_data["error"])

    return {
        "jumpseller_data": jumpseller_data.get("order", {}),
        "firestore_data": firestore_data
    }

@router.get("/service/{service_id}", summary="Auditar datos de un servicio entre Jumpseller y Firestore")
def audit_service_data(service_id: int):
    """
    Obtiene los datos de un producto/servicio desde Jumpseller y los documentos
    correspondientes desde Firestore para una comparación.
    """
    # 1. Obtener datos de Jumpseller (asumiendo que tienes una función para esto en el servicio)
    try:
        # Necesitaremos una función en jumpseller_service para obtener un solo producto
        jumpseller_data = jumpseller_service.get_product_by_id(service_id)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Producto ID {service_id} no encontrado en Jumpseller.")

    # 2. Obtener datos de Firestore (el ID es un string)
    firestore_data = firestore_service.get_firestore_service_data_for_audit(str(service_id))

    if firestore_data.get("error"):
        raise HTTPException(status_code=404, detail=firestore_data["error"])

    return {
        "jumpseller_data": jumpseller_data.get("product", {}),
        "firestore_data": firestore_data
    }