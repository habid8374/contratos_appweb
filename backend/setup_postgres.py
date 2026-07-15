import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / '.env'
DB_NAME = 'clinica_centro'
DB_USER = 'postgres'
DB_PASSWORD = 'postgres'


def write_env() -> None:
    env_content = f"""POSTGRES_DB={DB_NAME}
POSTGRES_USER={DB_USER}
POSTGRES_PASSWORD={DB_PASSWORD}
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
"""
    ENV_PATH.write_text(env_content, encoding='utf-8')
    print(f"Archivo .env creado en {ENV_PATH}")


def run_command(command: list[str], description: str) -> None:
    print(f"\n>>> {description}")
    result = subprocess.run(command, shell=True, cwd=str(BASE_DIR))
    if result.returncode != 0:
        raise SystemExit(f"Error ejecutando: {' '.join(command)}")


if __name__ == '__main__':
    write_env()

    candidates = [
        ['psql', '-U', DB_USER, '-c', f'CREATE DATABASE {DB_NAME};'],
        ['C:/Program Files/PostgreSQL/16/bin/psql.exe', '-U', DB_USER, '-c', f'CREATE DATABASE {DB_NAME};'],
        ['C:/Program Files/PostgreSQL/15/bin/psql.exe', '-U', DB_USER, '-c', f'CREATE DATABASE {DB_NAME};'],
    ]

    for candidate in candidates:
        try:
            run_command(candidate, f'Intentando crear la base de datos con {candidate[0]}')
            print(f"Base de datos '{DB_NAME}' creada correctamente.")
            break
        except SystemExit as exc:
            print(exc)
    else:
        print("\nNo se pudo crear la base de datos automáticamente.")
        print("Instala PostgreSQL y ejecuta manualmente:")
        print(f"  createdb -U {DB_USER} {DB_NAME}")
        print("o desde psql:")
        print(f"  CREATE DATABASE {DB_NAME};")
