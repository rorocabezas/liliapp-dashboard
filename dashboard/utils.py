# dashboard/utils.py
import sys
from pathlib import Path

def add_project_root_to_path():
    """
    Añade la carpeta raíz del proyecto al sys.path para permitir
    importaciones absolutas desde cualquier script.
    
    Ejemplo: from dashboard.auth import check_login
    """
    # Obtenemos la ruta al directorio del script actual (utils.py)
    script_dir = Path(__file__).parent
    # Subimos un nivel para llegar a la raíz del proyecto (liliapp-dashboard)
    project_root = script_dir.parent
    
    # Añadimos la ruta raíz al path de Python si no está ya
    if str(project_root) not in sys.path:
        sys.path.append(str(project_root))