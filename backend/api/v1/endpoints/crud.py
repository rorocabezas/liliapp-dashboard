# backend/api/v1/endpoints/crud.py

from fastapi import APIRouter, HTTPException, Body, Depends, BackgroundTasks
from typing import List, Dict, Any
from backend.services import firestore_service
from pydantic import BaseModel, EmailStr

router = APIRouter()

# --- Pydantic Models for Data Validation ---
class ServiceUpdate(BaseModel):
    name: str; description: str; price: float; status: str; categoryId: str
class CategoryUpdate(BaseModel):
    name: str; description: str = ""; imageUrl: str = ""
class UserUpdate(BaseModel):
    email: EmailStr; phone: str; accountStatus: str
class CustomerProfileUpdate(BaseModel):
    firstName: str; lastName: str; displayName: str; rut: str | None = None
class AddressUpdate(BaseModel):
    alias: str; street: str; number: str; commune: str; region: str; isPrimary: bool
    
# ===================================================================
# ===             CRUD Endpoints for 'users' & Profiles           ===
# ===================================================================

@router.get("/users", summary="Listar todos los usuarios", tags=["CRUD - Users & Customers"])
def list_users():
    return firestore_service.get_all_documents("users")

@router.get("/users/{user_id}/profile", summary="Obtener el perfil de un cliente", tags=["CRUD - Users & Customers"])
def get_customer_profile(user_id: str):
    profile = firestore_service.get_subcollection_document("users", user_id, "customer_profiles", "main")
    if not profile: raise HTTPException(status_code=404, detail="Perfil de cliente no encontrado")
    return profile

@router.get("/users/{user_id}/addresses", summary="Listar direcciones de un cliente", tags=["CRUD - Users & Customers"])
def get_customer_addresses(user_id: str):
    return firestore_service.list_nested_subcollection_documents("users", user_id, "customer_profiles", "main", "addresses")

