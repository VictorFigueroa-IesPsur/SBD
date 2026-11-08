import json
import pymysql
import redis

# ---------------------------------------------------------
# Configuración de Conexiones
# ---------------------------------------------------------
db_config = {
    'host': '127.0.0.1',
    'port': 3307,
    'user': 'root',
    'password': 'root',
    'database': 'edusuccess_db',
    'cursorclass': pymysql.cursors.DictCursor
}

redis_client = redis.Redis(host='127.0.0.1', port=6379, db=0, decode_responses=True)

def preparar_tablas_sql():
    """Crea la tabla 'cursos' e inserta datos iniciales en MariaDB."""
    connection = pymysql.connect(**db_config)
    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cursos (
                id INT PRIMARY KEY AUTO_INCREMENT,
                nombre VARCHAR(100),
                categoria VARCHAR(50),
                precio DECIMAL(10, 2)
            );
        """)
        cursor.execute("TRUNCATE TABLE cursos;")
        cursor.execute("""
            INSERT INTO cursos (nombre, categoria, precio) VALUES
            ('Python para Big Data', 'Programacion', 199.99),
            ('Administracion de Redes', 'Sistemas', 149.50),
            ('IA Aplicada', 'Inteligencia Artificial', 299.00);
        """)
    connection.commit()
    connection.close()
    print("[SQL] Tabla 'cursos' preparada con datos iniciales.")

# ---------------------------------------------------------
# EJERCICIO 21: SQL -> Redis
# Obtener datos de la BD mediante SQL e incluirlos en Redis
# ---------------------------------------------------------
def ejercicio_21_sql_a_redis():
    print("\n--- EJERCICIO 21: Migración de datos desde SQL (MariaDB) hacia Redis ---")
    connection = pymysql.connect(**db_config)
    
    with connection.cursor() as cursor:
        sql = "SELECT id, nombre, categoria, precio FROM cursos"
        cursor.execute(sql)
        registros_sql = cursor.fetchall()
        print(f"[SQL] Registros leídos de MariaDB: {len(registros_sql)}")
        
        for fila in registros_sql:
            # Convertir decimales a flotantes/strings para JSON
            fila['precio'] = float(fila['precio'])
            clave_redis = f"edusuccess:curso:{fila['id']}"
            
            # Guardar en Redis como JSON
            redis_client.set(clave_redis, json.dumps(fila))
            print(f"[Redis] Clave '{clave_redis}' guardada correctamente.")

    connection.close()
    print("-> Ejercicio 21 completado con éxito.")

# ---------------------------------------------------------
# EJERCICIO 22: Redis -> SQL
# Obtener datos de Redis e incluirlos en la BD relacional
# ---------------------------------------------------------
def ejercicio_22_redis_a_sql():
    print("\n--- EJERCICIO 22: Migración de datos desde Redis hacia SQL (MariaDB) ---")
    
    # Simular la creación de una nueva entidad en Redis
    nuevo_curso = {
        "id": 101,
        "nombre": "Seguridad en Entornos Cloud",
        "categoria": "Ciberseguridad",
        "precio": 250.00
    }
    redis_client.set("edusuccess:curso:101", json.dumps(nuevo_curso))
    print("[Redis] Se ha creado la clave temporal 'edusuccess:curso:101'")

    # Leer todas las claves con el patrón 'edusuccess:curso:*' desde Redis
    claves_redis = redis_client.keys("edusuccess:curso:*")
    print(f"[Redis] Claves encontradas con patrón: {claves_redis}")

    connection = pymysql.connect(**db_config)
    with connection.cursor() as cursor:
        for clave in claves_redis:
            datos_json = redis_client.get(clave)
            curso = json.loads(datos_json)
            
            # Insertar en MariaDB evitando duplicados por ID
            sql_insert = """
                INSERT INTO cursos (id, nombre, categoria, precio)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE nombre=%s, categoria=%s, precio=%s;
            """
            cursor.execute(sql_insert, (
                curso['id'], curso['nombre'], curso['categoria'], curso['precio'],
                curso['nombre'], curso['categoria'], curso['precio']
            ))
            print(f"[SQL] Curso ID {curso['id']} ({curso['nombre']}) guardado o actualizado en MariaDB.")

    connection.commit()
    connection.close()
    print("-> Ejercicio 22 completado con éxito.")

# ---------------------------------------------------------
# Flujo Principal
# ---------------------------------------------------------
if __name__ == '__main__':
    preparar_tablas_sql()
    ejercicio_21_sql_a_redis()
    ejercicio_22_redis_a_sql()