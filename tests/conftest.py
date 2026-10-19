"""Fixtures y utilidades compartidas por toda la suite de tests.
"""

import json
import re
from types import SimpleNamespace
from typing import Any

import pytest


# ── Constantes compartidas ────────────────────────────────────────────────────

# Bounding box de Bogotá. Debe coincidir con el chequeo de main.py::crear()
# y con los límites usados en los datos de ejemplo de 01_init.sql.
BOGOTA_BBOX: dict[str, float] = {
    "lat_min": 4.45,
    "lat_max": 4.85,
    "lng_min": -74.27,
    "lng_max": -73.98,
}

BOGOTA_CENTER: dict[str, float] = {
    "lat": 4.6100,
    "lng": -74.0820,
}


# ── Factories ─────────────────────────────────────────────────────────────────

@pytest.fixture
def casa_factory() -> Any:
    """Fábrica de objetos 'con forma de casa' (CasaLike).

    Cada test puede pedir una casa distinta sin repetir los 8 campos:

        def test_x(casa_factory):
            casa  = casa_factory(nombre="Mi Casa")
            otra  = casa_factory(id=2, tipo="apartamento")

    Los valores por defecto forman una casa válida dentro de Bogotá.
    """
    def _make(**overrides: Any) -> SimpleNamespace:
        base: dict[str, Any] = {
            "id":          1,
            "nombre":      "Test",
            "descripcion": "desc",
            "lat":         BOGOTA_CENTER["lat"],
            "lng":         BOGOTA_CENTER["lng"],
            "tipo":        "casa",
            "telefono":    "3000000000",
            "fotos":       [],
        }
        base.update(overrides)
        return SimpleNamespace(**base)
    return _make


@pytest.fixture
def usuario_factory() -> Any:
    """Fábrica de payloads de usuario autenticado (JWT decodificado).

    Es la forma que main.py::requiere_auth() recibe como `usuario` después
    de verificar_jwt(). Estructura: {"sub": str(id), "email": ..., ...}.
    """
    def _make(**overrides: Any) -> dict[str, Any]:
        base: dict[str, Any] = {
            "sub":    "1",
            "email":  "test@example.com",
            "nombre": "Usuario Test",
            "foto":   None,
        }
        base.update(overrides)
        return base
    return _make


# ── Helpers de parseo del HTML ────────────────────────────────────────────────

def extract_casas_data(html: str) -> list[dict[str, Any]]:
    """Extrae y parsea el JSON de `CASAS_DATA` del HTML de build_map.

    Lanza AssertionError con mensaje claro si CASAS_DATA no está presente,
    para que el test no falle con un IndexError o JSONDecodeError sin contexto.

    Uso:
        from conftest import extract_casas_data
        casas = extract_casas_data(map_generator.build_map([casa]))
    """
    match = re.search(r"const CASAS_DATA = (\[.*?\]);", html, re.DOTALL)
    assert match is not None, "No se encontró CASAS_DATA en el HTML generado"
    return json.loads(match.group(1))


def extract_js_constants(html: str) -> dict[str, str]:
    """Extrae las constantes JS (MARTIN, OSRM_CAR, OSRM_FOOT) del HTML.

    Devuelve un dict {nombre: valor}. Útil para verificar que build_map()
    inyectó las URLs correctas desde las variables de entorno.

    Uso:
        from conftest import extract_js_constants
        consts = extract_js_constants(html)
        assert consts["MARTIN"] == "http://localhost:3000"
    """
    constants: dict[str, str] = {}
    for name in ("MARTIN", "OSRM_CAR", "OSRM_FOOT"):
        match = re.search(rf'const {name}\s*=\s*"([^"]*)";', html)
        assert match is not None, f"No se encontró {name} en el HTML generado"
        constants[name] = match.group(1)
    return constants
