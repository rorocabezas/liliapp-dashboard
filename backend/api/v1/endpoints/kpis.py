# backend/api/v1/endpoints/kpis.py
from fastapi import APIRouter, HTTPException
from datetime import date, datetime
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
@router.get("/acquisition", summary="KPIs de Adquisición", tags=["Dashboard Pages"])
def get_acquisition_kpis_endpoint(start_date: date, end_date: date):
    """Obtiene todos los KPIs para la página de Adquisición."""
    try:
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        data = firestore_service.get_acquisition_kpis(start_datetime, end_datetime)
        data['onboarding_rate'] = round(data.get('onboarding_rate', 0), 2)
        data['rut_validation_rate'] = round(data.get('rut_validation_rate', 0), 2)
        return data
    except Exception as e:
        print(f"Error en endpoint /acquisition: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor al procesar KPIs de adquisición.")
    
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