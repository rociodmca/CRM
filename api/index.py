import os
import sys

# Asegurar que el directorio raíz del proyecto esté en sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import app

# Exportar app para el runtime Serverless de Vercel
# Vercel detecta la variable 'app' compatible con WSGI
