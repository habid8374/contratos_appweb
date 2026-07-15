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
