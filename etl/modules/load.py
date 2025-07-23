# etl/modules/load.py

from firebase_admin import firestore
from typing import List, Dict, Any

def load_orders_to_firestore(orders: List[Dict[str, Any]]):
    """
    Carga las órdenes transformadas a la colección 'orders' en Firestore
    usando escrituras por lotes.
    """
    print("\n📤 Iniciando carga a Firestore...")
    db = firestore.client()
    batch = db.batch()
    commit_count = 0
    total_loaded = 0

    for order in orders:
        doc_id = order.pop("id") # Extraemos el ID para usarlo como ID del documento
        doc_ref = db.collection('orders').document(doc_id)
        batch.set(doc_ref, order)
        commit_count += 1
        
        # Hacemos commit cada 400 documentos para no exceder los límites de Firestore
        if commit_count >= 400:
            batch.commit()
            total_loaded += commit_count
            print(f"  ...Lote de {commit_count} órdenes cargado.")
            batch = db.batch() # Iniciamos un nuevo lote
            commit_count = 0
    
    # Hacemos commit del último lote si queda algo
    if commit_count > 0:
        batch.commit()
        total_loaded += commit_count
        print(f"  ...Lote final de {commit_count} órdenes cargado.")

    print(f"✅ Carga finalizada. Se subieron un total de {total_loaded} órdenes a Firestore.")