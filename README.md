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

- `GET /health`
- `GET /salud`
- `POST /api/v1/autenticacion/registro`
- `POST /api/v1/autenticacion/token`
- `GET /api/v1/usuarios/me`
- `POST /api/v1/sedes`
- `GET /api/v1/sedes`

## Docker local

Crear variables de entorno locales:

```bash
cp .env.example .env
```

Docker Compose configura `DATABASE_URL` automáticamente apuntando al servicio interno `postgres`. Para ejecución sin Docker, usa el `DATABASE_URL` de `.env.example`, que apunta a `localhost`.

Si quieres cambiar el modo debug de Docker, usa `APP_DEBUG=true` o `APP_DEBUG=false` en `.env`; Compose lo traduce a la variable `DEBUG` que lee la aplicación.

Iniciar el proyecto:

```bash
docker compose up --build
```

El contenedor `api` espera a PostgreSQL, ejecuta `alembic upgrade head` y luego inicia FastAPI con recarga automática.

Reconstruir contenedores:

```bash
docker compose build --no-cache
docker compose up
```

Ejecutar migraciones:

```bash
docker compose exec api alembic upgrade head
```

Comprobar la API desde el host:

```bash
curl http://localhost:8000/health
```

Comprobar PostGIS:

```bash
docker compose exec postgres psql -U fedetec -d fedetec -c "CREATE EXTENSION IF NOT EXISTS postgis;"
docker compose exec postgres psql -U fedetec -d fedetec -c "SELECT postgis_full_version();"
```

El servicio `api` monta el código fuente como volumen y ejecuta `fastapi dev`, por lo que los cambios en `app/` recargan automáticamente el servidor.

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
