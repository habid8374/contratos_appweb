# Contratos App Web

Aplicacion web para consultar contratos, administradoras y alertas de vencimiento.

## Estructura

- `backend/`: API Django REST con PostgreSQL.
- `frontend/`: aplicacion Angular.

## Backend local

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py runserver
```

## Frontend local

```powershell
cd frontend
npm install
npm start
```

## Variables de entorno

Usa `backend/.env.example` como plantilla. No subas `backend/.env` al repositorio.

## Despliegue (Railway / Vercel)

Sigue la guía paso a paso en [DEPLOY.md](DEPLOY.md). Resumen:

- Backend → Railway con root directory `backend` (Python 3.13 fijado en `backend/.python-version`).
- Frontend → Vercel con root directory `frontend` (Node 24 fijado en `package.json`), o Railway con SSR.
- El frontend llama al backend a través del proxy `/api`; configura `API_TARGET_URL` con la URL pública del backend.
