import os
import json
import random
from decimal import Decimal
from datetime import date, datetime
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
import mysql.connector
from faker import Faker

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# -------------------------------
# CONFIGURACION GLOBAL
# -------------------------------
DB_INSTANCE_ID = os.getenv("DB_INSTANCE_ID")
DB_INSTANCE_CLASS = "db.t4g.micro"
DB_ENGINE = "mariadb"
DB_ALLOCATED_STORAGE = 20

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = int(os.getenv("DB_PORT", 3306))

fake = Faker('es_ES')


# Serializador personalizado para convertir objetos Date, Datetime y Decimal a JSON
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


# -------------------------------
# FASE 1: INFRAESTRUCTURA AWS RDS
# -------------------------------
def create_rds_instance():
    print("=" * 60)
    print("FASE 1: APROVISIONAMIENTO DE INSTANCIA AWS RDS (MariaDB)")
    print("=" * 60)

    session = boto3.session.Session(
        aws_access_key_id=os.getenv("ACCESS_KEY"),
        aws_secret_access_key=os.getenv("SECRET_KEY"),
        aws_session_token=os.getenv("SESSION_TOKEN"),
        region_name=os.getenv("REGION")
    )
    rds = session.client('rds')

    try:
        print(f"[*] Comprobando si la instancia '{DB_INSTANCE_ID}' ya existe...")
        info = rds.describe_db_instances(DBInstanceIdentifier=DB_INSTANCE_ID)
        estado = info['DBInstances'][0]['DBInstanceStatus']
        print(f"[+] La instancia '{DB_INSTANCE_ID}' ya existe (Estado actual: {estado}).")
        if estado != 'available':
            print("[*] Esperando a que la instancia esté disponible...")
            waiter = rds.get_waiter('db_instance_available')
            waiter.wait(DBInstanceIdentifier=DB_INSTANCE_ID)
    except ClientError as e:
        if e.response['Error']['Code'] == 'DBInstanceNotFound':
            print(f"[*] Creando nueva instancia RDS '{DB_INSTANCE_ID}'...")
            rds.create_db_instance(
                DBInstanceIdentifier=DB_INSTANCE_ID,
                AllocatedStorage=DB_ALLOCATED_STORAGE,
                DBInstanceClass=DB_INSTANCE_CLASS,
                Engine=DB_ENGINE,
                MasterUsername=DB_USER,
                MasterUserPassword=DB_PASSWORD,
                PubliclyAccessible=True
            )
            print("[*] Esperando a que la instancia RDS esté disponible (esto puede tardar varios minutos)...")
            waiter = rds.get_waiter('db_instance_available')
            waiter.wait(DBInstanceIdentifier=DB_INSTANCE_ID)
            print("[+] La instancia RDS está disponible.")
        else:
            raise e

    info = rds.describe_db_instances(DBInstanceIdentifier=DB_INSTANCE_ID)
    endpoint = info['DBInstances'][0]['Endpoint']['Address']
    print(f"[+] Endpoint obtenido dinámicamente: {endpoint}\n")
    return endpoint


