# etl/modules/transform.py

from datetime import datetime
from typing import List, Dict, Any, Tuple
import streamlit as st

# ===================================================================
# ===               FUNCIONES AUXILIARES (PRIVADAS)               ===
# ===================================================================

def _parse_utc_string(date_string: str) -> datetime:
    """Convierte un string de fecha UTC de Jumpseller a un objeto datetime."""
    if not date_string:
        return None
    try:
        # Formato de Jumpseller: "YYYY-MM-DD HH:MM:SS UTC"
        return datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S %Z")
    except ValueError:
        return None

def _create_order_status_history(source_order: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Construye el historial de estados de una orden a partir de sus timestamps."""
    history = []
    
    created_at = _parse_utc_string(source_order.get("created_at"))
    if created_at:
        history.append({
            "status": "pending_payment",
            "timestamp": created_at,
            "updatedBy": "customer"
        })

    # El webhook es para 'status/paid', por lo que 'completed_at' es la fecha de pago.
    paid_at = _parse_utc_string(source_order.get("completed_at"))
    if paid_at:
        history.append({
            "status": "paid",
            "timestamp": paid_at,
            "updatedBy": "system"
        })
    
    return history

def _extract_contact_on_site(source_order: Dict[str, Any]) -> Dict[str, str]:
    """Extrae el nombre de contacto del sitio desde los campos adicionales."""
    fields = source_order.get("additional_fields", [])
    contact_name = "No especificado"
    
    for field in fields:
        if field.get("label") == "Nombre de quien recibirá al profesional":
            contact_name = field.get("value")
            break
            
    customer_phone = source_order.get("customer", {}).get("phone", "N/A")
    
    return {"name": contact_name, "phone": f"+56{customer_phone}"}

# ===================================================================
# ===              TRANSFORMACIONES PRINCIPALES (PÚBLICAS)        ===
# ===================================================================

def transform_orders(source_orders: List[Dict[str, Any]], logger=st.info) -> List[Dict[str, Any]]:
    """Transforma una lista de órdenes de Jumpseller a la estructura de Firestore."""
    logger("🔄 Transformando datos de Órdenes...")
    transformed_orders = []
    for order in source_orders:
        new_order = {
            "id": str(order.get("id")),
            "customerId": str(order.get("customer", {}).get("id")),
            "professionalId": None,
            "total": order.get("total", 0),
            "status": order.get("status_enum", "unknown"),
            "createdAt": _parse_utc_string(order.get("created_at")),
            "updatedAt": datetime.now(),
            "items": [
                {
                    "serviceId": str(p.get("id")),
                    "serviceName": p.get("name"),
                    "quantity": p.get("qty"),
                    "price": p.get("price")
                } for p in order.get("products", [])
            ],
            "paymentDetails": {
                "type": order.get("payment_method_type"),
                "transactionId": order.get("payment_notification_id"),
                "methodId": None
            },
            "serviceAddress": {
                "addressId": f"addr_{order.get('id')}",
                "commune": order.get("shipping_address", {}).get("municipality"),
                "region": order.get("shipping_address", {}).get("region"),
                "instructions": order.get("shipping_address", {}).get("complement")
            },
            "contactOnSite": _extract_contact_on_site(order),
            "statusHistory": _create_order_status_history(order),
            "rating": None,
            "invoiceDetails": None
        }
        transformed_orders.append(new_order)
    
    logger(f"✅ Transformación de {len(transformed_orders)} órdenes completada.")
    return transformed_orders

def transform_products(source_products: List[Dict[str, Any]], logger=st.info) -> Tuple[List[Dict], List[Dict]]:
    """Transforma productos de Jumpseller en una lista de servicios y una de categorías."""
    logger("🔄 Transformando datos de Productos y Categorías...")
    
    transformed_services = []
    unique_categories = {}

    for product in source_products:
        product_categories = product.get("categories", [])
        main_category_id = None
        
        if product_categories:
            main_cat = product_categories[0]
            cat_id = str(main_cat.get("id"))
            main_category_id = cat_id
            
            if cat_id not in unique_categories:
                unique_categories[cat_id] = {
                    "id": cat_id,
                    "name": main_cat.get("name", "Sin Nombre"),
                    "description": "",
                    "imageUrl": product.get("images", [{}])[0].get("url")
                }

        new_service = {
            "id": str(product.get("id")),
            "name": product.get("name", "Servicio sin nombre"),
            "description": product.get("description", ""),
            "categoryId": main_category_id,
            "price": product.get("price", 0.0),
            "discount": 0,
            "status": 'active' if product.get("status") == 'available' else 'inactive',
            "createdAt": _parse_utc_string(product.get("created_at")),
            "stats": {
                "viewCount": 0,
                "purchaseCount": 0,
                "averageRating": 0.0
            }
        }
        transformed_services.append(new_service)
    
    categories_list = list(unique_categories.values())
    
    logger(f"✅ Transformación completada: {len(transformed_services)} servicios y {len(categories_list)} categorías únicas encontradas.")
    return transformed_services, categories_list

