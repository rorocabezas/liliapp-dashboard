# Archivo: backend/main.py
import uvicorn
from fastapi import FastAPI
import firebase_admin
from firebase_admin import credentials
from fastapi.middleware.cors import CORSMiddleware


# 1. Importa la instancia de configuración
from backend.core.config import settings
from backend.api.v1.endpoints import kpis, auth, crud, jumpseller, audit


# 2. Construye el diccionario de credenciales desde las variables de entorno
# Nota: La clave privada necesita que los '\n' sean reemplazados por saltos de línea reales.
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

# 3. Inicializa Firebase con el diccionario de credenciales
cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred)

app = FastAPI(title="LiliApp BI API")

# Configura CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],  # URL de Streamlit
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Incluir las rutas de los KPIs
app.include_router(kpis.router, prefix="/api/v1/kpis", tags=["KPIs"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(crud.router, prefix="/api/v1/crud", tags=["CRUD Operations"])
app.include_router(jumpseller.router, prefix="/api/v1/jumpseller", tags=["Jumpseller API"]) 
app.include_router(audit.router, prefix="/api/v1/audit", tags=["Audit"]) 

@app.get("/")
def read_root():
    return {"status": "LiliApp BI API is running"}

