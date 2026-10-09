"""Tests de app/main.py::_row_to_out — el traductor entre una fila cruda de
Postgres (donde `fotos` puede llegar como list, como string JSON, o como
JSON inválido) y el modelo CasaOut que ve el cliente.

REQUIERE: fastapi, sqlalchemy, python-jose, httpx instalados.
Correr con:  python -m unittest tests.test_casas_helpers -v
"""

import os
import sys
import unittest
from types import SimpleNamespace

APP_DIR = os.path.join(os.path.dirname(__file__), "..", "app")
sys.path.insert(0, os.path.abspath(APP_DIR))

import main  # noqa: E402


def make_row(**overrides):
    base = dict(
        id=1, nombre="Casa Test", descripcion="desc", tipo="casa",
        telefono="3000000000", fotos=[], lat=4.6, lng=-74.0,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


class RowToOutFotosTests(unittest.TestCase):
    def test_fotos_already_a_list_is_kept_as_is(self):
        out = main._row_to_out(make_row(fotos=["a.jpg", "b.jpg"]))
        self.assertEqual(out.fotos, ["a.jpg", "b.jpg"])

    def test_fotos_as_valid_json_string_is_parsed_into_a_list(self):
        out = main._row_to_out(make_row(fotos='["a.jpg", "b.jpg"]'))
        self.assertEqual(out.fotos, ["a.jpg", "b.jpg"])

    def test_fotos_as_invalid_json_string_falls_back_to_empty_list(self):
        # Defensivo: si algún registro viejo quedó con basura en la columna,
        # _row_to_out no debe reventar el endpoint entero por una fila.
        out = main._row_to_out(make_row(fotos="{esto no es json"))
        self.assertEqual(out.fotos, [])

    def test_fotos_none_becomes_empty_list(self):
        out = main._row_to_out(make_row(fotos=None))
        self.assertEqual(out.fotos, [])

    def test_fotos_empty_string_becomes_empty_list(self):
        out = main._row_to_out(make_row(fotos=""))
        self.assertEqual(out.fotos, [])


class RowToOutDefaultsTests(unittest.TestCase):
    def test_tipo_none_defaults_to_casa(self):
        out = main._row_to_out(make_row(tipo=None))
        self.assertEqual(out.tipo, "casa")

    def test_tipo_present_is_kept(self):
        out = main._row_to_out(make_row(tipo="apartamento"))
        self.assertEqual(out.tipo, "apartamento")

    def test_telefono_none_defaults_to_empty_string(self):
        out = main._row_to_out(make_row(telefono=None))
        self.assertEqual(out.telefono, "")

    def test_id_lat_lng_pass_through_unchanged(self):
        out = main._row_to_out(make_row(id=99, lat=4.123, lng=-74.456))
        self.assertEqual(out.id, 99)
        self.assertEqual(out.lat, 4.123)
        self.assertEqual(out.lng, -74.456)


if __name__ == "__main__":
    unittest.main()
