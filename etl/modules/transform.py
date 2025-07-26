# etl/modules/transform.py

from datetime import datetime
from typing import List, Dict, Any, Tuple
import streamlit as st
from bs4 import BeautifulSoup

# ===================================================================
# ===               FUNCIONES AUXILIARES (PRIVADAS)               ===
# ===================================================================

def _parse_utc_string(date_string: str) -> datetime:
    if not date_string: return None
    try:
        return datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S %Z")
    except ValueError:
        return None

def _create_order_status_history(source_order: Dict[str, Any]) -> List[Dict[str, Any]]:
    history = []
    created_at = _parse_utc_string(source_order.get("created_at"))
    if created_at:
        history.append({"status": "pending_payment", "timestamp": created_at, "updatedBy": "customer"})
    paid_at = _parse_utc_string(source_order.get("completed_at"))
    if paid_at:
        history.append({"status": "paid", "timestamp": paid_at, "updatedBy": "system"})
    return history

def _extract_contact_on_site(source_order: Dict[str, Any]) -> Dict[str, str]:
    fields = source_order.get("additional_fields", [])
    contact_name = next((field.get("value") for field in fields if field.get("label") == "Nombre de quien recibirá al profesional"), "No especificado")
    customer_phone = source_order.get("customer", {}).get("phone", "N/A")
    return {"name": contact_name, "phone": f"+56{customer_phone}"}

def _clean_html(raw_html: str) -> str:
    if not raw_html: return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator="\n").strip()

# ===================================================================
# ===              TRANSFORMACIONES PRINCIPALES (PÚBLICAS)        ===
# ===================================================================
def transform_single_product(product: Dict[str, Any]) -> Tuple[Dict, Dict, List[Dict], List[Dict]]:
    """
    Transforma UN ÚNICO producto de Jumpseller en un servicio, su categoría principal,
    una lista de sus variantes y una lista de sus subcategorías.
    Ideal para la herramienta de mapeo.
    """
    if not product:
        return {}, {}, [], []

    product_id = str(product.get("id"))
    
    # --- 1. Extraer Categoría Principal ---
    product_categories = product.get("categories", [])
    category_id, category_data = None, None
    if product_categories:
        main_cat = product_categories[0]
        category_id = str(main_cat.get("id"))
        category_data = {
            "id": category_id,
            "name": main_cat.get("name", "Sin Categoría"),
            "description": main_cat.get("description") or "",
            "imageUrl": product.get("images", [{}])[0].get("url")
        }

    # --- 2. Extraer Subcategorías ---
    subcategories_data = []
    if len(product_categories) > 1:
        for sub_cat in product_categories[1:]:
            subcategories_data.append({
                "id": str(sub_cat.get("id")),
                "serviceId": product_id,
                "name": sub_cat.get("name")
            })
            
    # --- 3. Transformar Variantes ---
    variants_data = []
    for variant in product.get("variants", []):
        options = variant.get("options", [{}])[0]
        variants_data.append({
            "id": str(variant.get("id")),
            "serviceId": product_id,
            "price": variant.get("price", 0.0),
            "options": {"name": options.get("name"), "value": options.get("value")},
            "sku": variant.get("sku"),
            "stock": variant.get("stock")
        })
    
    # --- 4. Transformar Producto en Servicio ---
    service_data = {
        "id": product_id,
        "name": product.get("name"),
        "description": _clean_html(product.get("description", "")),
        "categoryId": category_id,
        "price": product.get("price", 0.0),
        "status": 'active' if product.get("status") == 'available' else 'inactive',
        "createdAt": _parse_utc_string(product.get("created_at")),
        "hasVariants": len(variants_data) > 0,
        "hasSubcategories": len(subcategories_data) > 0, 
        "stats": {"viewCount": 0, "purchaseCount": 0, "averageRating": 0.0}
    }
    
    return service_data, category_data, variants_data, subcategories_data




def transform_single_order(order: Dict[str, Any]) -> Tuple[Dict, Dict, Dict, Dict]:
    """
    Transforma UNA ÚNICA orden de Jumpseller en 4 diccionarios para Firestore,
    ideal para la herramienta de mapeo y validación.
    """
    if not order:
        return {}, {}, {}, {}

    customer_data = order.get("customer", {})
    customer_id = str(customer_data.get("id"))
    full_name = customer_data.get("fullname", " ").split(" ")
    first_name = full_name[0]
    last_name = " ".join(full_name[1:]) if len(full_name) > 1 else ""

    user_payload = {
        "id": customer_id, "email": customer_data.get("email"),
        "phone": f"+{customer_data.get('phone_prefix', '56')}{customer_data.get('phone', '')}",
        "accountType": "customer", "accountStatus": "verified",
        "createdAt": _parse_utc_string(order.get("created_at")),
        "lastLoginAt": datetime.now(), "isDeleted": False, "onboardingCompleted": True
    }

    customer_profile_payload = {
        "id": customer_id, "firstName": first_name, "lastName": last_name,
        "displayName": customer_data.get("fullname"),
        "rut": order.get("billing_address", {}).get("taxid"), "rutVerified": False,
        "primaryAddressRegion": order.get("shipping_address", {}).get("region"),
        "totalSpending": 0, "serviceHistoryCount": 0,
        "metadata": {"createdAt": _parse_utc_string(order.get("created_at")), "updatedAt": datetime.now()}
    }

    shipping_address = order.get("shipping_address", {})
    address_id = f"addr_{order.get('id')}"
    
    address_payload = {
        "id": address_id, "customerId": customer_id, "alias": "Principal",
        "street": shipping_address.get("address"), "number": shipping_address.get("street_number") or "S/N",
        "commune": shipping_address.get("municipality"), "region": shipping_address.get("region"),
        "isPrimary": True, "timesUsed": 1
    }

    order_payload = {
        "id": str(order.get("id")), "customerId": customer_id, "total": order.get("total", 0),
        "status": order.get("status_enum", "unknown"),
        "createdAt": _parse_utc_string(order.get("created_at")), "updatedAt": datetime.now(),
        "items": [{"serviceId": str(p.get("id")), "serviceName": p.get("name"), "quantity": p.get("qty"), "price": p.get("price")} for p in order.get("products", [])],
        "paymentDetails": {"type": order.get("payment_method_type"), "transactionId": order.get("payment_notification_id")},
        "serviceAddress": {"addressId": address_id, "commune": shipping_address.get("municipality"), "region": shipping_address.get("region")},
        "contactOnSite": _extract_contact_on_site(order),
        "statusHistory": _create_order_status_history(order)
    }

    return user_payload, customer_profile_payload, address_payload, order_payload


