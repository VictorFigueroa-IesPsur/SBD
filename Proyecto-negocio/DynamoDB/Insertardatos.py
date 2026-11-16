import os
import random
from decimal import Decimal
import boto3
from dotenv import load_dotenv
from faker import Faker

load_dotenv()
fake = Faker('es_ES')

session = boto3.session.Session(
    aws_access_key_id=os.getenv("ACCESS_KEY"),
    aws_secret_access_key=os.getenv("SECRET_KEY"),
    aws_session_token=os.getenv("SESSION_TOKEN"),
    region_name=os.getenv("REGION", "us-east-1")
)
dynamodb = session.resource('dynamodb')


def auditar_conteo_items(momento):
    print(f"\n{'=' * 70}")
    print(f" 📊 AUDITORÍA DE VOLUMEN DE REGISTROS [{momento}]")
    print(f"{'=' * 70}")
    print(f"{'TABLA':<28} | {'TOTAL ITEMS':>12} | {'MUESTRA DE CLAVE PRIMARIA'}")
    print("-" * 70)
    for nombre in ["EduSuccess_Cursos", "EduSuccess_Evaluaciones", "EduSuccess_Alumnos"]:
        tabla = dynamodb.Table(nombre)
        resp = tabla.scan(Select="ALL_ATTRIBUTES")
        items = resp.get("Items", [])
        total = len(items)
        muestra = str(items[0])[:32] + "..." if total > 0 else "Tabla vacía"
        print(f"{nombre:<28} | {total:>12} | {muestra}")
    print("-" * 70)


def poblar_tablas():
    auditar_conteo_items("ANTES DE LA INSERCIÓN")
    print("\n[*] Generando e insertando volumen amplio de datos sintéticos...")

    t_cursos = dynamodb.Table("EduSuccess_Cursos")
    t_eval = dynamodb.Table("EduSuccess_Evaluaciones")
    t_alumnos = dynamodb.Table("EduSuccess_Alumnos")

    # 1. Insertar 6 Cursos
    cursos = [
        {"id_curso": "CUR-01", "nombre_ciclo": "DAM", "grado": "Superior", "turno": "Manana", "plazas": 30},
        {"id_curso": "CUR-02", "nombre_ciclo": "ASIR", "grado": "Superior", "turno": "Tarde", "plazas": 28},
        {"id_curso": "CUR-03", "nombre_ciclo": "DAW", "grado": "Superior", "turno": "Manana", "plazas": 32},
        {"id_curso": "CUR-04", "nombre_ciclo": "IA y Big Data", "grado": "Especializacion", "turno": "Tarde", "plazas": 20},
        {"id_curso": "CUR-05", "nombre_ciclo": "Ciberseguridad", "grado": "Especializacion", "turno": "Tarde", "plazas": 22},
        {"id_curso": "CUR-06", "nombre_ciclo": "SMR", "grado": "Medio", "turno": "Manana", "plazas": 35}
    ]
    with t_cursos.batch_writer() as batch:
        for c in cursos:
            batch.put_item(Item=c)
    print(f" -> [OK] {len(cursos)} registros insertados en 'EduSuccess_Cursos'.")

    # 2. Insertar 25 Alumnos
    factores = ["Alta tasa de faltas", "Bajo rendimiento en BD", "Retrasos recurrentes", "Historial irregular", "Sin factor critico"]
    alumnos_ids = []
    with t_alumnos.batch_writer() as batch:
        for i in range(1, 26):
            id_al = f"ALU-{i:03d}"
            alumnos_ids.append(id_al)
            score = Decimal(str(round(random.uniform(0.05, 0.98), 2)))
            nivel = "ALTO" if score >= Decimal("0.70") else ("MEDIO" if score >= Decimal("0.35") else "BAJO")
            factor = random.choice(factores[:-1]) if nivel != "BAJO" else factores[-1]
            batch.put_item(Item={
                "id_alumno": id_al,
                "nombre": f"{fake.first_name()} {fake.last_name()}",
                "email": fake.email(),
                "id_curso": random.choice(cursos)["id_curso"],
                "nivel_riesgo": nivel,
                "score_abandono": score,
                "faltas": random.randint(0, 18),
                "factor_principal": factor
            })
    print(f" -> [OK] {len(alumnos_ids)} registros insertados en 'EduSuccess_Alumnos'.")

    # 3. Insertar 100 Evaluaciones (25 alumnos x 4 módulos)
    modulos = [
        ("BD", "Bases de Datos"),
        ("PROG", "Programacion"),
        ("SIA", "Sistemas de IA"),
        ("BIGD", "Modelos de Big Data")
    ]
    total_eval = 0
    with t_eval.batch_writer() as batch:
        for id_al in alumnos_ids:
            for cod, nom in modulos:
                batch.put_item(Item={
                    "id_alumno": id_al,
                    "codigo_modulo": cod,
                    "nombre_modulo": nom,
                    "nota_numerica": Decimal(str(round(random.uniform(1.5, 10.0), 2))),
                    "trimestre": random.choice([1, 2]),
                    "convocatoria": "ORDINARIA"
                })
                total_eval += 1
    print(f" -> [OK] {total_eval} registros insertados en 'EduSuccess_Evaluaciones'.")

    auditar_conteo_items("DESPUÉS DE LA INSERCIÓN")


if __name__ == "__main__":
    poblar_tablas()
