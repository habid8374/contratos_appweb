# Guía de despliegue

La app tiene dos partes que se despliegan por separado:

- **Backend** (Django + PostgreSQL) → Railway
- **Frontend** (Angular) → Vercel (estático) o Railway (SSR)

> **Importante (monorepo):** el repositorio contiene `backend/` y `frontend/`.
> En Railway y en Vercel SIEMPRE hay que configurar el **Root Directory** del
> servicio/proyecto; si se deja en la raíz, el build falla o detecta mal el
> lenguaje.

## 1. Backend en Railway

1. Crea un proyecto en Railway y agrega un servicio desde este repositorio de GitHub.
2. En **Settings → Source → Root Directory** escribe `backend`.
3. Agrega una base de datos: **Create → Database → PostgreSQL** en el mismo proyecto.
4. En el servicio del backend, ve a **Variables** y define:

   | Variable | Valor |
   |---|---|
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (referencia al servicio Postgres) |
   | `DJANGO_SECRET_KEY` | una cadena aleatoria larga (50+ caracteres) |
   | `DJANGO_CORS_ALLOWED_ORIGINS` | la URL del frontend, p. ej. `https://tu-frontend.vercel.app` |

   No hace falta configurar `DJANGO_ALLOWED_HOSTS` ni `DJANGO_DEBUG`: el
   `settings.py` agrega automáticamente el dominio público de Railway
   (`RAILWAY_PUBLIC_DOMAIN`) y desactiva `DEBUG` cuando corre en Railway.

   Variables opcionales:

   | Variable | Para qué |
   |---|---|
   | `JWT_ACCESS_MINUTES` / `JWT_REFRESH_DAYS` | duración de los tokens (por defecto 60 min / 7 días) |
   | `DJANGO_EMAIL_BACKEND` + `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` | envío real de correos de alerta (SMTP) |
   | `DEFAULT_FROM_EMAIL`, `ALERTAS_RECIPIENTS` (lista separada por comas), `FRONTEND_BASE_URL` | remitente, destinatarios y enlace de las alertas de vencimiento |

   **Crear el superusuario (login):** la app exige iniciar sesión. La forma
   más sencilla es por variables de entorno: define en Railway

   | Variable | Ejemplo |
   |---|---|
   | `DJANGO_SUPERUSER_USERNAME` | `admin` |
   | `DJANGO_SUPERUSER_PASSWORD` | (una contraseña segura) |
   | `DJANGO_SUPERUSER_EMAIL` | `admin@clinicacentro.com` |

   Al desplegar, el arranque ejecuta `python manage.py ensure_superuser`, que
   crea ese superusuario (o actualiza su contraseña) de forma idempotente. Los
   demás usuarios se crean desde `/admin`. No hay registro público (app interna).
   Alternativamente puedes abrir la **Console** del servicio y ejecutar
   `python manage.py createsuperuser`.

5. En **Settings → Networking** genera el dominio público (`Generate Domain`).
6. Despliega. El `backend/railway.json` ya define:
   - migraciones + `collectstatic` + gunicorn como comando de arranque,
   - gunicorn enlazado a `[::]` (IPv6): el healthcheck y la red privada de
     Railway son IPv6; con `0.0.0.0` el healthcheck falla con
     "service unavailable",
   - healthcheck en `/api/health/`.

   El archivo `backend/.python-version` fija **Python 3.13** (Django 6 requiere
   Python ≥ 3.12; sin este archivo Railway instala 3.11 y `pip install` falla).

Verifica: `https://<tu-backend>.up.railway.app/api/health/` debe responder `{"status": "ok"}`.

## 2. Frontend en Vercel (recomendado)

1. En Vercel, **Add New → Project** e importa el repositorio.
2. En **Root Directory** selecciona `frontend` (imprescindible).
3. Framework preset: deja lo que detecte; `frontend/vercel.json` ya define build,
   salida (`dist/frontend/browser`) y el rewrite de SPA (excluyendo `/api/`).
4. En **Settings → Environment Variables** define:

   | Variable | Valor |
   |---|---|
   | `API_TARGET_URL` | URL del backend en Railway, p. ej. `https://tu-backend.up.railway.app` |

   Las llamadas del navegador a `/api/...` las atiende la función
   `frontend/api/[...path].ts`, que las reenvía al backend. **Sin esta variable
   el login y las búsquedas fallan** (el proxy no sabe a dónde reenviar).

5. Despliega. `package.json` fija Node 24 vía `engines` (Angular CLI 22
   requiere Node ≥ 22.22.3; con el Node por defecto el build fallaba).

## 3. Frontend en Railway (alternativa con SSR)

1. Crea otro servicio desde el mismo repositorio.
2. **Root Directory**: `frontend`.
3. Variables:

   | Variable | Valor |
   |---|---|
   | `API_TARGET_URL` | URL pública del backend, p. ej. `https://tu-backend.up.railway.app` |

4. Genera el dominio público. `frontend/railway.json` ya define build y
   `npm run serve:ssr:frontend` como arranque.

Notas del SSR:

- `angular.json` (`security.allowedHosts`) ya permite `*.up.railway.app`,
  `*.railway.app`, `*.vercel.app` y `localhost`. Con la lista vacía anterior,
  **todas las peticiones respondían 400 Bad Request**.
- Si usas un **dominio propio**, agrégalo a esa lista y vuelve a desplegar, o
  define la variable de entorno `NG_ALLOWED_HOSTS=mi-dominio.com` en Railway
  (no requiere rebuild).

## 4. Recordatorio de CORS

Cuando el frontend llama al backend a través del proxy (`/api`), la petición
sale del servidor del frontend, no del navegador, así que CORS casi no
interviene. Aun así, configura en el backend:

```
DJANGO_CORS_ALLOWED_ORIGINS=https://tu-frontend.vercel.app,https://tu-frontend.up.railway.app
```

## 5. Errores que existían y cómo se corrigieron

| Síntoma | Causa | Arreglo |
|---|---|---|
| Railway (backend): `No matching distribution found for Django<6.1,>=6.0.7` | Django 6 requiere Python ≥ 3.12 y Railway usaba 3.11 | `backend/.python-version` con `3.13` |
| Vercel/Railway (frontend): `The Angular CLI requires a minimum Node.js version of v22.22.3` | Node por defecto demasiado viejo | `engines: { node: "24.x" }` en `package.json` |
| Frontend SSR en Railway: toda página responde `400 Bad Request` | `security.allowedHosts: []` en `angular.json` | lista de hosts permitidos con comodines |
| SSR de `/contratos/:id` devolvía 500 | `new Audio(...)` no existe en Node | se crea el audio solo en el navegador |
| Archivos estáticos del admin sin comprimir/versionar | `STATICFILES_STORAGE` fue eliminado en Django 5.1+ y se ignoraba | migrado a `STORAGES` |
| 400 en el backend al abrir el dominio de Railway | `ALLOWED_HOSTS` solo tenía localhost | se agrega `RAILWAY_PUBLIC_DOMAIN` automáticamente |
