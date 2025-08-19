import os
import sys
# Añadir directorio raíz al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import firebase_admin
from firebase_admin import credentials, auth
from backend.core.config import settings

# Construir el diccionario de credenciales (igual que en main.py)
cred_dict = {
    "type": settings.FIREBASE_TYPE,
    "project_id": settings.FIREBASE_PROJECT_ID,
    "private_key_id": settings.FIREBASE_PRIVATE_KEY_ID,
    "private_key": settings.FIREBASE_PRIVATE_KEY.replace('\\n', '\n'),
    "client_email": settings.FIREBASE_CLIENT_EMAIL,
    "client_id": settings.FIREBASE_CLIENT_ID,
    "auth_uri": settings.FIREBASE_AUTH_URI,
    "token_uri": settings.FIREBASE_TOKEN_URI,
    "auth_provider_x509_cert_url": settings.FIREBASE_AUTH_PROVIDER_X509_CERT_URL,
    "client_x509_cert_url": settings.FIREBASE_CLIENT_X509_CERT_URL
}

# Inicializa Firebase (solo si no está inicializado)
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)

# Función para verificar si un usuario existe
def check_user(email):
    try:
        user = auth.get_user_by_email(email)
        print(f"✅ Usuario existe: {user.uid}")
        print(f"   Email: {user.email}")
        print(f"   Verificado: {user.email_verified}")
        print(f"   Creado: {user.user_metadata.creation_timestamp}")
        return True
    except Exception as e:
        print(f"❌ Usuario no existe o error: {str(e)}")
        return False

# Verificar el usuario específico
check_user("admin1@gmail.com")