# -------------------------------
# AUDITORÍA / COMPROBACIÓN DE ESTADO (ANTES Y DESPUÉS)
# -------------------------------
def auditar_estado_bd(endpoint, momento):
    print("-" * 60)
    print(f"🔍 AUDITORÍA DE BASE DE DATOS [{momento}]")
    print("-" * 60)
    try:
        conn = mysql.connector.connect(
            host=endpoint,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = conn.cursor()

        # 1. Comprobar si existe la base de datos
        cursor.execute("SHOW DATABASES LIKE %s;", (DB_NAME,))
        db_existe = cursor.fetchone()

        if not db_existe:
            print(f"[-] La base de datos '{DB_NAME}' NO existe todavía en el servidor.")
            cursor.close()
            conn.close()
            return

        print(f"[+] Base de datos '{DB_NAME}' detectada en el servidor.")
        cursor.execute(f"USE {DB_NAME};")

        # 2. Listar tablas y contar registros en cada una
        cursor.execute("SHOW TABLES;")
        tablas = [row[0] for row in cursor.fetchall()]

        if not tablas:
            print("[-] No hay tablas creadas dentro de la base de datos.")
        else:
            print(f"[+] Total de tablas encontradas: {len(tablas)}")
            print(f"    {'TABLA':<25} | {'REGISTROS':>10}")
            print("    " + "-" * 38)
            for tabla in tablas:
                cursor.execute(f"SELECT COUNT(*) FROM {tabla};")
                count = cursor.fetchone()[0]
                print(f"    {tabla:<25} | {count:>10}")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[!] Error durante la auditoría ({momento}): {e}")
    print("-" * 60 + "\n")


# -------------------------------
# FASE 2: CREACIÓN DE BD Y TABLAS
# -------------------------------
def create_bd_y_tablas(endpoint):
    print("=" * 60)
    print("FASE 2: CREACIÓN DE BASE DE DATOS Y ESQUEMA DE TABLAS")
    print("=" * 60)

    TABLES = {}
    TABLES['Cursos'] = (
        "CREATE TABLE IF NOT EXISTS Cursos ("
        "  id_curso INT AUTO_INCREMENT PRIMARY KEY,"
        "  nombre_ciclo VARCHAR(100) NOT NULL,"
        "  grado VARCHAR(20) NOT NULL,"
        "  curso_escolar VARCHAR(9) NOT NULL,"
        "  turno VARCHAR(15) NOT NULL"
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;"
    )
    TABLES['Profesores'] = (
        "CREATE TABLE IF NOT EXISTS Profesores ("
        "  id_profesor INT AUTO_INCREMENT PRIMARY KEY,"
        "  dni VARCHAR(9) UNIQUE NOT NULL,"
        "  nombre VARCHAR(50) NOT NULL,"
        "  apellidos VARCHAR(100) NOT NULL,"
        "  email VARCHAR(100) NOT NULL,"
        "  departamento VARCHAR(50) NOT NULL"
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;"
    )
    TABLES['Tornos_Acceso'] = (
        "CREATE TABLE IF NOT EXISTS Tornos_Acceso ("
        "  id_torno INT AUTO_INCREMENT PRIMARY KEY,"
        "  ubicacion VARCHAR(50) NOT NULL,"
        "  ip_dispositivo VARCHAR(15) NOT NULL,"
        "  activo BOOLEAN DEFAULT TRUE"
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;"
    )
    TABLES['Alumnos'] = (
        "CREATE TABLE IF NOT EXISTS Alumnos ("
        "  id_alumno INT AUTO_INCREMENT PRIMARY KEY,"
        "  dni VARCHAR(9) UNIQUE NOT NULL,"
        "  nombre VARCHAR(50) NOT NULL,"
        "  apellidos VARCHAR(100) NOT NULL,"
        "  fecha_nacimiento DATE NOT NULL,"
        "  email VARCHAR(100) NOT NULL,"
        "  telefono VARCHAR(15),"
        "  id_curso INT,"
        "  FOREIGN KEY (id_curso) REFERENCES Cursos(id_curso) ON DELETE CASCADE"
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;"
    )
    TABLES['Modulos'] = (
        "CREATE TABLE IF NOT EXISTS Modulos ("
        "  id_modulo INT AUTO_INCREMENT PRIMARY KEY,"
        "  codigo_oficial VARCHAR(10) NOT NULL,"
        "  nombre_modulo VARCHAR(100) NOT NULL,"
        "  horas_totales INT NOT NULL,"
        "  id_curso INT,"
        "  FOREIGN KEY (id_curso) REFERENCES Cursos(id_curso) ON DELETE CASCADE"
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;"
    )
    TABLES['Imparticion_Docente'] = (
        "CREATE TABLE IF NOT EXISTS Imparticion_Docente ("
        "  id_imparticion INT AUTO_INCREMENT PRIMARY KEY,"
        "  id_profesor INT,"
        "  id_modulo INT,"
        "  rol_tutor BOOLEAN DEFAULT FALSE,"
        "  curso_academico VARCHAR(9) NOT NULL,"
        "  FOREIGN KEY (id_profesor) REFERENCES Profesores(id_profesor) ON DELETE CASCADE,"
        "  FOREIGN KEY (id_modulo) REFERENCES Modulos(id_modulo) ON DELETE CASCADE"
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;"
    )
    TABLES['Registros_Accesos'] = (
        "CREATE TABLE IF NOT EXISTS Registros_Accesos ("
        "  id_acceso INT AUTO_INCREMENT PRIMARY KEY,"
        "  id_alumno INT,"
        "  id_torno INT,"
        "  fecha_hora DATETIME NOT NULL,"
        "  tipo_evento VARCHAR(10) NOT NULL,"
        "  FOREIGN KEY (id_alumno) REFERENCES Alumnos(id_alumno) ON DELETE CASCADE,"
        "  FOREIGN KEY (id_torno) REFERENCES Tornos_Acceso(id_torno) ON DELETE CASCADE"
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;"
    )
    TABLES['Partes_Asistencia'] = (
        "CREATE TABLE IF NOT EXISTS Partes_Asistencia ("
        "  id_asistencia INT AUTO_INCREMENT PRIMARY KEY,"
        "  id_alumno INT,"
        "  id_modulo INT,"
        "  fecha DATE NOT NULL,"
        "  hora_tramo INT NOT NULL,"
        "  estado VARCHAR(15) NOT NULL,"
        "  FOREIGN KEY (id_alumno) REFERENCES Alumnos(id_alumno) ON DELETE CASCADE,"
        "  FOREIGN KEY (id_modulo) REFERENCES Modulos(id_modulo) ON DELETE CASCADE"
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;"
    )
    TABLES['Evaluaciones_Notas'] = (
        "CREATE TABLE IF NOT EXISTS Evaluaciones_Notas ("
        "  id_evaluacion INT AUTO_INCREMENT PRIMARY KEY,"
        "  id_alumno INT,"
        "  id_modulo INT,"
        "  trimestre INT NOT NULL,"
        "  nota_numerica DECIMAL(4,2) NOT NULL,"
        "  convocatoria VARCHAR(15) NOT NULL,"
        "  FOREIGN KEY (id_alumno) REFERENCES Alumnos(id_alumno) ON DELETE CASCADE,"
        "  FOREIGN KEY (id_modulo) REFERENCES Modulos(id_modulo) ON DELETE CASCADE"
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;"
    )
    TABLES['Predicciones_Riesgo'] = (
        "CREATE TABLE IF NOT EXISTS Predicciones_Riesgo ("
        "  id_prediccion INT AUTO_INCREMENT PRIMARY KEY,"
        "  id_alumno INT,"
        "  fecha_calculo DATE NOT NULL,"
        "  score_abandono DECIMAL(4,2) NOT NULL,"
        "  nivel_riesgo VARCHAR(10) NOT NULL,"
        "  factor_principal VARCHAR(50),"
        "  FOREIGN KEY (id_alumno) REFERENCES Alumnos(id_alumno) ON DELETE CASCADE"
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;"
    )

    cnx = mysql.connector.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        host=endpoint,
        port=DB_PORT
    )
    cursor = cnx.cursor()

    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME};")
    cursor.execute(f"USE {DB_NAME};")

    for name, ddl in TABLES.items():
        print(f"[*] Verificando/Creando tabla '{name}'...")
        cursor.execute(ddl)

    print("[+] Base de datos y tablas creadas/verificadas correctamente.\n")
    cursor.close()
    cnx.close()


