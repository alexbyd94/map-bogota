"""Tests de integración HTTP contra los endpoints de FastAPI.

Requieren que la app esté corriendo en http://localhost:8000:

    docker compose up -d

Correr:
    pytest -m integration tests/test_main_endpoints.py -v
"""

import os
import sys

APP_DIR = os.path.join(os.path.dirname(__file__), "..", "app")
sys.path.insert(0, os.path.abspath(APP_DIR))

import httpx  # noqa: E402
import pytest  # noqa: E402

BASE = "http://localhost:8000"


# ── GET / ─────────────────────────────────────────────────────────────────────

@pytest.mark.integration
def test_get_index_devuelve_html_con_el_mapa() -> None:
    """GET / debe devolver HTML con el div del mapa y CASAS_DATA.

    Es la página principal. Si esto falla, nadie puede abrir la app.
    """
    r = httpx.get(f"{BASE}/", timeout=10)

    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert 'id="ml-map"' in r.text
    assert "const CASAS_DATA" in r.text


# ── GET /casas ────────────────────────────────────────────────────────────────

@pytest.mark.integration
def test_get_casas_devuelve_json() -> None:
    """GET /casas debe devolver application/json con un array."""
    r = httpx.get(f"{BASE}/casas", timeout=10)

    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    assert isinstance(r.json(), list)


@pytest.mark.integration
def test_get_casas_cada_item_tiene_los_8_campos() -> None:
    """Cada casa del JSON debe tener los 8 campos que map.js espera.

    Si el SELECT de _get_casas se rompe (por ejemplo, si ST_Y/ST_X dejan de
    existir), este test lo detecta con el nombre exacto del campo faltante.
    """
    r = httpx.get(f"{BASE}/casas", timeout=10)
    casas = r.json()

    if not casas:
        pytest.skip("No hay casas en la DB; el test de forma no aplica.")

    campos = {"id", "nombre", "descripcion", "lat", "lng", "tipo", "telefono", "fotos"}
    for casa in casas:
        faltantes = campos - casa.keys()
        assert not faltantes, (
            f"Casa {casa.get('id', '?')} sin campos: {sorted(faltantes)}"
        )


@pytest.mark.integration
def test_get_casas_coordenadas_dentro_de_bogota() -> None:
    """Todas las casas deben tener coordenadas dentro del bbox de Bogotá.

    Si alguien insertó una casa directo en la DB (saltándose crear()), este
    test lo detecta. Es el mismo bbox que valida main.py::crear.
    """
    r = httpx.get(f"{BASE}/casas", timeout=10)
    for casa in r.json():
        assert 4.45 <= casa["lat"] <= 4.85, (
            f"Casa {casa['id']} con lat fuera de Bogotá: {casa['lat']}"
        )
        assert -74.27 <= casa["lng"] <= -73.98, (
            f"Casa {casa['id']} con lng fuera de Bogotá: {casa['lng']}"
        )


# ── POST /casas (sin auth) ────────────────────────────────────────────────────

@pytest.mark.integration
def test_post_casas_sin_auth_devuelve_401() -> None:
    """POST /casas sin cookie debe devolver 401.

    La app requiere autenticación para publicar. Si esto devuelve 201,
    cualquiera podría publicar sin cuenta.
    """
    r = httpx.post(f"{BASE}/casas", json={
        "nombre": "Casa sin auth",
        "lat": 4.61,
        "lng": -74.08,
    }, timeout=10)

    assert r.status_code == 401


# ── DELETE /casas/{id} ────────────────────────────────────────────────────────

@pytest.mark.integration
def test_delete_casa_inexistente_devuelve_404() -> None:
    """DELETE /casas/{id} con un id que no existe debe devolver 404."""
    r = httpx.delete(f"{BASE}/casas/999999999", timeout=10)
    assert r.status_code == 404


# ── GET /auth/me ──────────────────────────────────────────────────────────────

@pytest.mark.integration
def test_auth_me_sin_cookie_devuelve_no_autenticado() -> None:
    """GET /auth/me sin cookie debe devolver {autenticado: false}."""
    r = httpx.get(f"{BASE}/auth/me", timeout=10)

    assert r.status_code == 200
    assert r.json() == {"autenticado": False}


@pytest.mark.integration
@pytest.mark.xfail(
    reason="DELETE no verifica auth. Pendiente: implementar ownership.",
    strict=True,
)
def test_delete_casa_sin_auth_devuelve_401() -> None:
    """DELETE /casas/{id} sin cookie debe devolver 401.

    Cualquier usuario autenticado puede borrar SOLO sus propias casas
    (o un admin puede borrar cualquiera). Sin autenticación, no se debe
    permitir ni siquiera intentarlo.

    Hoy este test FALLA: el endpoint es público y devuelve 404 o 204.
    """
    r = httpx.delete(f"{BASE}/casas/1", timeout=10)
    assert r.status_code == 401, (
        f"DELETE sin auth devolvió {r.status_code}. "
        f"Debería requerir autenticación. Bug: el endpoint no tiene "
        f"Depends(requiere_auth)."
    )


@pytest.mark.integration
def test_delete_casa_inexistente_con_auth_devuelve_404() -> None:
    """Con auth válida, borrar un id inexistente devuelve 404."""
    import main
    token = main.crear_jwt({"sub": "1", "email": "test@example.com"})
    r = httpx.delete(
        f"{BASE}/casas/999999999",
        cookies={"auth_token": token},
        timeout=10,
    )
    assert r.status_code == 404
