import os
import json
from decimal import Decimal
from datetime import date, datetime
import boto3
from boto3.dynamodb.conditions import Key, Attr
import mysql.connector
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# -------------------------------
# CONFIGURACIÓN DE CONEXIONES
# -------------------------------
DB_HOST = os.getenv("DB_ENDPOINT")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = int(os.getenv("DB_PORT", 3306))

session = boto3.session.Session(
    aws_access_key_id=os.getenv("ACCESS_KEY"),
    aws_secret_access_key=os.getenv("SECRET_KEY"),
    aws_session_token=os.getenv("SESSION_TOKEN"),
    region_name=os.getenv("REGION", "us-east-1")
)
dynamodb = session.resource('dynamodb')


# Serializador universal para manejar tipos de RDS (date, datetime, Decimal) y DynamoDB (Decimal)
class UniversalJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def banner(texto):
    print("\n" + "=" * 75)
    print(f" {texto}")
    print("=" * 75)


# ==============================================================================
# 1. EXTRACCIÓN CON FILTROS DESDE AMAZON DYNAMODB
# ==============================================================================
def obtener_datos_dynamodb():
    banner("1. EXTRAYENDO DATOS FILTRADOS DESDE AMAZON DYNAMODB")

    t_alumnos = dynamodb.Table("EduSuccess_Alumnos")
    t_eval = dynamodb.Table("EduSuccess_Evaluaciones")

    # 1A. Filtrar alumnos en DynamoDB usando el Índice Global (GSI) 'RiesgoScoreIndex'
    # Filtro: nivel_riesgo == 'ALTO' AND faltas >= 8
    print("[*] Consultando 'EduSuccess_Alumnos' (GSI 'RiesgoScoreIndex': nivel_riesgo='ALTO' y faltas >= 8)...")
    resp_alumnos = t_alumnos.query(
        IndexName="RiesgoScoreIndex",
        KeyConditionExpression=Key("nivel_riesgo").eq("ALTO"),
        FilterExpression=Attr("faltas").gte(8),
        ScanIndexForward=False  # Orden descendente por score_abandono
    )
    alumnos_dynamo = resp_alumnos.get("Items", [])
    print(f"[+] Registros obtenidos de EduSuccess_Alumnos: {len(alumnos_dynamo)}")

    # 1B. Filtrar evaluaciones en DynamoDB usando el Índice Local (LSI) 'NotaIndex'
    # Filtro: trimestre == 1 AND nota_numerica >= 7.0
    print("[*] Consultando 'EduSuccess_Evaluaciones' (LSI 'NotaIndex': trimestre=1 y nota >= 7.0)...")
    resp_eval = t_eval.scan(
        IndexName="NotaIndex",
        FilterExpression=Attr("trimestre").eq(1) & Attr("nota_numerica").gte(Decimal("7.0"))
    )
    evaluaciones_dynamo = resp_eval.get("Items", [])
    print(f"[+] Registros obtenidos de EduSuccess_Evaluaciones: {len(evaluaciones_dynamo)}")

    return {
        "alumnos_riesgo_critico": alumnos_dynamo,
        "evaluaciones_destacadas": evaluaciones_dynamo
    }


