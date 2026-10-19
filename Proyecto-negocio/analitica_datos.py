import json
import os
from datetime import date, datetime
from decimal import Decimal
import mysql.connector
import psycopg2

# Directorio de destino para los archivos JSON
OUTPUT_DIR = "analiticas"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def json_serial(obj):
    """Manejo de tipos no serializables nativamente en JSON (fechas y decimales)."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Tipo no serializable: {type(obj)}")

def exportar_postgresql():
    """
    Extracción desde PostgreSQL:
    Une Alumnos, Cursos, Predicciones_Riesgo y Evaluaciones_Notas.
    """
    query = """
        SELECT 
            c.nombre_ciclo,
            c.turno,
            a.id_alumno,
            CONCAT(a.nombre, ' ', a.apellidos) AS nombre_completo,
            p.score_abandono,
            p.nivel_riesgo,
            p.factor_principal,
            ROUND(AVG(e.nota_numerica), 2) AS media_calificaciones,
            COUNT(e.id_evaluacion) AS total_asignaturas_evaluadas
        FROM Predicciones_Riesgo p
        JOIN Alumnos a ON p.id_alumno = a.id_alumno
        JOIN Cursos c ON a.id_curso = c.id_curso
        LEFT JOIN Evaluaciones_Notas e ON a.id_alumno = e.id_alumno
        WHERE p.nivel_riesgo IN ('ALTO', 'MEDIO')
        GROUP BY c.nombre_ciclo, c.turno, a.id_alumno, a.nombre, a.apellidos, 
                 p.score_abandono, p.nivel_riesgo, p.factor_principal
        ORDER BY p.score_abandono DESC;
    """
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        user="root",
        password="root",
        dbname="edusuccess_db"
    )
    cursor = conn.cursor()
    cursor.execute(query)
    columnas = [desc[0] for desc in cursor.description]
    filas = cursor.fetchall()
    cursor.close()
    conn.close()

    resultados = [dict(zip(columnas, fila)) for fila in filas]
    ruta_archivo = os.path.join(OUTPUT_DIR, "analitica_riesgo_academico.json")

    with open(ruta_archivo, "w", encoding="utf-8") as f:
        json.dump({
            "motor_bd": "PostgreSQL",
            "proposito_analitico": "Correlacion entre probabilidad de abandono y media de notas para orientacion",
            "total_alumnos_en_riesgo": len(resultados),
            "registros": resultados
        }, f, indent=4, default=json_serial, ensure_ascii=False)

    print(f"Archivo guardado en '{ruta_archivo}'.")

# =============================================================================
# 2. MYSQL -> analiticas/analitica_control_asistencia.json
# =============================================================================
def exportar_mysql():
    """
    Extracción desde MySQL:
    Une Partes_Asistencia, Alumnos, Modulos y Cursos.
    """
    query = """
        SELECT 
            c.nombre_ciclo,
            m.nombre_modulo,
            a.id_alumno,
            CONCAT(a.nombre, ' ', a.apellidos) AS estudiante,
            COUNT(pa.id_asistencia) AS total_incidencias_asistencia,
            SUM(CASE WHEN pa.estado = 'FALTA_INJUST' THEN 1 ELSE 0 END) AS faltas_injustificadas,
            SUM(CASE WHEN pa.estado = 'RETRASO' THEN 1 ELSE 0 END) AS retrasos,
            SUM(CASE WHEN pa.estado = 'FALTA_JUSTIF' THEN 1 ELSE 0 END) AS faltas_justificadas
        FROM Partes_Asistencia pa
        JOIN Alumnos a ON pa.id_alumno = a.id_alumno
        JOIN Modulos m ON pa.id_modulo = m.id_modulo
        JOIN Cursos c ON a.id_curso = c.id_curso
        GROUP BY c.nombre_ciclo, m.nombre_modulo, a.id_alumno, a.nombre, a.apellidos
        HAVING faltas_injustificadas > 0 OR retrasos > 1
        ORDER BY faltas_injustificadas DESC, retrasos DESC;
    """
    conn = mysql.connector.connect(
        host="localhost",
        port=3306,
        user="root",
        password="root",
        database="edusuccess_db"
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query)
    resultados = cursor.fetchall()
    cursor.close()
    conn.close()

    ruta_archivo = os.path.join(OUTPUT_DIR, "analitica_control_asistencia.json")

    with open(ruta_archivo, "w", encoding="utf-8") as f:
        json.dump({
            "motor_bd": "MySQL",
            "proposito_analitico": "Control de absentismo no justificado y retrasos por modulo para perdida de evaluacion continua",
            "total_alumnos_con_incidencias": len(resultados),
            "registros": resultados
        }, f, indent=4, default=json_serial, ensure_ascii=False)

    print(f"Archivo guardado en '{ruta_archivo}'.")

# =============================================================================
# 3. MARIADB -> analiticas/analitica_rendimiento_docente.json
# =============================================================================
def exportar_mariadb():
    """
    Extracción desde MariaDB:
    Une Evaluaciones_Notas, Modulos, Imparticion_Docente y Profesores.
    """
    query = """
        SELECT 
            m.codigo_oficial,
            m.nombre_modulo,
            CONCAT(p.nombre, ' ', p.apellidos) AS profesor_impartidor,
            p.departamento,
            ROUND(AVG(e.nota_numerica), 2) AS nota_media_asignatura,
            SUM(CASE WHEN e.nota_numerica < 5.0 THEN 1 ELSE 0 END) AS total_suspensos,
            SUM(CASE WHEN e.nota_numerica >= 5.0 THEN 1 ELSE 0 END) AS total_aprobados,
            COUNT(e.id_evaluacion) AS total_calificaciones_emitidas
        FROM Evaluaciones_Notas e
        JOIN Modulos m ON e.id_modulo = m.id_modulo
        JOIN Imparticion_Docente imp ON m.id_modulo = imp.id_modulo
        JOIN Profesores p ON imp.id_profesor = p.id_profesor
        GROUP BY m.codigo_oficial, m.nombre_modulo, p.nombre, p.apellidos, p.departamento
        ORDER BY nota_media_asignatura ASC;
    """
    conn = mysql.connector.connect(
        host="localhost",
        port=3307,
        user="root",
        password="root",
        database="edusuccess_db"
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query)
    resultados = cursor.fetchall()
    cursor.close()
    conn.close()

    ruta_archivo = os.path.join(OUTPUT_DIR, "analitica_rendimiento_docente.json")

    with open(ruta_archivo, "w", encoding="utf-8") as f:
        json.dump({
            "motor_bd": "MariaDB",
            "proposito_analitico": "Auditoria del desempeno academico de materias y balanceo docente",
            "total_modulos_analizados": len(resultados),
            "registros": resultados
        }, f, indent=4, default=json_serial, ensure_ascii=False)

    print(f"Archivo guardado en '{ruta_archivo}'.")

def main():
    exportar_postgresql()
    exportar_mysql()
    exportar_mariadb()

if __name__ == "__main__":
    main()