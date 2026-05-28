# Fedetec Backend

Backend FastAPI con SQLAlchemy 2.0 async, PostgreSQL/PostGIS, Alembic, Pydantic v2, JWT y pytest.

## Requisitos

- Python 3.12
- PostgreSQL con extensión PostGIS

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Crear la base de datos y habilitar PostGIS:

```sql
CREATE DATABASE fedetec;
\c fedetec
CREATE EXTENSION IF NOT EXISTS postgis;
```

## Migraciones

```bash
alembic upgrade head
```

## Ejecutar

```bash
fastapi dev app/main.py
```

La API expone:

- `GET /salud`
- `POST /api/v1/autenticacion/registro`
- `POST /api/v1/autenticacion/token`
- `GET /api/v1/usuarios/me`
- `POST /api/v1/sedes`
- `GET /api/v1/sedes`

## Pruebas

```bash
pytest
```

## Estructura

```text
app/
  main.py
  core/
  modelos/
  schemas/
  api/
    v1/
      endpoints/
  servicios/
  repositorios/
  utils/
alembic/
tests/
```

