import mysql.connector
import psycopg2

# DDL compatible con sintaxis MySQL y MariaDB
DDL_MYSQL_MARIADB = """
CREATE TABLE IF NOT EXISTS Cursos (
    id_curso INT AUTO_INCREMENT PRIMARY KEY,
    nombre_ciclo VARCHAR(100) NOT NULL,
    grado VARCHAR(20) NOT NULL,
    curso_escolar VARCHAR(9) NOT NULL,
    turno VARCHAR(15) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Alumnos (
    id_alumno INT AUTO_INCREMENT PRIMARY KEY,
    dni VARCHAR(9) UNIQUE NOT NULL,
    nombre VARCHAR(50) NOT NULL,
    apellidos VARCHAR(100) NOT NULL,
    fecha_nacimiento DATE NOT NULL,
    email VARCHAR(100) NOT NULL,
    telefono VARCHAR(15),
    id_curso INT,
    FOREIGN KEY (id_curso) REFERENCES Cursos(id_curso) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Profesores (
    id_profesor INT AUTO_INCREMENT PRIMARY KEY,
    dni VARCHAR(9) UNIQUE NOT NULL,
    nombre VARCHAR(50) NOT NULL,
    apellidos VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    departamento VARCHAR(50) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Modulos (
    id_modulo INT AUTO_INCREMENT PRIMARY KEY,
    codigo_oficial VARCHAR(10) NOT NULL,
    nombre_modulo VARCHAR(100) NOT NULL,
    horas_totales INT NOT NULL,
    id_curso INT,
    FOREIGN KEY (id_curso) REFERENCES Cursos(id_curso) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Imparticion_Docente (
    id_imparticion INT AUTO_INCREMENT PRIMARY KEY,
    id_profesor INT,
    id_modulo INT,
    rol_tutor BOOLEAN DEFAULT FALSE,
    curso_academico VARCHAR(9) NOT NULL,
    FOREIGN KEY (id_profesor) REFERENCES Profesores(id_profesor) ON DELETE CASCADE,
    FOREIGN KEY (id_modulo) REFERENCES Modulos(id_modulo) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Tornos_Acceso (
    id_torno INT AUTO_INCREMENT PRIMARY KEY,
    ubicacion VARCHAR(50) NOT NULL,
    ip_dispositivo VARCHAR(15) NOT NULL,
    activo BOOLEAN DEFAULT TRUE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Registros_Accesos (
    id_acceso INT AUTO_INCREMENT PRIMARY KEY,
    id_alumno INT,
    id_torno INT,
    fecha_hora DATETIME NOT NULL,
    tipo_evento VARCHAR(10) NOT NULL,
    FOREIGN KEY (id_alumno) REFERENCES Alumnos(id_alumno) ON DELETE CASCADE,
    FOREIGN KEY (id_torno) REFERENCES Tornos_Acceso(id_torno) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Partes_Asistencia (
    id_asistencia INT AUTO_INCREMENT PRIMARY KEY,
    id_alumno INT,
    id_modulo INT,
    fecha DATE NOT NULL,
    hora_tramo INT NOT NULL,
    estado VARCHAR(15) NOT NULL,
    FOREIGN KEY (id_alumno) REFERENCES Alumnos(id_alumno) ON DELETE CASCADE,
    FOREIGN KEY (id_modulo) REFERENCES Modulos(id_modulo) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Evaluaciones_Notas (
    id_evaluacion INT AUTO_INCREMENT PRIMARY KEY,
    id_alumno INT,
    id_modulo INT,
    trimestre INT NOT NULL,
    nota_numerica DECIMAL(4,2) NOT NULL,
    convocatoria VARCHAR(15) NOT NULL,
    FOREIGN KEY (id_alumno) REFERENCES Alumnos(id_alumno) ON DELETE CASCADE,
    FOREIGN KEY (id_modulo) REFERENCES Modulos(id_modulo) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Predicciones_Riesgo (
    id_prediccion INT AUTO_INCREMENT PRIMARY KEY,
    id_alumno INT,
    fecha_calculo DATE NOT NULL,
    score_abandono DECIMAL(4,2) NOT NULL,
    nivel_riesgo VARCHAR(10) NOT NULL,
    factor_principal VARCHAR(50),
    FOREIGN KEY (id_alumno) REFERENCES Alumnos(id_alumno) ON DELETE CASCADE
) ENGINE=InnoDB;
"""

