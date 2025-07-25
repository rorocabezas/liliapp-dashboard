# etl/modules/load.py

from firebase_admin import firestore
from google.cloud.firestore_v1.field_path import FieldPath 
from typing import List, Dict, Any
import streamlit as st

def load_data_to_firestore(collection_name: str, data: List[Dict[str, Any]], id_key: str = "id", logger=st.info):
    """
    Función genérica para cargar datos a una COLECCIÓN PRINCIPAL de forma inteligente.
    """
    logger(f"📤 Iniciando carga a la colección '{collection_name}'...")
    
    if not data:
        logger(f"  ⚠️ No hay datos para cargar en '{collection_name}'. Saltando proceso.")
        return

    db = firestore.client()
    collection_ref = db.collection(collection_name)
    
    ids_to_process = [item.get(id_key) for item in data if item.get(id_key)]
    
    logger(f"  🔍 Verificando {len(ids_to_process)} documentos existentes...")
    existing_docs = {}
    if ids_to_process:
        for i in range(0, len(ids_to_process), 30):
            batch_ids = ids_to_process[i:i+30]
            query = collection_ref.where(FieldPath.document_id(), 'in', batch_ids)
            for doc in query.stream():
                existing_docs[doc.id] = doc.to_dict()
    logger(f"  ✅ Se encontraron {len(existing_docs)} documentos preexistentes.")

    batch = db.batch()
    commit_count, items_to_create, items_to_update, items_unchanged = 0, 0, 0, 0

    progress_bar = st.progress(0, text=f"Procesando lotes para '{collection_name}'...")
    total_items = len(data)

    for i, item_data in enumerate(data):
        doc_id = item_data.pop(id_key, None)
        if not doc_id: continue

        doc_ref = collection_ref.document(doc_id)
        
        if doc_id not in existing_docs:
            batch.set(doc_ref, item_data)
            items_to_create += 1
            commit_count += 1
        else:
            existing_data = existing_docs[doc_id]
            has_changes = any(str(item_data.get(key)) != str(existing_data.get(key)) for key in item_data.keys())
            
            if has_changes:
                batch.set(doc_ref, item_data, merge=True)
                items_to_update += 1
                commit_count += 1
            else:
                items_unchanged += 1

        if commit_count >= 400 or (i + 1) == total_items:
            if commit_count > 0:
                batch.commit()
                logger(f"  ...Lote de {commit_count} operaciones para '{collection_name}' procesado.")
                batch = db.batch()
                commit_count = 0
        
        progress_bar.progress((i + 1) / total_items, text=f"Procesando '{collection_name}'... {i+1}/{total_items}")

    st.success(f"Resumen de Carga para '{collection_name}':")
    col1, col2, col3 = st.columns(3)
    col1.metric(f"✨ Creados", items_to_create)
    col2.metric(f"🔄 Actualizados", items_to_update)
    col3.metric(f"🧘 Sin cambios", items_unchanged)

def load_variants_to_firestore(variants: List[Dict[str, Any]], logger=st.info):
    """
    Función especializada para cargar variantes a sus respectivas SUBCOLECCIONES en 'services'.
    """
    logger("📤 Iniciando carga de Variantes a subcolecciones...")
    
    if not variants:
        logger("  ⚠️ No hay variantes para cargar. Saltando proceso.")
        return

    db = firestore.client()
    batch = db.batch()
    commit_count = 0

    progress_bar = st.progress(0, text="Procesando lotes para 'variantes'...")
    total_items = len(variants)

    for i, variant_data in enumerate(variants):
        service_id = variant_data.pop("serviceId", None)
        variant_id = variant_data.pop("id", None)
        
        if not service_id or not variant_id: continue

        doc_ref = db.collection('services').document(service_id).collection('variants').document(variant_id)
        
        batch.set(doc_ref, variant_data, merge=True)
        commit_count += 1

        if commit_count >= 400 or (i + 1) == total_items:
            if commit_count > 0:
                batch.commit()
                logger(f"  ...Lote de {commit_count} variantes procesado.")
                batch = db.batch()
                commit_count = 0
        
        progress_bar.progress((i + 1) / total_items, text=f"Procesando 'variantes'... {i+1}/{total_items}")
    
    st.success(f"Resumen de Carga para 'variantes': {total_items} documentos procesados.")