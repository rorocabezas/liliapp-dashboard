import streamlit as st
from firebase_admin import firestore

# --- HELPER FUNCTIONS ---
def get_db_client():
    return firestore.client()

# ==========================================================
# ===         FUNCIONES DE CARGA GENÉRICAS               ===
# ==========================================================

def load_data_to_firestore(collection_name: str, data: list, id_field: str, logger=st.info, merge: bool = False):
    """
    Carga una lista de diccionarios a una colección de nivel superior en Firestore.
    Usa el valor de 'id_field' como el ID del documento.
    Si merge=True, crea o actualiza el documento si ya existe (idempotente).
    """
    if not data:
        logger(f"🧘 No hay nuevos datos para cargar en '{collection_name}'.")
        return

    db = get_db_client()
    batch = db.batch()
    
    logger(f"🚀 Procesando '{collection_name}'... {len(data)} registros.")
    
    # Esta función ya no necesita contar, la dejamos más simple
    # para set (crear/sobrescribir) o set con merge (crear/actualizar)
    for item in data:
        doc_id = str(item.get(id_field))
        if not doc_id:
            logger(f"⚠️ Saltando registro en '{collection_name}' por falta de ID.")
            continue
        
        doc_ref = db.collection(collection_name).document(doc_id)
        batch.set(doc_ref, item, merge=merge)

    batch.commit()
    
    action = "creados/actualizados" if merge else "creados/sobrescritos"
    logger(f"✅ Carga de {len(data)} registros para '{collection_name}' completada ({action}).")

# ==========================================================
# ===         FUNCIONES DE CARGA ESPECÍFICAS             ===
# ==========================================================

def load_customer_profiles(profiles_data: list, logger=st.info):
    """
    Carga datos de perfiles de cliente en la subcolección 
    users/{userId}/customer_profiles.
    """
    if not profiles_data:
        logger("🧘 No hay nuevos perfiles de cliente para cargar.")
        return

    db = get_db_client()
    batch = db.batch()
    
    logger(f"🚀 Procesando 'customer_profiles'... {len(profiles_data)} registros.")
    
    for profile_data in profiles_data:
        # --- CORRECCIÓN: Usar 'userId' en lugar de 'customerId' ---
        user_id = profile_data.pop('userId', None)
        profile_id = profile_data.get('id')

        if not user_id or not profile_id:
            logger("⚠️ Saltando perfil por falta de 'userId' o 'id'.")
            continue
            
        doc_ref = db.collection('users').document(user_id).collection('customer_profiles').document(profile_id)
        batch.set(doc_ref, profile_data)

    batch.commit()
    logger(f"✅ Carga de {len(profiles_data)} perfiles completada.")

def load_addresses(addresses_data: list, logger=st.info):
    """
    Carga direcciones en la subcolección anidada
    users/{userId}/customer_profiles/main/addresses.
    """
    if not addresses_data:
        logger("🧘 No hay nuevas direcciones para cargar.")
        return

    db = get_db_client()
    batch = db.batch()
    
    logger(f"🚀 Procesando 'addresses'... {len(addresses_data)} registros.")

    for address_data in addresses_data:
        # --- CORRECCIÓN: Usar 'userId' en lugar de 'customerId' ---
        user_id = address_data.pop('userId', None)
        address_id = address_data.get('id')

        if not user_id or not address_id:
            logger("⚠️ Saltando dirección por falta de 'userId' o 'id'.")
            continue
            
        # Asumimos que el profileId es el mismo que el userId
        profile_id = user_id
        doc_ref = db.collection('users').document(user_id).collection('customer_profiles').document(profile_id).collection('addresses').document(address_id)
        batch.set(doc_ref, address_data)
        
    batch.commit()
    logger(f"✅ Carga de {len(addresses_data)} direcciones completada.")

def load_variants_to_firestore(variants_data: list, logger=st.info):
    """Carga variantes en la subcolección services/{serviceId}/variants."""
    if not variants_data:
        logger("🧘 No hay nuevas variantes para cargar.")
        return

    db = get_db_client()
    batch = db.batch()
    
    logger(f"🚀 Procesando 'variants'... {len(variants_data)} registros.")

    for variant_data in variants_data:
        service_id = variant_data.pop('serviceId', None)
        variant_id = variant_data.get('id')

        if not service_id or not variant_id:
            logger("⚠️ Saltando variante por falta de 'serviceId' o 'id'.")
            continue

        doc_ref = db.collection('services').document(service_id).collection('variants').document(variant_id)
        batch.set(doc_ref, variant_data)
        
    batch.commit()
    logger(f"✅ Carga de {len(variants_data)} variantes completada.")

