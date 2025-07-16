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
        user = auth.get_user_by_email(user_credentials.email)
        user_role = firestore_service.get_user_role(user.uid)

        custom_token = auth.create_custom_token(user.uid)

        # Devolvemos el token al frontend
        return {
            "custom_token": custom_token.decode('utf-8'), 
            "uid": user.uid,
            "role": user_role,
            "email": user.email # También devolvemos el email para mostrarlo
        }
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail="Credenciales inválidas.",
        )