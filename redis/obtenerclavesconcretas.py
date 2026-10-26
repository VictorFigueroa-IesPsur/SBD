import redis

conexionRedis = redis.ConnectionPool(host='localhost', port=6379, db=0,decode_responses=True)
baseDatosRedis = redis.Redis(connection_pool=conexionRedis)

baseDatosRedis.set("comic_1","New Fantasy Spiderman")
baseDatosRedis.set("comic_2","Wolverine")

#El patrón puede ir acompañado por:
#*  -> Cualquier número de caracteres o ninguno
#?  -> Un Carácter
#[]  -> Que contenga los caracteres dentro de los corchetes

print("Los Libros:")
for clave in baseDatosRedis.scan_iter('libro*'):
    print(clave,": ", baseDatosRedis.get(clave))


print("Los Comics:")
for clave in baseDatosRedis.scan_iter('comic*'):
    print(clave,": ", baseDatosRedis.get(clave))

baseDatosRedis.close()