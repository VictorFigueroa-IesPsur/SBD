import os
import json
import random
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from faker import Faker

# Cargar credenciales desde el archivo .env
load_dotenv()
fake = Faker('es_ES')

session = boto3.session.Session(
    aws_access_key_id=os.getenv("ACCESS_KEY"),
    aws_secret_access_key=os.getenv("SECRET_KEY"),
    aws_session_token=os.getenv("SESSION_TOKEN"),
    region_name=os.getenv("REGION", "us-east-1")
)

# Cliente de bajo nivel (creación de tablas y PartiQL)
client = session.client('dynamodb')
# Recurso de alto nivel (CRUD, scan y query)
dynamodb = session.resource('dynamodb')


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


# ==============================================================================
# UTILIDADES DE VISUALIZACIÓN Y AUDITORÍA EN CONSOLA
# ==============================================================================
def banner_fase(numero, titulo):
    print("\n" + "█" * 80)
    print(f"  FASE {numero}: {titulo}")
    print("█" * 80)


def subseccion(titulo):
    print(f"\n▶ {titulo}")
    print("-" * 80)


def auditar_estado_global(momento):
    print(f"\n╔{'═' * 78}╗")
    print(f"║ 🔍 AUDITORÍA DE ESTADO DYNAMODB: {momento:<43} ║")
    print(f"╠{'═' * 28}╦{'═' * 12}╦{'═' * 10}╦{'═' * 25}╣")
    print(f"║ {'TABLA':<26} ║ {'ESTADO':<10} ║ {'ITEMS':>8} ║ {'ÍNDICES ACTIVOS':<23} ║")
    print(f"╠{'═' * 28}╬{'═' * 12}╬{'═' * 10}╬{'═' * 25}╣")

    existentes = client.list_tables().get("TableNames", [])
    tablas_objetivo = ["EduSuccess_Cursos", "EduSuccess_Evaluaciones", "EduSuccess_Alumnos"]

    for nombre in tablas_objetivo:
        if nombre in existentes:
            desc = client.describe_table(TableName=nombre)["Table"]
            estado = desc["TableStatus"]
            total_items = dynamodb.Table(nombre).scan(Select="COUNT")["Count"]
            lsi = [f"{i['IndexName']}(LSI)" for i in desc.get("LocalSecondaryIndexes", [])]
            gsi = [f"{i['IndexName']}(GSI)" for i in desc.get("GlobalSecondaryIndexes", [])]
            idx_str = ", ".join(lsi + gsi) if (lsi or gsi) else "Ninguno"
            print(f"║ {nombre:<26} ║ {estado:<10} ║ {total_items:>8} ║ {idx_str:<23} ║")
        else:
            print(f"║ {nombre:<26} ║ {'NO EXISTE':<10} ║ {'-':>8} ║ {'-':<23} ║")

    print(f"╚{'═' * 28}╩{'═' * 12}╩{'═' * 10}╩{'═' * 25}╝")


def mostrar_comparativa_antes_despues(entidad, clave_str, antes, despues):
    print(f"  ┌─ COMPARATIVA DE CAMBIOS [{entidad} -> {clave_str}]")
    print(f"  │  [ANTES]   : {json.dumps(antes, cls=DecimalEncoder, ensure_ascii=False)}")
    print(f"  │  [DESPUÉS] : {json.dumps(despues, cls=DecimalEncoder, ensure_ascii=False)}")
    print(f"  └{'─' * 76}")


def imprimir_tabla_resultados(items, columnas, max_filas=6):
    if not items:
        print("  (0 registros encontrados)")
        return
    cabecera = " | ".join([f"{col:<18}" for col in columnas])
    print("  " + cabecera)
    print("  " + "-" * len(cabecera))
    for item in items[:max_filas]:
        fila = " | ".join([f"{str(item.get(col, '-')):<18}"[:18] for col in columnas])
        print("  " + fila)
    if len(items) > max_filas:
        print(f"  ... (+{len(items) - max_filas} registros adicionales omitidos en vista previa)")


