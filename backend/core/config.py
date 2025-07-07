# Archivo: backend/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Lee todas las variables de Firebase del archivo .env
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
    
    # Esto le dice a Pydantic que busque un archivo .env
    model_config = SettingsConfigDict(env_file=".env")

# Creamos una única instancia que será usada en toda la aplicación
settings = Settings()