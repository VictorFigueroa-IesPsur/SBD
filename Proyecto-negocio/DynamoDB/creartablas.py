import os
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
client = session.client('dynamodb')

TABLAS = [
    {
        "nombre": "EduSuccess_Cursos",
        "tipo": "Sin índices (Tabla base)",
        "params": {
            "TableName": "EduSuccess_Cursos",
            "AttributeDefinitions": [
                {"AttributeName": "id_curso", "AttributeType": "S"}
            ],
            "KeySchema": [
                {"AttributeName": "id_curso", "KeyType": "HASH"}
            ],
            "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5}
        }
    },
    {
        "nombre": "EduSuccess_Evaluaciones",
        "tipo": "Con Índice Secundario Local (LSI: NotaIndex)",
        "params": {
            "TableName": "EduSuccess_Evaluaciones",
            "AttributeDefinitions": [
                {"AttributeName": "id_alumno", "AttributeType": "S"},
                {"AttributeName": "codigo_modulo", "AttributeType": "S"},
                {"AttributeName": "nota_numerica", "AttributeType": "N"}
            ],
            "KeySchema": [
                {"AttributeName": "id_alumno", "KeyType": "HASH"},
                {"AttributeName": "codigo_modulo", "KeyType": "RANGE"}
            ],
            "LocalSecondaryIndexes": [
                {
                    "IndexName": "NotaIndex",
                    "KeySchema": [
                        {"AttributeName": "id_alumno", "KeyType": "HASH"},
                        {"AttributeName": "nota_numerica", "KeyType": "RANGE"}
                    ],
                    "Projection": {"ProjectionType": "ALL"}
                }
            ],
            "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5}
        }
    },
    {
        "nombre": "EduSuccess_Alumnos",
        "tipo": "Con Índice Secundario Global (GSI: RiesgoScoreIndex)",
        "params": {
            "TableName": "EduSuccess_Alumnos",
            "AttributeDefinitions": [
                {"AttributeName": "id_alumno", "AttributeType": "S"},
                {"AttributeName": "nivel_riesgo", "AttributeType": "S"},
                {"AttributeName": "score_abandono", "AttributeType": "N"}
            ],
            "KeySchema": [
                {"AttributeName": "id_alumno", "KeyType": "HASH"}
            ],
            "GlobalSecondaryIndexes": [
                {
                    "IndexName": "RiesgoScoreIndex",
                    "KeySchema": [
                        {"AttributeName": "nivel_riesgo", "KeyType": "HASH"},
                        {"AttributeName": "score_abandono", "KeyType": "RANGE"}
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5}
                }
            ],
            "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5}
        }
    }
]


def auditar_infraestructura(momento):
    print(f"\n{'=' * 75}")
    print(f" 🔍 AUDITORÍA DE INFRAESTRUCTURA DYNAMODB [{momento}]")
    print(f"{'=' * 75}")
    existentes = client.list_tables().get("TableNames", [])
    print(f"{'TABLA':<26} | {'ESTADO':<10} | {'PK / SK':<22} | {'ÍNDICES'}")
    print("-" * 75)
    for t in TABLAS:
        nombre = t["nombre"]
        if nombre in existentes:
            desc = client.describe_table(TableName=nombre)["Table"]
            estado = desc["TableStatus"]
            ks = "/".join([f"{k['AttributeName']}({k['KeyType'][0]})" for k in desc["KeySchema"]])
            lsi = [i["IndexName"] + "(LSI)" for i in desc.get("LocalSecondaryIndexes", [])]
            gsi = [i["IndexName"] + "(GSI)" for i in desc.get("GlobalSecondaryIndexes", [])]
            indices_str = ", ".join(lsi + gsi) if (lsi or gsi) else "Ninguno"
            print(f"{nombre:<26} | {estado:<10} | {ks:<22} | {indices_str}")
        else:
            print(f"{nombre:<26} | {'NO EXISTE':<10} | {'-':<22} | -")
    print("-" * 75)


def crear_tablas():
    auditar_infraestructura("ANTES DE CREAR TABLAS")
    print("\n[*] Iniciando creación de tablas en AWS DynamoDB...")
    for t in TABLAS:
        nombre = t["nombre"]
        try:
            print(f" -> Creando '{nombre}' [{t['tipo']}]...")
            client.create_table(**t["params"])
            client.get_waiter("table_exists").wait(TableName=nombre)
            print(f"    [OK] '{nombre}' creada y disponible.")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceInUseException":
                print(f"    [AVISO] '{nombre}' ya existe en la cuenta.")
            else:
                raise
    auditar_infraestructura("DESPUÉS DE CREAR TABLAS")


if __name__ == "__main__":
    crear_tablas()
