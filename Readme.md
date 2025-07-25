# 📊 LiliApp - Dashboard de Business Intelligence & Plataforma ETL

Este repositorio contiene una solución integral de datos para LiliApp, compuesta por:

1.  **Dashboard de BI (Frontend):** Una aplicación interactiva construida con **Streamlit** para visualizar KPIs de negocio.
2.  **API de Datos (Backend):** Una API de alto rendimiento con **FastAPI** que sirve los datos procesados desde Firestore.
3.  **Plataforma ETL:** Un conjunto de herramientas modulares en Python para extraer, transformar y cargar (ETL) datos desde fuentes externas (como Jumpseller) a nuestra base de datos **Firestore**, asegurando la calidad y consistencia de los datos.

## 🚀 Tecnologías Utilizadas

-   **Backend:** [FastAPI](https://fastapi.tiangolo.com/) - Para una API rápida, moderna y con documentación automática.
-   **Frontend:** [Streamlit](https://streamlit.io/) - Para construir el dashboard interactivo de forma rápida.
-   **Base de Datos:** [Google Firestore](https://firebase.google.com/docs/firestore) - Base de datos NoSQL flexible y escalable.
-   **Procesamiento de Datos (ETL):** [Pandas](https://pandas.pydata.org/) - Para la manipulación y transformación de datos.
-   **Entorno:** Python 3.8+ y `venv` para la gestión de dependencias.

---

## ⚙️ Guía de Puesta en Marcha Local

Sigue estos pasos para configurar y ejecutar el proyecto completo en tu máquina.

### 1. Prerrequisitos

-   Tener **Python 3.8** o superior instalado.
-   Tener **Git** instalado.
-   Tener acceso al proyecto **LiliApp en la Consola de Firebase**.
-   Tener la **CLI de Google Cloud (`gcloud`)** instalada y configurada (ver paso 4).

### 2. Clonar el Repositorio

```bash
git clone https://github.com/rorocabezas/liliapp-dashboard.git
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

### 4. Configurar las Credenciales de Google Cloud (Método Recomendado)
Este proyecto utiliza Application Default Credentials (ADC) para una autenticación segura sin necesidad de archivos de clave.
1. Instala la CLI de Google Cloud si aún no lo has hecho: Instrucciones Oficiales.
2. Inicia sesión en tu cuenta:

```bash
gcloud auth application-default login
```
Se abrirá un navegador para que inicies sesión con la cuenta de Google asociada a tu proyecto de Firebase.

3. Configura tu proyecto por defecto:
```bash
gcloud config set project TU_ID_DE_PROYECTO
```
(Reemplaza TU_ID_DE_PROYECTO con el ID de tu proyecto en Firebase, ej: liliapp-fe07b).

5. Instalar Dependencias
Con el entorno virtual activado, instala todas las librerías necesarias.
```bash
pip install -r requirements.txt
```
▶️ Cómo Ejecutar el Proyecto
Necesitarás dos terminales abiertas, ambas con el entorno virtual activado.
1. Iniciar el Backend (FastAPI)
En tu primera terminal, ejecuta:
```bash
uvicorn backend.main:app --reload
```
* El servidor de la API se iniciará en http://127.0.0.1:8000.
* Puedes probar y explorar los endpoints en la documentación interactiva: http://127.0.0.1:8000/docs.

2. Iniciar el Frontend (Streamlit)
En tu segunda terminal, ejecuta:
```bash
streamlit run dashboard/app.py
```
* El dashboard se abrirá en tu navegador en http://localhost:8501.

## 🛠️ Uso de la Plataforma ETL
El proyecto incluye una interfaz gráfica para ejecutar los procesos de migración de datos.
### 1. Preparar los Datos de Origen
 * Coloca los archivos JSON exportados desde Jumpseller (u otra fuente) en la carpeta etl/data/.
    * source_orders.json: Para el ETL de órdenes.
    * source_products.json: Para el ETL de productos.
### 2. Ejecutar el ETL desde el Dashboard
  1. Inicia sesión en el dashboard de Streamlit.
  2. Navega a la página "Panel ETL" o "Cargas" en el menú lateral.
  3. Selecciona el proceso que deseas ejecutar (ej: "Órdenes" o "Productos y Categorías").
  4. Haz clic en "Iniciar Proceso de Carga".
  5. Podrás ver el progreso y el resumen de la operación en tiempo real directamente en la interfaz.
### 3. Herramientas de Validación

El dashboard también incluye páginas de Mapeo de Datos que te permiten seleccionar una orden o producto individual del archivo de origen y ver una previsualización de cómo será transformado antes de ejecutar la carga masiva.

# 📂 Estructura del Proyecto

```
liliapp-dashboard/
├── backend/          # Lógica de la API con FastAPI (servidor)
│   ├── api/          # Endpoints de la API
│   └── services/     # Lógica de negocio y consultas a Firestore
├── dashboard/        # Código del dashboard con Streamlit (cliente)
│   ├── assets/       # Imágenes y otros archivos estáticos
│   ├── pages/        # Cada archivo .py aquí es una página del dashboard
│   ├── app.py        # Página de bienvenida y punto de entrada
│   └── menu.py       # Lógica del menú de navegación dinámico
├── etl/              # Plataforma de Extracción, Transformación y Carga
│   ├── data/         # Archivos de datos de origen (JSON, CSV)
│   └── modules/      # Lógica modular para los procesos ETL
├── .gitignore        # Archivos a ignorar por Git (¡muy importante!)
└── requirements.txt  # Lista de dependencias de Python
```