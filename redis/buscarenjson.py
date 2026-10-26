import redis

conexionRedis = redis.ConnectionPool(host='localhost', port=6379, db=0,decode_responses=True)
baseDatosRedis = redis.Redis(connection_pool=conexionRedis)

res1= baseDatosRedis.json().get("usuarios_array",'$[?(@.edad>50)]')
res2= baseDatosRedis.json().get("usuarios_array",'$[?(@.nombre == "Pepe")]')

print(res1)
print(res2)