def transform_orders(source_orders: List[Dict[str, Any]], existing_user_emails: set, logger=st.info) -> Tuple[List, List, List, List]:
    """
    Orquesta la transformación de una lista de órdenes, extrayendo y de-duplicando
    datos de usuarios, perfiles y direcciones.
    """
    logger("🔄 Transformando datos de Órdenes, Usuarios, Perfiles y Direcciones...")
    
    all_orders, unique_users, unique_profiles, unique_addresses = [], {}, {}, {}
    first_order_dates = {}

    for order in sorted(source_orders, key=lambda o: o['created_at']):
        customer_id = str(order.get("customer", {}).get("id"))
        if customer_id and customer_id not in first_order_dates:
            first_order_dates[customer_id] = _parse_utc_string(order.get("created_at"))

    for order in source_orders:
        user, profile, address, transformed_order = transform_single_order(order)
        
        customer_id = transformed_order.get("customerId")
        customer_email = user.get("email")

        if not customer_id or not customer_email:
            continue

        if customer_id not in unique_users and customer_email not in existing_user_emails:
            unique_users[customer_id] = user
            unique_profiles[customer_id] = profile

        shipping_address = order.get("shipping_address", {})
        address_str = shipping_address.get("address", "").lower().strip()
        commune_str = shipping_address.get("municipality", "").lower().strip()
        address_key = f"{customer_id}_{address_str}_{commune_str}"

        if address_key not in unique_addresses:
            unique_addresses[address_key] = address

        all_orders.append(transformed_order)

    users_list, profiles_list, addresses_list = list(unique_users.values()), list(unique_profiles.values()), list(unique_addresses.values())
    logger(f"✅ Transformación completada: {len(all_orders)} órdenes, {len(users_list)} usuarios únicos, y {len(addresses_list)} direcciones únicas encontradas.")
    return users_list, profiles_list, addresses_list, all_orders


def transform_products(source_products: List[Dict[str, Any]], logger=st.info) -> Tuple[List, List, List, List]:
    """Transforma productos de Jumpseller en servicios, categorías, variantes y subcategorías."""
    logger("🔄 Transformando datos de Productos...")
    all_services, all_variants, all_subcategories, unique_categories = [], [], [], {}

    # 0. Extraer Servicios
    for product in source_products:
        product_id = str(product.get("id"))
        
        # 1. Extraer Categoría Principal
        product_categories = product.get("categories", [])
        category_id = None
        if product_categories:
            main_cat = product_categories[0]
            category_id = str(main_cat.get("id"))
            if category_id not in unique_categories:
                unique_categories[category_id] = {
                    "id": category_id,
                    "name": main_cat.get("name"),
                    "description": main_cat.get("description") or "",
                    "imageUrl": product.get("images", [{}])[0].get("url")
                }

        # 2. Extraer Subcategorías
        if len(product_categories) > 1:
            for sub_cat in product_categories[1:]:
                all_subcategories.append({
                    "id": str(sub_cat.get("id")),
                    "serviceId": product_id,
                    "name": sub_cat.get("name")
                })
            
        # 3. Transformar Variantes
        for variant in product.get("variants", []):
            options = variant.get("options", [{}])[0]
            all_variants.append({
                "id": str(variant.get("id")),
                "serviceId": product_id,
                "price": variant.get("price", 0.0),
                "options": {"name": options.get("name"), "value": options.get("value")},
                "sku": variant.get("sku"),
                "stock": variant.get("stock")
            })
        
        # 4. Transformar Producto en Servicio
        all_services.append({
            "id": product_id,
            "name": product.get("name"),
            "description": _clean_html(product.get("description", "")),
            "categoryId": category_id,
            "price": product.get("price", 0.0),
            "status": 'active' if product.get("status") == 'available' else 'inactive',
            "createdAt": _parse_utc_string(product.get("created_at")),
            "hasVariants": len(product.get("variants", [])) > 0,
            "hasSubcategories": len(product_categories) > 1, 
            "stats": {"viewCount": 0, "purchaseCount": 0, "averageRating": 0.0}
        })
  
    
    categories_list = list(unique_categories.values())
    logger(f"✅ Transformación completada: {len(all_services)} servicios, {len(categories_list)} categorías, {len(all_variants)} variantes y {len(all_subcategories)} subcategorías.")
    return all_services, categories_list, all_variants, all_subcategories