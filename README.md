# Bogotá Arriendos 


Claro: como ya están versionados, `.gitignore` no dejará de registrar sus cambios. **No uses `git rm --cached`** para esto: los quitaría del repositorio y podrías perderlos al cambiar de rama.

Para conservarlos distintos en `dev` y `main`, pero ignorar automáticamente sus cambios locales en `dev`, usa `skip-worktree`. Por los archivos que mencionaste:

```bash
git switch dev
git update-index --skip-worktree Dockerfile docker-compose.prod.yml Caddyfile
```

Git dejará de mostrar cambios locales en esos archivos en `dev`, sin quitarlos del repositorio. En `main` seguirán las versiones de producción. Puedes comprobarlo con `git status --short`.

Cuando necesites que Git vuelva a detectar cambios en esos archivos en `dev`:

```bash
git update-index --no-skip-worktree Dockerfile docker-compose.prod.yml Caddyfile
```

**Ojo:** `skip-worktree` es local a tu copia del repositorio; no se comparte con otros colaboradores. No lo uses si necesitas guardar cambios de configuración en esos archivos en `dev`.


### Mapa de la ciudad donden ubicar de forma rapida un piso en alquiler

**Stack:** FastAPI · PostGIS · Martin  · OSRM  · MapLibre GL 

---
## Estructura del proyecto
```
bogota-map/
├── app/
│   ├── main.py              # FastAPI backend
│   ├── map_generator.py     # Genera el HTML del mapa con MapLibre
│   ├── templates/
│   │   └── index.html       # Plantilla base 
│   └── static/libs/         # MapLibre GL 
├── init/
│   ├── 01_init.sql          # Crea extensiones + tabla casas
│   └── 02_crear_vistas.sql  # Vistas para Martin 
├── martin/
│   └── config.yaml          # Configuración del tile server
├── data/                    
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```




---

## Setup 

### 1. Prerequisitos
- Docker Desktop 
- `osmium-tool`: `brew install osmium-tool` 

### 2. Descargar assets de MapLibre

### 3. Preparar datos OSM 

### 4. Preparar datos de routing 

### 5. Levantar todo
```bash
docker compose up -d
```

### 6. Abrir la app
[http://localhost:8000](http://localhost:8000)

---

## Uso 

```bash
docker compose up -d      
docker compose down      
docker compose logs -f app 
```

---
## SQL

```sql
 CREATE VIEW bogota_casas_view AS
  SELECT id,
     nombre,
     tipo,
     telefono,
     descripcion,
     creado_en,
     (ubicacion)::geometry AS geom
    FROM casas;

 CREATE VIEW bogota_ciclovias AS
  SELECT osm_id,
     name,
     way AS geom
     FROM planet_osm_line
     WHERE (highway = 'cycleway'::text);

```
---

## Características

- **Mapa** — solo el mapa, sin barras ni botones de zoom
- **Botón +** — abre formulario para publicar un arriendo
- **Formulario**
  - Tipo: Apartamento / Habitación / Apartaestudio / Casa
  - Número de contacto del arrendador
  - Hasta 4 fotos 
  - Ubicación automática por GPS al abrir el formulario
- **Rutas** — cálculo de rutas
- **Tiempo real** — WebSockets: los nuevos arriendos aparecen en todos los clientes abiertos

---

## Producción
