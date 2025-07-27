# backend/api/v1/endpoints/jumpseller.py

from fastapi import APIRouter, HTTPException, Query
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

@router.get("/products", summary="Obtener Productos", tags=["Jumpseller API"])
def get_products_endpoint(
    status: str = Query("available", description="Estado del producto"),
    limit: int = Query(20, le=100),
    page: int = Query(1)
):
    try:
        return jumpseller_service.get_products(limit=limit, page=page, status=status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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