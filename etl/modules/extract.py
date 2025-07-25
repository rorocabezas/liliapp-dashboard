# etl/modules/extract.py

import json
from typing import List, Dict, Any
import streamlit as st

def load_data_from_json(filepath: str, data_key: str, logger=st.info) -> List[Dict[str, Any]]:
    """
    Función genérica para cargar datos desde un archivo JSON de Jumpseller.
    
    Args:
        filepath (str): La ruta al archivo JSON.
        data_key (str): La clave principal que envuelve cada objeto (ej: "order", "product").
        logger: El logger de Streamlit para reportar progreso.
        
    Returns:
        Una lista de diccionarios con los datos extraídos.
    """
    logger(f"📄 Extrayendo datos desde: {filepath}...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)        
 
        if not isinstance(raw_data, list):
            st.error(f"❌ ERROR: El archivo JSON de origen no es una lista como se esperaba.")
            return []

        items = [item[data_key] for item in raw_data if data_key in item]
        
        logger(f"✅ Extracción completada. Se encontraron {len(items)} '{data_key}'(s).")
        return items
    except Exception as e:
        st.error(f"❌ ERROR durante la extracción de '{data_key}': {e}")
        return []