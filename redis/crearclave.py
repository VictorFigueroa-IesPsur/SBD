import redis

conexionRedis = redis.ConnectionPool(host='localhost', port=6379, db=0,decode_responses=True)
baseDatosRedis = redis.Redis(connection_pool=conexionRedis)

#Crear registros

baseDatosRedis.set('libro_1', 'Quijote')
baseDatosRedis.set('libro_2', 'Hamlet', ex=10) # ex= tiempo de vida
baseDatosRedis.set('juanito','lererer')
baseDatosRedis.set('libro_3', 'Pepe el de los palotes')
baseDatosRedis.set('libro_4', 'El arbol de la vida')
baseDatosRedis.set('libro_5', 'El lazarillo de Tórmes')
baseDatosRedis.set('libro_6', 'Los Pilares de la tierra')
baseDatosRedis.set('libro_7', 'Una corte de Rosas y Espinas')

#Actualizar

baseDatosRedis.set("libro_1","El señor de los anillos")

baseDatosRedis.close()