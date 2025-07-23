# etl/modules/extract.py

import json
from typing import List, Dict, Any

def load_orders_from_json(filepath: str) -> List[Dict[str, Any]]:
    """
    Carga las órdenes desde un archivo JSON de Jumpseller.
    El formato esperado es una lista de objetos {"order": {...}}.
    
    Returns:
        Una lista de diccionarios, donde cada diccionario es una orden.
    """
    print(f"📄 Extrayendo datos desde: {filepath}")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        # El JSON de Jumpseller es una lista de {"order": ...}, extraemos el contenido.
        orders = [item['order'] for item in raw_data if 'order' in item]
        
        print(f"✅ Extracción completada. Se encontraron {len(orders)} órdenes.")
        return orders
    except FileNotFoundError:
        print(f"❌ ERROR: El archivo no fue encontrado en '{filepath}'")
        return []
    except Exception as e:
        print(f"❌ ERROR durante la extracción: {e}")
        return []