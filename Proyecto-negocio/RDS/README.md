# 🎓 EduSuccess - RDS Data Pipeline & Analytics

![AWS RDS](https://img.shields.io/badge/AWS-RDS%20MySQL-orange?logo=amazon-aws)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)
![Faker](https://img.shields.io/badge/Data-Faker-green)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

Este repositorio contiene la arquitectura, los scripts de población sintética y las consultas analíticas en formato JSON para el sistema de gestión académica y prevención de abandono escolar **EduSuccess**, desplegado en **AWS RDS (MySQL)**.

---

## 📌 Tabla de Contenidos

- [Requisitos Previos](#-requisitos-previos)
- [Obtención de Credenciales e Información de AWS RDS](#-obtención-de-credenciales-e-información-de-aws-rds)
- [Configuración del Archivo `.env`](#-configuración-del-archivo-env)
- [Instalación y Configuración](#-instalación-y-configuración)
- [Estructura de la Base de Datos](#-estructura-de-la-base-de-datos)
- [Uso y Ejecución](#-uso-y-ejecución)
- [Consultas Analíticas Generadas](#-consultas-analíticas-generadas)
- [Resolución de Problemas](#-resolución-de-problemas)

---

## 📋 Requisitos Previos

- **Python 3.8+** instalado en tu sistema local.
- Una cuenta activa en **AWS** con una instancia de **Amazon RDS (MySQL)** desplegada.
- Permisos de red para conectar de forma remota a la base de datos (Security Group configurado).

---

## 🔎 Obtención de Credenciales e Información de AWS RDS

Para configurar las variables de entorno correctamente, sigue estos pasos en la Consola de AWS:

### 1. Datos de Conexión a la Base de Datos (RDS)
1. Inicia sesión en la **Consola de AWS** y navega hasta el servicio **RDS**.
2. En el menú lateral, haz clic en **Databases** y selecciona tu instancia (ej. `EduSuccessDB`).
3. En la sección **Connectivity & security**:
   - **Endpoint:** Copia la URL (ej. `edusuccessdb.cr3mvpcsnodl.us-east-1.rds.amazonaws.com`). Corresponde a `DB_ENDPOINT`.
   - **Port:** Copia el puerto (normalmente `3306`). Corresponde a `DB_PORT`.
4. En la pestaña **Configuration**:
   - **Master username:** Copia el usuario administrador (ej. `admin`). Corresponde a `DB_USER`.
   - **DB Name:** El nombre asignado a la base de datos inicial (ej. `EduSuccess`). Corresponde a `DB_NAME`.
   - **Password:** La contraseña configurada al crear la instancia (corresponde a `DB_PASSWORD`).

### 2. Credenciales de Claves AWS (IAM / AWS Academy)
Si utilizas credenciales temporales (como **AWS Academy / Learner Labs**):
1. En el panel de AWS Academy, haz clic en **AWS Details**.
2. Junto a **AWS CLI**, haz clic en **Show**.
3. Copia los valores correspondientes para tu `.env`:
   - `aws_access_key_id` $\rightarrow$ `ACCESS_KEY`
   - `aws_secret_access_key` $\rightarrow$ `SECRET_KEY`
   - `aws_session_token` $\rightarrow$ `SESSION_TOKEN`

---

## 🔑 Configuración del Archivo `.env`

Crea un archivo llamado `.env` en la raíz del proyecto basándote en la siguiente estructura:

```env
# AWS Credentials
ACCESS_KEY="TU_ACCESS_KEY_AQUI"
SECRET_KEY="TU_SECRET_KEY_AQUI"
SESSION_TOKEN="TU_SESSION_TOKEN_AQUI"
REGION="us-east-1"

# RDS Database Configuration
DB_USER="admin"
DB_PASSWORD="TuPasswordSeguro123"
DB_NAME="EduSuccess"
DB_INSTANCE_ID="EduSuccessDB"
DB_ENDPOINT="edusuccessdb.cr3mvpcsnodl.us-east-1.rds.amazonaws.com"
DB_PORT=3306
```

---

## 🚀 Instalación y Configuración

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/tu-usuario/edusuccess-rds.git
   cd edusuccess-rds
   ```

2. **Crear y activar un entorno virtual:**
   ```bash
   # Linux/macOS
   python3 -m venv venv
   source venv/bin/activate

   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Instalar dependencias:**
   ```bash
   pip install python-dotenv mysql-connector-python psycopg2-binary faker
   ```

---

## 🗄️ Estructura de la Base de Datos

El esquema relacional cuenta con las siguientes tablas interconectadas:

- **Entidades Principales:** `Cursos`, `Profesores`, `Tornos_Acceso`
- **Entidades Académicas:** `Alumnos`, `Modulos`
- **Relaciones e Históricos:** `Imparticion_Docente`, `Registros_Accesos`, `Partes_Asistencia`, `Evaluaciones_Notas`, `Predicciones_Riesgo`

---

## 🔄 Uso y Ejecución

### 1. Poblado de Datos Sintéticos
Para truncar las tablas e insertar registros sintéticos aleatorios generados con `Faker`:

```bash
python Insertardatos.py
```

### 2. Ejecución de Consultas Analíticas y Exportación a JSON
Para ejecutar las 3 consultas analíticas en RDS y guardar los resultados en archivos JSON independientes:

```bash
python consultas_json.py
```

**Archivos JSON generados:**
- 📄 `consulta_1_alumnos_riesgo.json`: Alumnos en nivel de riesgo ALTO o MEDIO.
- 📄 `consulta_2_promedio_notas.json`: Estadísticas de rendimiento y notas medias por módulo.
- 📄 `consulta_3_resumen_asistencias.json`: Balance de presencias, retrasos y faltas de asistencia del Top 10 de alumnos.

---

## 🛠️ Resolución de Problemas

- **Error de Conexión `Can't connect to MySQL server`:**
  - Verifica que la opción **Publicly Accessible** esté activada (**Yes**) en las opciones de RDS.
  - Asegúrate de agregar tu dirección IP actual a las **Inbound Rules** (Puerto `3306`) del **VPC Security Group** asociado a tu instancia RDS.
- **Error `Table doesn't exist`:**
  - Asegúrate de haber ejecutado los scripts de creación de tablas (`CREATE TABLE`) en la base de datos `EduSuccess` antes de ejecutar la población de datos.