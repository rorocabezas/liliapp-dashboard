# 📊 LiliApp - Dashboard de Business Intelligence

Este repositorio contiene el backend (FastAPI) y el frontend (Streamlit) para el panel de administración y Business Intelligence (BI) de LiliApp. El objetivo es proporcionar métricas y KPIs clave para la toma de decisiones estratégicas del negocio.

## 🚀 Tecnologías Utilizadas

-   **Backend:** [FastAPI](https://fastapi.tiangolo.com/) - Un framework de Python moderno y de alto rendimiento para construir APIs.
-   **Frontend:** [Streamlit](https://streamlit.io/) - Un framework de Python para construir aplicaciones web de datos de forma rápida y sencilla.
-   **Base de Datos:** [Google Firestore](https://firebase.google.com/docs/firestore) - Base de datos NoSQL, flexible y escalable.
-   **Entorno:** Python 3.8+ y `venv` para la gestión de entornos virtuales.
-   **Configuración:** `pydantic-settings` para la gestión segura de variables de entorno.

---

## ⚙️ Guía de Instalación y Puesta en Marcha Local

Sigue estos pasos para configurar y ejecutar el proyecto en tu máquina local.

### 1. Prerrequisitos

-   Tener **Python 3.8** o superior instalado.
-   Tener **Git** instalado.
-   Tener acceso al proyecto **LiliApp en la Consola de Firebase**.

### 2. Clonar el Repositorio

Abre tu terminal y clona este repositorio:

```bash
git clone https://github.com/TU_USUARIO/liliapp-dashboard.git
cd liliapp-dashboard
```

### 3. Configurar el Entorno Virtual

Es crucial usar un entorno virtual para aislar las dependencias del proyecto.

```bash
# Crear el entorno virtual
python -m venv venv

# Activar el entorno virtual
# En macOS / Linux:
source venv/bin/activate

# En Windows (PowerShell):
.\venv\Scripts\Activate.ps1
```

*Deberías ver `(venv)` al principio de la línea de tu terminal.*

### 4. Instalar Dependencias

Con el entorno virtual activado, instala todas las librerías necesarias desde el archivo `requirements.txt`.

```bash
pip install -r requirements.txt
```

### 5. Configurar las Credenciales (Paso CRÍTICO)

Este proyecto necesita credenciales para conectarse de forma segura a Firestore. **Estos archivos son secretos y NUNCA deben subirse a GitHub.**

#### a) Archivo de Clave de Servicio (`serviceAccountKey.json`)

1.  Ve a la **Consola de Firebase** -> tu proyecto "LiliApp".
2.  Haz clic en el ícono de engranaje ⚙️ -> **Configuración del proyecto**.
3.  Ve a la pestaña **Cuentas de servicio**.
4.  Haz clic en **"Generar nueva clave privada"**.
5.  Se descargará un archivo. **Renómbralo a `serviceAccountKey.json`**.
6.  **Mueve este archivo a la raíz de tu proyecto** (`liliapp-dashboard/`). El archivo `.gitignore` ya está configurado para ignorarlo.

#### b) Archivo de Variables de Entorno (`.env`)

Este archivo contiene la configuración que lee la aplicación.

1.  En la raíz del proyecto, crea una copia del archivo de ejemplo:

    ```bash
    # En macOS / Linux:
    cp example.env .env

    # En Windows:
    copy example.env .env
    ```

2.  **Abre el archivo `.env`** con tu editor de código y rellena los valores. Puedes obtenerlos del archivo `serviceAccountKey.json` que acabas de descargar.

    ```dotenv
    # Archivo: .env
    # Rellena estos valores copiándolos de tu serviceAccountKey.json

    FIREBASE_TYPE="service_account"
    FIREBASE_PROJECT_ID="tu-project-id"
    FIREBASE_PRIVATE_KEY_ID="tu-private-key-id"
    FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...tu-clave-privada...\n-----END PRIVATE KEY-----\n"
    FIREBASE_CLIENT_EMAIL="tu-client-email"
    FIREBASE_CLIENT_ID="tu-client-id"
    # ... y el resto de las variables requeridas por config.py
    ```

---

## ▶️ Cómo Ejecutar el Proyecto

Necesitarás **dos terminales** abiertas, ambas con el entorno virtual activado.

#### 1. Iniciar el Backend (FastAPI)

En tu primera terminal, ejecuta:

```bash
uvicorn backend.main:app --reload
```

-   Esto iniciará el servidor de la API en `http://127.0.0.1:8000`.
-   El flag `--reload` hará que el servidor se reinicie automáticamente cada vez que guardes un cambio en el código del backend.
-   Puedes ver la documentación interactiva de la API en **`http://127.0.0.1:8000/docs`**.

#### 2. Iniciar el Frontend (Streamlit)

En tu segunda terminal, ejecuta:

```bash
streamlit run dashboard/app.py
```

-   Esto abrirá una nueva pestaña en tu navegador con el dashboard en **`http://localhost:8501`**.
-   El dashboard se actualizará automáticamente cada vez que guardes un cambio en el código del frontend.

---

## 📂 Estructura del Proyecto

```
liliapp-dashboard/
├── backend/          # Lógica de la API con FastAPI
│   ├── api/          # Endpoints (rutas) de la API
│   ├── core/         # Configuración centralizada (lectura del .env)
│   └── services/     # Lógica de negocio y consultas a Firestore
├── dashboard/        # Código del dashboard con Streamlit
│   ├── pages/        # Cada archivo .py aquí es una página del dashboard
│   └── app.py        # Página principal del dashboard
├── .gitignore        # Archivos y carpetas a ignorar por Git
├── requirements.txt  # Lista de dependencias de Python
└── .env              # Plantilla para el archivo .env
```