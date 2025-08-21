
import streamlit as st
from etl.modules.auditoria_pedidos import get_pedidos_firestore, get_jumpseller_order, comparar_pedidos

st.set_page_config(page_title="Auditoría de Pedidos - Mapeo Inverso", layout="wide", initial_sidebar_state="expanded")
st.title("🧾 Auditoría Visual de Pedidos: Firestore → Jumpseller")
st.markdown("Esta herramienta te permite comparar visualmente cada pedido en Firestore con su versión original en Jumpseller, para decidir cuál estructura es más completa y confiable.")


pedidos = get_pedidos_firestore()
if not pedidos:
    st.warning("No se encontraron pedidos en Firestore.")
    st.stop()

# --- Selector de Pedido usando el ID del documento Firestore ---
pedido_ids = [p['__doc_id__'] if '__doc_id__' in p else None for p in pedidos]
if not any(pedido_ids):
    # Si no se agregó el id, lo obtenemos manualmente
    from firebase_admin import firestore as fs
    db = fs.client()
    pedidos_ref = db.collection('pedidos')
    docs = list(pedidos_ref.stream())
    pedidos = [{**doc.to_dict(), '__doc_id__': doc.id} for doc in docs]
    pedido_ids = [doc.id for doc in docs]

selected_pedido_id = st.selectbox(
    "Selecciona un Pedido de Firestore:",
    options=[""] + pedido_ids,
    format_func=lambda pid: "Selecciona un pedido..." if not pid else f"Pedido ID: {pid}",
    key="pedido_auditoria_selector"
)

if selected_pedido_id:
    pedido_firestore = next((p for p in pedidos if p.get('__doc_id__') == selected_pedido_id), None)
    order_id = str(pedido_firestore.get('orderId')) if pedido_firestore and pedido_firestore.get('orderId') else None
    pedido_jumpseller = get_jumpseller_order(order_id) if order_id else None
    diferencias = comparar_pedidos(pedido_firestore, pedido_jumpseller)

    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1], gap="large")

    with col1:
        st.subheader("⬅️ Origen: Pedido en Firestore")
        st.json(pedido_firestore, expanded=False)

    with col2:
        st.subheader("🔎 Diferencias campo a campo")
        if diferencias:
            for campo, vals in diferencias.items():
                st.markdown(f"**{campo}**")
                st.write(f"Firestore: {vals['firestore']}")
                st.write(f"Jumpseller: {vals['jumpseller']}")
                st.markdown("---")
        else:
            st.success("Sin diferencias relevantes.")

    with col3:
        st.subheader("➡️ Destino: Pedido en Jumpseller")
        if pedido_jumpseller:
            st.json(pedido_jumpseller, expanded=False)
        else:
            st.warning("No se encontró el pedido en Jumpseller.")

    st.markdown("---")
    st.subheader("💬 Nota del Arquitecto: Recomendaciones")
    st.info(
        "Revisa visualmente los campos y decide si la estructura de Firestore es más completa. Si es necesario, puedes mejorar la colección final para los desarrolladores consolidando lo mejor de ambos modelos.",
        icon="✅"
    )
