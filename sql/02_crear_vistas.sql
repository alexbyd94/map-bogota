-- 02_crear_vistas.sql — Vistas para Martin tile server (auto-discovery)
-- Ejecutar DESPUÉS de cargar bogota.osm.pbf con osm2pgsql
--
-- Todas las vistas que Martin debe publicar viven en el schema `tiles`.
-- martin/config.yaml usa config MANUAL (auto_publish: false) — si agregas una
-- vista nueva aquí, también hay que agregarla a mano en config.yaml.
--
-- Cada vista lleva su propio DROP VIEW IF EXISTS ... CASCADE justo antes del
-- CREATE, para que el script sea idempotente sin depender de CREATE OR
-- REPLACE VIEW: OR REPLACE falla con "cannot change data type of view
-- column" si el typmod de una columna cambia entre corridas (nos pasó de
-- verdad con bogota_casas_view al agregarle el SRID explícito). DROP+CREATE
-- no tiene ese problema porque no intenta preservar nada de la versión
-- anterior.

-- ES MEJOR QUE ESTAS VISTAS ESTEN EN 01_init.sql TENIENDO UN SOLO ARCHIVO Y NO 
-- VARIOS DISPERSOS
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS tiles;

-- Sigo teniendo schema public. Aunque las view se estan creando todas en tiles.bogota_...
-- Donde se encuentra almacenada la base de datos y porque esta alli, idealmente donde deberia estar???
--  si ahora esta en: public.planet_osm_line
-- acceder mediante dadbob vin a la base de datos alojada en docker
-- Eliminar esto una vez hecha nueva la arquitectura de la app
-- Limpieza de las vistas viejas en `public` (quedaron de la config manual
-- anterior; ya no las usa nadie una vez Martin apunta a `tiles`).
DROP VIEW IF EXISTS public.bogota_calles        CASCADE;
DROP VIEW IF EXISTS public.bogota_edificios     CASCADE;
DROP VIEW IF EXISTS public.bogota_parques       CASCADE;
DROP VIEW IF EXISTS public.bogota_agua          CASCADE;
DROP VIEW IF EXISTS public.bogota_casas_view    CASCADE;
DROP VIEW IF EXISTS public.bogota_ciclovias     CASCADE;
DROP VIEW IF EXISTS public.bogota_comercio      CASCADE;
DROP VIEW IF EXISTS public.bogota_equipamiento  CASCADE;
DROP VIEW IF EXISTS public.bogota_landuse       CASCADE;
DROP VIEW IF EXISTS public.bogota_leisure       CASCADE;
DROP VIEW IF EXISTS public.bogota_peatonal      CASCADE;

-- ── Calles ────────────────────────────────────────────────────────────────────
DROP VIEW IF EXISTS tiles.bogota_calles CASCADE;
CREATE VIEW tiles.bogota_calles AS
SELECT
    osm_id,
    highway,
    name,
    way AS geom
FROM public.planet_osm_line
WHERE highway IS NOT NULL
  AND highway NOT IN ('footway', 'path', 'cycleway', 'steps', 'platform');

-- ── Peatonal ──────────────────────────────────────────────────────────────────
DROP VIEW IF EXISTS tiles.bogota_peatonal CASCADE;
CREATE VIEW tiles.bogota_peatonal AS
SELECT
    osm_id,
    highway,
    name,
    way AS geom
FROM public.planet_osm_line
WHERE highway IN ('footway', 'steps', 'pedestrian', 'path');

-- ── Ciclovías ─────────────────────────────────────────────────────────────────
DROP VIEW IF EXISTS tiles.bogota_ciclovias CASCADE;
CREATE VIEW tiles.bogota_ciclovias AS
SELECT
    osm_id,
    name,
    way AS geom
FROM public.planet_osm_line
WHERE highway = 'cycleway';

-- ── Agua ──────────────────────────────────────────────────────────────────────
DROP VIEW IF EXISTS tiles.bogota_agua CASCADE;
CREATE VIEW tiles.bogota_agua AS
SELECT osm_id, waterway, name, way::geometry(Geometry, 3857) AS geom
FROM public.planet_osm_line
WHERE waterway IS NOT NULL
UNION ALL
SELECT osm_id, 'area' AS waterway, name, way::geometry(Geometry, 3857) AS geom
FROM public.planet_osm_polygon
WHERE water IS NOT NULL OR waterway IS NOT NULL;

