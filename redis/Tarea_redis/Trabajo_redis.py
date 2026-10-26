import redis
from redis.commands.json.path import Path
from redis.commands.search.field import TextField, NumericField, TagField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query
import redis.commands.search.aggregation as aggregations
import redis.commands.search.reducers as reducers


conexionRedis = redis.ConnectionPool(host='localhost', port=6379, db=0,decode_responses=True)
baseDatosRedis = redis.Redis(connection_pool=conexionRedis)

#1- Crear registros clave-valor(0.25 puntos)
print("Ejercicio 1 : Crear registros clave-valor")
baseDatosRedis.set('Centro_1','IES Poligono Sur')
baseDatosRedis.set('Centro_2','IES Galileo Galilei')
baseDatosRedis.set('Centro_3','IES Maria Galiana')
baseDatosRedis.set('Centro_4','IES Mariana de Pineda')
baseDatosRedis.set('Centro_5','CEIP Gloria Fuertes')
baseDatosRedis.set('Centro_6','IES Los Salesianos')
baseDatosRedis.set('Centro_7','IES Escolapios')
print("Registros creados.")
print("")
print("==================")
print("")
#2 - Obtener y mostrar el número de claves registradas (0.25 puntos)
print("Ejercicio 2 : Obtener y mostrar el número de claves registradas ")
claves= baseDatosRedis.keys()
print(f"{len(claves)}")
print("")
print("==================")
print("")

#3 - Obtener y mostrar un registro en base a una clave (0.25 puntos)
print("Ejercicio 3 : Obtener y mostrar un registro en base a una clave ")
print(baseDatosRedis.get("Centro_2"))
print("")
print("==================")
print("")

#4 - Actualizar el valor de una clave y mostrar el nuevo valor(0.25 puntos)
print("Ejercicio 4 : Actualizar el valor de una clave y mostrar ")
baseDatosRedis.set('Centro_2', 'IES Punta del Verde')
print(baseDatosRedis.get("Centro_2"))
print("")
print("==================")
print("")

#5 - Eliminar una clave-valor y mostrar la clave y el valor eliminado(0.25 puntos)
print("Ejercicio 5 : Eliminar una clave-valor y mostrar la clave ")
baseDatosRedis.delete("Centro_2")
print(baseDatosRedis.get("Centro_2"))
print("")
print("==================")
print("")

#6 - Obtener y mostrar todas las claves guardadas (0.25 puntos)
print("Ejercicio 6 : Obtener y mostrar todas las claves guardadas ")

claves=baseDatosRedis.keys()

for clave in claves:
    print(clave)

print("")
print("==================")
print("")

#7 - Obtener y mostrar todos los valores guardados(0.25 puntos)
print("Ejercicio 7 : Obtener y mostrar todos los valores guardados ")
claves=baseDatosRedis.keys()

for clave in claves:
    print(clave,":",baseDatosRedis.get(clave))

print("")
print("==================")
print("")


#8 - Obtener y mostrar varios registros con una clave con un patrón en común usando * (0.5 puntos)
print("Ejercicio 8 : Obtener y mostrar varios registros con una clave con un patrón en común usando * ")
print("Centros: ")
print("==========")
for clave in baseDatosRedis.scan_iter('Centro*'):
    print(clave,": ", baseDatosRedis.get(clave))
print("")
print("==================")
print("")
#9 - Obtener y mostrar varios registros con una clave con un patrón en común usando [] (0.5 puntos)
print("Ejercicio 9 : Obtener y mostrar varios registros con una clave con un patrón en común usando []  ")
print("Centros: ")
print("==========")
for clave in baseDatosRedis.keys('Centro_[13467]'):
    print(clave,": ", baseDatosRedis.get(clave))
print("")
print("==================")
print("")

#10 - Obtener y mostrar varios registros con una clave con un patrón en común usando ? (0.5 puntos)
print("Ejercicio 10 : Obtener y mostrar varios registros con una clave con un patrón en común usando ? ")
print("Centros: ")
print("==========")
for clave in baseDatosRedis.keys('Centro_?'):
    print(clave,": ", baseDatosRedis.get(clave))
print("")
print("==================")
print("")

#11 - Obtener y mostrar varios registros y filtrarlos por un valor en concreto. (0.5 puntos)
print("Ejercicio 10 : Obtener y mostrar varios registros con una clave con un patrón en común usando ? ")

print("")
print("==================")
print("")
#12 - Actualizar una serie de registros en base a un filtro (por ejemplo aumentar su valor en 1 )(0.5 puntos)
print("Ejercicio 12 : Actualizar una serie de registros en base a un filtro")
for c in baseDatosRedis.keys('Centro_*'):
    val = baseDatosRedis.get(c)
    if "IES" in val:
        baseDatosRedis.set(c, f"[Instituto] {val}")
        print(f"Actualizado {c} -> {baseDatosRedis.get(c)}")
