# etl/modules/transform.py

from datetime import datetime
from typing import List, Dict, Any, Tuple
import streamlit as st
from bs4 import BeautifulSoup

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

def transform_single_product(product: Dict[str, Any]) -> Tuple[Dict, Dict, List[Dict]]:
    """

    Transforma un único producto de Jumpseller en un servicio, su categoría principal,
    y una lista de sus variantes. (DEVUELVE 3 VALORES)
    """
    if not product:
        return None, None, []

    # --- 1. Extraer Categoría Principal ---
    product_categories = product.get("categories", [])
    category_id, category_data = None, None
    if product_categories:
        main_cat_index = 1 if len(product_categories) > 1 else 0
        main_cat = product_categories[main_cat_index]
        category_id = str(main_cat.get("id"))
        category_data = {
            "id": category_id, "name": main_cat.get("name", "Sin Categoría"),
            "description": main_cat.get("description") or "",
            "imageUrl": product.get("images", [{}])[0].get("url")
        }

    # --- 2. Limpiar Descripción HTML ---
    soup = BeautifulSoup(product.get("description", ""), "html.parser")
    clean_description = soup.get_text(separator="\n").strip()

    # --- 3. Transformar Producto en Servicio ---
    product_variants = product.get("variants", [])
    service_data = {
        "id": str(product.get("id")), "name": product.get("name"),
        "description": clean_description, "categoryId": category_id,
        "hasVariants": len(product_variants) > 0, "price": product.get("price", 0.0),
        "discount": 0.0, "status": 'active' if product.get("status") == 'available' else 'inactive',
        "createdAt": _parse_utc_string(product.get("created_at")),
        "stats": {"viewCount": 0, "purchaseCount": 0, "averageRating": 0.0}
    }
    
    # --- 4. Transformar Variantes ---
    variants_data = []
    for variant in product_variants:
        variant_options = variant.get("options", [{}])[0]
        new_variant = {
            "id": str(variant.get("id")), "serviceId": service_data["id"],
            "price": variant.get("price", 0.0),
            "options": {"name": variant_options.get("name"), "value": variant_options.get("value")}
        }
        variants_data.append(new_variant)
    
    return service_data, category_data, variants_data

def transform_products(source_products: List[Dict[str, Any]], logger=st.info) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """
    Orquesta la transformación de una lista de productos en servicios, categorías y variantes.
    """
    logger("🔄 Transformando datos de Productos, Categorías y Variantes...")
    
    all_services, all_variants, unique_categories = [], [], {}

    for product in source_products:
        service, category, variants = transform_single_product(product)
        if service: all_services.append(service)
        if variants: all_variants.extend(variants)
        if category and category.get("id") and category["id"] not in unique_categories:
            unique_categories[category["id"]] = category
    
    categories_list = list(unique_categories.values)
    
    logger(f"✅ Transformación completada: {len(all_services)} servicios, {len(categories_list)} categorías y {len(all_variants)} variantes encontradas.")
    return all_services, categories_list, all_variants