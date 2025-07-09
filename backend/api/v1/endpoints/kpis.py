from fastapi import APIRouter
from backend.services.firestore_service import  calculate_average_order_value, get_valid_users_data


router = APIRouter()


@router.get("/average-order-value")
def get_average_order_value():
    """
    Obtiene el ticket promedio (AOV) de todas las órdenes completadas.
    """
    aov = calculate_average_order_value()
    
    # Devuelve una respuesta JSON estructurada y clara
    return {"average_order_value": round(aov, 2), "currency": "CLP"}


@router.get("/valid-users-data")
def list_valid_users():
    """
    Obtiene los datos de los primeros 50 usuarios con validUser = true.
    La consulta está limitada a 50 resultados para proteger el rendimiento.
    """
    users = get_valid_users_data()
    return {"users": users}
