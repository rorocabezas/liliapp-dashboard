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
        return datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S %Z")
    except ValueError:
        try:
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
    if not product: return {}, {}, [], []
    product_id = str(product.get("id"))
    product_categories = product.get("categories", [])
    category_id, category_data = None, None
    if product_categories:
        main_cat = product_categories[0]
        category_id = str(main_cat.get("id"))
        category_data = {"id": category_id, "name": main_cat.get("name", "Sin Categoría"), "description": main_cat.get("description") or "", "imageUrl": product.get("images", [{}])[0].get("url")}
    subcategories_data = [{"id": str(sub_cat.get("id")), "serviceId": product_id, "name": sub_cat.get("name")} for sub_cat in product_categories[1:]]
    variants_data = [{"id": str(v.get("id")), "serviceId": product_id, "price": v.get("price", 0.0), "options": v.get("options", [{}])[0], "sku": v.get("sku"), "stock": v.get("stock")} for v in product.get("variants", [])]
    service_data = {"id": product_id, "name": product.get("name"), "description": _clean_html(product.get("description", "")), "categoryId": category_id, "price": product.get("price", 0.0), "status": 'active' if product.get("status") == 'available' else 'inactive', "createdAt": _parse_utc_string(product.get("created_at")), "hasVariants": len(variants_data) > 0, "hasSubcategories": len(subcategories_data) > 0, "stats": {"viewCount": 0, "purchaseCount": 0, "averageRating": 0.0}}
    return service_data, category_data, variants_data, subcategories_data

def transform_single_order(order: Dict[str, Any]) -> Tuple[Dict, Dict, Dict, Dict]:
    if not order: return None, None, None, None
    customer_data = order.get("customer") or {}
    shipping_address = order.get("shipping_address") or {}
    billing_address = order.get("billing_address") or {}
    payment_method = order.get("payment_method") or {}
    customer_id = str(customer_data.get("id"))
    if not customer_id or customer_id == 'None': return None, None, None, None
    full_name_str = (customer_data.get("fullname") or "").strip()
    if " " in full_name_str: first_name, last_name = full_name_str.split(" ", 1)
    else: first_name, last_name = full_name_str, ""
    user_payload = {"id": customer_id, "email": customer_data.get("email"), "phone": f"+{customer_data.get('phone_prefix', '56')}{customer_data.get('phone', '')}", "accountType": "customer", "accountStatus": "verified", "createdAt": _parse_utc_string(order.get("created_at")), "lastLoginAt": datetime.now(), "isDeleted": False, "onboardingCompleted": True}
    customer_profile_payload = {"id": customer_id, "userId": customer_id, "firstName": first_name, "lastName": last_name, "displayName": full_name_str, "rut": billing_address.get("taxid"), "rutVerified": False, "primaryAddressRegion": shipping_address.get("region"), "totalSpending": 0, "serviceHistoryCount": 0, "metadata": {"createdAt": _parse_utc_string(order.get("created_at")), "updatedAt": datetime.now()}}
    address_id = f"addr_{order.get('id')}"
    address_payload = {"id": address_id, "userId": customer_id, "alias": "Principal", "street": shipping_address.get("address"), "number": shipping_address.get("street_number") or "S/N", "commune": shipping_address.get("municipality"), "region": shipping_address.get("region"), "isPrimary": True, "timesUsed": 1}
    order_payload = {"id": str(order.get("id")), "userId": customer_id, "addressId": address_id, "total": order.get("total", 0), "status": order.get("status"), "createdAt": _parse_utc_string(order.get("created_at")), "updatedAt": datetime.now(), "items": [{"serviceId": str(p.get("id")), "serviceName": p.get("name"), "quantity": p.get("qty"), "price": p.get("price")} for p in order.get("products", [])], "paymentDetails": {"type": payment_method.get('type'), "transactionId": order.get("payment_notification_id")}, "serviceAddress": {"commune": shipping_address.get("municipality"), "region": shipping_address.get("region")}, "contactOnSite": _extract_contact_on_site(order), "statusHistory": _create_order_status_history(order)}
    return user_payload, customer_profile_payload, address_payload, order_payload