def load_subcategories_to_firestore(subcategories_data: list, logger=st.info):
    """Carga subcategorías en la subcolección services/{serviceId}/subcategories."""
    if not subcategories_data:
        logger("🧘 No hay nuevas subcategorías para cargar.")
        return

    db = get_db_client()
    batch = db.batch()

    logger(f"🚀 Procesando 'subcategories'... {len(subcategories_data)} registros.")

    for subcat_data in subcategories_data:
        service_id = subcat_data.pop('serviceId', None)
        subcat_id = subcat_data.get('id')

        if not service_id or not subcat_id:
            logger("⚠️ Saltando subcategoría por falta de 'serviceId' o 'id'.")
            continue

        doc_ref = db.collection('services').document(service_id).collection('subcategories').document(subcat_id)
        batch.set(doc_ref, subcat_data)
        
    batch.commit()
    logger(f"✅ Carga de {len(subcategories_data)} subcategorías completada.")


@firestore.transactional
def _update_customer_in_transaction(transaction, doc_ref, new_data):
    """Función transaccional para actualizar o crear un documento de cliente."""
    snapshot = doc_ref.get(transaction=transaction)
    
    if snapshot.exists:
        # El cliente ya existe, fusionamos los datos
        existing_data = snapshot.to_dict()
        
        # Fusionar direcciones sin duplicados
        existing_addresses = existing_data.get("addresses", [])
        existing_address_ids = {addr["id"] for addr in existing_addresses}
        new_address = new_data["addresses"][0]
        if new_address["id"] not in existing_address_ids:
            existing_addresses.append(new_address)

        # Actualizar campos
        update_payload = {
            "firstName": new_data["firstName"],
            "lastName": new_data["lastName"],
            "displayName": new_data["displayName"],
            "phone": new_data["phone"],
            "rut": new_data["rut"],
            "addresses": existing_addresses,
            "totalSpending": firestore.Increment(new_data["totalSpending"]),
            "serviceHistoryCount": firestore.Increment(new_data["serviceHistoryCount"]),
            "lastLoginAt": new_data["lastLoginAt"]
        }
        transaction.update(doc_ref, update_payload)
        return "updated"
    else:
        # El cliente es nuevo, creamos el documento
        transaction.set(doc_ref, new_data)
        return "created"

def load_customers_denormalized(customers_data: list, logger=st.info):
    """
    Carga o actualiza documentos en la colección 'customers' de forma segura,
    fusionando el arreglo de direcciones.
    """
    if not customers_data:
        logger("🧘 No hay nuevos datos de clientes para cargar.")
        return

    db = get_db_client()
    logger(f"🚀 Procesando 'customers'... {len(customers_data)} registros únicos.")
    
    created_count, updated_count = 0, 0
    
    for customer in customers_data:
        customer_id = str(customer.get("id"))
        if not customer_id:
            logger("⚠️ Saltando registro de cliente por falta de ID.")
            continue
        
        doc_ref = db.collection('customers').document(customer_id)
        transaction = db.transaction()
        result = _update_customer_in_transaction(transaction, doc_ref, customer)
        
        if result == "created":
            created_count += 1
        elif result == "updated":
            updated_count += 1
    
    summary = (
        f"Resumen de Carga para 'customers':\n"
        f"✨ Creados: {created_count} | "
        f"🔄 Actualizados: {updated_count}"
    )
    logger(summary)

# ==========================================================
# ===         FUNCIONES DE CARGA HÍBRIDA DE SERVICIOS     ===
# ==========================================================
def load_services_hybrid(services_data: list, categories_data: list, logger=st.info):
    """
    Carga los datos del modelo de servicio híbrido. Primero asegura que las categorías
    existan (crea o actualiza) y luego carga los documentos de servicio.
    """
    db = get_db_client()
    
    # --- Carga de Categorías (Idempotente) ---
    if categories_data:
        logger(f"🚀 Procesando 'categories'... {len(categories_data)} registros únicos encontrados.")
        batch_cat = db.batch()
        for cat in categories_data:
            cat_id = str(cat.get("id"))
            if not cat_id: continue
            doc_ref = db.collection('categories').document(cat_id)
            # Usamos set con merge=True para crear si no existe o actualizar si ya existe.
            batch_cat.set(doc_ref, cat, merge=True)
        batch_cat.commit()
        logger("✅ Carga de categorías completada.")
    else:
        logger("🧘 No hay nuevas categorías para cargar.")

    # --- Carga de Servicios ---
    if services_data:
        logger(f"🚀 Procesando 'services'... {len(services_data)} registros.")
        batch_srv = db.batch()
        for srv in services_data:
            srv_id = str(srv.get("id"))
            if not srv_id: continue
            doc_ref = db.collection('services').document(srv_id)
            batch_srv.set(doc_ref, srv)
        batch_srv.commit()
        logger("✅ Carga de servicios completada.")
    else:
        logger("🧘 No hay nuevos servicios para cargar.")