# backend/api/v1/endpoints/kpis.py
from fastapi import APIRouter, HTTPException, Query 
from datetime import date, datetime, timedelta, timezone
from backend.services import firestore_service


router = APIRouter()

# ===================================================================
# ===               ENDPOINTS PARA EL DASHBOARD                   ===
# ===================================================================

@router.get("/summary", summary="KPIs para Resumen Ejecutivo", tags=["Dashboard Pages"])
def get_summary_kpis_endpoint(start_date: date, end_date: date):
    """Obtiene el resumen de KPIs para la página principal."""
    try:
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        return firestore_service.get_summary_kpis(start_datetime, end_datetime)
    except Exception as e:
        print(f"Error en endpoint /summary: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor al procesar KPIs de resumen.")

# --- funcion para pagina de Adquisición y Crecimiento ---
@router.get("/acquisition", summary="Obtener KPIs de Adquisición de Clientes")
def get_acquisition_kpis_endpoint(
    start_date: str = Query(None, description="Fecha de inicio (YYYY-MM-DD)"),
    end_date: str = Query(None, description="Fecha de fin (YYYY-MM-DD)")
):
    """
    Devuelve un resumen de los KPIs de adquisición.
    Si no se proveen fechas, usa los últimos 30 días por defecto.
    """
    if start_date and end_date:
        # Creamos las fechas "ingenuas"
        naive_start = datetime.strptime(start_date, "%Y-%m-%d")
        naive_end = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59) # Incluir todo el día
        
        # --- CORRECCIÓN: Hacemos las fechas "conscientes" de UTC ---
        range_start = naive_start.replace(tzinfo=timezone.utc)
        range_end = naive_end.replace(tzinfo=timezone.utc)
    else:
        # datetime.now(timezone.utc) ya es consciente de la zona horaria
        range_end = datetime.now(timezone.utc)
        range_start = range_end - timedelta(days=30)
        
    kpis = firestore_service.get_acquisition_kpis(range_start, range_end)
    return kpis
    
# --- funcion para pagina de Engagement y Conversión ---
@router.get("/engagement", summary="KPIs de Engagement", tags=["Dashboard Pages"])
def get_engagement_kpis_endpoint(start_date: date, end_date: date):
    """Obtiene todos los KPIs para la página de Engagement y Conversión."""
    try:
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        data = firestore_service.get_engagement_kpis(start_datetime, end_datetime)
        data['aov_clp'] = round(data.get('aov_clp', 0))
        data['purchase_frequency'] = round(data.get('purchase_frequency', 0), 2)
        data['abandonment_rate'] = round(data.get('abandonment_rate', 0), 2)
        return data
    except Exception as e:
        print(f"Error en endpoint /engagement: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor al procesar KPIs de engagement.")
    

# --- funcion para pagina de Operaciones y Calidad ---
@router.get("/operations", summary="KPIs de Operaciones", tags=["Dashboard Pages"])
def get_operations_kpis_endpoint(start_date: date, end_date: date):
    """Obtiene todos los KPIs para la página de Operaciones."""
    try:
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        data = firestore_service.get_operations_kpis(start_datetime, end_datetime)
        data['cancellation_rate'] = round(data.get('cancellation_rate', 0), 2)
        data['avg_cycle_time_days'] = round(data.get('avg_cycle_time_days', 0), 1)
        data['avg_rating'] = round(data.get('avg_rating', 0), 2)
        return data
    except Exception as e:
        print(f"Error en endpoint /operations: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor al procesar KPIs de operaciones.")
    
# --- funcion para pagina de Retención y Lealtad ---
@router.get("/retention", summary="KPIs de Retención", tags=["Dashboard Pages"])
def get_retention_kpis_endpoint(end_date: date):
    """Obtiene todos los KPIs para la página de Retención."""
    try:
        end_datetime = datetime.combine(end_date, datetime.max.time())
        data = firestore_service.get_retention_kpis(end_datetime)
        data['ltv_clp'] = round(data.get('ltv_clp', 0))
        data['repurchase_rate'] = round(data.get('repurchase_rate', 0), 2)
        return data
    except Exception as e:
        print(f"Error en endpoint /retention: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor al procesar KPIs de retención.")
    

# --- funcion para pagina de Segmentación y Marketing ---
@router.get("/segmentation", summary="Segmentación de Clientes (RFM)", tags=["Dashboard Pages"])
def get_rfm_segmentation_endpoint(end_date: date):
    """Obtiene la distribución de clientes por segmento RFM."""
    try:
        end_datetime = datetime.combine(end_date, datetime.max.time())
        return firestore_service.get_rfm_segmentation(end_datetime)
    except Exception as e:
        print(f"Error en endpoint /segmentation: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor al procesar segmentación RFM.")