-- ── Edificios ─────────────────────────────────────────────────────────────────
DROP VIEW IF EXISTS tiles.bogota_edificios CASCADE;
CREATE VIEW tiles.bogota_edificios AS
SELECT
    osm_id,
    building,
    name,
    way AS geom
FROM public.planet_osm_polygon
WHERE building IS NOT NULL;

-- ── Parques ───────────────────────────────────────────────────────────────────
DROP VIEW IF EXISTS tiles.bogota_parques CASCADE;
CREATE VIEW tiles.bogota_parques AS
SELECT
    osm_id,
    COALESCE(leisure, landuse) AS tipo,
    name,
    way AS geom
FROM public.planet_osm_polygon
WHERE leisure IN ('park', 'garden', 'pitch', 'playground')
   OR landuse  IN ('grass', 'forest', 'recreation_ground');

-- ── Leisure (más amplio que parques) ─────────────────────────────────────────
DROP VIEW IF EXISTS tiles.bogota_leisure CASCADE;
CREATE VIEW tiles.bogota_leisure AS
SELECT
    osm_id,
    leisure,
    name,
    way AS geom
FROM public.planet_osm_polygon
WHERE leisure IN ('park', 'garden', 'pitch', 'playground',
                   'sports_centre', 'stadium', 'track', 'nature_reserve');

-- ── Landuse ───────────────────────────────────────────────────────────────────
DROP VIEW IF EXISTS tiles.bogota_landuse CASCADE;
CREATE VIEW tiles.bogota_landuse AS
SELECT
    osm_id,
    landuse,
    name,
    way AS geom
FROM public.planet_osm_polygon
WHERE landuse IN ('residential', 'commercial', 'industrial', 'retail',
                   'grass', 'forest', 'meadow', 'cemetery', 'religious',
                   'recreation_ground', 'construction', 'farmland');

-- ── Comercio ──────────────────────────────────────────────────────────────────
DROP VIEW IF EXISTS tiles.bogota_comercio CASCADE;
CREATE VIEW tiles.bogota_comercio AS
SELECT
    osm_id,
    shop,
    name,
    way AS geom
FROM public.planet_osm_polygon
WHERE shop IN ('mall', 'supermarket', 'car_repair', 'convenience',
               'bakery', 'car', 'clothes', 'hardware');

-- ── Equipamiento (salud, educación, servicios) ───────────────────────────────
DROP VIEW IF EXISTS tiles.bogota_equipamiento CASCADE;
CREATE VIEW tiles.bogota_equipamiento AS
SELECT
    osm_id,
    amenity,
    name,
    way AS geom
FROM public.planet_osm_polygon
WHERE amenity IN ('hospital', 'clinic', 'school', 'university', 'college',
                   'kindergarten', 'bus_station', 'police',
                   'place_of_worship', 'community_centre', 'fuel');

-- ── Arriendos (pines) ─────────────────────────────────────────────────────────
-- OJO: expone telefono/descripcion en un tile público. Si no quieres ese dato
-- viajando por /tiles/bogota_casas_view/{z}/{x}/{y} sin autenticación, quita
-- la columna telefono de aquí (map.js ya no consume esta vista, los pines
-- llegan por /casas vía FastAPI+WebSocket, así que es seguro achicarla).
DROP VIEW IF EXISTS tiles.bogota_casas_view CASCADE;
CREATE VIEW tiles.bogota_casas_view AS
SELECT id, nombre, tipo, descripcion, creado_en,
       ubicacion::geometry(Point, 4326) AS geom
FROM public.casas;

-- ── Índices de soporte (sobre las tablas base, no cambian de schema) ─────────
-- si es necesario estos indices y porque???
-- Porque estos indices de soporte? cual es su funcion, toca tratar de almacenar 
-- la mayor cantidad de recursos en el dispositivo del cliente para evitar 
-- consultas a nuestra db y asi ahorrar costos por trafico web de datos y cachear lo mas 
-- posible con el cliente: investigar cual de estos recursos de nosotros ya estan en el 
-- dispositivo del cliente y no volver a consultar nuestra base de datos

CREATE INDEX IF NOT EXISTS idx_osm_line_highway
    ON public.planet_osm_line USING GIST(way)
    WHERE highway IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_osm_polygon_building
    ON public.planet_osm_polygon USING GIST(way)
    WHERE building IS NOT NULL;

SELECT 'Vistas para Martin creadas correctamente en schema tiles.' AS status;