@router.put("/users/{user_id}", summary="Actualizar datos de un usuario", tags=["CRUD - Users & Customers"])
def update_user(user_id: str, user_data: UserUpdate):
    try:
        firestore_service.update_document("users", user_id, user_data.dict())
        return {"status": "success", "message": f"Usuario {user_id} actualizado."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/users/{user_id}/profile", summary="Actualizar perfil de un cliente", tags=["CRUD - Users & Customers"])
def update_customer_profile(user_id: str, profile_data: CustomerProfileUpdate):
    try:
        firestore_service.update_subcollection_document("users", user_id, "customer_profiles", "main", profile_data.dict())
        return {"status": "success", "message": f"Perfil del cliente {user_id} actualizado."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/users/{user_id}/addresses/{address_id}", summary="Actualizar una dirección", tags=["CRUD - Users & Customers"])
def update_address(user_id: str, address_id: str, address_data: AddressUpdate):
    try:
        firestore_service.update_document_in_nested_subcollection("users", user_id, "customer_profiles", "main", "addresses", address_id, address_data.dict())
        return {"status": "success", "message": f"Dirección {address_id} actualizada."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
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
    

# --- Pydantic Models for 'subcategories' ---
class SubcategoryCreate(BaseModel):
    name: str

class SubcategoryUpdate(BaseModel):
    name: str

# ===================================================================
# ===            CRUD Endpoints for 'subcategories'               ===
# ===================================================================

@router.get("/services/{service_id}/subcategories", summary="Listar subcategorías de un servicio", tags=["CRUD - Subcategories"])
def list_subcategories(service_id: str):
    """Obtiene todas las subcategorías de un servicio específico."""
    try:
        # Usaremos una nueva función de servicio genérica para listar subcolecciones
        return firestore_service.list_subcollection_documents("services", service_id, "subcategories")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/services/{service_id}/subcategories", summary="Crear una nueva subcategoría", tags=["CRUD - Subcategories"])
def create_subcategory(service_id: str, subcategory_data: SubcategoryCreate):
    """Crea una nueva subcategoría dentro de un servicio."""
    try:
        # Nueva función de servicio genérica
        new_id = firestore_service.create_subcollection_document("services", service_id, "subcategories", subcategory_data.dict())
        return {"status": "success", "message": "Nueva subcategoría creada.", "id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/services/{service_id}/subcategories/{subcategory_id}", summary="Actualizar una subcategoría", tags=["CRUD - Subcategories"])
def update_subcategory(service_id: str, subcategory_id: str, subcategory_data: SubcategoryUpdate):
    try:
        firestore_service.update_document_in_subcollection("services", service_id, "subcategories", subcategory_id, subcategory_data.dict())
        return {"status": "success", "message": f"Subcategoría {subcategory_id} actualizada."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/services/{service_id}/subcategories/{subcategory_id}", summary="Eliminar una subcategoría", tags=["CRUD - Subcategories"])
def delete_subcategory(service_id: str, subcategory_id: str):
    """Elimina una subcategoría de un servicio."""
    try:
        # Nueva función de servicio genérica
        firestore_service.delete_document_in_subcollection("services", service_id, "subcategories", subcategory_id)
        return {"status": "success", "message": f"Subcategoría {subcategory_id} eliminada."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# --- Pydantic Models for 'variants' ---
class VariantOption(BaseModel):
    name: str
    value: str

class VariantCreate(BaseModel):
    price: float
    options: VariantOption
    sku: str | None = None
    stock: int = 0

class VariantUpdate(BaseModel):
    price: float
    options: VariantOption
    sku: str | None = None
    stock: int = 0

# ===================================================================
# ===               CRUD Endpoints for 'variants'                 ===
# ===================================================================

@router.get("/services/{service_id}/variants", summary="Listar variantes de un servicio", tags=["CRUD - Variants"])
def list_variants(service_id: str):
    """Obtiene todas las variantes de un servicio específico."""
    try:
        return firestore_service.list_subcollection_documents("services", service_id, "variants")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/services/{service_id}/variants", summary="Crear una nueva variante", tags=["CRUD - Variants"])
def create_variant(service_id: str, variant_data: VariantCreate):
    """Crea una nueva variante dentro de un servicio."""
    try:
        new_id = firestore_service.create_subcollection_document("services", service_id, "variants", variant_data.dict())
        return {"status": "success", "message": "Nueva variante creada.", "id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/services/{service_id}/variants/{variant_id}", summary="Actualizar una variante", tags=["CRUD - Variants"])
def update_variant(service_id: str, variant_id: str, variant_data: VariantUpdate):
    try:
        firestore_service.update_document_in_subcollection("services", service_id, "variants", variant_id, variant_data.dict())
        return {"status": "success", "message": f"Variante {variant_id} actualizada."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/services/{service_id}/variants/{variant_id}", summary="Eliminar una variante", tags=["CRUD - Variants"])
def delete_variant(service_id: str, variant_id: str):
    """Elimina una variante de un servicio."""
    try:
        firestore_service.delete_document_in_subcollection("services", service_id, "variants", variant_id)
        return {"status": "success", "message": f"Variante {variant_id} eliminada."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

# --- Nuevos Endpoints para la gestión de arreglos en Servicios ---

class SubcategoryPayload(BaseModel):
    id: str
    name: str

class VariantPayload(BaseModel):
    id: str
    price: float
    options: Dict[str, Any]
    stock: int
    sku: str = ""

@router.post("/services/{service_id}/subcategories", summary="Añadir una subcategoría a un servicio")
def add_subcategory_to_service(service_id: str, subcategory: SubcategoryPayload):
    try:
        firestore_service.add_item_to_service_array(service_id, "subcategories", subcategory.dict())
        return {"status": "success", "message": f"Subcategoría añadida al servicio {service_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/services/{service_id}/variants", summary="Añadir una variante a un servicio")
def add_variant_to_service(service_id: str, variant: VariantPayload):
    try:
        firestore_service.add_item_to_service_array(service_id, "variants", variant.dict())
        return {"status": "success", "message": f"Variante añadida al servicio {service_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    


@router.get("/customers", summary="Obtener todos los clientes")
def get_all_customers_endpoint():
    return firestore_service.get_all_customers()

@router.get("/customers/{customer_id}", summary="Obtener un cliente por ID")
def get_customer_endpoint(customer_id: str):
    customer = firestore_service.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return customer

@router.put("/customers/{customer_id}", summary="Actualizar datos de un cliente")
def update_customer_endpoint(customer_id: str, data: Dict[str, Any]):
    firestore_service.update_customer_main_fields(customer_id, data)
    return {"status": "success"}

@router.post("/customers/{customer_id}/addresses", summary="Añadir una dirección a un cliente")
def add_address_endpoint(customer_id: str, address: Dict[str, Any]):
    firestore_service.add_address_to_customer(customer_id, address)
    return {"status": "success"}


@router.put("/customers/{customer_id}/addresses/{address_id}", summary="Actualizar una dirección de un cliente")
def update_address_endpoint(customer_id: str, address_id: str, address_data: Dict[str, Any]):
    # Aseguramos que el ID en el payload coincida con el de la URL
    if address_data.get("id") != address_id:
        raise HTTPException(status_code=400, detail="El ID de la dirección en el payload no coincide con el de la URL.")
    
    try:
        firestore_service.update_address_in_customer_array(customer_id, address_data)
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    


@router.post("/services/clean-subcollections", 
             summary="[PELIGRO] Inicia la limpieza de subcolecciones en segundo plano",
             status_code=202) # Usamos 202 Accepted para tareas en segundo plano
def clean_services_subcollections_endpoint(background_tasks: BackgroundTasks):
    """
    Inicia una tarea en segundo plano para eliminar las subcolecciones 'variants' y
    'subcategories' de todos los servicios. Responde inmediatamente.
    """
    try:
        # Añadimos la función de larga duración a la cola de tareas en segundo plano
        background_tasks.add_task(firestore_service.clean_services_subcollections)
        
        # Devolvemos una respuesta inmediata al cliente
        return {
            "status": "accepted",
            "message": "El proceso de limpieza de subcolecciones se ha iniciado en segundo plano. Revisa los logs del servidor para ver el progreso."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo iniciar la tarea de limpieza: {str(e)}")