# ==============================================================================
# 2. EXTRACCIÓN CON FILTROS DESDE AWS RDS (MariaDB / MySQL)
# ==============================================================================
def obtener_datos_rds():
    banner("2. EXTRAYENDO DATOS FILTRADOS DESDE AWS RDS (MariaDB)")

    conn = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    cursor = conn.cursor(dictionary=True)

    # 2A. Consulta filtrada en RDS: Alumnos con predicción de riesgo ALTO o MEDIO y score >= 0.50
    print("[*] Ejecutando consulta filtrada de Predicciones_Riesgo + Alumnos + Cursos en RDS...")
    query_riesgo_rds = """
    SELECT 
        a.id_alumno,
        a.dni,
        CONCAT(a.nombre, ' ', a.apellidos) AS nombre_completo,
        a.email,
        c.nombre_ciclo AS curso,
        c.turno,
        pr.nivel_riesgo,
        pr.score_abandono,
        pr.factor_principal,
        pr.fecha_calculo
    FROM Predicciones_Riesgo pr
    INNER JOIN Alumnos a ON pr.id_alumno = a.id_alumno
    INNER JOIN Cursos c ON a.id_curso = c.id_curso
    WHERE pr.nivel_riesgo IN ('ALTO', 'MEDIO')
      AND pr.score_abandono >= 0.50
    ORDER BY pr.score_abandono DESC;
    """
    cursor.execute(query_riesgo_rds)
    riesgo_rds = cursor.fetchall()
    print(f"[+] Registros obtenidos de RDS (Alumnos en riesgo >= 0.50): {len(riesgo_rds)}")

    # 2B. Consulta filtrada en RDS: Módulos con nota media >= 5.0 y evaluaciones registradas
    print("[*] Ejecutando consulta filtrada de rendimiento por Módulos en RDS...")
    query_modulos_rds = """
    SELECT 
        m.codigo_oficial,
        m.nombre_modulo,
        c.nombre_ciclo,
        COUNT(e.id_evaluacion) AS total_evaluaciones,
        ROUND(AVG(e.nota_numerica), 2) AS nota_media
    FROM Modulos m
    INNER JOIN Cursos c ON m.id_curso = c.id_curso
    INNER JOIN Evaluaciones_Notas e ON m.id_modulo = e.id_modulo
    WHERE e.convocatoria = 'ORDINARIA'
    GROUP BY m.id_modulo, m.codigo_oficial, m.nombre_modulo, c.nombre_ciclo
    HAVING ROUND(AVG(e.nota_numerica), 2) >= 5.0
    ORDER BY nota_media DESC;
    """
    cursor.execute(query_modulos_rds)
    modulos_rds = cursor.fetchall()
    print(f"[+] Registros obtenidos de RDS (Módulos aprobados de media): {len(modulos_rds)}")

    cursor.close()
    conn.close()

    return {
        "alumnos_riesgo_relacional": riesgo_rds,
        "estadisticas_modulos": modulos_rds
    }


# ==============================================================================
# 3. UNIFICACIÓN Y EXPORTACIÓN A JSON ÚNICO
# ==============================================================================
def generar_json_unificado(archivo_salida="edusuccess_reporte_unificado.json"):
    try:
        datos_dynamo = obtener_datos_dynamodb()
        datos_rds = obtener_datos_rds()

        banner("3. UNIFICANDO INFORMACIÓN Y GENERANDO ARCHIVO JSON ÚNICO")

        # Estructura consolidada con metadatos de auditoría + bloques de cada origen
        reporte_unificado = {
            "proyecto": "EduSuccess",
            "fecha_generacion": datetime.now().isoformat(),
            "resumen_extraccion": {
                "total_dynamo_alumnos_filtrados": len(datos_dynamo["alumnos_riesgo_critico"]),
                "total_dynamo_evaluaciones_filtradas": len(datos_dynamo["evaluaciones_destacadas"]),
                "total_rds_alumnos_filtrados": len(datos_rds["alumnos_riesgo_relacional"]),
                "total_rds_modulos_filtrados": len(datos_rds["estadisticas_modulos"]),
                "total_registros_combinados": (
                    len(datos_dynamo["alumnos_riesgo_critico"])
                    + len(datos_dynamo["evaluaciones_destacadas"])
                    + len(datos_rds["alumnos_riesgo_relacional"])
                    + len(datos_rds["estadisticas_modulos"])
                )
            },
            "origen_nosql_dynamodb": datos_dynamo,
            "origen_relacional_rds": datos_rds
        }

        json_str = json.dumps(reporte_unificado, indent=4, cls=UniversalJSONEncoder, ensure_ascii=False)

        with open(archivo_salida, "w", encoding="utf-8") as f:
            f.write(json_str)

        print(f"[✓] Archivo JSON unificado generado con éxito: '{archivo_salida}'")
        print(f"[✓] Resumen de conteo combinado:")
        print(json.dumps(reporte_unificado["resumen_extraccion"], indent=4, ensure_ascii=False))

        print(f"\n--- VISTA PREVIA DE '{archivo_salida}' (Primeros 800 caracteres) ---")
        print(json_str[:800] + "\n... [archivo completo guardado en disco]")

    except Exception as e:
        print(f"\n[❌ ERROR AL UNIFICAR DATOS DE DYNAMODB Y RDS]: {e}")


if __name__ == "__main__":
    generar_json_unificado()