# -------------------------------
# FASE 3: POBLADO DE DATOS SINTÉTICOS
# -------------------------------
def poblar_mariadb(endpoint):
    print("=" * 60)
    print("FASE 3: INSERCIÓN DE DATOS SINTÉTICOS (FAKER)")
    print("=" * 60)

    conn = mysql.connector.connect(
        host=endpoint,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    cursor = conn.cursor()

    print("[*] Limpiando registros previos (TRUNCATE)...")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
    tablas = [
        "Predicciones_Riesgo", "Evaluaciones_Notas", "Partes_Asistencia",
        "Registros_Accesos", "Imparticion_Docente", "Tornos_Acceso",
        "Modulos", "Profesores", "Alumnos", "Cursos"
    ]
    for tabla in tablas:
        cursor.execute(f"TRUNCATE TABLE {tabla};")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

    print("[*] Insertando Cursos...")
    cursos_data = [
        ("Desarrollo de Aplicaciones Multiplataforma", "Superior", "2025/2026", "Manana"),
        ("Administracion de Sistemas Informaticos en Red", "Superior", "2025/2026", "Tarde"),
        ("Inteligencia Artificial y Big Data", "Especializacion", "2025/2026", "Tarde"),
        ("Sistemas Microinformaticos y Redes", "Medio", "2025/2026", "Manana")
    ]
    cursor.executemany("INSERT INTO Cursos (nombre_ciclo, grado, curso_escolar, turno) VALUES (%s, %s, %s, %s)", cursos_data)
    conn.commit()

    cursor.execute("SELECT id_curso FROM Cursos;")
    id_cursos = [row[0] for row in cursor.fetchall()]

    print("[*] Insertando 40 Alumnos...")
    alumnos_data = []
    fake.unique.clear()
    for _ in range(40):
        alumnos_data.append((
            fake.unique.bothify(text='########?'),
            fake.first_name(),
            f"{fake.last_name()} {fake.last_name()}",
            fake.date_between(start_date='-25y', end_date='-17y'),
            fake.email(),
            fake.phone_number()[:15],
            random.choice(id_cursos)
        ))
    cursor.executemany("INSERT INTO Alumnos (dni, nombre, apellidos, fecha_nacimiento, email, telefono, id_curso) VALUES (%s, %s, %s, %s, %s, %s, %s)", alumnos_data)
    conn.commit()

    cursor.execute("SELECT id_alumno FROM Alumnos;")
    id_alumnos = [row[0] for row in cursor.fetchall()]

    print("[*] Insertando 10 Profesores...")
    profesores_data = []
    departamentos = ["Informatica", "Sistemas", "Matematicas", "FOL"]
    for _ in range(10):
        profesores_data.append((
            fake.unique.bothify(text='########?'),
            fake.first_name(),
            f"{fake.last_name()} {fake.last_name()}",
            fake.email(),
            random.choice(departamentos)
        ))
    cursor.executemany("INSERT INTO Profesores (dni, nombre, apellidos, email, departamento) VALUES (%s, %s, %s, %s, %s)", profesores_data)
    conn.commit()

    cursor.execute("SELECT id_profesor FROM Profesores;")
    id_profesores = [row[0] for row in cursor.fetchall()]

    print("[*] Insertando Módulos e Impartición Docente...")
    modulos_base = [
        ("BD", "Bases de Datos", 192),
        ("PROG", "Programacion", 256),
        ("SI", "Sistemas Informaticos", 160),
        ("RED", "Planificacion y Redes", 192),
        ("BIGD", "Modelos de Big Data", 120),
        ("SIA", "Sistemas de IA", 140)
    ]
    modulos_data = [(cod, nom, h, random.choice(id_cursos)) for cod, nom, h in modulos_base]
    cursor.executemany("INSERT INTO Modulos (codigo_oficial, nombre_modulo, horas_totales, id_curso) VALUES (%s, %s, %s, %s)", modulos_data)
    conn.commit()

    cursor.execute("SELECT id_modulo FROM Modulos;")
    id_modulos = [row[0] for row in cursor.fetchall()]

    imparticiones = [(random.choice(id_profesores), m_id, random.choice([True, False]), "2025/2026") for m_id in id_modulos]
    cursor.executemany("INSERT INTO Imparticion_Docente (id_profesor, id_modulo, rol_tutor, curso_academico) VALUES (%s, %s, %s, %s)", imparticiones)

    print("[*] Insertando Tornos y Registros de Acceso...")
    tornos_data = [
        ("Acceso Principal Norte", fake.ipv4(), True),
        ("Acceso Principal Sur", fake.ipv4(), True),
        ("Entrada Talleres Informatica", fake.ipv4(), True),
        ("Acceso Biblioteca", fake.ipv4(), True)
    ]
    cursor.executemany("INSERT INTO Tornos_Acceso (ubicacion, ip_dispositivo, activo) VALUES (%s, %s, %s)", tornos_data)
    conn.commit()

    cursor.execute("SELECT id_torno FROM Tornos_Acceso;")
    id_tornos = [row[0] for row in cursor.fetchall()]

    accesos = [
        (random.choice(id_alumnos), random.choice(id_tornos), fake.date_time_between(start_date='-30d', end_date='now'), random.choice(["ENTRADA", "SALIDA"]))
        for _ in range(120)
    ]
    cursor.executemany("INSERT INTO Registros_Accesos (id_alumno, id_torno, fecha_hora, tipo_evento) VALUES (%s, %s, %s, %s)", accesos)

    print("[*] Insertando Partes de Asistencia, Evaluaciones y Predicciones de Riesgo...")
    estados = ["PRESENTE", "RETRASO", "FALTA_JUSTIF", "FALTA_INJUST"]
    asistencias = [
        (random.choice(id_alumnos), random.choice(id_modulos), fake.date_between(start_date='-30d', end_date='today'), fake.random_int(min=1, max=6), random.choice(estados))
        for _ in range(150)
    ]
    cursor.executemany("INSERT INTO Partes_Asistencia (id_alumno, id_modulo, fecha, hora_tramo, estado) VALUES (%s, %s, %s, %s, %s)", asistencias)

    evaluaciones = [
        (al_id, mod_id, 1, float(fake.pydecimal(left_digits=1, right_digits=2, min_value=1.0, max_value=10.0)), "ORDINARIA")
        for al_id in id_alumnos for mod_id in id_modulos
    ]
    cursor.executemany("INSERT INTO Evaluaciones_Notas (id_alumno, id_modulo, trimestre, nota_numerica, convocatoria) VALUES (%s, %s, %s, %s, %s)", evaluaciones)

    factores = ["Alta tasa de faltas", "Bajo rendimiento en BD", "Retrasos recurrentes", "Historial academico irregular"]
    predicciones = []
    for al_id in id_alumnos:
        score = float(fake.pydecimal(left_digits=1, right_digits=2, min_value=0.0, max_value=1.0))
        nivel = "ALTO" if score > 0.65 else ("MEDIO" if score > 0.35 else "BAJO")
        factor = random.choice(factores) if score > 0.35 else "Sin factor critico"
        predicciones.append((al_id, fake.date_between(start_date='-7d', end_date='today'), score, nivel, factor))
    cursor.executemany("INSERT INTO Predicciones_Riesgo (id_alumno, fecha_calculo, score_abandono, nivel_riesgo, factor_principal) VALUES (%s, %s, %s, %s, %s)", predicciones)

    conn.commit()
    cursor.close()
    conn.close()
    print("[+] Población de datos completada con éxito.\n")


# -------------------------------
# FASE 4: CONSULTAS Y EXPORTACIÓN JSON
# -------------------------------
def guardar_y_mostrar_json(data, nombre_archivo):
    json_output = json.dumps(data, indent=4, cls=CustomJSONEncoder, ensure_ascii=False)
    print(f"--- RESULTADO JSON: {nombre_archivo} (Total registros: {len(data)}) ---")
    print(json_output[:600] + ("\n... [truncado en consola, ver archivo completo]" if len(json_output) > 600 else ""))
    
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        f.write(json_output)
    print(f"[+] Archivo '{nombre_archivo}' guardado con éxito.\n")


def ejecutar_consultas_separadas(endpoint):
    print("=" * 60)
    print("FASE 4: EJECUCIÓN DE CONSULTAS ANALÍTICAS Y EXPORTACIÓN JSON")
    print("=" * 60)

    conn = mysql.connector.connect(
        host=endpoint,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    cursor = conn.cursor(dictionary=True)

    # Consulta 1
    query_1 = """
    SELECT 
        a.id_alumno,
        CONCAT(a.nombre, ' ', a.apellidos) AS alumno,
        a.email,
        pr.nivel_riesgo,
        pr.score_abandono,
        pr.factor_principal,
        pr.fecha_calculo
    FROM Predicciones_Riesgo pr
    JOIN Alumnos a ON pr.id_alumno = a.id_alumno
    WHERE pr.nivel_riesgo IN ('ALTO', 'MEDIO')
    ORDER BY pr.score_abandono DESC;
    """
    cursor.execute(query_1)
    guardar_y_mostrar_json(cursor.fetchall(), "consulta_1_alumnos_riesgo.json")

    # Consulta 2
    query_2 = """
    SELECT 
        m.codigo_oficial,
        m.nombre_modulo,
        COUNT(e.id_evaluacion) AS total_evaluaciones,
        ROUND(AVG(e.nota_numerica), 2) AS nota_media,
        MAX(e.nota_numerica) AS nota_maxima,
        MIN(e.nota_numerica) AS nota_minima
    FROM Modulos m
    LEFT JOIN Evaluaciones_Notas e ON m.id_modulo = e.id_modulo
    GROUP BY m.id_modulo, m.codigo_oficial, m.nombre_modulo
    ORDER BY nota_media DESC;
    """
    cursor.execute(query_2)
    guardar_y_mostrar_json(cursor.fetchall(), "consulta_2_promedio_notas.json")

    # Consulta 3
    query_3 = """
    SELECT 
        a.id_alumno,
        CONCAT(a.nombre, ' ', a.apellidos) AS alumno,
        SUM(CASE WHEN pa.estado = 'PRESENTE' THEN 1 ELSE 0 END) AS total_presencias,
        SUM(CASE WHEN pa.estado = 'RETRASO' THEN 1 ELSE 0 END) AS total_retrasos,
        SUM(CASE WHEN pa.estado = 'FALTA_INJUST' THEN 1 ELSE 0 END) AS faltas_injustificadas,
        SUM(CASE WHEN pa.estado = 'FALTA_JUSTIF' THEN 1 ELSE 0 END) AS faltas_justificadas
    FROM Alumnos a
    JOIN Partes_Asistencia pa ON a.id_alumno = pa.id_alumno
    GROUP BY a.id_alumno, alumno
    ORDER BY faltas_injustificadas DESC
    LIMIT 10;
    """
    cursor.execute(query_3)
    guardar_y_mostrar_json(cursor.fetchall(), "consulta_3_resumen_asistencias.json")

    cursor.close()
    conn.close()


# -------------------------------
# ORQUESTADOR PRINCIPAL
# -------------------------------
def main():
    try:
        # 1. Crear o verificar RDS y obtener su Endpoint real
        endpoint = create_rds_instance()

        # 2. Auditoría ANTES de crear/poblar la base de datos
        auditar_estado_bd(endpoint, "ANTES DE LA EJECUCIÓN")

        # 3. Crear base de datos y tablas
        create_bd_y_tablas(endpoint)

        # 4. Poblar tablas con datos sintéticos
        poblar_mariadb(endpoint)

        # 5. Auditoría DESPUÉS de crear/poblar la base de datos
        auditar_estado_bd(endpoint, "DESPUÉS DE LA EJECUCIÓN")

        # 6. Ejecutar consultas analíticas y generar archivos JSON
        ejecutar_consultas_separadas(endpoint)

        print("=" * 60)
        print("🎉 PROCESO COMPLETO FINALIZADO SIN ERRORES")
        print("=" * 60)

    except Exception as e:
        print(f"\n[❌ ERROR CRÍTICO EN EL PIPELINE]: {e}")


if __name__ == "__main__":
    main()
