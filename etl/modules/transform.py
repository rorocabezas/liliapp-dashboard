# etl/modules/transform.py

from datetime import datetime
from typing import List, Dict, Any

def _parse_utc_string(date_string: str) -> datetime:
    """Convierte un string de fecha UTC de Jumpseller a un objeto datetime."""
    if not date_string:
        return None
    # Jumpseller usa "YYYY-MM-DD HH:MM:SS UTC"
    return datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S %Z")

def _create_status_history(source_order: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Construye el historial de estados a partir de los timestamps disponibles.
    """
    history = []
    
    # Estado de creación
    created_at = _parse_utc_string(source_order.get("created_at"))
    if created_at:
        history.append({
            "status": "pending_payment", # Asumimos que este es el primer estado
            "timestamp": created_at,
            "updatedBy": "customer"
        })

    # El webhook es para 'status/paid', por lo que 'completed_at' es la fecha de pago.
    paid_at = _parse_utc_string(source_order.get("completed_at"))
    if paid_at:
        history.append({
            "status": "paid",
            "timestamp": paid_at,
            "updatedBy": "system"
        })
    
    # Nota: Otros estados como 'scheduled', 'in_progress', 'completed' no están en
    # los datos de origen, por lo que no se pueden añadir en esta migración.
    
    return history

def _extract_contact_on_site(source_order: Dict[str, Any]) -> Dict[str, str]:
    """Extrae el nombre de contacto del sitio desde los campos adicionales."""
    fields = source_order.get("additional_fields", [])
    contact_name = "No especificado"
    
    for field in fields:
        if field.get("label") == "Nombre de quien recibirá al profesional":
            contact_name = field.get("value")
            break
            
    # Usamos el teléfono principal del cliente como fallback
    customer_phone = source_order.get("customer", {}).get("phone", "N/A")
    
    return {"name": contact_name, "phone": f"+56{customer_phone}"}


def transform_orders(source_orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Transforma una lista de órdenes de Jumpseller a la estructura de Firestore.
    """
    print("\n🔄 Iniciando transformación de datos...")
    transformed_orders = []
    for order in source_orders:
        
        # Mapeo de campos principales
        new_order = {
            "id": str(order.get("id")),
            "customerId": str(order.get("customer", {}).get("id")),
            "professionalId": None, # No disponible en el origen
            "total": order.get("total", 0),
            "status": order.get("status_enum", "unknown"), # ej: 'paid'
            
            # Timestamps
            "createdAt": _parse_utc_string(order.get("created_at")),
            "updatedAt": datetime.now(), # Usamos la fecha actual de la migración
            
            # Estructuras anidadas
            "items": [
                {
                    "serviceId": str(p.get("id")),
                    "serviceName": p.get("name"),
                    "quantity": p.get("qty"),
                    "price": p.get("price")
                } for p in order.get("products", [])
            ],
            
            "paymentDetails": {
                "type": order.get("payment_method_type"),
                "transactionId": order.get("payment_notification_id"),
                "methodId": None # No disponible en el origen
            },
            
            "serviceAddress": {
                "addressId": f"addr_{order.get('id')}", # Creamos un ID simple
                "commune": order.get("shipping_address", {}).get("municipality"),
                "region": order.get("shipping_address", {}).get("region"),
                "instructions": order.get("shipping_address", {}).get("complement")
            },

            "contactOnSite": _extract_contact_on_site(order),
            
            "statusHistory": _create_status_history(order),
            
            "rating": None # No disponible en el origen
        }
        transformed_orders.append(new_order)
    
    print(f"✅ Transformación completada para {len(transformed_orders)} órdenes.")
    return transformed_orders