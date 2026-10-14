import os
import sys
import json
import secrets
import string
import time
import urllib.request
import urllib.error

# Cargar .env si existe
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env_path):
    with open(_env_path, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip().strip("'\""))

def request_supabase(endpoint, token, method="GET", data=None):
    url = f"https://api.supabase.com/v1/{endpoint.lstrip('/')}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "CalzaCRM-Setup/1.0"
    }
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            return (json.loads(content) if content else {}), resp.status
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode("utf-8")
        try:
            parsed = json.loads(error_msg)
        except Exception:
            parsed = {"error": error_msg}
        return parsed, e.code
    except Exception as e:
        return {"error": str(e)}, 500

def list_projects(token):
    data, status = request_supabase("projects", token)
    if status == 200:
        return data
    else:
        print(f"[!] Error al listar proyectos (código {status}): {data}")
        return []

def set_database_password(token, project_ref, password):
    endpoint = f"projects/{project_ref}/database/password"
    data, status = request_supabase(endpoint, token, method="PATCH", data={"password": password})
    return status in (200, 201, 204), data

def execute_sql(token, project_ref, query):
    endpoint = f"projects/{project_ref}/database/query"
    data, status = request_supabase(endpoint, token, method="POST", data={"query": query})
    return data, status

def generate_secure_password(length=24):
    chars = string.ascii_letters + string.digits
    while True:
        pwd = "".join(secrets.choice(chars) for _ in range(length))
        if (any(c.islower() for c in pwd)
            and any(c.isupper() for c in pwd)
            and any(c.isdigit() for c in pwd)):
            return pwd

def setup(token):
    print(f"\n=======================================================")
    print(f"       CONECTOR AUTOMÁTICO DE SUPABASE (CalzaCRM)")
    print(f"=======================================================")
    print(f"[*] Validando token: {token[:8]}...")

    projects = list_projects(token)
    if not projects:
        print("[!] No se pudo acceder a tus proyectos. Revisa que el token sea correcto y tenga permisos.")
        return False

    print(f"[OK] Token valido. Proyectos encontrados:")
    for i, p in enumerate(projects):
        print(f"    [{i+1}] {p.get('name')} (ID: {p.get('id')}, Region: {p.get('region')})")

    project = projects[0]
    ref = project.get("id")
    region = project.get("region", "eu-central-1")
    name = project.get("name")
    print(f"\n[*] Configurando proyecto: '{name}' (ID: {ref})")

    # Generar contraseña segura para la base de datos
    new_password = generate_secure_password(22)
    print(f"[*] Estableciendo contrasena segura para PostgreSQL en Supabase...")
    ok, err = set_database_password(token, ref, new_password)
    if not ok:
        print(f"[!] Error al actualizar contrasena: {err}")
        return False

    print(f"[OK] Contrasena de base de datos actualizada exitosamente.")

    # Cadena de conexión Connection Pooler (puerto 6543)
    pooler_host = f"aws-0-{region}.pooler.supabase.com"
    database_url = f"postgresql://postgres.{ref}:{new_password}@{pooler_host}:6543/postgres?sslmode=require"

    # Escribir en .env local
    env_content = f"""# Configuración automática generada por setup_supabase.py
SUPABASE_ACCESS_TOKEN={token}
SUPABASE_PROJECT_REF={ref}
DATABASE_URL={database_url}
"""
    with open(".env", "w", encoding="utf-8") as f:
        f.write(env_content)
    print(f"[OK] Archivo .env local creado y configurado con la cadena DATABASE_URL.")

    # Esperar 2 segundos para propagación en Supavisor
    time.sleep(2)

    # Inicializar tablas y datos semilla
    print(f"[*] Inicializando tablas y datos de ejemplo en Supabase...")
    try:
        import database
        database.DATABASE_URL = database_url
        os.environ["DATABASE_URL"] = database_url
        database.init_db()
        database.seed_data()
        print(f"[OK] Tablas y datos iniciales creados en Supabase con exito!")
    except Exception as e:
        print(f"[!] Aviso al conectar inmediatamente (puede tardar unos segundos en propagar): {e}")

    print(f"\n=======================================================")
    print(f"   CONEXION CON SUPABASE COMPLETADA CON EXITO!")
    print(f"=======================================================")
    print(f"\n1. Tu archivo local .env ya está listo.")
    print(f"2. Para Vercel, copia y añade esta variable de entorno:")
    print(f"   -------------------------------------------------")
    print(f"   Nombre: DATABASE_URL")
    print(f"   Valor : {database_url}")
    print(f"   -------------------------------------------------")
    print(f"\nYa puedes ejecutar 'py app.py' para probar localmente.")
    return True

if __name__ == "__main__":
    token = os.environ.get("SUPABASE_ACCESS_TOKEN")
    if len(sys.argv) > 1:
        token = sys.argv[1].strip()

    if not token:
        print("Uso: py setup_supabase.py <sbp_tu_token>")
        sys.exit(1)

    setup(token)
