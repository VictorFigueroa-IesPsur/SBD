import pymysql
import redis

# Configuración de conexiones
db_config = {
    'host': '127.0.0.1',
    'port': 3307,
    'user': 'root',
    'password': 'root',
    'database': 'edusuccess_db'
}

def vaciar_mariadb():
    """Elimina la tabla 'cursos' y su contenido de MariaDB."""
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS cursos;")
            print("[SQL] Tabla 'cursos' eliminada correctamente de MariaDB.")
        connection.commit()
        connection.close()
    except Exception as e:
        print(f"[SQL Error] No se pudo limpiar MariaDB: {e}")

def vaciar_redis():
    """Elimina todas las claves registradas en la base de datos activa de Redis."""
    try:
        redis_client = redis.Redis(host='127.0.0.1', port=6379, db=0)
        redis_client.flushdb()
        print("[Redis] Base de datos vaciada completamente (FLUSHDB).")
    except Exception as e:
        print(f"[Redis Error] No se pudo limpiar Redis: {e}")

if __name__ == '__main__':
    print("--- INICIANDO LIMPIEZA COMPLETA DE ENTORNOS ---")
    vaciar_mariadb()
    vaciar_redis()
    print("--- LIMPIEZA FINALIZADA ---")