def transform_orders(source_orders: List[Dict[str, Any]], existing_user_emails: set, logger) -> Tuple[List, List, List, List]:
    logger("🔄 Transformando datos de Órdenes (Modelo Normalizado)...")
    cleaned_source_orders = [order for order in source_orders if order is not None]
    if len(cleaned_source_orders) < len(source_orders): logger(f"🧹 Se eliminaron {len(source_orders) - len(cleaned_source_orders)} registros nulos.")
    all_orders, unique_users, unique_profiles, unique_addresses = [], {}, {}, {}
    processed_count, skipped_count = 0, 0
    for order in cleaned_source_orders:
        order_id = order.get('id', 'ID Desconocido')
        user, profile, address, transformed_order = transform_single_order(order)
        if not all((user, profile, address, transformed_order)): logger(f"⚠️ Saltando orden ID {order_id} por datos internos inválidos."); skipped_count += 1; continue
        customer_id, customer_email = user.get("id"), user.get("email")
        if customer_id not in unique_users and customer_email not in existing_user_emails: unique_users[customer_id] = user; unique_profiles[customer_id] = profile
        shipping_address = order.get("shipping_address") or {}
        address_key = f"{customer_id}_{shipping_address.get('address', '').lower().strip()}_{shipping_address.get('municipality', '').lower().strip()}"
        if address_key not in unique_addresses: unique_addresses[address_key] = address
        all_orders.append(transformed_order); processed_count += 1
    users_list, profiles_list, addresses_list = list(unique_users.values()), list(unique_profiles.values()), list(unique_addresses.values())
    logger(f"✅ Transformación completada: {processed_count} órdenes procesadas, {skipped_count} saltadas. Se encontraron {len(users_list)} nuevos usuarios y {len(addresses_list)} direcciones únicas.")
    return users_list, profiles_list, addresses_list, all_orders

def transform_products(source_products: List[Dict[str, Any]], logger) -> Tuple[List, List, List, List]:
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
            if category_id not in unique_categories: unique_categories[category_id] = {"id": category_id, "name": main_cat.get("name"), "description": main_cat.get("description") or "", "imageUrl": product.get("images", [{}])[0].get("url")}
        all_subcategories.extend([{"id": str(sub_cat.get("id")), "serviceId": product_id, "name": sub_cat.get("name")} for sub_cat in product_categories[1:]])
        all_variants.extend([{"id": str(v.get("id")), "serviceId": product_id, "price": v.get("price", 0.0), "options": v.get("options", [{}])[0], "sku": v.get("sku"), "stock": v.get("stock")} for v in product.get("variants", [])])
        all_services.append({"id": product_id, "name": product.get("name"), "description": _clean_html(product.get("description", "")), "categoryId": category_id, "price": product.get("price", 0.0), "status": 'active' if product.get("status") == 'available' else 'inactive', "createdAt": _parse_utc_string(product.get("created_at")), "hasVariants": len(product.get("variants", [])) > 0, "hasSubcategories": len(product_categories) > 1, "stats": {"viewCount": 0, "purchaseCount": 0, "averageRating": 0.0}})
    categories_list = list(unique_categories.values())
    logger(f"✅ Transformación completada: {len(all_services)} servicios, {len(categories_list)} categorías, {len(all_variants)} variantes y {len(all_subcategories)} subcategorías.")
    return all_services, categories_list, all_variants, all_subcategories

# --- NUEVAS FUNCIONES PARA EL MODELO CUSTOMER-CENTRIC (CON DEPURACIÓN) ---

