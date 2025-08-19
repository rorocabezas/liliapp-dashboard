# backend/api/v1/endpoints/auth.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from firebase_admin import auth
from backend.services import firestore_service
import firebase_admin



from backend.services import firestore_service

router = APIRouter()

# --- Modelos de Datos para Pydantic ---
class UserLogin(BaseModel):
    email: str
    password: str

# --- Inicialización de Firebase Admin SDK ---
if not firebase_admin._apps:
    # Esto es un fallback. La inicialización principal debe estar en main.py
    # cred = credentials.Certificate("serviceAccountKey.json")
    # firebase_admin.initialize_app(cred)
    pass


@router.post("/login")
async def login_for_access_token(user_credentials: UserLogin):
    """
    Toma un email y contraseña, los verifica con Firebase Auth
    y devuelve un custom token si son válidos.
    """
    email = user_credentials.email
    password = user_credentials.password

    try:
        # Primero verificamos la contraseña usando la API REST de Firebase
        import requests
        firebase_api_key = settings.FIREBASE_WEB_API_KEY  # Debes agregar esta configuración
        auth_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={firebase_api_key}"
        
        auth_response = requests.post(auth_url, json={
            "email": email,
            "password": password,
            "returnSecureToken": True
        })
        
        if auth_response.status_code != 200:
            raise HTTPException(status_code=401, detail="Credenciales inválidas.")
            
        # Si llegamos aquí, la autenticación fue exitosa
        # Ahora obtenemos el usuario completo y creamos el token personalizado
        user = auth.get_user_by_email(email)
        user_role = firestore_service.get_user_role(user.uid)

        custom_token = auth.create_custom_token(user.uid)

        # Devolvemos el token al frontend
        return {
            "custom_token": custom_token.decode('utf-8'), 
            "uid": user.uid,
            "role": user_role,
            "email": user.email 
        }
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Credenciales inválidas. {str(e) if settings.DEBUG else ''}",
        )