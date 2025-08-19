import firebase_admin
from firebase_admin import credentials, auth
import os

def init_firebase():
    try:
        # Si Firebase ya está inicializado, no hacemos nada
        if len(firebase_admin._apps) > 0:
            return True

        # Intentamos usar las credenciales del archivo .env
        from backend.core.config import settings
        
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
        print("✅ Firebase inicializado correctamente")
        return True
    except Exception as e:
        print(f"❌ Error inicializando Firebase: {str(e)}")
        return False

def check_user(email):
    try:
        user = auth.get_user_by_email(email)
        print(f"\n✅ Usuario encontrado:")
        print(f"   UID: {user.uid}")
        print(f"   Email: {user.email}")
        print(f"   Email verificado: {user.email_verified}")
        return True
    except auth.UserNotFoundError:
        print(f"\n❌ Usuario {email} no encontrado en Firebase")
        return False
    except Exception as e:
        print(f"\n❌ Error al buscar usuario: {str(e)}")
        return False

def create_test_user(email, password):
    try:
        user = auth.create_user(
            email=email,
            password=password,
            email_verified=True
        )
        print(f"\n✅ Usuario creado exitosamente:")
        print(f"   UID: {user.uid}")
        print(f"   Email: {user.email}")
        return True
    except auth.EmailAlreadyExistsError:
        print(f"\n⚠️ El usuario {email} ya existe")
        return False
    except Exception as e:
        print(f"\n❌ Error al crear usuario: {str(e)}")
        return False

if __name__ == "__main__":
    if init_firebase():
        email = "admin1@gmail.com"
        password = "123456"
        
        print("\nVerificando usuario existente...")
        if not check_user(email):
            print("\nIntentando crear usuario de prueba...")
            create_test_user(email, password)
        else:
            print("\nEl usuario ya existe, no es necesario crearlo")