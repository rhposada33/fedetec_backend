import os

os.environ["DEBUG"] = "false"
os.environ["SECRET_KEY"] = "clave-local-para-pruebas-con-longitud-segura"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://fedetec:fedetec@localhost:5432/fedetec"

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_salud() -> None:
    response = client.get("/salud")
    assert response.status_code == 200
    assert response.json() == {"estado": "ok"}
