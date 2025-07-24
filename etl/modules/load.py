# etl/modules/load.py

from firebase_admin import firestore
from google.cloud.firestore_v1.field_path import FieldPath 
from typing import List, Dict, Any
import streamlit as st

def load_data_to_firestore(collection_name: str, data: List[Dict[str, Any]], id_key: str = "id", logger=st.info):
    """
    Función genérica para cargar datos a cualquier colección de Firestore de forma inteligente.
    - Si un documento no existe, lo crea.
    - Si ya existe, lo actualiza solo si hay cambios, sin borrar campos existentes (merge=True).
    
    Args:
        collection_name (str): El nombre de la colección destino.
        data (list): La lista de diccionarios a cargar.
        id_key (str): La clave en cada diccionario que se usará como ID del documento.
        logger: El logger de Streamlit para reportar progreso.
    """
    logger(f"📤 Iniciando carga inteligente a la colección '{collection_name}'...")
    
    if not data:
        logger(f"  ⚠️ No hay datos para cargar en '{collection_name}'. Saltando proceso.")
        return

    db = firestore.client()
    collection_ref = db.collection(collection_name)
    
    ids_to_process = [item.get(id_key) for item in data if item.get(id_key)]
    
    logger(f"  🔍 Verificando {len(ids_to_process)} documentos existentes en '{collection_name}'...")
    existing_docs = {}
    if ids_to_process:
        for i in range(0, len(ids_to_process), 30):
            batch_ids = ids_to_process[i:i+30]
            query = collection_ref.where(FieldPath.document_id(), 'in', batch_ids)
            for doc in query.stream():
                existing_docs[doc.id] = doc.to_dict()
    logger(f"  ✅ Se encontraron {len(existing_docs)} documentos preexistentes.")

    batch = db.batch()
    commit_count = 0
    items_to_create = 0
    items_to_update = 0
    items_unchanged = 0

    progress_bar = st.progress(0, text=f"Procesando lotes para '{collection_name}'...")
    total_items = len(data)

    for i, item_data in enumerate(data):
        doc_id = item_data.pop(id_key, None)
        if not doc_id:
            continue # Si no hay ID, no podemos procesar este item

        doc_ref = collection_ref.document(doc_id)
        
        if doc_id not in existing_docs:
            batch.set(doc_ref, item_data)
            items_to_create += 1
            commit_count += 1
        else:
            existing_data = existing_docs[doc_id]
            has_changes = False
            for key in item_data.keys():
                if str(item_data.get(key)) != str(existing_data.get(key)):
                    has_changes = True
                    break
            
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

    # --- Reporte final en Streamlit ---
    st.success(f"Resumen de Carga para '{collection_name}':")
    
    col1, col2, col3 = st.columns(3)
    col1.metric(f"✨ Creados", items_to_create)
    col2.metric(f"🔄 Actualizados", items_to_update)
    col3.metric(f"🧘 Sin cambios", items_unchanged)