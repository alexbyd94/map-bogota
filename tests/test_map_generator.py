import os
import sys

APP_DIR = os.path.join(os.path.dirname(__file__), "..", "app")
sys.path.insert(0, os.path.abspath(APP_DIR))

import map_generator
from conftest import extract_casas_data

def test_build_map_returns_html_with_the_map_div() -> None:
    html = map_generator.build_map([])
    assert isinstance(html, str)
    assert 'id="ml-map"' in html


def test_casas_data_field_map(casa_factory) -> None:
    from types import SimpleNamespace

    casa = casa_factory(nombre="Casa Test")
    casas = extract_casas_data(map_generator.build_map([casa]))

    assert casas == [
        {
            "id":          1,
            "nombre":      "Casa Test",
            "descripcion": "desc",
            "lat":         4.61,
            "lng":         -74.082,
            "tipo":        "casa",
            "telefono":    "3000000000",
            "fotos":       [],
        }
    ]


def test_map_scapes_closing_tags_in_nombre(casa_factory) -> None:

    casa = casa_factory(nombre="</scrip><script>alert(1)</script>")
    html = map_generator.build_map([casa])

    assert html.count("</script") == 3,(
            f"Se encontraron {html.count('</script>')} cierres de </script>. "
        f"Esperado: 1 (el que cierra el bloque CASAS_DATA). "
        f"Un valor mayor significa que el nombre de la casa inyectó HTML/JS."
    )
def test_build_map_is_deterministic_with_same_input(casa_factory) -> None:

    casa = casa_factory(nombre="Casa Determinista")

    html1 = map_generator.build_map([casa])
    html2 = map_generator.build_map([casa])

    assert html1 == html2

def test_build_map_with_empty_list_produces_empty_json_array() -> None:

    casas = extract_casas_data(map_generator.build_map([]))
    assert casas == []
