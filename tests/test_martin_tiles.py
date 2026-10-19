import pytest
import httpx

@pytest.mark.integration
def test_martin_sirve_un_tile_de_calles():
    r = httpx.get("http://localhost:3000/bogota_calles/12/1205/1995")
    assert r.status_code in (200, 204)
    assert r.headers["content-type"] == "application/x-protobuf"


@pytest.mark.integration
@pytest.mark.xfail(
    reason="Martin no emite Cache-Control en fuentes PostgreSQL. "
           "Bug/limitación conocida. Ver docs/BUGS.md.",
    strict=True,
)
def test_martin_emite_cache_control_en_tiles():
    """Martin debería emitir Cache-Control para que el navegador cachee tiles."""
    r = httpx.get("http://localhost:3000/bogota_calles/12/1205/1995")
    assert "cache-control" in r.headers, (
        "Martin no emite Cache-Control. Los tiles no se cachean en el navegador."
    )