# DDL compatible con sintaxis PostgreSQL
DDL_POSTGRESQL = """
CREATE TABLE IF NOT EXISTS Cursos (
    id_curso SERIAL PRIMARY KEY,
    nombre_ciclo VARCHAR(100) NOT NULL,
    grado VARCHAR(20) NOT NULL,
    curso_escolar VARCHAR(9) NOT NULL,
    turno VARCHAR(15) NOT NULL
);

CREATE TABLE IF NOT EXISTS Alumnos (
    id_alumno SERIAL PRIMARY KEY,
    dni VARCHAR(9) UNIQUE NOT NULL,
    nombre VARCHAR(50) NOT NULL,
    apellidos VARCHAR(100) NOT NULL,
    fecha_nacimiento DATE NOT NULL,
    email VARCHAR(100) NOT NULL,
    telefono VARCHAR(15),
    id_curso INT REFERENCES Cursos(id_curso) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Profesores (
    id_profesor SERIAL PRIMARY KEY,
    dni VARCHAR(9) UNIQUE NOT NULL,
    nombre VARCHAR(50) NOT NULL,
    apellidos VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    departamento VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS Modulos (
    id_modulo SERIAL PRIMARY KEY,
    codigo_oficial VARCHAR(10) NOT NULL,
    nombre_modulo VARCHAR(100) NOT NULL,
    horas_totales INT NOT NULL,
    id_curso INT REFERENCES Cursos(id_curso) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Imparticion_Docente (
    id_imparticion SERIAL PRIMARY KEY,
    id_profesor INT REFERENCES Profesores(id_profesor) ON DELETE CASCADE,
    id_modulo INT REFERENCES Modulos(id_modulo) ON DELETE CASCADE,
    rol_tutor BOOLEAN DEFAULT FALSE,
    curso_academico VARCHAR(9) NOT NULL
);

CREATE TABLE IF NOT EXISTS Tornos_Acceso (
    id_torno SERIAL PRIMARY KEY,
    ubicacion VARCHAR(50) NOT NULL,
    ip_dispositivo VARCHAR(15) NOT NULL,
    activo BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS Registros_Accesos (
    id_acceso SERIAL PRIMARY KEY,
    id_alumno INT REFERENCES Alumnos(id_alumno) ON DELETE CASCADE,
    id_torno INT REFERENCES Tornos_Acceso(id_torno) ON DELETE CASCADE,
    fecha_hora TIMESTAMP NOT NULL,
    tipo_evento VARCHAR(10) NOT NULL
);

CREATE TABLE IF NOT EXISTS Partes_Asistencia (
    id_asistencia SERIAL PRIMARY KEY,
    id_alumno INT REFERENCES Alumnos(id_alumno) ON DELETE CASCADE,
    id_modulo INT REFERENCES Modulos(id_modulo) ON DELETE CASCADE,
    fecha DATE NOT NULL,
    hora_tramo INT NOT NULL,
    estado VARCHAR(15) NOT NULL
);

CREATE TABLE IF NOT EXISTS Evaluaciones_Notas (
    id_evaluacion SERIAL PRIMARY KEY,
    id_alumno INT REFERENCES Alumnos(id_alumno) ON DELETE CASCADE,
    id_modulo INT REFERENCES Modulos(id_modulo) ON DELETE CASCADE,
    trimestre INT NOT NULL,
    nota_numerica DECIMAL(4,2) NOT NULL,
    convocatoria VARCHAR(15) NOT NULL
);

CREATE TABLE IF NOT EXISTS Predicciones_Riesgo (
    id_prediccion SERIAL PRIMARY KEY,
    id_alumno INT REFERENCES Alumnos(id_alumno) ON DELETE CASCADE,
    fecha_calculo DATE NOT NULL,
    score_abandono DECIMAL(4,2) NOT NULL,
    nivel_riesgo VARCHAR(10) NOT NULL,
    factor_principal VARCHAR(50)
);
"""

def execute_statements(conn, ddl_statements, is_postgres=False):
    cursor = conn.cursor()
    if is_postgres:
        cursor.execute(ddl_statements)
    else:
        for statement in ddl_statements.split(';'):
            stmt = statement.strip()
            if stmt:
                cursor.execute(stmt)
    conn.commit()
    cursor.close()
    conn.close()

def main():
    print("Creando tablas en MySQL...")
    conn_mysql = mysql.connector.connect(
        host="localhost", port=3306, user="root", password="root", database="edusuccess_db"
    )
    execute_statements(conn_mysql, DDL_MYSQL_MARIADB)

    print("Creando tablas en PostgreSQL...")
    conn_pg = psycopg2.connect(
        host="localhost", port=5432, user="root", password="root", dbname="edusuccess_db"
    )
    execute_statements(conn_pg, DDL_POSTGRESQL, is_postgres=True)

    print("Creando tablas en MariaDB...")
    conn_mariadb = mysql.connector.connect(
        host="localhost", port=3307, user="root", password="root", database="edusuccess_db"
    )
    execute_statements(conn_mariadb, DDL_MYSQL_MARIADB)

    print("Creación de tablas finalizada en las tres bases de datos.")

if __name__ == "__main__":
    main()