# 📚 Sistema de Gestión Escolar API

Backend desarrollado con Django y Django REST Framework para la gestión académica de una institución educativa.

## 🚀 Tecnologías

* Python
* Django
* Django REST Framework
* SQLite (desarrollo)
* PostgreSQL (producción)

---

## 📦 Requisitos

Antes de comenzar, asegúrate de tener instalado:

* Python 3.10 o superior
* Git

---

## 📥 Clonar el repositorio

```bash
git clone https://github.com/ErikCaballeroh/school-management-api.git
cd school-management-api
```

---

## 🧪 Crear entorno virtual

```bash
python -m venv venv
```

### Activar entorno virtual

#### Git Bash / Linux / Mac:

```bash
source venv/Scripts/activate
```

#### CMD:

```bash
venv\Scripts\activate
```

#### PowerShell:

```bash
venv\Scripts\Activate.ps1
```

---

## 📦 Instalar dependencias

```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuración del proyecto

### 1. Variables de entorno

Crear un archivo `.env` en la raíz del proyecto (puedes copiar el archivo `.env.example` y renombrarlo):

```env
DEBUG=True
SECRET_KEY=tu_secret_key_aqui

# Cloudflare R2 Credentials (para la subida de archivos)
R2_ACCOUNT_ID=tu_account_id_de_cloudflare
R2_ACCESS_KEY_ID=tu_access_key_id
R2_SECRET_ACCESS_KEY=tu_secret_access_key
R2_BUCKET_NAME=nombre_de_tu_bucket
R2_CUSTOM_DOMAIN=https://pub-midominio.r2.dev
```

---

### 2. Base de datos

Por defecto, el proyecto usa SQLite (no requiere configuración adicional).

---

## 🗄️ Migraciones

Aplicar migraciones para crear la base de datos:

```bash
python manage.py makemigrations
python manage.py migrate
```

---

## 👤 Crear superusuario

```bash
python manage.py createsuperuser
```

Sigue las instrucciones para crear el usuario administrador.

---

## ▶️ Ejecutar servidor

```bash
python manage.py runserver
```

El servidor estará disponible en:

```
http://127.0.0.1:8000/
```

---

## 🔐 Panel de administración

Accede al panel en:

```
http://127.0.0.1:8000/admin
```

Inicia sesión con el superusuario creado.

---

## 📁 Estructura del proyecto

```
school-management-api/
│
├── config/        # Configuración global del proyecto
├── users/         # Usuarios, autenticación y roles
├── academic/      # Materias, grupos, tareas
├── reports/       # Reportes y procesamiento
├── manage.py
└── requirements.txt
```

---

## 🔑 Autenticación

El proyecto utiliza **JWT (JSON Web Tokens)** para la autenticación. Todas las rutas de la API (excepto la obtención de tokens) requieren un token válido en el header:

```
Authorization: Bearer <access_token>
```

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/token/` | Obtener access y refresh token (login) |
| POST | `/api/token/refresh/` | Refrescar el access token |

### Ejemplo de login

```json
POST /api/token/
{
    "email": "usuario@ejemplo.com",
    "password": "tu_contraseña"
}
```

**Respuesta:**

```json
{
    "access": "eyJ...",
    "refresh": "eyJ..."
}
```

---

## 📡 Rutas de la API

### 👤 Usuarios (`/api/users/`)

CRUD completo para la gestión de usuarios.

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/users/` | Listar todos los usuarios |
| POST | `/api/users/` | Crear un nuevo usuario |
| GET | `/api/users/{id}/` | Obtener detalle de un usuario |
| PUT | `/api/users/{id}/` | Actualizar un usuario completo |
| PATCH | `/api/users/{id}/` | Actualizar parcialmente un usuario |
| DELETE | `/api/users/{id}/` | Eliminar un usuario |

**Campos:** `id`, `email`, `nombre`, `rol` (alumno/docente/admin), `matricula`, `activo`, `created_at`

---

### 📅 Ciclos Escolares (`/api/ciclos/`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/ciclos/` | Listar todos los ciclos escolares |
| POST | `/api/ciclos/` | Crear un nuevo ciclo escolar |
| GET | `/api/ciclos/{id}/` | Obtener detalle de un ciclo |
| PUT | `/api/ciclos/{id}/` | Actualizar un ciclo completo |
| PATCH | `/api/ciclos/{id}/` | Actualizar parcialmente un ciclo |
| DELETE | `/api/ciclos/{id}/` | Eliminar un ciclo |

