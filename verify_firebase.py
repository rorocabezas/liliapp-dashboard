import os
import firebase_admin
from firebase_admin import credentials, auth

print("Verificando configuración de Firebase...")

# 1. Verifica si hay una variable de entorno GOOGLE_APPLICATION_CREDENTIALS
if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
    print(f"Usando credenciales de variable de entorno: {os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')}")
    firebase_admin.initialize_app()
else:
    # 2. Intenta usar las credenciales de tu archivo main.py
    try:
        from backend.core.config import settings
        
        print("Usando credenciales de settings...")
        
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
        
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"Error al cargar credenciales desde settings: {str(e)}")
        
        # 3. Intenta usar un archivo JSON directamente
        try:
            print("Intentando usar archivo serviceAccountKey.json...")
            cred = credentials.Certificate("serviceAccountKey.json")
            firebase_admin.initialize_app(cred)
        except Exception as e:
            print(f"Error al cargar serviceAccountKey.json: {str(e)}")
            exit(1)

# 4. Intenta operaciones básicas
try:
    # Listar los primeros 10 usuarios (sólo para verificar conexión)
    print("Probando conexión a Firebase Auth...")
    users = auth.list_users().iterate_all()
    user_count = 0
    
    for user in users:
        if user_count >= 3:
            break
        print(f"Usuario encontrado: {user.uid} ({user.email})")
        user_count += 1
        
    if user_count == 0:
        print("No se encontraron usuarios en Firebase Auth.")
    else:
        print(f"Conexión exitosa! Se encontraron usuarios.")
        
    # Ahora verifica específicamente admin1@gmail.com
    try:
        user = auth.get_user_by_email("admin1@gmail.com")
        print(f"\n✅ Usuario admin1@gmail.com existe:")
        print(f"  UID: {user.uid}")
        print(f"  Email: {user.email}")
        print(f"  Email verificado: {user.email_verified}")
    except Exception as e:
        print(f"\n❌ Usuario admin1@gmail.com no existe: {str(e)}")
        
except Exception as e:
    print(f"Error al verificar Firebase: {str(e)}")