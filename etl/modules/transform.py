# etl/modules/transform.py
import streamlit as st
from datetime import datetime
from typing import List, Dict, Any, Tuple
from bs4 import BeautifulSoup

# ===================================================================
# ===               FUNCIONES AUXILIARES (PRIVADAS)               ===
# ===================================================================

def _parse_utc_string(date_string: str) -> datetime:
    if not date_string: return None
    try:
        # Intenta parsear con el formato completo
        return datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S %Z")
    except ValueError:
        try:
            # Intenta parsear si falta la zona horaria
            return datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
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
    
    # Versión robusta que maneja customer: null
    customer_data = source_order.get("customer") or {}
    customer_phone = customer_data.get("phone", "N/A")
    
    return {"name": contact_name, "phone": f"+56{customer_phone}"}

def _clean_html(raw_html: str) -> str:
    if not raw_html: return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator="\n").strip()

# ===================================================================
# ===              TRANSFORMACIONES PRINCIPALES (PÚBLICAS)        ===
# ===================================================================

def transform_single_product(product: Dict[str, Any]) -> Tuple[Dict, Dict, List[Dict], List[Dict]]:
    # Esta función ya era robusta, no necesita cambios.
    if not product:
        return {}, {}, [], []
    product_id = str(product.get("id"))
    product_categories = product.get("categories", [])
    category_id, category_data = None, None
    if product_categories:
        main_cat = product_categories[0]
        category_id = str(main_cat.get("id"))
        category_data = {
            "id": category_id, "name": main_cat.get("name", "Sin Categoría"),
            "description": main_cat.get("description") or "",
            "imageUrl": product.get("images", [{}])[0].get("url")
        }
    subcategories_data = []
    if len(product_categories) > 1:
        for sub_cat in product_categories[1:]:
            subcategories_data.append({"id": str(sub_cat.get("id")), "serviceId": product_id, "name": sub_cat.get("name")})
    variants_data = []
    for variant in product.get("variants", []):
        options = variant.get("options", [{}])[0]
        variants_data.append({
            "id": str(variant.get("id")), "serviceId": product_id, "price": variant.get("price", 0.0),
            "options": {"name": options.get("name"), "value": options.get("value")},
            "sku": variant.get("sku"), "stock": variant.get("stock")
        })
    service_data = {
        "id": product_id, "name": product.get("name"), "description": _clean_html(product.get("description", "")),
        "categoryId": category_id, "price": product.get("price", 0.0),
        "status": 'active' if product.get("status") == 'available' else 'inactive',
        "createdAt": _parse_utc_string(product.get("created_at")),
        "hasVariants": len(variants_data) > 0, "hasSubcategories": len(subcategories_data) > 0, 
        "stats": {"viewCount": 0, "purchaseCount": 0, "averageRating": 0.0}
    }
    return service_data, category_data, variants_data, subcategories_data

def transform_single_order(order: Dict[str, Any]) -> Tuple[Dict, Dict, Dict, Dict]:
    """ VERSIÓN DEFINITIVA A PRUEBA DE ERRORES """
    if not order:
        return None, None, None, None

    customer_data = order.get("customer") or {}
    shipping_address = order.get("shipping_address") or {}
    billing_address = order.get("billing_address") or {}
    payment_method = order.get("payment_method") or {}

    customer_id = str(customer_data.get("id"))
    if not customer_id or customer_id == 'None':
        return None, None, None, None

    # Lógica de extracción de nombre a prueba de 'None'
    full_name_str = (customer_data.get("fullname") or "").strip()
    if " " in full_name_str:
        first_name, last_name = full_name_str.split(" ", 1)
    else:
        first_name = full_name_str
        last_name = ""

    user_payload = {
        "id": customer_id, "email": customer_data.get("email"),
        "phone": f"+{customer_data.get('phone_prefix', '56')}{customer_data.get('phone', '')}",
        "accountType": "customer", "accountStatus": "verified",
        "createdAt": _parse_utc_string(order.get("created_at")),
        "lastLoginAt": datetime.now(), "isDeleted": False, "onboardingCompleted": True
    }

    customer_profile_payload = {
        "id": customer_id, "userId": customer_id, "firstName": first_name, "lastName": last_name,
        "displayName": full_name_str, "rut": billing_address.get("taxid"), "rutVerified": False,
        "primaryAddressRegion": shipping_address.get("region"), "totalSpending": 0,
        "serviceHistoryCount": 0, "metadata": {"createdAt": _parse_utc_string(order.get("created_at")), "updatedAt": datetime.now()}
    }

    address_id = f"addr_{order.get('id')}"
    address_payload = {
        "id": address_id, "userId": customer_id, "alias": "Principal",
        "street": shipping_address.get("address"), "number": shipping_address.get("street_number") or "S/N",
        "commune": shipping_address.get("municipality"), "region": shipping_address.get("region"),
        "isPrimary": True, "timesUsed": 1
    }

    order_payload = {
        "id": str(order.get("id")), "userId": customer_id, "addressId": address_id,
        "total": order.get("total", 0), "status": order.get("status"),
        "createdAt": _parse_utc_string(order.get("created_at")), "updatedAt": datetime.now(),
        "items": [{"serviceId": str(p.get("id")), "serviceName": p.get("name"), "quantity": p.get("qty"), "price": p.get("price")} for p in order.get("products", [])],
        "paymentDetails": {"type": payment_method.get('type'), "transactionId": order.get("payment_notification_id")},
        "serviceAddress": {"commune": shipping_address.get("municipality"), "region": shipping_address.get("region")},
        "contactOnSite": _extract_contact_on_site(order), "statusHistory": _create_order_status_history(order)
    }

    return user_payload, customer_profile_payload, address_payload, order_payload

