# backend/api/v1/endpoints/crud.py

from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict, Any
from backend.services import firestore_service
from pydantic import BaseModel

router = APIRouter()

# --- Pydantic Models for Data Validation ---
class ServiceUpdate(BaseModel):
    name: str
    description: str
    price: float
    status: str
    categoryId: str

# ===================================================================
# ===               CRUD Endpoints for 'services'                 ===
# ===================================================================

@router.get("/services", summary="Listar todos los servicios", tags=["CRUD - Services"])
def list_services():
    try:
        return firestore_service.get_all_documents("services")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/services/{service_id}", summary="Obtener un servicio por ID", tags=["CRUD - Services"])
def get_service(service_id: str):
    try:
        service = firestore_service.get_document_by_id("services", service_id)
        if not service:
            raise HTTPException(status_code=404, detail="Servicio no encontrado")
        return service
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/services/{service_id}", summary="Actualizar un servicio", tags=["CRUD - Services"])
def update_service(service_id: str, service_data: ServiceUpdate):
    try:
        # Convertimos el modelo Pydantic a un diccionario
        update_data = service_data.dict()
        firestore_service.update_document("services", service_id, update_data)
        return {"status": "success", "message": f"Servicio {service_id} actualizado."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/services", summary="Crear un nuevo servicio", tags=["CRUD - Services"])
def create_service(service_data: ServiceUpdate):
    try:
        new_id = firestore_service.create_document("services", service_data.dict())
        return {"status": "success", "message": "Nuevo servicio creado.", "id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Pydantic Models for 'categories' ---
class CategoryUpdate(BaseModel):
    name: str
    description: str = ""
    imageUrl: str = ""

# ===================================================================
# ===               CRUD Endpoints for 'categories'               ===
# ===================================================================

@router.get("/categories", summary="Listar todas las categorías", tags=["CRUD - Categories"])
def list_categories():
    try:
        # Reutilizamos nuestra función genérica
        return firestore_service.get_all_documents("categories")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/categories/{category_id}", summary="Actualizar una categoría", tags=["CRUD - Categories"])
def update_category(category_id: str, category_data: CategoryUpdate):
    try:
        firestore_service.update_document("categories", category_id, category_data.dict())
        return {"status": "success", "message": f"Categoría {category_id} actualizada."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/categories", summary="Crear una nueva categoría", tags=["CRUD - Categories"])
def create_category(category_data: CategoryUpdate):
    try:
        # En este caso, el ID es autogenerado por Firestore
        new_id = firestore_service.create_document("categories", category_data.dict())
        return {"status": "success", "message": "Nueva categoría creada.", "id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))