@echo off
cd /d "%~dp0"
"%~dp0venv\Scripts\python.exe" manage.py runserver 0.0.0.0:8000
