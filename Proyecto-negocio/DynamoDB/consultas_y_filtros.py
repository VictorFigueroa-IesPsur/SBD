import os
import json
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

session = boto3.session.Session(
    aws_access_key_id=os.getenv("ACCESS_KEY"),
    aws_secret_access_key=os.getenv("SECRET_KEY"),
    aws_session_token=os.getenv("SESSION_TOKEN"),
    region_name=os.getenv("REGION", "us-east-1")
)
client = session.client('dynamodb')
dynamodb = session.resource('dynamodb')


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        return float(obj) if isinstance(obj, Decimal) else super().default(obj)


def imprimir_bloque(titulo):
    print(f"\n{'=' * 75}")
    print(f" {titulo}")
    print(f"{'=' * 75}")


def ejecutar_consultas_avanzadas():
    t_cursos = dynamodb.Table("EduSuccess_Cursos")
    t_eval = dynamodb.Table("EduSuccess_Evaluaciones")
    t_alumnos = dynamodb.Table("EduSuccess_Alumnos")

    # --------------------------------------------------------------------------
    # 1. FILTRADO USANDO SCAN (Y USANDO EL ÍNDICE GLOBAL EN LA GLOBAL)
    # --------------------------------------------------------------------------
    imprimir_bloque("1. FILTRADO USANDO SCAN (CON ÍNDICE GLOBAL EN ALUMNOS)")

    # 1A. Cursos (sin índice)
    f_cursos = t_cursos.scan(
        FilterExpression=Attr("grado").eq("Superior")
    ).get("Items", [])
    print(f"[Cursos] Grado = 'Superior' -> {len(f_cursos)} encontrados:")
    for c in f_cursos:
        print(f"   - {c['id_curso']}: {c['nombre_ciclo']} ({c['turno']})")

    # 1B. Evaluaciones (usando Índice Local NotaIndex)
    f_eval = t_eval.scan(
        IndexName="NotaIndex",
        FilterExpression=Attr("nota_numerica").gte(Decimal("8.5"))
    ).get("Items", [])
    print(f"\n[Evaluaciones - LSI 'NotaIndex'] Nota >= 8.5 -> {len(f_eval)} encontrados (muestra 5):")
    for e in f_eval[:5]:
        print(f"   - {e['id_alumno']} | {e['codigo_modulo']}: {e['nota_numerica']}")

    # 1C. Alumnos (usando Índice Global RiesgoScoreIndex)
    f_alumnos = t_alumnos.scan(
        IndexName="RiesgoScoreIndex",
        FilterExpression=Attr("nivel_riesgo").eq("ALTO")
    ).get("Items", [])
    print(f"\n[Alumnos - GSI 'RiesgoScoreIndex'] nivel_riesgo = 'ALTO' -> {len(f_alumnos)} encontrados:")
    for a in f_alumnos[:5]:
        print(f"   - {a['id_alumno']} | {a['nombre']} | Score: {a['score_abandono']} | Faltas: {a['faltas']}")

    # --------------------------------------------------------------------------
    # 2. ELIMINACIÓN CONDICIONAL EN CADA TABLA (USANDO GSI EN LA GLOBAL)
    # --------------------------------------------------------------------------
    imprimir_bloque("2. ELIMINACIÓN CONDICIONAL (ANTES Y DESPUÉS)")

    # 2A. Cursos: Eliminar CUR-05 solo si turno == 'Tarde'
    antes_c = t_cursos.scan(Select="COUNT")["Count"]
    try:
        t_cursos.delete_item(
            Key={"id_curso": "CUR-05"},
            ConditionExpression=Attr("turno").eq("Tarde")
        )
        print(f"[Cursos] CUR-05 eliminado condicionalmente (turno='Tarde'). Total cursos: {antes_c} -> {t_cursos.scan(Select='COUNT')['Count']}")
    except ClientError as err:
        print(f"[Cursos] No se cumplió condición o no existía: {err.response['Error']['Message']}")

    # 2B. Evaluaciones: Eliminar ALU-002/PROG solo si nota_numerica < 5.0 (si no cumple, lo indicamos)
    item_eval = t_eval.get_item(Key={"id_alumno": "ALU-002", "codigo_modulo": "PROG"}).get("Item")
    if item_eval:
        print(f"\n[Evaluaciones] Comprobando ALU-002/PROG (nota actual = {item_eval['nota_numerica']}) para borrar si nota < 6.0...")
        try:
            t_eval.delete_item(
                Key={"id_alumno": "ALU-002", "codigo_modulo": "PROG"},
                ConditionExpression=Attr("nota_numerica").lt(Decimal("6.0"))
            )
            print("   -> [OK] Eliminado porque su nota era menor a 6.0.")
        except ClientError:
            print("   -> [OMITIDO] No eliminado: su nota es >= 6.0 (ConditionExpression protegida).")

    # 2C. Alumnos: Localizar mediante Índice Global 'RiesgoScoreIndex' y aplicar delete_item condicional
    print("\n[Alumnos - GSI] Buscando en 'RiesgoScoreIndex' alumnos con nivel_riesgo='BAJO' y score < 0.25...")
    candidatos_gsi = t_alumnos.query(
        IndexName="RiesgoScoreIndex",
        KeyConditionExpression=Key("nivel_riesgo").eq("BAJO") & Key("score_abandono").lt(Decimal("0.25"))
    ).get("Items", [])
    print(f"   -> Candidatos encontrados vía GSI: {len(candidatos_gsi)}")
    for cand in candidatos_gsi:
        try:
            t_alumnos.delete_item(
                Key={"id_alumno": cand["id_alumno"]},
                ConditionExpression=Attr("faltas").lte(5)
            )
            print(f"   -> [OK] Eliminado {cand['id_alumno']} ({cand['nombre']}) tras verificar faltas <= 5.")
        except ClientError:
            print(f"   -> [OMITIDO] {cand['id_alumno']} no cumplía faltas <= 5.")

    # --------------------------------------------------------------------------
    # 3. CONSULTAS CON VARIOS FILTROS COMBINADOS EN CADA TABLA
    # --------------------------------------------------------------------------
    imprimir_bloque("3. CONSULTAS CON MÚLTIPLES FILTROS COMBINADOS (&)")

    # 3A. Cursos: grado == 'Superior' AND turno == 'Manana' AND plazas >= 30
    res_c = t_cursos.scan(
        FilterExpression=Attr("grado").eq("Superior") & Attr("turno").eq("Manana") & Attr("plazas").gte(30)
    ).get("Items", [])
    print(f"[Cursos] grado='Superior' AND turno='Manana' AND plazas>=30 -> {len(res_c)} resultados:")
    print("  ", json.dumps(res_c, cls=DecimalEncoder, ensure_ascii=False))

    # 3B. Evaluaciones: trimestre == 1 AND nota_numerica >= 7.0 AND codigo_modulo == 'BD'
    res_e = t_eval.scan(
        FilterExpression=Attr("trimestre").eq(1) & Attr("nota_numerica").gte(Decimal("7.0")) & Attr("codigo_modulo").eq("BD")
    ).get("Items", [])
    print(f"\n[Evaluaciones] trimestre=1 AND nota>=7.0 AND modulo='BD' -> {len(res_e)} resultados:")
    print("  ", json.dumps(res_e[:3], cls=DecimalEncoder, ensure_ascii=False))

    # 3C. Alumnos: nivel_riesgo == 'ALTO' AND faltas >= 10 AND score_abandono >= 0.75
    res_a = t_alumnos.scan(
        FilterExpression=Attr("nivel_riesgo").eq("ALTO") & Attr("faltas").gte(10) & Attr("score_abandono").gte(Decimal("0.75"))
    ).get("Items", [])
    print(f"\n[Alumnos] nivel_riesgo='ALTO' AND faltas>=10 AND score>=0.75 -> {len(res_a)} resultados:")
    print("  ", json.dumps(res_a[:3], cls=DecimalEncoder, ensure_ascii=False))

    # --------------------------------------------------------------------------
    # 4. SENTENCIAS PARTIQL EN CADA TABLA
    # --------------------------------------------------------------------------
    imprimir_bloque("4. CONSULTAS MEDIANTE PARTIQL (client.execute_statement)")

    # 4A. PartiQL en EduSuccess_Cursos
    q_cursos = """SELECT id_curso, nombre_ciclo, plazas FROM "EduSuccess_Cursos" WHERE turno = 'Manana'"""
    r_cursos = client.execute_statement(Statement=q_cursos).get("Items", [])
    print(f"[PartiQL Cursos] '{q_cursos}' -> {len(r_cursos)} filas:")
    print("  ", r_cursos)

    # 4B. PartiQL en EduSuccess_Evaluaciones
    q_eval = """SELECT id_alumno, codigo_modulo, nota_numerica FROM "EduSuccess_Evaluaciones" WHERE nota_numerica >= 9.0"""
    r_eval = client.execute_statement(Statement=q_eval).get("Items", [])
    print(f"\n[PartiQL Evaluaciones] '{q_eval}' -> {len(r_eval)} filas (muestra 3):")
    print("  ", r_eval[:3])

    # 4C. PartiQL en EduSuccess_Alumnos (atacando el Índice Global RiesgoScoreIndex)
    q_alumnos = """SELECT id_alumno, nombre, score_abandono FROM "EduSuccess_Alumnos"."RiesgoScoreIndex" WHERE nivel_riesgo = 'ALTO'"""
    r_alumnos = client.execute_statement(Statement=q_alumnos).get("Items", [])
    print(f"\n[PartiQL Alumnos GSI] '{q_alumnos}' -> {len(r_alumnos)} filas (muestra 3):")
    print("  ", r_alumnos[:3])


if __name__ == "__main__":
    ejecutar_consultas_avanzadas()
