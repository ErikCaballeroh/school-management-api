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

Crear un archivo `.env` en la raíz del proyecto:

```env
DEBUG=True
SECRET_KEY=your_secret_key
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