print("")
print("==================")
print("")
#13 - Eliminar una serie de registros en base a un filtro (0.5 puntos)
print("Ejercicio 13 : Eliminar una serie de registros en base a un filtro")
print("Creamos unos registros para borrarlos (Ej: Clave = Edificio)")
print("")
baseDatosRedis.set('Edificio_1', 'Edificio España')
baseDatosRedis.set('Edificio_2', 'Edificio San Marino')
baseDatosRedis.set('Edificio_3', 'Edificio Calasanz')

print("Claves antes de eliminar registros")
print(baseDatosRedis.keys())

print("")
print("Eliminando registros por filtro (Clave Edificio)")
for clave in baseDatosRedis.keys('Edificio_*'):
    baseDatosRedis.delete(clave)
    print(f"eliminando: {clave}")
print("")
print("Claves despues de eliminar registros")
print(baseDatosRedis.keys())

print("")
print("==================")
print("")
#14 - Crear una estructura en JSON de array de los datos que vayais a almacenar(0.5 puntos)
print("Ejercicio 14 : Crear una estructura en JSON de array de los datos")
print("")
print("Creamos esquema en JSON")
esquema = (
    TextField("$.nombre", as_name="nombre"),
    TagField("$.centro", as_name="centro"),
    NumericField("$.edad", as_name="edad")
)
if "indice:alumnos" not in baseDatosRedis.execute_command("FT._LIST"):
    baseDatosRedis.ft("indice:alumnos").create_index(
        esquema,
        definition=IndexDefinition(
            prefix=["alumnos:"], index_type=IndexType.JSON
        )
    )
    print("Esquema JSON creado")
else:
    print("El índice indice:alumnos ya existe")

print("Añadimos registros al JSON")
alumno1 = {
    "nombre": "Juanjo Lopez",
    "centro": "IES Poligono Sur",
    "edad": 15,
}

alumno2 = {
    "nombre": "Isabel Gonzalez",
    "centro": "IES Galileo Galilei",
    "edad": 13,
}

alumno3 = {
    "nombre": "Maria del Carmen Pascual",
    "centro": "IES Los Salesianos",
    "edad": 16,
}

alumno4 = {
    "nombre": "Jose Maria Rodriguez",
    "centro": "IES Los Salesianos",
    "edad": 16,
}
alumno1Set = baseDatosRedis.json().set("alumnos:1", Path.root_path(), alumno1)
alumno2Set = baseDatosRedis.json().set("alumnos:2", Path.root_path(), alumno2)
alumno3Set = baseDatosRedis.json().set("alumnos:3", Path.root_path(), alumno3)
alumno4Set = baseDatosRedis.json().set("alumnos:4", Path.root_path(), alumno4)

print("Registros creados")
print("")
print("==================")
print("")
#15 - Realizar un filtro por cada atributo de la estructura JSON anterior (0.5 puntos)


agrup_edad = baseDatosRedis.ft("indice:alumnos").search(
    Query("@edad:[16 30]")
)
agrup_centro = aggregations.AggregateRequest("*").group_by(
    '@centro', reducers.count().alias('count')
)

agrup_nombre = baseDatosRedis.ft("indice:alumnos").search(
    Query("@nombre:Juanjo Lopez")
)
resultado = baseDatosRedis.ft("indice:alumnos").aggregate(agrup_centro).rows
print("")
print("Agrupamos por Centro")
print(resultado)
print("")
print("Agrupamos por Edad [16 30]")
print(agrup_edad)
print("")
print("Agrupamos por nombre (Juanjo)")
print(agrup_nombre)

#16 - Crear una lista en Redis (0.25 puntos)
print("Ejercicio 16 : Crear una lista en Redis")
baseDatosRedis.delete("lista_alumnos")  # Limpiar la lista si ya existía

baseDatosRedis.lpush("alumnos:discap", "auditiva:1") 
baseDatosRedis.lpush("alumnos:discap", "verbal-auditiva:2")
baseDatosRedis.lpush("alumnos:discap", "mental:3")
baseDatosRedis.lpush("alumnos:discap", "visual:4")

print("Lista creada exitosamente.")
print(
    baseDatosRedis.lrange("alumnos:discap",0,-1)
)
print("")
print("==================")
print("")
#17 - Obtener elementos de una lista con un filtro en concreto(0.5 puntos)


#18 - Crea datos con índices, definiendo un esquema de al menos tres campos (0.5 puntos)


#19 - Realiza una búsqueda con índices en base a un campo(0.5 puntos)


#20 - Realiza un group  by usando los índices(0.5 puntos)