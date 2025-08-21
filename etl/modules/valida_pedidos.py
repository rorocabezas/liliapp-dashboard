# Script para validar la estructura y datos de la colección 'pedidos' en Firestore
import firebase_admin
from firebase_admin import credentials, firestore

# Inicializa Firebase
cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

COLLECTIONS = ['pedidos', 'customers', 'services', 'categories', 'carts']
SAMPLE_SIZE = 5

def show_collection_structure(collection_name):
    print(f"\n--- {collection_name.upper()} ---")
    docs = db.collection(collection_name).limit(SAMPLE_SIZE).stream()
    count = 0
    for doc in docs:
        count += 1
        data = doc.to_dict()
        print(f"Document ID: {doc.id}")
        print(f"Fields: {list(data.keys())}")
        print(f"Sample: {data}\n")
    if count == 0:
        print(f"La colección '{collection_name}' está vacía.")

def main():
    for col in COLLECTIONS:
        show_collection_structure(col)

if __name__ == "__main__":
    main()