**Campos:** `id`, `nombre`, `fecha_inicio`, `fecha_fin`, `activo`

---

### 📘 Materias (`/api/materias/`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/materias/` | Listar todas las materias |
| POST | `/api/materias/` | Crear una nueva materia |
| GET | `/api/materias/{id}/` | Obtener detalle de una materia |
| PUT | `/api/materias/{id}/` | Actualizar una materia completa |
| PATCH | `/api/materias/{id}/` | Actualizar parcialmente una materia |
| DELETE | `/api/materias/{id}/` | Eliminar una materia |

**Campos:** `id`, `nombre`, `clave`, `ciclo`

---

### 👥 Grupos (`/api/grupos/`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/grupos/` | Listar todos los grupos |
| POST | `/api/grupos/` | Crear un nuevo grupo |
| GET | `/api/grupos/{id}/` | Obtener detalle de un grupo |
| PUT | `/api/grupos/{id}/` | Actualizar un grupo completo |
| PATCH | `/api/grupos/{id}/` | Actualizar parcialmente un grupo |
| DELETE | `/api/grupos/{id}/` | Eliminar un grupo |

**Campos:** `id`, `nombre`, `codigo`, `materia`, `docente`, `ciclo`

---

### 📝 Inscripciones (`/api/inscripciones/`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/inscripciones/` | Listar todas las inscripciones |
| POST | `/api/inscripciones/` | Crear una nueva inscripción |
| GET | `/api/inscripciones/{id}/` | Obtener detalle de una inscripción |
| PUT | `/api/inscripciones/{id}/` | Actualizar una inscripción completa |
| PATCH | `/api/inscripciones/{id}/` | Actualizar parcialmente una inscripción |
| DELETE | `/api/inscripciones/{id}/` | Eliminar una inscripción |

**Campos:** `id`, `alumno`, `grupo`, `materia`, `ciclo`, `fecha_inscripcion`

---

### 📋 Tareas (`/api/tareas/`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/tareas/` | Listar todas las tareas |
| POST | `/api/tareas/` | Crear una nueva tarea |
| GET | `/api/tareas/{id}/` | Obtener detalle de una tarea |
| PUT | `/api/tareas/{id}/` | Actualizar una tarea completa |
| PATCH | `/api/tareas/{id}/` | Actualizar parcialmente una tarea |
| DELETE | `/api/tareas/{id}/` | Eliminar una tarea |

**Campos:** `id`, `titulo`, `descripcion`, `fecha_limite`, `grupo`, `created_at`

---

### 📤 Entregas (`/api/entregas/`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/entregas/` | Listar todas las entregas |
| POST | `/api/entregas/` | Crear una nueva entrega |
| GET | `/api/entregas/{id}/` | Obtener detalle de una entrega |
| PUT | `/api/entregas/{id}/` | Actualizar una entrega completa |
| PATCH | `/api/entregas/{id}/` | Actualizar parcialmente una entrega |
| DELETE | `/api/entregas/{id}/` | Eliminar una entrega |

**Campos:** `id`, `alumno`, `tarea`, `archivo_url`, `video_url`, `nombre_archivo`, `tamano_bytes`, `calificacion`, `comentario`, `fecha_entrega`

---

### 📰 Publicaciones (`/api/publicaciones/`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/publicaciones/` | Listar todas las publicaciones |
| POST | `/api/publicaciones/` | Crear una nueva publicación |
| GET | `/api/publicaciones/{id}/` | Obtener detalle de una publicación |
| PUT | `/api/publicaciones/{id}/` | Actualizar una publicación completa |
| PATCH | `/api/publicaciones/{id}/` | Actualizar parcialmente una publicación |
| DELETE | `/api/publicaciones/{id}/` | Eliminar una publicación |

