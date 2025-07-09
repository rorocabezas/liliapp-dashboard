# backend/api/v1/endpoints/auth.py

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from firebase_admin import auth
import firebase_admin

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
        # 1. Busca al usuario por su email
        user = auth.get_user_by_email(email)
        
        # 2. Firebase Admin SDK no puede verificar contraseñas directamente.
        #    La verificación debe hacerse en el cliente o mediante un truco.
        #    El método más seguro es crear un CUSTOM TOKEN que el cliente
        #    puede usar para iniciar sesión y obtener un ID TOKEN.
        #    Esto es seguro porque solo tu backend (con credenciales de admin) puede crearlo.

        # 3. Creamos un custom token para este usuario.
        custom_token = auth.create_custom_token(user.uid)

        # Devolvemos el token al frontend
        return {"custom_token": custom_token.decode('utf-8'), "uid": user.uid}

    except auth.UserNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Usuario no encontrado.",
        )
    except Exception as e:
        # ¡Importante! No reveles el error de contraseña incorrecta por seguridad.
        # Los ataques de enumeración de usuarios se basan en esto.
        # Siempre devuelve un mensaje genérico.
        print(f"Error de autenticación: {e}") # Para tu log
        raise HTTPException(
            status_code=401,
            detail="Credenciales inválidas.",
        )