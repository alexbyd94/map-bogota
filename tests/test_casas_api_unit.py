"""Tests de app/main.py::crear y app/main.py::eliminar (los endpoints de
POST/DELETE /casas).

Diseño deliberado: en vez de levantar el ASGI app completo con TestClient
(lo cual dispara el `lifespan` de FastAPI, que intenta conectarse a Postgres
de una — ver nota abajo), llamamos las funciones async directamente como
funciones Python normales. Eso separa dos cosas que main.py mezcla:
  1) la resolución de Depends(requiere_auth) -> ya cubierta en test_auth.py
  2) la lógica propia de crear()/eliminar() -> lo que se prueba aquí

Para crear(), inyectamos `usuario` a mano (bypass total de Depends) y
mockeamos `Session` para no necesitar una base de datos real en pie.

NOTA DE ARQUITECTURA: main.py crea `Session(engine)` a mano dentro de cada
endpoint en vez de usar `Depends(get_session)`. Sin ese punto de inyección,
un TestClient real no tiene forma de sustituir la DB por un fake — por eso
este archivo mockea `main.Session` directamente. Si algún día se refactoriza
a Depends(get_session), este archivo se simplifica bastante.

REQUIERE: fastapi, sqlalchemy, python-jose, httpx instalados.
Correr con:  python -m unittest tests.test_casas_api_unit -v
"""

import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

APP_DIR = os.path.join(os.path.dirname(__file__), "..", "app")
sys.path.insert(0, os.path.abspath(APP_DIR))

from fastapi import HTTPException

import main  # noqa: E402


def usuario_falso(sub="1"):
    return {"sub": sub, "email": "test@example.com"}


def fake_session_returning(row):
    """Un doble de `with Session(engine) as session: ...` cuyo
    execute(...).fetchone() siempre devuelve `row`."""
    session = MagicMock()
    session.execute.return_value.fetchone.return_value = row
    session.__enter__.return_value = session
    session.__exit__.return_value = False
    return session


class CrearCasaValidationTests(unittest.IsolatedAsyncioTestCase):
    """Estas validaciones ocurren ANTES de tocar la base de datos — no hace
    falta mockear Session para probarlas."""

    async def test_coords_outside_bogota_bbox_raise_422(self):
        casa = main.CasaIn(nombre="X", lat=0.0, lng=0.0)  # Bogotá NO está en (0,0)
        with self.assertRaises(HTTPException) as ctx:
            await main.crear(casa, usuario=usuario_falso())
        self.assertEqual(ctx.exception.status_code, 422)

    async def test_lat_just_outside_the_north_boundary_raises_422(self):
        casa = main.CasaIn(nombre="X", lat=4.86, lng=-74.08)  # límite es 4.85
        with self.assertRaises(HTTPException):
            await main.crear(casa, usuario=usuario_falso())

    async def test_lat_lng_at_the_exact_boundary_are_accepted(self):
        # 4.85 / -73.98 son los límites inclusive (<=) del chequeo real.
        casa = main.CasaIn(nombre="X", lat=4.85, lng=-73.98)
        fake_row = SimpleNamespace(
            id=1, nombre="X", descripcion="", tipo="casa", telefono="",
            fotos="[]", lat=4.85, lng=-73.98,
        )
        with patch.object(main, "Session", return_value=fake_session_returning(fake_row)), \
             patch.object(main.manager, "broadcast", new=AsyncMock()):
            result = await main.crear(casa, usuario=usuario_falso())
        self.assertEqual(result.id, 1)

    async def test_more_than_four_fotos_raise_422(self):
        casa = main.CasaIn(nombre="X", lat=4.6, lng=-74.08, fotos=["a", "b", "c", "d", "e"])
        with self.assertRaises(HTTPException) as ctx:
            await main.crear(casa, usuario=usuario_falso())
        self.assertEqual(ctx.exception.status_code, 422)

    async def test_exactly_four_fotos_is_accepted(self):
        casa = main.CasaIn(nombre="X", lat=4.6, lng=-74.08, fotos=["a", "b", "c", "d"])
        fake_row = SimpleNamespace(
            id=2, nombre="X", descripcion="", tipo="casa", telefono="",
            fotos='["a","b","c","d"]', lat=4.6, lng=-74.08,
        )
        with patch.object(main, "Session", return_value=fake_session_returning(fake_row)), \
             patch.object(main.manager, "broadcast", new=AsyncMock()):
            result = await main.crear(casa, usuario=usuario_falso())
        self.assertEqual(len(result.fotos), 4)


class CrearCasaSuccessPathTests(unittest.IsolatedAsyncioTestCase):
    async def test_valid_casa_is_inserted_and_broadcast(self):
        casa = main.CasaIn(nombre="Apto", lat=4.65, lng=-74.05, tipo="apartamento")
        fake_row = SimpleNamespace(
            id=10, nombre="Apto", descripcion="", tipo="apartamento",
            telefono="", fotos="[]", lat=4.65, lng=-74.05,
        )
        fake_session = fake_session_returning(fake_row)

        with patch.object(main, "Session", return_value=fake_session) as mock_session_cls, \
             patch.object(main.manager, "broadcast", new=AsyncMock()) as mock_broadcast:
            result = await main.crear(casa, usuario=usuario_falso(sub="99"))

        # Se insertó con el usuario correcto.
        _, insert_params = fake_session.execute.call_args[0]
        self.assertEqual(insert_params["usuario_id"], 99)
        self.assertEqual(insert_params["nombre"], "Apto")

        # Se confirmó la transacción.
        fake_session.commit.assert_called_once()

        # Se notificó por WebSocket con el pin nuevo.
        mock_broadcast.assert_awaited_once()
        (broadcast_payload,), _ = mock_broadcast.call_args
        self.assertEqual(broadcast_payload["tipo"], "nuevo_pin")
        self.assertEqual(broadcast_payload["casa"]["id"], 10)

        self.assertEqual(result.id, 10)


class EliminarCasaTests(unittest.IsolatedAsyncioTestCase):
    async def test_deleting_a_nonexistent_casa_raises_404(self):
        session = MagicMock()
        session.execute.return_value.rowcount = 0
        session.__enter__.return_value = session
        session.__exit__.return_value = False

        with patch.object(main, "Session", return_value=session):
            with self.assertRaises(HTTPException) as ctx:
                await main.eliminar(casa_id=999)
        self.assertEqual(ctx.exception.status_code, 404)

    async def test_deleting_an_existing_casa_broadcasts_pin_eliminado(self):
        session = MagicMock()
        session.execute.return_value.rowcount = 1
        session.__enter__.return_value = session
        session.__exit__.return_value = False

        with patch.object(main, "Session", return_value=session), \
             patch.object(main.manager, "broadcast", new=AsyncMock()) as mock_broadcast:
            await main.eliminar(casa_id=5)

        mock_broadcast.assert_awaited_once_with({"tipo": "pin_eliminado", "id": 5})
        session.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
