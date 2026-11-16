import os
import json
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

session = boto3.session.Session(
    aws_access_key_id=os.getenv("ACCESS_KEY"),
    aws_secret_access_key=os.getenv("SECRET_KEY"),
    aws_session_token=os.getenv("SESSION_TOKEN"),
    region_name=os.getenv("REGION", "us-east-1")
)
dynamodb = session.resource('dynamodb')


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        return float(obj) if isinstance(obj, Decimal) else super().default(obj)


def mostrar_json(titulo, data):
    print(f"\n--- {titulo} ---")
    print(json.dumps(data, indent=2, cls=DecimalEncoder, ensure_ascii=False))


def ejecutar_crud():
    t_cursos = dynamodb.Table("EduSuccess_Cursos")
    t_eval = dynamodb.Table("EduSuccess_Evaluaciones")
    t_alumnos = dynamodb.Table("EduSuccess_Alumnos")

    print("=" * 75)
    print(" PASO 1: OBTENER UN REGISTRO DE CADA TABLA (get_item)")
    print("=" * 75)
    c1 = t_cursos.get_item(Key={"id_curso": "CUR-01"}).get("Item")
    e1 = t_eval.get_item(Key={"id_alumno": "ALU-001", "codigo_modulo": "BD"}).get("Item")
    a1 = t_alumnos.get_item(Key={"id_alumno": "ALU-001"}).get("Item")
    mostrar_json("Curso CUR-01", c1)
    mostrar_json("Evaluación ALU-001 / BD", e1)
    mostrar_json("Alumno ALU-001", a1)

    print("\n" + "=" * 75)
    print(" PASO 2: ACTUALIZAR UN REGISTRO DE CADA TABLA (update_item + Verificación)")
    print("=" * 75)
    # 2A. Cursos
    print(f"[ANTES] CUR-01 plazas = {c1.get('plazas')}")
    upd_c = t_cursos.update_item(
        Key={"id_curso": "CUR-01"},
        UpdateExpression="SET plazas = :p",
        ExpressionAttributeValues={":p": 40},
        ReturnValues="ALL_NEW"
    )["Attributes"]
    print(f"[DESPUÉS] CUR-01 plazas = {upd_c.get('plazas')}")

    # 2B. Evaluaciones
    print(f"\n[ANTES] ALU-001/BD nota = {e1.get('nota_numerica')}")
    upd_e = t_eval.update_item(
        Key={"id_alumno": "ALU-001", "codigo_modulo": "BD"},
        UpdateExpression="SET nota_numerica = :n",
        ExpressionAttributeValues={":n": Decimal("9.75")},
        ReturnValues="ALL_NEW"
    )["Attributes"]
    print(f"[DESPUÉS] ALU-001/BD nota = {upd_e.get('nota_numerica')}")

    # 2C. Alumnos
    print(f"\n[ANTES] ALU-001 faltas = {a1.get('faltas')} | nivel_riesgo = {a1.get('nivel_riesgo')}")
    upd_a = t_alumnos.update_item(
        Key={"id_alumno": "ALU-001"},
        UpdateExpression="SET faltas = :f, nivel_riesgo = :r, score_abandono = :s",
        ExpressionAttributeValues={":f": 16, ":r": "ALTO", ":s": Decimal("0.92")},
        ReturnValues="ALL_NEW"
    )["Attributes"]
    print(f"[DESPUÉS] ALU-001 faltas = {upd_a.get('faltas')} | nivel_riesgo = {upd_a.get('nivel_riesgo')}")

    print("\n" + "=" * 75)
    print(" PASO 3: ELIMINAR UN REGISTRO DE CADA TABLA (delete_item + Verificación)")
    print("=" * 75)
    # 3A. Eliminar CUR-06
    t_cursos.delete_item(Key={"id_curso": "CUR-06"})
    check_c = t_cursos.get_item(Key={"id_curso": "CUR-06"}).get("Item")
    print(f" -> CUR-06 eliminado. Comprobación get_item posterior: {check_c} (None = borrado confirmado)")

    # 3B. Eliminar ALU-025 / BIGD
    t_eval.delete_item(Key={"id_alumno": "ALU-025", "codigo_modulo": "BIGD"})
    check_e = t_eval.get_item(Key={"id_alumno": "ALU-025", "codigo_modulo": "BIGD"}).get("Item")
    print(f" -> ALU-025/BIGD eliminado. Comprobación get_item posterior: {check_e}")

    # 3C. Eliminar ALU-025
    t_alumnos.delete_item(Key={"id_alumno": "ALU-025"})
    check_a = t_alumnos.get_item(Key={"id_alumno": "ALU-025"}).get("Item")
    print(f" -> ALU-025 eliminado. Comprobación get_item posterior: {check_a}")

    print("\n" + "=" * 75)
    print(" PASO 4: OBTENER TODOS LOS REGISTROS DE CADA TABLA (scan completo)")
    print("=" * 75)
    for nombre in ["EduSuccess_Cursos", "EduSuccess_Evaluaciones", "EduSuccess_Alumnos"]:
        items = dynamodb.Table(nombre).scan().get("Items", [])
        print(f" -> {nombre:<26}: {len(items)} registros recuperados.")
        print(f"    Primeros 2 elementos: {json.dumps(items[:2], cls=DecimalEncoder, ensure_ascii=False)}")


if __name__ == "__main__":
    ejecutar_crud()
