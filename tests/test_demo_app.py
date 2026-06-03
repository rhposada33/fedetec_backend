from app.scripts.demo_app import SERVICIOS_DEMO


def test_servicios_demo_tienen_claves_idempotentes_y_estados_esperados() -> None:
    claves = [servicio.clave_idempotencia for servicio in SERVICIOS_DEMO]
    estados = {servicio.estado for servicio in SERVICIOS_DEMO}

    assert len(claves) == len(set(claves))
    assert estados == {
        "CREADO",
        "DISPONIBLE",
        "ACEPTADO",
        "EN_PROCESO",
        "FINALIZADO",
    }
    assert all(clave.startswith("fedetec-demo-") for clave in claves)