**Campos:** `id`, `titulo`, `contenido`, `materia`, `autor`, `created_at`

---

### 💬 Comentarios (`/api/comentarios/`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/comentarios/` | Listar todos los comentarios |
| POST | `/api/comentarios/` | Crear un nuevo comentario |
| GET | `/api/comentarios/{id}/` | Obtener detalle de un comentario |
| PUT | `/api/comentarios/{id}/` | Actualizar un comentario completo |
| PATCH | `/api/comentarios/{id}/` | Actualizar parcialmente un comentario |
| DELETE | `/api/comentarios/{id}/` | Eliminar un comentario |

**Campos:** `id`, `contenido`, `publicacion`, `autor`, `created_at`

---

### 📂 Materiales (`/api/materiales/`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/materiales/` | Listar todos los materiales |
| POST | `/api/materiales/` | Crear un nuevo material |
| GET | `/api/materiales/{id}/` | Obtener detalle de un material |
| PUT | `/api/materiales/{id}/` | Actualizar un material completo |
| PATCH | `/api/materiales/{id}/` | Actualizar parcialmente un material |
| DELETE | `/api/materiales/{id}/` | Eliminar un material |

**Campos:** `id`, `titulo`, `descripcion`, `tipo`, `archivo_url`, `grupo`, `autor`, `created_at`

---

### 📎 Subida de Archivos (`/api/upload/`)

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/upload/` | Subir un archivo a Cloudflare R2 |

**Body:** `multipart/form-data` con campo `file`

**Respuesta:**

```json
{
    "url": "https://pub-midominio.r2.dev/archivo.pdf"
}
```

---

### 📊 Reportes PDF con Procesamiento Paralelo (`/api/reports/`)

Rutas para generar reportes en formato PDF. Cada ruta utiliza **procesamiento paralelo** con `ThreadPoolExecutor` para calcular los datos de forma concurrente.

| Método | Ruta | Descripción | Paralelismo |
|--------|------|-------------|-------------|
| GET | `/api/reports/promedio-alumno/{alumno_id}/` | Promedio de un alumno en cada materia | 1 hilo por materia |
| GET | `/api/reports/promedio-grupo/{grupo_id}/` | Promedio de cada alumno de un grupo | 1 hilo por alumno |
| GET | `/api/reports/promedio-materia/{materia_id}/` | Promedio de todos los alumnos en una materia | 1 hilo por grupo |
| GET | `/api/reports/indice-reprobacion/{grupo_id}/` | Índice de reprobación de un grupo | 1 hilo por alumno |

> **Nota:** La calificación mínima aprobatoria es **70**. Cada ruta retorna un archivo PDF descargable.

#### Promedio por Alumno

```
GET /api/reports/promedio-alumno/1/
```

Genera un PDF con el promedio del alumno en **cada una de sus materias** y un promedio general.

#### Promedio por Grupo

```
GET /api/reports/promedio-grupo/1/
```

Genera un PDF con las **calificaciones y promedio de cada alumno** dentro del grupo.

#### Promedio por Materia

```
GET /api/reports/promedio-materia/1/
```

Genera un PDF con el promedio de **todos los alumnos de todos los grupos** de una materia.

#### Índice de Reprobación

```
GET /api/reports/indice-reprobacion/1/
```

Genera un PDF con el **porcentaje de aprobación y reprobación** de un grupo, detallando el estatus de cada alumno.

---

## 🧠 Notas importantes

* Este proyecto utiliza un modelo de usuario personalizado (`users.User`)
* Los roles del sistema son:

  * alumno
  * docente
  * admin
* Los archivos no se almacenan en la base de datos (solo URLs)

---

## 🧹 Archivos ignorados

El proyecto incluye un `.gitignore` con:

```
venv/
__pycache__/
*.pyc
db.sqlite3
.env
```