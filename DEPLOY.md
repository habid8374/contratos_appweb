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
   salida (`dist/frontend/browser`) y el rewrite de SPA.
4. Despliega. `package.json` fija Node 24 vía `engines` (Angular CLI 22
   requiere Node ≥ 22.22.3; con el Node por defecto el build fallaba).

   El frontend es una **SPA que llama directamente al backend de Railway**. La
   URL del backend está en `frontend/src/environments/environment.prod.ts`
   (`apiUrl`). Si cambias el dominio del backend, actualiza esa URL y vuelve a
   desplegar. **No se necesita configurar `API_TARGET_URL` en Vercel** (ese
   proxy se eliminó; puedes borrar la variable si la tenías).

   Como el navegador llama al backend en otro dominio, el backend debe permitir
   ese origen por **CORS**: define en Railway
   `DJANGO_CORS_ALLOWED_ORIGINS=https://tu-frontend.vercel.app`.

## 3. CORS (imprescindible)

El frontend (SPA) llama al backend desde el navegador y en otro dominio, así
que el backend debe permitir ese origen por CORS. En Railway define:

```
DJANGO_CORS_ALLOWED_ORIGINS=https://tu-frontend.vercel.app
```

## 4. Errores que existían y cómo se corrigieron

| Síntoma | Causa | Arreglo |
|---|---|---|
| Railway (backend): `No matching distribution found for Django<6.1,>=6.0.7` | Django 6 requiere Python ≥ 3.12 y Railway usaba 3.11 | `backend/.python-version` con `3.13` |
| Vercel/Railway (frontend): `The Angular CLI requires a minimum Node.js version of v22.22.3` | Node por defecto demasiado viejo | `engines: { node: "24.x" }` en `package.json` |
| Vercel: el build fallaba (no generaba `index.html`) | el modo SSR solo generaba `index.csr.html` y Vercel sirve estático | frontend convertido a **SPA** client-side |
| Vercel: login daba `404`/`504` en `/api/auth/token/` | el proxy serverless de Vercel no funcionaba de forma fiable | el frontend llama **directo** al backend de Railway (con CORS); proxy eliminado |
| Archivos estáticos del admin sin comprimir/versionar | `STATICFILES_STORAGE` fue eliminado en Django 5.1+ y se ignoraba | migrado a `STORAGES` |
| 400 en el backend al abrir el dominio de Railway | `ALLOWED_HOSTS` solo tenía localhost | se agrega `RAILWAY_PUBLIC_DOMAIN` automáticamente |
