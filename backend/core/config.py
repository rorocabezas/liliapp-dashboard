# Archivo: backend/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Gestiona la configuración de la aplicación cargando variables
    desde un archivo .env.
    """
    # Configuración de Jumpseller
    JUMPSELLER_LOGIN: str
    JUMPSELLER_AUTHTOKEN: str
    API_BASE_URL: str 
    # Configuración de Firebase
    FIREBASE_TYPE: str
    FIREBASE_PROJECT_ID: str
    FIREBASE_PRIVATE_KEY_ID: str
    FIREBASE_PRIVATE_KEY: str
    FIREBASE_CLIENT_EMAIL: str
    FIREBASE_CLIENT_ID: str
    FIREBASE_AUTH_URI: str
    FIREBASE_TOKEN_URI: str
    FIREBASE_AUTH_PROVIDER_X509_CERT_URL: str
    FIREBASE_CLIENT_X509_CERT_URL: str


    FIREBASE_API_KEY: str
    PORT: int
    
    # Configuración para que Pydantic lea desde un archivo .env
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8')

# Creamos una única instancia que será usada en toda la aplicación
settings = Settings()