import streamlit as st
from firebase_admin import firestore

# --- HELPER FUNCTIONS ---
def get_db_client():
    return firestore.client()

# ==========================================================
# ===         FUNCIONES DE CARGA GENÉRICAS               ===
# ==========================================================

def load_data_to_firestore(collection_name: str, data: list, id_field: str, logger=st.info):
    """
    Carga una lista de diccionarios a una colección de nivel superior en Firestore.
    Usa el valor de 'id_field' como el ID del documento.
    """
    if not data:
        logger(f"🧘 No hay nuevos datos para cargar en '{collection_name}'.")
        return

    db = get_db_client()
    batch = db.batch()
    
    logger(f"🚀 Procesando '{collection_name}'... {len(data)} registros.")
    
    created_count = 0
    updated_count = 0
    unchanged_count = 0

    for item in data:
        doc_id = str(item.get(id_field))
        if not doc_id:
            logger(f"⚠️ Saltando registro en '{collection_name}' por falta de ID.")
            continue
        
        doc_ref = db.collection(collection_name).document(doc_id)
        # Aquí podrías añadir lógica para comparar con datos existentes si fuera necesario
        # Por ahora, asumimos que son todos nuevos o se sobreescriben.
        batch.set(doc_ref, item)
        created_count += 1

    batch.commit()
    
    summary = (
        f"Resumen de Carga para '{collection_name}':\n"
        f"✨ Creados: {created_count} | "
        f"🔄 Actualizados: {updated_count} | "
        f"🧘 Sin cambios: {unchanged_count}"
    )
    logger(summary)

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