def transform_order_to_customer_model(order: Dict[str, Any]) -> Tuple[Dict, Dict]:
    """Transforma una única orden. Devuelve (None, None) si no es válida."""
    
    print(f"\n--- [DEBUG] Intentando transformar Orden ID: {order.get('id', 'N/A')} ---")

    if not order: 
        print("[DEBUG] RECHAZADO: El objeto de la orden es None.")
        return None, None

    customer_data = order.get("customer") or {}
    shipping_address = order.get("shipping_address") or {}
    billing_address = order.get("billing_address") or {}
    
    customer_id = customer_data.get("id")
    print(f"[DEBUG] ID de cliente encontrado: {repr(customer_id)} (Tipo: {type(customer_id)})")

    if customer_id is None or str(customer_id).strip() == '':
        print(f"[DEBUG] RECHAZADO: ID de cliente es '{customer_id}'. No es válido.")
        return None, None
        
    customer_id = str(customer_id)
    
    full_name_str = (customer_data.get("fullname") or "").strip()
    print(f"[DEBUG] Nombre completo encontrado: '{full_name_str}'")

    if " " in full_name_str: first_name, last_name = full_name_str.split(" ", 1)
    else: first_name, last_name = full_name_str, ""
    
    print(f"[DEBUG] ACEPTADO: La orden ID {order.get('id')} ha pasado todas las validaciones.")

    customer_payload = { "id": customer_id, "email": customer_data.get("email"), "phone": f"+{customer_data.get('phone_prefix', '56')}{customer_data.get('phone', '')}", "accountType": "customer", "accountStatus": "verified", "createdAt": _parse_utc_string(order.get("created_at")), "lastLoginAt": datetime.now(), "isDeleted": False, "onboardingCompleted": True, "firstName": first_name, "lastName": last_name, "displayName": full_name_str, "rut": billing_address.get("taxid"), "rutVerified": False, "addresses": [{"id": f"addr_{order.get('id')}", "alias": "Principal", "street": shipping_address.get("address"), "number": shipping_address.get("street_number") or "S/N", "commune": shipping_address.get("municipality"), "region": shipping_address.get("region"), "isPrimary": True}], "totalSpending": order.get("total", 0), "serviceHistoryCount": 1 }
    order_payload = { "id": str(order.get("id")), "customerId": customer_id, "addressId": f"addr_{order.get('id')}", "total": order.get("total", 0), "status": order.get("status"), "createdAt": _parse_utc_string(order.get("created_at")), "updatedAt": datetime.now(), "items": [{"serviceId": str(p.get("id")), "serviceName": p.get("name"), "quantity": p.get("qty"), "price": p.get("price")} for p in order.get("products", [])] }
    
    return customer_payload, order_payload

def transform_orders_for_customer_model(source_orders: List[Dict[str, Any]]) -> Tuple[List[Dict], List[Dict]]:
    """Toma una lista de órdenes y las consolida en documentos de 'customer' únicos."""
    
    # --- DEPURACIÓN FINAL ---
    print(f"\n--- [TRANSFORM.PY DEBUG] La función recibió {len(source_orders)} órdenes ---")

    unique_customers, all_orders = {}, []
    
    # Hemos eliminado el 'sorted' para simplificar la depuración.
    # El ordenamiento no es crítico para la funcionalidad.
    for order in source_orders:
        customer_payload, order_payload = transform_order_to_customer_model(order)
        
        if not customer_payload or not order_payload:
            continue # Salta órdenes inválidas
            
        customer_id = customer_payload["id"]
        if customer_id in unique_customers:
            # Lógica de fusión de clientes
            existing_addresses = unique_customers[customer_id]["addresses"]
            new_address = customer_payload["addresses"][0]
            if new_address["id"] not in {addr["id"] for addr in existing_addresses}:
                existing_addresses.append(new_address)
            unique_customers[customer_id]["totalSpending"] += customer_payload["totalSpending"]
            unique_customers[customer_id]["serviceHistoryCount"] += 1
            if customer_payload["createdAt"] < unique_customers[customer_id]["createdAt"]:
                unique_customers[customer_id]["createdAt"] = customer_payload["createdAt"]
            if customer_payload["lastLoginAt"] > unique_customers[customer_id]["lastLoginAt"]:
                unique_customers[customer_id]["lastLoginAt"] = customer_payload["lastLoginAt"]
        else:
            unique_customers[customer_id] = customer_payload
            
        all_orders.append(order_payload)
        
    customers_list = list(unique_customers.values())
    print(f"[TRANSFORM.PY DEBUG] La función va a devolver {len(customers_list)} clientes y {len(all_orders)} órdenes.")
    return customers_list, all_orders


