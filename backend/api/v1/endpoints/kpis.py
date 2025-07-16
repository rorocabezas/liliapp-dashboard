# backend/api/v1/endpoints/kpis.py
from fastapi import APIRouter, HTTPException, Query
from datetime import date, datetime 
from backend.services import firestore_service 
from backend.services.firestore_service import  calculate_average_order_value, get_valid_users_data


router = APIRouter()

def get_db_client():
    """
    Función para obtener el cliente de Firestore.
    Esto asegura que firestore.client() solo se llame DESPUÉS
    de que firebase_admin.initialize_app() se haya ejecutado.
    """
    return firestore.client()

@router.get("/summary", summary="Obtiene KPIs para el resumen ejecutivo")
def get_summary_kpis_endpoint(start_date: date, end_date: date):
    """
    Endpoint para obtener el resumen de KPIs para la página principal.
    Recibe un rango de fechas como parámetros de consulta.
    """
    try:
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        kpis = firestore_service.get_summary_kpis(start_datetime, end_datetime)
        return kpis
    except Exception as e:
        print(f"Error en el endpoint /summary: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")


@router.get("/average-order-value", summary="Calcula el Ticket Promedio (AOV)")
def get_average_order_value_endpoint():
    """
    Obtiene el ticket promedio (AOV) de todas las órdenes completadas.
    """
    try:
        aov = firestore_service.calculate_average_order_value()
        return {"average_order_value": round(aov, 2), "currency": "CLP"}
    except Exception as e:
        print(f"Error en el endpoint /average-order-value: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")


@router.get("/valid-users-data", summary="Obtiene una lista de usuarios válidos")
def list_valid_users_endpoint():
    """
    Obtiene los datos de los primeros 50 usuarios con validUser = true.
    """
    try:
        users = firestore_service.get_valid_users_data()
        return {"count": len(users), "users": users}
    except Exception as e:
        print(f"Error en el endpoint /valid-users-data: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")

# Este endpoint ya no es necesario si no lo usas, pero lo dejo por si acaso.
@router.get("/new-users", deprecated=True)
def get_new_users_deprecated():
    return {"message": "Este endpoint está obsoleto. Usa /summary."}


@router.get("/acquisition", summary="KPIs de Adquisición y Crecimiento")
def get_acquisition_kpis_endpoint(start_date: date, end_date: date):
    # Llama a la función del servicio y devuelve los datos
    # ... (implementación similar al endpoint /summary)
    return {"message": "Datos de adquisición aquí"}

@router.get("/conversion", summary="KPIs de Engagement y Conversión")
def get_conversion_kpis_endpoint(start_date: date, end_date: date):
    # Llama a la función del servicio y devuelve los datos
    # ...
    return {"message": "Datos de conversión aquí"}