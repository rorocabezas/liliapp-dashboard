# etl/run_etl.py

import firebase_admin
from firebase_admin import credentials
from modules import extract, transform, load

def main():
    """
    Orquesta el proceso completo de ETL: Extract, Transform, Load.
    """
    print("🚀 Iniciando Proceso ETL para Órdenes de LiliApp 🚀")

    # --- 1. Inicialización de Firebase ---
    # Asegúrate de que tu serviceAccountKey.json está en la raíz del proyecto
    try:
        # Al inicializar, le pasamos el ID del proyecto explícitamente.
        # El SDK seguirá usando tus credenciales locales (ADC), pero ahora sabrá a qué proyecto apuntar.
        firebase_admin.initialize_app(options={
            'projectId': 'liliapp-fe07b',
        })
        print("🔥 Conexión con Firebase establecida usando Application Default Credentials.")
    except Exception as e:
        print(f"❌ ERROR: No se pudo inicializar Firebase. Detalle: {e}")
        print("Asegúrate de haber corrido 'gcloud auth application-default login' en tu terminal.")
        return

    # --- 2. Extract ---
    source_file = "data/source_orders.json"
    raw_orders = extract.load_orders_from_json(source_file)
    
    if not raw_orders:
        print(" Proceso detenido. No hay datos para procesar.")
        return

    # --- 3. Transform ---
    transformed_orders = transform.transform_orders(raw_orders)
    
    if not transformed_orders:
        print(" Proceso detenido. No se generaron datos transformados.")
        return

    # --- 4. Load ---
    load.load_orders_to_firestore(transformed_orders)
    
    print("\n✨ Proceso ETL finalizado con éxito. ✨")

if __name__ == "__main__":
    main()