def transform_orders(source_orders: List[Dict[str, Any]], existing_user_emails: set, logger=st.info) -> Tuple[List, List, List, List]:
    """ VERSIÓN DEFINITIVA A PRUEBA DE ERRORES """
    logger("🔄 Transformando datos de Órdenes, Usuarios, Perfiles y Direcciones...")
    
    initial_count = len(source_orders)
    cleaned_source_orders = [order for order in source_orders if order is not None]
    if len(cleaned_source_orders) < initial_count:
        logger(f"🧹 Se eliminaron {initial_count - len(cleaned_source_orders)} registros nulos de la lista de origen.")
    
    all_orders, unique_users, unique_profiles, unique_addresses = [], {}, {}, {}
    
    valid_orders_for_sorting = [o for o in cleaned_source_orders if o.get('createdAt')]
    first_order_dates = {}
    for order in sorted(valid_orders_for_sorting, key=lambda o: o['createdAt']):
        customer_data = order.get("customer")
        if customer_data and isinstance(customer_data, dict):
            customer_id = str(customer_data.get("id"))
            if customer_id and customer_id not in first_order_dates:
                first_order_dates[customer_id] = _parse_utc_string(order.get("created_at"))

    processed_count = 0
    skipped_count = 0
    for order in cleaned_source_orders:
        order_id = order.get('id', 'ID Desconocido')
        user, profile, address, transformed_order = transform_single_order(order)
        
        if not all((user, profile, address, transformed_order)):
            logger(f"⚠️ Saltando orden ID {order_id} por datos internos inválidos (ej: sin cliente o dirección).")
            skipped_count += 1
            continue

        customer_id = user.get("id")
        customer_email = user.get("email")
        if customer_id not in unique_users and customer_email not in existing_user_emails:
            unique_users[customer_id] = user
            unique_profiles[customer_id] = profile

        shipping_address = order.get("shipping_address") or {}
        address_str = shipping_address.get("address", "").lower().strip()
        commune_str = shipping_address.get("municipality", "").lower().strip()
        address_key = f"{customer_id}_{address_str}_{commune_str}"
        if address_key not in unique_addresses:
            unique_addresses[address_key] = address

        all_orders.append(transformed_order)
        processed_count += 1

    users_list = list(unique_users.values())
    profiles_list = list(unique_profiles.values())
    addresses_list = list(unique_addresses.values())
    
    summary_message = (
        f"✅ Transformación completada: {processed_count} órdenes procesadas, "
        f"{skipped_count} saltadas. Se encontraron {len(users_list)} nuevos usuarios "
        f"y {len(addresses_list)} direcciones únicas."
    )
    logger(summary_message)
    return users_list, profiles_list, addresses_list, all_orders

def transform_products(source_products: List[Dict[str, Any]], logger=st.info) -> Tuple[List, List, List, List]:
    # Esta función ya era robusta, no necesita cambios.
    logger("🔄 Transformando datos de Productos...")
    all_services, all_variants, all_subcategories, unique_categories = [], [], [], {}
    cleaned_source_products = [p for p in source_products if p is not None]

    for product in cleaned_source_products:
        product_id = str(product.get("id"))
        product_categories = product.get("categories", [])
        category_id = None
        if product_categories:
            main_cat = product_categories[0]
            category_id = str(main_cat.get("id"))
            if category_id not in unique_categories:
                unique_categories[category_id] = {
                    "id": category_id, "name": main_cat.get("name"), "description": main_cat.get("description") or "",
                    "imageUrl": product.get("images", [{}])[0].get("url")
                }
        if len(product_categories) > 1:
            for sub_cat in product_categories[1:]:
                all_subcategories.append({"id": str(sub_cat.get("id")), "serviceId": product_id, "name": sub_cat.get("name")})
        for variant in product.get("variants", []):
            options = variant.get("options", [{}])[0]
            all_variants.append({
                "id": str(variant.get("id")), "serviceId": product_id, "price": variant.get("price", 0.0),
                "options": {"name": options.get("name"), "value": options.get("value")},
                "sku": variant.get("sku"), "stock": variant.get("stock")
            })
        all_services.append({
            "id": product_id, "name": product.get("name"), "description": _clean_html(product.get("description", "")),
            "categoryId": category_id, "price": product.get("price", 0.0),
            "status": 'active' if product.get("status") == 'available' else 'inactive',
            "createdAt": _parse_utc_string(product.get("created_at")),
            "hasVariants": len(product.get("variants", [])) > 0, "hasSubcategories": len(product_categories) > 1, 
            "stats": {"viewCount": 0, "purchaseCount": 0, "averageRating": 0.0}
        })
    categories_list = list(unique_categories.values())
    logger(f"✅ Transformación completada: {len(all_services)} servicios, {len(categories_list)} categorías, {len(all_variants)} variantes y {len(all_subcategories)} subcategorías.")
    return all_services, categories_list, all_variants, all_subcategories