# ==============================================================================
# 1. CREAR LAS 3 TABLAS CON SUS ÍNDICES
# ==============================================================================
def crear_tablas():
    banner_fase(1, "CREACIÓN DE TABLAS E ÍNDICES (BASE, LSI Y GSI)")

    # 1A. Tabla SIN índice local ni global: EduSuccess_Cursos
    subseccion("1.1. EduSuccess_Cursos (Sin índice local ni global)")
    try:
        client.create_table(
            TableName='EduSuccess_Cursos',
            AttributeDefinitions=[{'AttributeName': 'id_curso', 'AttributeType': 'S'}],
            KeySchema=[{'AttributeName': 'id_curso', 'KeyType': 'HASH'}],
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        print("  [*] Esperando disponibilidad de 'EduSuccess_Cursos'...")
        client.get_waiter('table_exists').wait(TableName='EduSuccess_Cursos')
        print("  [✓] Creada correctamente (PK: id_curso [S]).")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print("  [!] La tabla 'EduSuccess_Cursos' ya existía en AWS.")
        else:
            raise

    # 1B. Tabla CON ÍNDICE LOCAL (LSI): EduSuccess_Evaluaciones
    subseccion("1.2. EduSuccess_Evaluaciones (Con Índice Local 'NotaIndex')")
    try:
        client.create_table(
            TableName='EduSuccess_Evaluaciones',
            AttributeDefinitions=[
                {'AttributeName': 'id_alumno', 'AttributeType': 'S'},
                {'AttributeName': 'codigo_modulo', 'AttributeType': 'S'},
                {'AttributeName': 'nota_numerica', 'AttributeType': 'N'}
            ],
            KeySchema=[
                {'AttributeName': 'id_alumno', 'KeyType': 'HASH'},
                {'AttributeName': 'codigo_modulo', 'KeyType': 'RANGE'}
            ],
            LocalSecondaryIndexes=[
                {
                    'IndexName': 'NotaIndex',
                    'KeySchema': [
                        {'AttributeName': 'id_alumno', 'KeyType': 'HASH'},
                        {'AttributeName': 'nota_numerica', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        print("  [*] Esperando disponibilidad de 'EduSuccess_Evaluaciones'...")
        client.get_waiter('table_exists').wait(TableName='EduSuccess_Evaluaciones')
        print("  [✓] Creada correctamente (PK: id_alumno, SK: codigo_modulo, LSI: NotaIndex [nota_numerica]).")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print("  [!] La tabla 'EduSuccess_Evaluaciones' ya existía en AWS.")
        else:
            raise

    # 1C. Tabla CON ÍNDICE GLOBAL (GSI): EduSuccess_Alumnos
    subseccion("1.3. EduSuccess_Alumnos (Con Índice Global 'RiesgoScoreIndex')")
    try:
        client.create_table(
            TableName='EduSuccess_Alumnos',
            AttributeDefinitions=[
                {'AttributeName': 'id_alumno', 'AttributeType': 'S'},
                {'AttributeName': 'nivel_riesgo', 'AttributeType': 'S'},
                {'AttributeName': 'score_abandono', 'AttributeType': 'N'}
            ],
            KeySchema=[{'AttributeName': 'id_alumno', 'KeyType': 'HASH'}],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'RiesgoScoreIndex',
                    'KeySchema': [
                        {'AttributeName': 'nivel_riesgo', 'KeyType': 'HASH'},
                        {'AttributeName': 'score_abandono', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                }
            ],
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        print("  [*] Esperando disponibilidad de 'EduSuccess_Alumnos'...")
        client.get_waiter('table_exists').wait(TableName='EduSuccess_Alumnos')
        print("  [✓] Creada correctamente (PK: id_alumno, GSI: RiesgoScoreIndex [nivel_riesgo / score_abandono]).")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print("  [!] La tabla 'EduSuccess_Alumnos' ya existía en AWS.")
        else:
            raise


# ==============================================================================
# 2. INSERCIÓN DE REGISTROS (6 CURSOS, 20 ALUMNOS, 80 EVALUACIONES)
# ==============================================================================
def insertar_registros():
    banner_fase(2, "POBLACIÓN DE DATOS SINTÉTICOS EN LAS 3 TABLAS")

    t_cursos = dynamodb.Table('EduSuccess_Cursos')
    t_eval = dynamodb.Table('EduSuccess_Evaluaciones')
    t_alumnos = dynamodb.Table('EduSuccess_Alumnos')

    # Limpieza previa para que las demostraciones de cambios sean 100% reproducibles
    subseccion("2.0. Limpiando posibles residuos de ejecuciones anteriores")
    for t, keys in [
        (t_cursos, ['id_curso']),
        (t_eval, ['id_alumno', 'codigo_modulo']),
        (t_alumnos, ['id_alumno'])
    ]:
        items_previos = t.scan().get('Items', [])
        if items_previos:
            with t.batch_writer() as batch:
                for it in items_previos:
                    batch.delete_item(Key={k: it[k] for k in keys})
            print(f"  [-] Limpiados {len(items_previos)} items previos de '{t.name}'.")
        else:
            print(f"  [✓] '{t.name}' ya estaba vacía.")

    # 2.1 Cursos (6 registros)
    subseccion("2.1. Insertando catálogo de Cursos en 'EduSuccess_Cursos'")
    cursos = [
        {'id_curso': 'CUR-01', 'nombre_ciclo': 'DAM', 'grado': 'Superior', 'turno': 'Manana', 'plazas': 30},
        {'id_curso': 'CUR-02', 'nombre_ciclo': 'ASIR', 'grado': 'Superior', 'turno': 'Tarde', 'plazas': 28},
        {'id_curso': 'CUR-03', 'nombre_ciclo': 'DAW', 'grado': 'Superior', 'turno': 'Manana', 'plazas': 32},
        {'id_curso': 'CUR-04', 'nombre_ciclo': 'IA y Big Data', 'grado': 'Especializacion', 'turno': 'Tarde', 'plazas': 20},
        {'id_curso': 'CUR-05', 'nombre_ciclo': 'Ciberseguridad', 'grado': 'Especializacion', 'turno': 'Tarde', 'plazas': 22},
        {'id_curso': 'CUR-06', 'nombre_ciclo': 'SMR', 'grado': 'Medio', 'turno': 'Manana', 'plazas': 35}
    ]
    with t_cursos.batch_writer() as batch:
        for c in cursos:
            batch.put_item(Item=c)
    print(f"  [✓] {len(cursos)} cursos insertados.")
    imprimir_tabla_resultados(cursos, ['id_curso', 'nombre_ciclo', 'grado', 'turno', 'plazas'])

    # 2.2 Alumnos (20 registros)
    subseccion("2.2. Insertando 20 Alumnos en 'EduSuccess_Alumnos'")
    alumnos = [
        {'id_alumno': 'ALU-001', 'nombre': 'Laura Gomez', 'id_curso': 'CUR-01', 'nivel_riesgo': 'ALTO', 'score_abandono': Decimal('0.85'), 'faltas': 12},
        {'id_alumno': 'ALU-002', 'nombre': 'Carlos Ruiz', 'id_curso': 'CUR-01', 'nivel_riesgo': 'ALTO', 'score_abandono': Decimal('0.74'), 'faltas': 9},
        {'id_alumno': 'ALU-003', 'nombre': 'Elena Martin', 'id_curso': 'CUR-03', 'nivel_riesgo': 'BAJO', 'score_abandono': Decimal('0.15'), 'faltas': 1},
        {'id_alumno': 'ALU-004', 'nombre': 'Mario Diaz', 'id_curso': 'CUR-01', 'nivel_riesgo': 'ALTO', 'score_abandono': Decimal('0.91'), 'faltas': 16},
        {'id_alumno': 'ALU-005', 'nombre': 'Sofia Navarro', 'id_curso': 'CUR-02', 'nivel_riesgo': 'BAJO', 'score_abandono': Decimal('0.18'), 'faltas': 2}
    ]
    for i in range(6, 21):
        score = Decimal(str(round(random.uniform(0.10, 0.95), 2)))
        nivel = 'ALTO' if score >= Decimal('0.70') else ('MEDIO' if score >= Decimal('0.35') else 'BAJO')
        alumnos.append({
            'id_alumno': f'ALU-{i:03d}',
            'nombre': f"{fake.first_name()} {fake.last_name()}",
            'id_curso': random.choice(cursos)['id_curso'],
            'nivel_riesgo': nivel,
            'score_abandono': score,
            'faltas': random.randint(0, 17)
        })
    with t_alumnos.batch_writer() as batch:
        for a in alumnos:
            batch.put_item(Item=a)
    print(f"  [✓] {len(alumnos)} alumnos insertados.")
    imprimir_tabla_resultados(alumnos, ['id_alumno', 'nombre', 'id_curso', 'nivel_riesgo', 'score_abandono', 'faltas'])

    # 2.3 Evaluaciones (20 alumnos x 4 módulos = 80 registros)
    subseccion("2.3. Insertando 80 Evaluaciones en 'EduSuccess_Evaluaciones'")
    modulos = [
        ('BD', 'Bases de Datos'),
        ('PROG', 'Programacion'),
        ('SIA', 'Sistemas de IA'),
        ('BIGD', 'Modelos de Big Data')
    ]
    evaluaciones = [
        {'id_alumno': 'ALU-001', 'codigo_modulo': 'BD', 'nombre_modulo': 'Bases de Datos', 'nota_numerica': Decimal('8.50'), 'trimestre': 1},
        {'id_alumno': 'ALU-001', 'codigo_modulo': 'PROG', 'nombre_modulo': 'Programacion', 'nota_numerica': Decimal('4.20'), 'trimestre': 1},
        {'id_alumno': 'ALU-001', 'codigo_modulo': 'SIA', 'nombre_modulo': 'Sistemas de IA', 'nota_numerica': Decimal('9.10'), 'trimestre': 1},
        {'id_alumno': 'ALU-001', 'codigo_modulo': 'BIGD', 'nombre_modulo': 'Modelos de Big Data', 'nota_numerica': Decimal('7.40'), 'trimestre': 1}
    ]
    for a in alumnos[1:]:
        for cod, nom in modulos:
            evaluaciones.append({
                'id_alumno': a['id_alumno'],
                'codigo_modulo': cod,
                'nombre_modulo': nom,
                'nota_numerica': Decimal(str(round(random.uniform(2.0, 9.8), 2))),
                'trimestre': 1
            })
    with t_eval.batch_writer() as batch:
        for ev in evaluaciones:
            batch.put_item(Item=ev)
    print(f"  [✓] {len(evaluaciones)} evaluaciones insertadas.")
    imprimir_tabla_resultados(evaluaciones, ['id_alumno', 'codigo_modulo', 'nombre_modulo', 'nota_numerica', 'trimestre'])


# ==============================================================================
# 3. OBTENER UN REGISTRO DE CADA TABLA (GET_ITEM)
# ==============================================================================
def obtener_un_registro():
    banner_fase(3, "LECTURA INDIVIDUAL DE UN REGISTRO POR TABLA (get_item)")

    r_curso = dynamodb.Table('EduSuccess_Cursos').get_item(Key={'id_curso': 'CUR-01'}).get('Item')
    print("  [1] EduSuccess_Cursos (PK='CUR-01'):")
    print(f"      -> {json.dumps(r_curso, cls=DecimalEncoder, ensure_ascii=False)}")

    r_eval = dynamodb.Table('EduSuccess_Evaluaciones').get_item(
        Key={'id_alumno': 'ALU-001', 'codigo_modulo': 'BD'}
    ).get('Item')
    print("[2] EduSuccess_Evaluaciones (PK='ALU-001', SK='BD'):")
    print(f"      -> {json.dumps(r_eval, cls=DecimalEncoder, ensure_ascii=False)}")

    r_alumno = dynamodb.Table('EduSuccess_Alumnos').get_item(Key={'id_alumno': 'ALU-001'}).get('Item')
    print("[3] EduSuccess_Alumnos (PK='ALU-001'):")
    print(f"      -> {json.dumps(r_alumno, cls=DecimalEncoder, ensure_ascii=False)}")


# ==============================================================================
# 4. ACTUALIZAR UN REGISTRO DE CADA TABLA (CON COMPARATIVA ANTES/DESPUÉS)
# ==============================================================================
def actualizar_un_registro():
    banner_fase(4, "ACTUALIZACIÓN DE REGISTROS CON DEMOSTRACIÓN ANTES / DESPUÉS")

    t_cursos = dynamodb.Table('EduSuccess_Cursos')
    t_eval = dynamodb.Table('EduSuccess_Evaluaciones')
    t_alumnos = dynamodb.Table('EduSuccess_Alumnos')

    # 4.1 Actualizar plazas en Cursos
    subseccion("4.1. Actualizando plazas del curso CUR-01 (30 -> 40)")
    antes_c = t_cursos.get_item(Key={'id_curso': 'CUR-01'}).get('Item')
    despues_c = t_cursos.update_item(
        Key={'id_curso': 'CUR-01'},
        UpdateExpression="SET plazas = :p, turno = :t",
        ExpressionAttributeValues={':p': 40, ':t': 'Manana-Ampliado'},
        ReturnValues="ALL_NEW"
    )['Attributes']
    mostrar_comparativa_antes_despues("EduSuccess_Cursos", "CUR-01", antes_c, despues_c)

    # 4.2 Actualizar nota en Evaluaciones
    subseccion("4.2. Actualizando nota de ALU-001 en PROG tras recuperación (4.20 -> 5.75)")
    antes_e = t_eval.get_item(Key={'id_alumno': 'ALU-001', 'codigo_modulo': 'PROG'}).get('Item')
    despues_e = t_eval.update_item(
        Key={'id_alumno': 'ALU-001', 'codigo_modulo': 'PROG'},
        UpdateExpression="SET nota_numerica = :n",
        ExpressionAttributeValues={':n': Decimal('5.75')},
        ReturnValues="ALL_NEW"
    )['Attributes']
    mostrar_comparativa_antes_despues("EduSuccess_Evaluaciones", "ALU-001 / PROG", antes_e, despues_e)

    # 4.3 Actualizar faltas y score en Alumnos
    subseccion("4.3. Actualizando faltas y score de riesgo de ALU-002")
    antes_a = t_alumnos.get_item(Key={'id_alumno': 'ALU-002'}).get('Item')
    despues_a = t_alumnos.update_item(
        Key={'id_alumno': 'ALU-002'},
        UpdateExpression="SET faltas = :f, score_abandono = :s",
        ExpressionAttributeValues={':f': 13, ':s': Decimal('0.79')},
        ReturnValues="ALL_NEW"
    )['Attributes']
    mostrar_comparativa_antes_despues("EduSuccess_Alumnos", "ALU-002", antes_a, despues_a)


# ==============================================================================
# 5. ELIMINAR UN REGISTRO DE CADA TABLA (CON COMPROBACIÓN POST-BORRADO)
# ==============================================================================
def eliminar_un_registro():
    banner_fase(5, "ELIMINACIÓN INDIVIDUAL DE REGISTROS Y VERIFICACIÓN DE BORRADO")

    t_cursos = dynamodb.Table('EduSuccess_Cursos')
    t_eval = dynamodb.Table('EduSuccess_Evaluaciones')
    t_alumnos = dynamodb.Table('EduSuccess_Alumnos')

    # 5.1 Cursos
    antes_c = t_cursos.get_item(Key={'id_curso': 'CUR-06'}).get('Item')
    t_cursos.delete_item(Key={'id_curso': 'CUR-06'})
    despues_c = t_cursos.get_item(Key={'id_curso': 'CUR-06'}).get('Item')
    print(f"  [1] Cursos (CUR-06)           | Existía antes: {bool(antes_c)} -> Existe después: {bool(despues_c)} (Valor: {despues_c})")

    # 5.2 Evaluaciones
    antes_e = t_eval.get_item(Key={'id_alumno': 'ALU-001', 'codigo_modulo': 'SIA'}).get('Item')
    t_eval.delete_item(Key={'id_alumno': 'ALU-001', 'codigo_modulo': 'SIA'})
    despues_e = t_eval.get_item(Key={'id_alumno': 'ALU-001', 'codigo_modulo': 'SIA'}).get('Item')
    print(f"  [2] Evaluaciones (ALU-001/SIA)| Existía antes: {bool(antes_e)} -> Existe después: {bool(despues_e)} (Valor: {despues_e})")

    # 5.3 Alumnos
    antes_a = t_alumnos.get_item(Key={'id_alumno': 'ALU-020'}).get('Item')
    t_alumnos.delete_item(Key={'id_alumno': 'ALU-020'})
    despues_a = t_alumnos.get_item(Key={'id_alumno': 'ALU-020'}).get('Item')
    print(f"  [3] Alumnos (ALU-020)         | Existía antes: {bool(antes_a)} -> Existe después: {bool(despues_a)} (Valor: {despues_a})")


# ==============================================================================
# 6. OBTENER TODOS LOS REGISTROS DE CADA TABLA (SCAN COMPLETO)
# ==============================================================================
def obtener_todos():
    banner_fase(6, "LECTURA COMPLETA DE TODAS LAS TABLAS (scan)")

    for nombre, cols in [
        ('EduSuccess_Cursos', ['id_curso', 'nombre_ciclo', 'grado', 'turno', 'plazas']),
        ('EduSuccess_Evaluaciones', ['id_alumno', 'codigo_modulo', 'nombre_modulo', 'nota_numerica']),
        ('EduSuccess_Alumnos', ['id_alumno', 'nombre', 'id_curso', 'nivel_riesgo', 'score_abandono'])
    ]:
        items = dynamodb.Table(nombre).scan().get('Items', [])
        subseccion(f"Tabla '{nombre}' -> Total recuperados: {len(items)} registros")
        imprimir_tabla_resultados(items, cols, max_filas=5)


# ==============================================================================
# 7. FILTRADO USANDO SCAN (Y USANDO EL ÍNDICE GLOBAL EN LA TABLA CON GSI)
# ==============================================================================
def filtrado_scan_y_gsi():
    banner_fase(7, "FILTRADO CON SCAN (UTILIZANDO ÍNDICE GLOBAL EN ALUMNOS)")

    subseccion("7.1. Scan en 'EduSuccess_Cursos' (Filtro: grado == 'Superior')")
    f_cursos = dynamodb.Table('EduSuccess_Cursos').scan(
        FilterExpression=Attr('grado').eq('Superior')
    ).get('Items', [])
    print(f"  [✓] Encontrados {len(f_cursos)} cursos de grado Superior:")
    imprimir_tabla_resultados(f_cursos, ['id_curso', 'nombre_ciclo', 'grado', 'turno', 'plazas'])

    subseccion("7.2. Scan en 'EduSuccess_Evaluaciones' usando LSI 'NotaIndex' (Filtro: nota >= 8.5)")
    f_eval = dynamodb.Table('EduSuccess_Evaluaciones').scan(
        IndexName='NotaIndex',
        FilterExpression=Attr('nota_numerica').gte(Decimal('8.5'))
    ).get('Items', [])
    print(f"  [✓] Encontradas {len(f_eval)} evaluaciones sobresalientes (>= 8.5):")
    imprimir_tabla_resultados(f_eval, ['id_alumno', 'codigo_modulo', 'nombre_modulo', 'nota_numerica'])

    subseccion("7.3. Scan en 'EduSuccess_Alumnos' usando GSI 'RiesgoScoreIndex' (Filtro: nivel_riesgo == 'ALTO')")
    f_alumnos = dynamodb.Table('EduSuccess_Alumnos').scan(
        IndexName='RiesgoScoreIndex',
        FilterExpression=Attr('nivel_riesgo').eq('ALTO')
    ).get('Items', [])
    print(f"  [✓] Encontrados {len(f_alumnos)} alumnos en riesgo ALTO a través del Índice Global:")
    imprimir_tabla_resultados(f_alumnos, ['id_alumno', 'nombre', 'nivel_riesgo', 'score_abandono', 'faltas'])


# ==============================================================================
# 8. ELIMINACIÓN CONDICIONAL EN CADA TABLA (USANDO GSI EN LA GLOBAL)
# ==============================================================================
def eliminacion_condicional():
    banner_fase(8, "ELIMINACIÓN CONDICIONAL CON VERIFICACIÓN ANTES / DESPUÉS")

    t_cursos = dynamodb.Table('EduSuccess_Cursos')
    t_eval = dynamodb.Table('EduSuccess_Evaluaciones')
    t_alumnos = dynamodb.Table('EduSuccess_Alumnos')

    # 8.1 Cursos: Eliminar CUR-05 solo si turno == 'Tarde'
    subseccion("8.1. Cursos: Eliminar CUR-05 si turno == 'Tarde'")
    total_antes = t_cursos.scan(Select='COUNT')['Count']
    try:
        t_cursos.delete_item(
            Key={'id_curso': 'CUR-05'},
            ConditionExpression=Attr('turno').eq('Tarde')
        )
        total_despues = t_cursos.scan(Select='COUNT')['Count']
        print(f"  [✓] CONDICIÓN CUMPLIDA: CUR-05 eliminado. Conteo en tabla: {total_antes} -> {total_despues}")
    except ClientError as e:
        print(f"  [!] CONDICIÓN FALLIDA: {e.response['Error']['Message']}")

    # 8.2 Evaluaciones: Prueba doble (1ª falla por condición, 2ª se cumple)
    subseccion("8.2. Evaluaciones: Prueba de protección condicional en ALU-001 / PROG (nota = 5.75)")
    try:
        print("  [*] Intento A: Eliminar solo si nota_numerica < 5.0 (debe ser bloqueado)...")
        t_eval.delete_item(
            Key={'id_alumno': 'ALU-001', 'codigo_modulo': 'PROG'},
            ConditionExpression=Attr('nota_numerica').lt(Decimal('5.0'))
        )
    except ClientError:
        print("  [✓] BLOQUEO CONFIRMADO: DynamoDB impidió el borrado porque la nota actual es 5.75 (>= 5.0).")

    total_ev_antes = t_eval.scan(Select='COUNT')['Count']
    print("  [*] Intento B: Eliminar si nota_numerica < 6.0 (debe ejecutarse)...")
    t_eval.delete_item(
        Key={'id_alumno': 'ALU-001', 'codigo_modulo': 'PROG'},
        ConditionExpression=Attr('nota_numerica').lt(Decimal('6.0'))
    )
    total_ev_despues = t_eval.scan(Select='COUNT')['Count']
    print(f"  [✓] BORRADO CONFIRMADO: Conteo en Evaluaciones: {total_ev_antes} -> {total_ev_despues}")

    # 8.3 Alumnos: Consultar primero vía Índice Global 'RiesgoScoreIndex' y borrar condicionalmente
    subseccion("8.3. Alumnos: Localizar vía GSI 'RiesgoScoreIndex' (nivel='BAJO' y score < 0.25) y borrar si faltas <= 3")
    total_al_antes = t_alumnos.scan(Select='COUNT')['Count']
    candidatos_gsi = t_alumnos.query(
        IndexName='RiesgoScoreIndex',
        KeyConditionExpression=Key('nivel_riesgo').eq('BAJO') & Key('score_abandono').lt(Decimal('0.25'))
    ).get('Items', [])
    print(f"  [*] Candidatos localizados mediante el Índice Global: {len(candidatos_gsi)}")

    eliminados = 0
    for cand in candidatos_gsi:
        try:
            t_alumnos.delete_item(
                Key={'id_alumno': cand['id_alumno']},
                ConditionExpression=Attr('faltas').lte(3)
            )
            eliminados += 1
            print(f"      -> [✓] Eliminado {cand['id_alumno']} ({cand['nombre']}) | Score: {cand['score_abandono']} | Faltas: {cand['faltas']}")
        except ClientError:
            print(f"      -> [!] Omitido {cand['id_alumno']} (faltas > 3)")

    total_al_despues = t_alumnos.scan(Select='COUNT')['Count']
    print(f"  [✓] Resumen Alumnos tras borrado condicional vía GSI: {total_al_antes} -> {total_al_despues} (-{eliminados} registros)")


# ==============================================================================
# 9. CONSULTAS CON VARIOS FILTROS APLICADOS EN CADA TABLA
# ==============================================================================
def consulta_varios_filtros():
    banner_fase(9, "CONSULTAS CON MÚLTIPLES FILTROS COMBINADOS (OPERADOR &)")

    # 9.1 Cursos
    subseccion("9.1. Cursos: grado == 'Superior' AND plazas >= 30")
    res_c = dynamodb.Table('EduSuccess_Cursos').scan(
        FilterExpression=Attr('grado').eq('Superior') & Attr('plazas').gte(30)
    ).get('Items', [])
    print(f"  [✓] Coincidencias: {len(res_c)}")
    imprimir_tabla_resultados(res_c, ['id_curso', 'nombre_ciclo', 'grado', 'turno', 'plazas'])

    # 9.2 Evaluaciones
    subseccion("9.2. Evaluaciones: trimestre == 1 AND codigo_modulo == 'BD' AND nota_numerica >= 7.0")
    res_e = dynamodb.Table('EduSuccess_Evaluaciones').scan(
        FilterExpression=Attr('trimestre').eq(1) & Attr('codigo_modulo').eq('BD') & Attr('nota_numerica').gte(Decimal('7.0'))
    ).get('Items', [])
    print(f"  [✓] Coincidencias: {len(res_e)}")
    imprimir_tabla_resultados(res_e, ['id_alumno', 'codigo_modulo', 'nombre_modulo', 'nota_numerica', 'trimestre'])

    # 9.3 Alumnos
    subseccion("9.3. Alumnos: id_curso == 'CUR-01' AND nivel_riesgo == 'ALTO' AND faltas >= 10")
    res_a = dynamodb.Table('EduSuccess_Alumnos').scan(
        FilterExpression=Attr('id_curso').eq('CUR-01') & Attr('nivel_riesgo').eq('ALTO') & Attr('faltas').gte(10)
    ).get('Items', [])
    print(f"  [✓] Coincidencias: {len(res_a)}")
    imprimir_tabla_resultados(res_a, ['id_alumno', 'nombre', 'id_curso', 'nivel_riesgo', 'score_abandono', 'faltas'])


# ==============================================================================
# 10. UTILIZAR PARTIQL STATEMENT EN CADA TABLA
# ==============================================================================
def ejecutar_partiql():
    banner_fase(10, "EJECUCIÓN DE SENTENCIAS PARTIQL EN LAS 3 TABLAS")

    # 10.1 PartiQL sobre EduSuccess_Cursos
    subseccion("10.1. PartiQL en 'EduSuccess_Cursos'")
    q1 = """SELECT id_curso, nombre_ciclo, plazas FROM "EduSuccess_Cursos" WHERE grado = 'Superior'"""
    print(f"  SQL/PartiQL > {q1}")
    r1 = client.execute_statement(Statement=q1).get('Items', [])
    print(f"  [✓] Resultados devueltos ({len(r1)} filas):")
    for row in r1:
        print(f"      {row}")

    # 10.2 PartiQL sobre EduSuccess_Evaluaciones
    subseccion("10.2. PartiQL en 'EduSuccess_Evaluaciones'")
    q2 = """SELECT id_alumno, codigo_modulo, nota_numerica FROM "EduSuccess_Evaluaciones" WHERE nota_numerica >= 9.0"""
    print(f"  SQL/PartiQL > {q2}")
    r2 = client.execute_statement(Statement=q2).get('Items', [])
    print(f"  [✓] Resultados devueltos ({len(r2)} filas - mostrando primeras 5):")
    for row in r2[:5]:
        print(f"      {row}")

    # 10.3 PartiQL sobre el Índice Global de EduSuccess_Alumnos
    subseccion("10.3. PartiQL en 'EduSuccess_Alumnos' atacando el Índice Global 'RiesgoScoreIndex'")
    q3 = """SELECT id_alumno, nombre, score_abandono FROM "EduSuccess_Alumnos"."RiesgoScoreIndex" WHERE nivel_riesgo = 'ALTO'"""
    print(f"  SQL/PartiQL > {q3}")
    r3 = client.execute_statement(Statement=q3).get('Items', [])
    print(f"  [✓] Resultados devueltos ({len(r3)} filas - mostrando primeras 5):")
    for row in r3[:5]:
        print(f"      {row}")


# ==============================================================================
# ORQUESTADOR PRINCIPAL
# ==============================================================================
def main():
    try:
        auditar_estado_global("ANTES DE INICIAR EL PIPELINE")
        crear_tablas()
        insertar_registros()
        auditar_estado_global("TRAS POBLACIÓN DE DATOS INICIALES")

        obtener_un_registro()
        actualizar_un_registro()
        eliminar_un_registro()
        obtener_todos()

        filtrado_scan_y_gsi()
        eliminacion_condicional()
        consulta_varios_filtros()
        ejecutar_partiql()

        auditar_estado_global("ESTADO FINAL TRAS TODAS LAS OPERACIONES")
        print("\n" + "█" * 80)
        print("  🎉 TODAS LAS OPERACIONES DE DYNAMODB FINALIZARON CON ÉXITO")
        print("█" * 80)
    except Exception as e:
        print(f"\n[❌ ERROR CRÍTICO EN LA EJECUCIÓN]: {e}")


if __name__ == "__main__":
    main()