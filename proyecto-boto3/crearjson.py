import json
import os
from decimal import Decimal
from datetime import date, datetime
from dotenv import load_dotenv
import mysql.connector

# Cargar variables de entorno desde el archivo .env
load_dotenv()

DB_HOST = os.getenv("DB_ENDPOINT")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = int(os.getenv("DB_PORT", 3306))


# Convertidor personalizado para serializar objetos Date, Datetime y Decimal a JSON
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def ejecutar_consultas():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        cursor = conn.cursor(dictionary=True)  # Formato diccionario para fácil conversión a JSON

        resultados = {}

        # ---------------------------------------------------------------------
        # Consulta 1: Alumnos en riesgo ALTO o MEDIO con su score y factor principal
        # ---------------------------------------------------------------------
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
        resultados["alumnos_en_riesgo"] = cursor.fetchall()

        # ---------------------------------------------------------------------
        # Consulta 2: Promedio de notas y asignaturas evaluadas por módulo/materia
        # ---------------------------------------------------------------------
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
        resultados["promedio_notas_por_modulo"] = cursor.fetchall()

        # ---------------------------------------------------------------------
        # Consulta 3: Resumen de asistencias por alumno (Faltas y Retrasos)
        # ---------------------------------------------------------------------
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
        resultados["top10_alumnos_asistencia"] = cursor.fetchall()

        cursor.close()
        conn.close()

        # Convertir todo el conjunto de datos a JSON formateado
        json_output = json.dumps(resultados, indent=4, cls=CustomJSONEncoder, ensure_ascii=False)
        
        # Imprimir por consola
        print(json_output)

        # Opcional: Guardar el resultado en un archivo JSON local
        with open("resultados_consultas.json", "w", encoding="utf-8") as f:
            f.write(json_output)
            print("\n[+] Resultados exportados correctamente a 'resultados_consultas.json'")

    except Exception as e:
        print(f"Error al conectar o consultar la BD en RDS: {e}")


if __name__ == "__main__":
    ejecutar_consultas()