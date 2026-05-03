# Sistema de Gestión Escolar — API

Backend Django + DRF para la gestión académica de una institución educativa. Incluye los módulos de Alumno, Docente y Administración, generación de reportes con procesamiento paralelo, almacenamiento de archivos en Cloudflare R2 y un stack distribuido (Nginx + Postgres + Redis + 2 backends) para el PIA.

---

## Tabla de contenidos

1. [Cómo correrlo (modo desarrollo)](#cómo-correrlo-modo-desarrollo)
2. [Cómo correrlo (modo distribuido / Docker)](#cómo-correrlo-modo-distribuido--docker)
3. [Variables de entorno](#variables-de-entorno)
4. [Características del PIA: Sistema Distribuido](#características-del-pia-sistema-distribuido)
5. [API: rutas y permisos](#api-rutas-y-permisos)
6. [Política de archivos](#política-de-archivos)
7. [Estructura del proyecto](#estructura-del-proyecto)

---

## Cómo correrlo (modo desarrollo)

Requiere Python 3.10+.

```bash
git clone https://github.com/ErikCaballeroh/school-management-api.git
cd school-management-api

# 1. Entorno virtual
python -m venv venv
source venv/bin/activate            # Linux / Mac
# venv\Scripts\activate              # Windows

# 2. Dependencias
pip install -r requirements.txt

# 3. Variables de entorno (crea un .env en la raíz)
cat > .env <<'EOF'
DEBUG=True
SECRET_KEY=cambia-esta-llave-en-produccion
ALLOWED_HOSTS=*
EOF

# 4. Migraciones + superusuario
python manage.py migrate
python manage.py createsuperuser

# 5. Arrancar
python manage.py runserver
```

API en `http://127.0.0.1:8000/`. Admin en `/admin/`.

---

## Cómo correrlo (modo distribuido / Docker)

Este es el modo que cumple los requisitos del **PIA**: distribución de carga, tolerancia a fallos, escalabilidad. Levanta 2 instancias backend, Nginx como load balancer, Postgres y Redis.

```bash
# 0. Asegúrate de tener Docker Desktop / Docker Engine corriendo

# 1. (Opcional) crea un .env con tu SECRET_KEY y credenciales R2
cat > .env <<'EOF'
SECRET_KEY=cambia-esta-llave-en-produccion
R2_ACCOUNT_ID=tu_account
R2_ACCESS_KEY_ID=tu_key
R2_SECRET_ACCESS_KEY=tu_secret
R2_BUCKET_NAME=tu_bucket
R2_CUSTOM_DOMAIN=https://pub-tu-dominio.r2.dev
EOF

# 2. Levantar todo el stack
docker compose up --build

# La API queda en http://localhost:8080/
```

### Comandos útiles del stack

```bash
# Ver logs en vivo
docker compose logs -f

# Escalar horizontalmente (agregar más instancias)
docker compose up --scale backend1=3

# Probar tolerancia a fallos: matar una instancia
docker compose stop backend1
# Nginx automáticamente enruta al backend2; recupera con:
docker compose start backend1

# Apagar todo
docker compose down

# Apagar y borrar la BD
docker compose down -v
```

### Comprobaciones rápidas

```bash
# Liveness (sin auth, lo usa Nginx)
curl http://localhost:8080/healthz

# Readiness (chequea DB y cache)
curl http://localhost:8080/api/system/health/

# Headers que agrega el middleware
curl -i http://localhost:8080/api/ciclos/
# Verás: X-Request-ID, X-Response-Time-MS, X-Server-Instance: backend1|backend2
```

---

## Variables de entorno

| Variable | Default | Notas |
|---|---|---|
| `SECRET_KEY` | — | **Obligatorio**. ≥32 chars en prod. |
| `DEBUG` | `False` | `True` para desarrollo. |
| `ALLOWED_HOSTS` | `*` | CSV separado por comas. |
| `DB_ENGINE` | `django.db.backends.sqlite3` | Cambia a `postgresql` para Docker. |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | — | Solo necesario con Postgres. |
| `DB_CONN_MAX_AGE` | `60` | Segundos de reuso de conexión (tolerancia a fallos). |
| `CACHE_BACKEND` | `locmem` | `redis` para usar Redis. |
| `REDIS_URL` | `redis://redis:6379/1` | Solo si `CACHE_BACKEND=redis`. |
| `INSTANCE_ID` | hostname | Identifica la instancia en métricas y headers. |
| `GUNICORN_WORKERS` | `3` | Procesos por contenedor. |
| `GUNICORN_THREADS` | `2` | Threads por worker. |
| `R2_ACCOUNT_ID` / `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` / `R2_BUCKET_NAME` / `R2_CUSTOM_DOMAIN` | — | Para subir archivos a Cloudflare R2. |

---

## Características : Sistema Distribuido

| Requisito | Implementación |
|---|---|
| **Monitoreo de Recursos** | App `system/` expone CPU, RAM, disco, latencia DB, métricas de peticiones, estado de circuit breakers. Endpoints `/api/system/health/`, `/metrics/`, `/resources/`, `/info/`. Dashboard React en `/admin/monitoreo`. |
| **Middleware** | `system.middleware`: `RequestIDMiddleware` (X-Request-ID propagado a logs y respuesta), `RequestMetricsMiddleware` (latencia + headers), `HealthCheckBypassMiddleware` (liveness sin tocar DB). |
| **Distribución de peticiones** | Nginx (`docker/nginx.conf`) con `upstream` `least_conn` balanceando entre `backend1` y `backend2`. Cada backend corre Gunicorn multi-worker (3×2 por defecto). |
| **Tolerancia a fallos** | (1) Nginx `proxy_next_upstream` reintenta en otra instancia si una falla; (2) `max_fails=3 fail_timeout=15s` saca instancias enfermas; (3) `system.resilience.CircuitBreaker` + `retry()` para R2 (CLOSED→OPEN→HALF_OPEN); (4) `CONN_MAX_AGE` + `CONN_HEALTH_CHECKS` reabren conexiones DB caídas. |
| **Escalabilidad** | (1) `docker compose --scale backend1=N` agrega instancias; (2) reportes JSON usan `system.parallel.run_parallel` y `@cached_report` (TTL 60s); (3) Redis compartido entre instancias para que el cache funcione across nodes. |

### Endpoints de monitoreo

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/healthz` | Liveness ultra-barato (no toca DB). Lo usa Nginx. |
| GET | `/api/system/health/` | Readiness (DB + cache). |
| GET | `/api/system/metrics/` | Latencias agregadas (avg/p50/p95/p99), top routes, status counts, circuit breakers. |
| GET | `/api/system/resources/` | CPU por core, RAM, disco, load average, memoria del proceso. |
| GET | `/api/system/info/` | Info del proceso (PID, workers, instancia, cache backend). |

---

## API: rutas y permisos

Todas las rutas (excepto las indicadas) requieren JWT en el header:

```
Authorization: Bearer <access_token>
```

### Autenticación

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| POST | `/api/token/` | público | Login con `email` + `password`. Devuelve `access` y `refresh`. |
| POST | `/api/token/refresh/` | público | Refresca el `access` token. |

### Permisos por rol

Los ViewSets aplican permisos según el rol del usuario autenticado y filtran el queryset por dueño:

| Recurso | Lectura | Escritura | Filtrado del queryset |
|---|---|---|---|
| `users/` | autenticado | admin | — |
| `ciclos/` | autenticado | admin | — |
| `materias/` | autenticado | admin | — |
| `grupos/` | autenticado | docente o admin | — |
| `inscripciones/` | autenticado | autenticado | alumno→propias, docente→de sus grupos, admin→todas |
| `tareas/` | autenticado | docente o admin | alumno→de sus grupos, docente→de los que imparte |
| `entregas/` | autenticado | autenticado | alumno→propias, docente→de sus grupos. `alumno` se auto-asigna a `request.user` en POST |
| `publicaciones/` | autenticado | docente o admin | alumno→de sus materias, docente→propias. `autor` auto-asignado |
| `comentarios/` | autenticado | autenticado | filtrado por publicaciones visibles. `autor` auto-asignado |
| `materiales/` | autenticado | docente o admin | alumno→de sus grupos, docente→propios. `autor` auto-asignado |

### Endpoints destacados

#### Inscripción por código (alumno)

```http
POST /api/grupos/join-by-code/
Authorization: Bearer <access_token>
Content-Type: application/json

{ "codigo": "HS2B8R" }
```

Respuestas:
- `201` — inscrito (devuelve `inscripcion` y `grupo`)
- `200` — ya estaba inscrito en ese mismo grupo
- `404` — código no encontrado
- `409` — ya inscrito en otro grupo de la misma materia/ciclo (UNIQUE constraint)
- `403` — el usuario no es alumno

El campo `Grupo.codigo` se autogenera al crear el grupo si no se proporciona (6 caracteres, sin O/0/I/1).

#### Subida de archivos

```http
POST /api/upload/
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

file=<binary>
```

Validaciones automáticas:
- **Permitidos**: PDF, DOCX, PPTX, XLSX, JPG, JPEG, PNG, ZIP, RAR
- **Bloqueados**: MP4, AVI, MOV, MKV, WMV (usar `video_url` en `Entrega`)
- **Máximo**: 30 MB

Respuesta:
```json
{
    "url": "https://pub-tudominio.r2.dev/<uuid>.pdf",
    "nombre_archivo": "tarea.pdf",
    "tamano_bytes": 1234567
}
```

Errores:
- `400` extensión inválida o tamaño excedido
- `502` fallo del servicio R2 (después de 3 reintentos)
- `503` circuit breaker abierto (R2 caído repetidas veces)

#### Reportes

PDF (descarga directa):
| Ruta | Descripción |
|---|---|
| `GET /api/reports/promedio-alumno/<id>/` | Promedio por materia + general |
| `GET /api/reports/promedio-grupo/<id>/` | Promedio de cada alumno del grupo |
| `GET /api/reports/promedio-materia/<id>/` | Promedio de todos los grupos de una materia |
| `GET /api/reports/indice-reprobacion/<id>/` | Aprobados / reprobados (mín. aprobatoria: 70) |

JSON (con caché y métricas de paralelismo):
| Ruta | Descripción |
|---|---|
| `GET /api/reports/json/promedio-alumno/<id>/` | Mismos datos, JSON. Incluye `parallel.elapsed_ms` y `cached: bool` |
| `GET /api/reports/json/promedio-grupo/<id>/` | — |
| `GET /api/reports/json/promedio-materia/<id>/` | — |
| `GET /api/reports/json/indice-reprobacion/<id>/` | — |

---

## Política de archivos

| Parámetro | Valor |
|---|---|
| Tipos permitidos | PDF, DOCX, PPTX, XLSX, JPG, PNG, ZIP, RAR |
| Tipos bloqueados | MP4, AVI, MOV, MKV, WMV |
| Tamaño máximo | 30 MB |
| Entregas por tarea | Ilimitadas hasta la fecha límite |
| Almacenamiento | Cloudflare R2 (la BD solo guarda la URL) |

Para evidencia en video el alumno usa el campo `video_url` con un enlace de YouTube o Google Drive.

---

## Estructura del proyecto

```
school-management-api/
├── config/                # Settings, URLs, WSGI/ASGI, LOGGING
├── users/                 # Modelo User custom + permissions por rol
├── academic/              # Ciclos, materias, grupos, inscripciones, tareas, entregas, publicaciones, comentarios, materiales
│   ├── upload_view.py     # Subida a R2 con retry + circuit breaker
│   └── migrations/
├── reports/               # Reportes PDF (paralelos) y JSON (cacheados)
├── system/                # PIA: middleware, monitoreo, resilience, parallel, cache
│   ├── middleware.py      # RequestID + Métricas + HealthCheckBypass
│   ├── metrics.py         # Store en memoria de latencias y top routes
│   ├── resilience.py      # CircuitBreaker + retry()
│   ├── parallel.py        # run_parallel() + @cached_report
│   ├── views.py           # /api/system/{health,metrics,resources,info}/
│   └── urls.py
├── docker/
│   └── nginx.conf         # Load balancer least_conn + failover
├── docker-compose.yml     # 2 backends + Nginx + Postgres + Redis
├── Dockerfile             # Imagen Django + Gunicorn multi-worker
├── manage.py
└── requirements.txt
```
