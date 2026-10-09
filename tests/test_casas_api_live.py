"""Tests end-to-end contra la app FastAPI real, corriendo en Docker.

A diferencia de test_casas_api_unit.py (que mockea la DB), estos SÍ pegan por
HTTP a una instancia real de `bogota_app` — sirven para agarrar problemas que
un mock no puede: el `lifespan` fallando al conectar a Postgres, columnas que
no calzan entre la vista SQL y CasaOut, JSON malformado de verdad, etc.

Usan solo la librería estándar (como MartinLiveTests en test_martin_contract.py)
así que no hace falta instalar nada nuevo para correrlos.

Correr con el stack levantado:
    APP_URL=http://localhost:8000 python -m unittest tests.test_casas_api_live -v
"""

import json
import os
import unittest
from urllib.request import urlopen
from urllib.error import URLError


@unittest.skipUnless(os.getenv("APP_URL"), "Define APP_URL para probar la app corriendo (docker compose up -d)")
class AppLiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_url = os.environ["APP_URL"].rstrip("/")

    def get(self, path, timeout=10):
        return urlopen(f"{self.base_url}{path}", timeout=timeout)

    def test_home_page_serves_html_with_the_map_container(self):
        with self.get("/") as response:
            self.assertEqual(response.status, 200)
            body = response.read().decode("utf-8")
        self.assertIn('id="ml-map"', body)
        self.assertIn("const CASAS_DATA", body)

    def test_casas_endpoint_returns_a_json_array(self):
        with self.get("/casas") as response:
            self.assertEqual(response.status, 200)
            self.assertIn("application/json", response.headers.get("Content-Type", ""))
            data = json.loads(response.read())
        self.assertIsInstance(data, list)
        # Si hay al menos una casa, confirmamos la forma exacta que CasaOut promete.
        if data:
            casa = data[0]
            for campo in ("id", "nombre", "descripcion", "lat", "lng", "tipo", "telefono", "fotos"):
                with self.subTest(campo=campo):
                    self.assertIn(campo, casa)

    def test_casas_are_within_bogota_bounding_box(self):
        # Si esto falla, algo insertó una casa saltándose la validación de
        # crear() (por ejemplo, un INSERT manual directo a la DB).
        with self.get("/casas") as response:
            data = json.loads(response.read())
        for casa in data:
            with self.subTest(id=casa["id"]):
                self.assertTrue(4.45 <= casa["lat"] <= 4.85)
                self.assertTrue(-74.27 <= casa["lng"] <= -73.98)

    def test_auth_me_without_cookie_reports_not_authenticated(self):
        with self.get("/auth/me") as response:
            data = json.loads(response.read())
        self.assertEqual(data, {"autenticado": False})

    def test_static_maplibre_assets_are_served(self):
        # Regresión directa del bug real: 03_descargar_assets.sh nunca corrido
        # -> maplibre-gl.js 404 -> mapa en blanco sin ningún error de servidor.
        for asset in ("/static/libs/maplibre-gl.js", "/static/libs/maplibre-gl.css", "/static/js/map.js"):
            with self.subTest(asset=asset):
                with self.get(asset) as response:
                    self.assertEqual(response.status, 200)

    def test_deleting_a_nonexistent_casa_returns_404(self):
        import urllib.request
        req = urllib.request.Request(f"{self.base_url}/casas/999999999", method="DELETE")
        try:
            urlopen(req, timeout=10)
            self.fail("Se esperaba un 404 al borrar una casa inexistente")
        except URLError as e:
            self.assertEqual(getattr(e, "code", None), 404)


if __name__ == "__main__":
    unittest.main()
