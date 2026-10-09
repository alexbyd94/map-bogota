--
-- PostgreSQL database dump
--

-- Dumped from database version 16.4 (Debian 16.4-1.pgdg110+2)
-- Dumped by pg_dump version 16.4 (Debian 16.4-1.pgdg110+2)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: casas; Type: TABLE DATA; Schema: public; Owner: bogota_user
--

COPY public.casas (id, nombre, descripcion, ubicacion, tipo, telefono, fotos, creado_en) FROM stdin;
1	Apartamento Chapinero	Cerca al parque, 2 hab	0101000020E610000039454772F98352C00EBE30992A981240	apartamento	3001234567	[]	2026-04-02 06:34:38.535832+00
2	Casa Usaquén	Barrio tranquilo, 3 hab	0101000020E610000020D26F5F078252C06688635DDCC61240	casa	3109876543	[]	2026-04-02 06:34:38.535832+00
3	Habitación Kennedy	Zona residencial	0101000020E610000013F241CF668952C06C787AA52C831240	habitacion	3205551234	[]	2026-04-02 06:34:38.535832+00
4	Apartaestudio La Candelaria	Centro histórico	0101000020E6100000CDCCCCCCCC8452C03108AC1C5A641240	apartaestudio	3154445566	[]	2026-04-02 06:34:38.535832+00
\.


--
-- Name: casas_id_seq; Type: SEQUENCE SET; Schema: public; Owner: bogota_user
--

SELECT pg_catalog.setval('public.casas_id_seq', 33, true);


--
-- PostgreSQL database dump complete
--

