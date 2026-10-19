import os
import sys

APP_DIR = os.path.join(os.path.dirname(__file__), "..", "app")
sys.path.insert(0, os.path.abspath(APP_DIR))

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session
import main

VISTAS_MARTIN = {
    "bogota_agua",
    "bogota_calles",
    "bogota_casas_view",
    "bogota_ciclovias",
    "bogota_comercio",
    "bogota_edificios",
    "bogota_equipamiento",
    "bogota_landuse",
    "bogota_leisure",
    "bogota_parques",
    "bogota_peatonal",
}

def test_vistas_de_martin_existen_en_la_db():
    with main.engine.connect() as conn:
        rows = conn.execute(text("""
            select viewname
            from pg_views
            where schemaname = 'tiles'
        """)).fetchall()

    vistas_existentes = {r[0] for r in rows}
    faltantes = VISTAS_MARTIN - vistas_existentes

    assert not faltantes, (
        f"Faltan {len(faltantes)} vistas en el schema tiles: {sorted(faltantes)}. "

        f"Verifica que 02_crear_vistas.sql se ejecutó (docker compose up -d vistas)."
        )


@pytest.mark.integration
def test_vistas_bogota_casas_refleja_la_tabla_casas():
    """tiles.bogota_casas_view debe tener las mismas filas que public.casas.

    Si están desincronizadas, los pines del mapa no coinciden con la DB.
    """
    with main.engine.connect() as conn:
        n_tabla = conn.execute(text("SELECT COUNT(*) FROM casas")).scalar()
        n_vista = conn.execute(
            text("SELECT COUNT(*) FROM tiles.bogota_casas_view")
        ).scalar()

    assert n_vista == n_tabla, (
        f"La vista tiene {n_vista} filas, la tabla tiene {n_tabla}. "
        f"Alguien recreó la tabla sin recrear la vista."
    )

@pytest.mark.integration
def test_ciclo_de_vida_de_una_casa():
    """Insertar una casa, leerla de la DB, y verificar que build_map la incluye.

    Verifica el ciclo completo:
    1. INSERT en casas (simulando POST /casas).
    2. SELECT con _get_casas (simulando GET /casas).
    3. build_map (simulando GET /).
    4. Verificar que CASAS_DATA contiene la casa insertada.
    """
    from map_generator import build_map
    from conftest import extract_casas_data

    with main.engine.connect() as conn:
        # 1. INSERT.
        row = conn.execute(text("""
            INSERT INTO casas (nombre, descripcion, ubicacion, tipo, telefono, fotos)
            VALUES (:nombre, :descripcion,
                    ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
                    :tipo, :telefono, '[]'::jsonb)
            RETURNING id
        """), {
            "nombre": "Casa del Test E2E",
            "descripcion": "Insertada por pytest",
            "lat": 4.61,
            "lng": -74.08,
            "tipo": "casa",
            "telefono": "3000000000",
        }).fetchone()
        conn.commit()
        casa_id = row.id

    try:
        # 2. SELECT.
        with Session(main.engine) as session:
            casas = main._get_casas(session)

        # 3. build_map.
        html = build_map(casas)
        casas_json = extract_casas_data(html)

        # 4. Verificar.
        ids_en_html = [c["id"] for c in casas_json]
        assert casa_id in ids_en_html, (
            f"La casa {casa_id} se insertó en la DB pero no aparece en CASAS_DATA."
        )
    finally:
        # Cleanup: borrar la casa insertada.
        with main.engine.connect() as conn:
            conn.execute(
                text("DELETE FROM casas WHERE id = :id"),
                {"id": casa_id}
            )
            conn.commit()
