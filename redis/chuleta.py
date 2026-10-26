import redis
conexionRedis = redis.ConnectionPool(host='localhost', port=6379, db=0,decode_responses=True)
baseDatosRedis = redis.Redis(connection_pool=conexionRedis)

#Crear registros

baseDatosRedis.set('libro_1', 'Quijote')
baseDatosRedis.set('libro_2', 'Hamlet', ex=10) # ex= tiempo de vida

#Obtener valores

baseDatosRedis.get("libro_1") # en binario
baseDatosRedis.get("libro_1").decode("utf-8") # Obtener en string
baseDatosRedis.get("libro_2") #estara vacio

#Actualizar valores

baseDatosRedis.set("libro_1","El señor de los anillos") #lanzamos otro set

#Eliminar Claves

baseDatosRedis.delete("libro_1")
baseDatosRedis.delete("libro_2")

#Obtener todas las claves

claves = baseDatosRedis.keys()

# Si queremos mostrar todos los valores
for clave in claves:
    print('Clave:', clave , ' y Valor: ', baseDatosRedis.get(clave))
