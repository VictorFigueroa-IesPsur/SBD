"""
=============================================================================
LISTA DE PROVIDERS DE FAKER UTILIZADOS:
1.  fake.first_name()        -> Faker.providers.person (Nombres de personas)
2.  fake.last_name()         -> Faker.providers.person (Apellidos de personas)
3.  fake.unique.bothify()    -> Faker.providers.misc (Formateo de DNI sintético)
4.  fake.date_between()      -> Faker.providers.date_time (Fechas acotadas)
5.  fake.date_time_between()-> Faker.providers.date_time (Marcas de tiempo completas)
6.  fake.email()             -> Faker.providers.internet (Correos electrónicos)
7.  fake.ipv4()              -> Faker.providers.internet (Direcciones IP para tornos)
8.  fake.phone_number()      -> Faker.providers.phone_number (Teléfonos de contacto)
9.  fake.random_int()        -> Faker.providers.python (Enteros para horas y tramos)
10. fake.pydecimal()         -> Faker.providers.python (Decimales para notas y scores)
=============================================================================
"""

import random
from faker import Faker
import mysql.connector
import psycopg2

fake = Faker('es_ES')

def poblar_mysql_mariadb(conn):
    cursor = conn.cursor()
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
    tablas = [
        "Predicciones_Riesgo", "Evaluaciones_Notas", "Partes_Asistencia",
        "Registros_Accesos", "Imparticion_Docente", "Tornos_Acceso",
        "Modulos", "Profesores", "Alumnos", "Cursos"
    ]
    for tabla in tablas:
        cursor.execute(f"TRUNCATE TABLE {tabla};")
    cursor.execute("SET FOREIGNKEY_CHECKS = 1;" if False else "SET FOREIGN_KEY_CHECKS = 1;")

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

    # 5. Imparticion Docente
    imparticiones = [(random.choice(id_profesores), m_id, random.choice([True, False]), "2025/2026") for m_id in id_modulos]
    cursor.executemany("INSERT INTO Imparticion_Docente (id_profesor, id_modulo, rol_tutor, curso_academico) VALUES (%s, %s, %s, %s)", imparticiones)

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


def poblar_postgres(conn):
    cursor = conn.cursor()
    tablas = [
        "Predicciones_Riesgo", "Evaluaciones_Notas", "Partes_Asistencia",
        "Registros_Accesos", "Imparticion_Docente", "Tornos_Acceso",
        "Modulos", "Profesores", "Alumnos", "Cursos"
    ]
    cursor.execute(f"TRUNCATE TABLE {', '.join(tablas)} RESTART IDENTITY CASCADE;")

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


def main():
    print("Poblando MySQL...")
    poblar_mysql_mariadb(mysql.connector.connect(
        host="localhost", port=3306, user="root", password="root", database="edusuccess_db"
    ))

    print("Poblando PostgreSQL...")
    poblar_postgres(psycopg2.connect(
        host="localhost", port=5432, user="root", password="root", dbname="edusuccess_db"
    ))

    print("Poblando MariaDB...")
    poblar_mysql_mariadb(mysql.connector.connect(
        host="localhost", port=3307, user="root", password="root", database="edusuccess_db"
    ))

    print("Población completada en las 3 bases de datos.")

if __name__ == "__main__":
    main()