import redis
conexionRedis = redis.ConnectionPool(host='localhost', port=6379, db=0,decode_responses=True)
baseDatosRedis = redis.Redis(connection_pool=conexionRedis)

res1= baseDatosRedis.json().set("usuarios:1","$",{"nombre":"Jorge","apellido":"Baron","edad":37})
res2= baseDatosRedis.json().set("usuarios:2","$",{"nombre":"Lucia","apellido":"Benitez","edad":24})

#añadir elementos a unj array

baseDatosRedis.json().set("usuarios_array","$",[])

res3=baseDatosRedis.json().arrappend("usuarios_array","$",{"nombre":"Pepe","apellido":"Padilla","edad":32})
res4=baseDatosRedis.json().arrappend("usuarios_array","$",{"nombre":"Pepe","apellido":"Padilla","edad":32})
res5= baseDatosRedis.json().get("usuarios_array","$")
print(res5)