import json
import subprocess
import redis
from redis.commands.json.path import Path

# 1. Conexión a Redis
conexionRedis = redis.ConnectionPool(
    host='localhost', port=6379, db=0, decode_responses=True
)
baseDatosRedis = redis.Redis(connection_pool=conexionRedis)

print(
    "Ejercicio 21 : Obtener datos de MariaDB (Docker) mediante SQL e incluirlos"
    " en Redis"
)

# Configuración del contenedor Docker de MariaDB
NOMBRE_CONTENEDOR = (
    "edusuccess_mariadb"  # Cambia por el nombre de tu contenedor Docker
)
USUARIO_DB = "root"
PASSWORD_DB = "root"
NOMBRE_DB = "edusuccess_db"

# Consulta SQL sobre la tabla PROFESORES del esquema
sql_query = "SELECT id_profesor, dni, nombre, apellidos, email, departamento FROM PROFESORES;"

# Comando para ejecutar dentro del contenedor y obtener el resultado en JSON nativo de MariaDB
comando_docker = [
    "docker",
    "exec",
    "-i",
    NOMBRE_CONTENEDOR,
    "mariadb",
    "-u",
    USUARIO_DB,
    f"-p{PASSWORD_DB}",
    NOMBRE_DB,
    "--json",
    "-e",
    sql_query,
]

try:
    resultado = subprocess.run(
        comando_docker, capture_output=True, text=True, check=True
    )
    profesores = json.loads(resultado.stdout)

    for prof in profesores:
        prof_id = prof["id_profesor"]
        datos_profesor = {
            "dni": prof["dni"],
            "nombre": prof["nombre"],
            "apellidos": prof["apellidos"],
            "email": prof["email"],
            "departamento": prof["departamento"],
        }

        # Guardar en Redis en formato JSON
        baseDatosRedis.json().set(
            f"profesores:{prof_id}", Path.root_path(), datos_profesor
        )
        print(
            f"Insertado en Redis desde MariaDB -> profesores:{prof_id} :"
            f" {datos_profesor}"
        )

except Exception as e:
    print(f"Error al ejecutar la consulta en Docker: {e}")

print("\nProceso finalizado con éxito.")