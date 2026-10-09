# Bogotá Arriendos 

# .env porque en main.py estan todas las CREDENCIALES EXPUESTAS

# Para que websockets???
# separar modelos de logica en main.py



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
