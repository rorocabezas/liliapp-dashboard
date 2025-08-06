# backend/api/v1/endpoints/kpis.py
from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timedelta, timezone
from backend.services import firestore_service

router = APIRouter()

def get_date_range(start_date: str, end_date: str) -> tuple[datetime, datetime]:
    """
    Función de ayuda para procesar el rango de fechas de los endpoints de manera consistente.
    Asegura que las fechas sean 'timezone-aware' (UTC).
    """
    try:
        if start_date and end_date:
            range_start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            # Se ajusta la fecha de fin para incluir el día completo
            range_end = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        else:
            # Valor por defecto: últimos 30 días
            range_end = datetime.now(timezone.utc)
            range_start = range_end - timedelta(days=30)
        return range_start, range_end
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Usa YYYY-MM-DD.")

@router.get("/acquisition", summary="Obtener KPIs de Adquisición")
def get_kpis_acquisition_endpoint(start_date: str = None, end_date: str = None):
    """
    Endpoint para los KPIs de la página de Adquisición.
    """
    range_start, range_end = get_date_range(start_date, end_date)
    return firestore_service.get_acquisition_kpis(range_start, range_end)

@router.get("/engagement", summary="Obtener KPIs de Engagement y Conversión")
def get_kpis_engagement_endpoint(start_date: str = None, end_date: str = None):
    """
    Endpoint para los KPIs de la página de Engagement y Conversión.
    """
    range_start, range_end = get_date_range(start_date, end_date)
    return firestore_service.get_engagement_kpis(range_start, range_end)

@router.get("/operations", summary="Obtener KPIs de Operaciones y Calidad")
def get_kpis_operations_endpoint(start_date: str = None, end_date: str = None):
    """
    Endpoint para los KPIs de la página de Operaciones y Calidad.
    """
    range_start, range_end = get_date_range(start_date, end_date)
    return firestore_service.get_operations_kpis(range_start, range_end)

@router.get("/retention", summary="Obtener KPIs de Retención y Lealtad")
def get_kpis_retention_endpoint(start_date: str = None, end_date: str = None):
    """
    Endpoint para los KPIs de la página de Retención y Lealtad.
    """
    range_start, range_end = get_date_range(start_date, end_date)
    return firestore_service.get_retention_kpis(range_start, range_end)

@router.get("/segmentation", summary="Obtener Segmentación RFM de Clientes")
def get_kpis_segmentation_endpoint(start_date: str = None, end_date: str = None):
    """
    Endpoint para el análisis de segmentación RFM.
    """
    range_start, range_end = get_date_range(start_date, end_date)
    return firestore_service.get_rfm_segmentation(range_start, range_end)