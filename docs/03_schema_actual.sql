
CREATE VIEW public.bogota_agua AS
 SELECT planet_osm_line.osm_id,
    planet_osm_line.waterway,
    planet_osm_line.name,
    (planet_osm_line.way)::public.geometry(Geometry,3857) AS geom
   FROM public.planet_osm_line
  WHERE (planet_osm_line.waterway IS NOT NULL)
UNION ALL
 SELECT planet_osm_polygon.osm_id,
    'area'::text AS waterway,
    planet_osm_polygon.name,
    planet_osm_polygon.way AS geom
   FROM public.planet_osm_polygon
  WHERE ((planet_osm_polygon.water IS NOT NULL) OR (planet_osm_polygon.waterway IS NOT NULL));



CREATE VIEW public.bogota_calles AS
 SELECT osm_id,
    highway,
    name,
    way AS geom
   FROM public.planet_osm_line
  WHERE ((highway IS NOT NULL) AND (highway <> ALL (ARRAY['footway'::text, 'path'::text, 'cycleway'::text, 'steps'::text, 'platform'::text])));



CREATE TABLE public.casas (
    id integer NOT NULL,
    nombre character varying(200) NOT NULL,
    descripcion text DEFAULT ''::text,
    ubicacion public.geography(Point,4326) NOT NULL,
    tipo character varying(30) DEFAULT 'casa'::character varying,
    telefono character varying(30) DEFAULT ''::character varying,
    fotos jsonb DEFAULT '[]'::jsonb,
    creado_en timestamp with time zone DEFAULT now(),
    usuario_id integer,
    CONSTRAINT casas_tipo_check CHECK (((tipo)::text = ANY ((ARRAY['apartamento'::character varying, 'habitacion'::character varying, 'apartaestudio'::character varying, 'casa'::character varying])::text[])))
);



CREATE VIEW public.bogota_casas_view AS
 SELECT id,
    nombre,
    tipo,
    telefono,
    descripcion,
    creado_en,
    (ubicacion)::public.geometry AS geom
   FROM public.casas;



CREATE VIEW public.bogota_ciclovias AS
 SELECT osm_id,
    name,
    way AS geom
   FROM public.planet_osm_line
  WHERE (highway = 'cycleway'::text);




CREATE VIEW public.bogota_comercio AS
 SELECT osm_id,
    shop,
    name,
    way AS geom
   FROM public.planet_osm_polygon
  WHERE (shop = ANY (ARRAY['mall'::text, 'supermarket'::text, 'car_repair'::text, 'convenience'::text, 'bakery'::text, 'car'::text, 'clothes'::text, 'hardware'::text]));


CREATE VIEW public.bogota_edificios AS
 SELECT osm_id,
    building,
    name,
    way AS geom
   FROM public.planet_osm_polygon
  WHERE (building IS NOT NULL);



CREATE VIEW public.bogota_equipamiento AS
 SELECT osm_id,
    amenity,
    name,
    way AS geom
   FROM public.planet_osm_polygon
  WHERE (amenity = ANY (ARRAY['hospital'::text, 'clinic'::text, 'school'::text, 'university'::text, 'college'::text, 'kindergarten'::text, 'bus_station'::text, 'police'::text, 'place_of_worship'::text, 'community_centre'::text, 'fuel'::text]));



CREATE VIEW public.bogota_landuse AS
 SELECT osm_id,
    landuse,
    name,
    way AS geom
   FROM public.planet_osm_polygon
  WHERE (landuse = ANY (ARRAY['residential'::text, 'commercial'::text, 'industrial'::text, 'retail'::text, 'grass'::text, 'forest'::text, 'meadow'::text, 'cemetery'::text, 'religious'::text, 'recreation_ground'::text, 'construction'::text, 'farmland'::text]));



CREATE VIEW public.bogota_leisure AS
 SELECT osm_id,
    leisure,
    name,
    way AS geom
   FROM public.planet_osm_polygon
  WHERE (leisure = ANY (ARRAY['park'::text, 'garden'::text, 'pitch'::text, 'playground'::text, 'sports_centre'::text, 'stadium'::text, 'track'::text, 'nature_reserve'::text]));



CREATE VIEW public.bogota_parques AS
 SELECT osm_id,
    COALESCE(leisure, landuse) AS tipo,
    name,
    way AS geom
   FROM public.planet_osm_polygon
  WHERE ((leisure = ANY (ARRAY['park'::text, 'garden'::text, 'pitch'::text, 'playground'::text])) OR (landuse = ANY (ARRAY['grass'::text, 'forest'::text, 'recreation_ground'::text])));



CREATE VIEW public.bogota_peatonal AS
 SELECT osm_id,
    highway,
    name,
    way AS geom
   FROM public.planet_osm_line
  WHERE (highway = ANY (ARRAY['footway'::text, 'steps'::text, 'pedestrian'::text, 'path'::text]));



CREATE SEQUENCE public.casas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



ALTER SEQUENCE public.casas_id_seq OWNED BY public.casas.id;



CREATE TABLE public.osm2pgsql_properties (
    property text NOT NULL,
    value text NOT NULL
);



CREATE TABLE public.planet_osm_nodes (
    id bigint NOT NULL,
    lat integer NOT NULL,
    lon integer NOT NULL,
    tags jsonb
);


CREATE INDEX idx_casas_usuario ON public.casas USING btree (usuario_id);