def transform_product_to_service_model(product: Dict[str, Any]) -> Tuple[Dict, List[Dict]]:
    """
    Transforma un producto de Jumpseller en un documento 'service' con referencias
    anidadas (modelo híbrido) y una lista de las categorías únicas encontradas.
    """
    if not product:
        return None, []

    product_id = str(product.get("id"))
    
    # --- Extraer Categoría Principal (solo referencia) ---
    product_categories_raw = product.get("categories", [])
    category_reference = None
    if product_categories_raw:
        main_cat = product_categories_raw[0]
        category_reference = {"id": str(main_cat.get("id"))}

    # --- Extraer Subcategorías como un Arreglo de Referencias ---
    subcategories_references = []
    if len(product_categories_raw) > 1:
        for sub_cat in product_categories_raw[1:]:
            subcategories_references.append({"id": str(sub_cat.get("id"))})
            
    # --- Extraer Variantes (completamente anidadas) ---
    variants_array = []
    for variant in product.get("variants", []):
        options = variant.get("options", [{}])[0]
        variants_array.append({
            "id": str(variant.get("id")), "price": variant.get("price", 0.0),
            "options": {"name": options.get("name"), "value": options.get("value")},
            "sku": variant.get("sku"), "stock": variant.get("stock")
        })
    
    # --- Ensamblar el Documento de Servicio Final ---
    service_payload = {
        "id": product_id, "name": product.get("name"), "description": _clean_html(product.get("description", "")),
        "price": product.get("price", 0.0), "status": 'active' if product.get("status") == 'available' else 'inactive',
        "createdAt": _parse_utc_string(product.get("created_at")), "imageUrl": product.get("images", [{}])[0].get("url"),
        
        # --- Datos Anidados (Modelo Híbrido) ---
        "category": category_reference,
        "subcategories": subcategories_references,
        "variants": variants_array,
        
        "stats": {"viewCount": 0, "purchaseCount": 0, "averageRating": 0.0}
    }
    
    # --- También devolvemos los documentos de categoría completos para la colección 'categories' ---
    categories_found = []
    for cat in product_categories_raw:
        categories_found.append({
            "id": str(cat.get("id")),
            "name": cat.get("name"),
            "description": cat.get("description") or ""
        })

    return service_payload, categories_found

# --- Función para Transformar Múltiples Productos al Modelo 'Service-Híbrido' ---
def transform_products_for_service_model(source_products: List[Dict[str, Any]], logger) -> Tuple[List[Dict], List[Dict]]:
    """
    Toma una lista de productos de Jumpseller y los transforma en documentos 'service'
    (modelo híbrido) y una lista de documentos de categoría únicos.
    """
    logger("🔄 Transformando productos al modelo 'Service-Híbrido'...")
    
    all_services = []
    unique_categories = {}
    
    cleaned_source_products = [p for p in source_products if p is not None]

    for product in cleaned_source_products:
        service_doc, categories_docs = transform_product_to_service_model(product)
        
        if not service_doc:
            continue
            
        all_services.append(service_doc)
        
        # Agregamos las categorías encontradas a un diccionario para de-duplicar
        for cat in categories_docs:
            if cat['id'] not in unique_categories:
                unique_categories[cat['id']] = cat

    services_list = all_services
    categories_list = list(unique_categories.values())
    
    logger(f"✅ Transformación completada: {len(services_list)} servicios y {len(categories_list)} categorías únicas generadas.")
    return services_list, categories_list

def transform_categories(source_categories: List[Dict[str, Any]], logger) -> List[Dict]:
    """
    Transforma la lista de categorías de Jumpseller al modelo de Firestore.
    """
    logger(f"🔄 Transformando {len(source_categories)} categorías...")
    
    transformed = []
    for item in source_categories:
        cat = item.get("category", {})
        if not cat or not cat.get("id"):
            continue
            
        transformed.append({
            "id": str(cat.get("id")),
            "name": cat.get("name"),
            "description": cat.get("description") or "",
        })
        
    logger(f"✅ Transformación de categorías completada.")
    return transformed