https://web.facebook.com/watch/?v=270552697826645
https://vkvideo.ru/?q=perdona%20si%20te%20llamo%20amor
https://ok.ru/video/7542630189694

------------------------------------------------------------------------------
# FIX aguas SQL

Encontrado. Ahí está el error.

Estás mezclando *líneas y polígonos en la misma vista* y por eso se ven fuera de cauce.

SELECT... way::geometry(Geometry, 3857) AS geom
FROM planet_osm_line -- esto es LINEA
UNION ALL
SELECT... way::geometry(Geometry, 3857) AS geom
FROM planet_osm_polygon -- esto es POLIGONO

Martin te crea un solo MVT con líneas y polígonos juntos. Si en MapLibre lo pintas como `fill`, 
las líneas se triangulan mal y parecen ríos desbordados.

## Fix - Separa en 2 vistas:

Cambia tu SQL a esto:

-- ── Agua líneas (ríos, quebradas) ──
DROP VIEW IF EXISTS tiles.bogota_agua_line CASCADE;
CREATE VIEW tiles.bogota_agua_line AS
SELECT osm_id, waterway, name, way AS geom
FROM public.planet_osm_line
WHERE waterway IS NOT NULL;

-- ── Agua polígonos (lagos, humedales, rondas) ──
DROP VIEW IF EXISTS tiles.bogota_agua_polygon CASCADE;
CREATE VIEW tiles.bogota_agua_polygon AS
SELECT osm_id, 'area' AS waterway, name, way AS geom
FROM public.planet_osm_polygon
WHERE water IS NOT NULL OR waterway IS NOT NULL;

Ya no necesitas el `::geometry(Geometry, 3857)` porque `planet_osm_line.way` ya viene en 3857 con osm2pgsql.

Y en tu MapLibre:

sources: {
 agua_line: { type: 'vector', tiles: [MARTIN + '/bogota_agua_line/{z}/{x}/{y}'], maxzoom: 22 },
 agua_poly: { type: 'vector', tiles: [MARTIN + '/bogota_agua_polygon/{z}/{x}/{y}'], maxzoom: 22 }
},
layers: [
 {
 id: 'agua-poligono',
 type: 'fill',
 source: 'agua_poly',
 'source-layer': 'bogota_agua_polygon',
 paint: { 'fill-color': '#', 'fill-opacity': 0.5 }
 },
 {
 id: 'agua-linea',
 type: 'line',
 source: 'agua_line',
 'source-layer': 'bogota_agua_line',
 paint: { 'line-color': '#', 'line-width': ['interpolate', ['linear'], ['zoom'], 12, 1, 18, 4] }
 }
]

Con eso cada río queda en su cauce.

Haz el DROP/CREATE y reinicia Martin con `docker restart martin` y prueba en zoom 17-18 sobre el Río Bogotá.

------------------------------------------------------------------------------

`layout` es *CÓMO* se coloca la capa en el mapa, `paint` es *DE QUÉ COLOR* se pinta.

Se ponen los dos dentro de la capa, pero hacen cosas diferentes:

map.addLayer({
 id: 'mi-capa',
 type: 'symbol',
 source: 'bogota',
 layout: { // <-- DÓNDE y CÓMO se coloca
 'icon-image': 'tienda',
 'text-field': ['get', 'name']
 },
 paint: { // <-- DE QUÉ COLOR / QUÉ TAN TRANSPARENTE
 'text-color': 'red'
 }
});

Regla fácil para no confundirte:

*layout = cambia con zoom, paint = no puedes hacer zoom con él?* No.

La regla real de MapLibre:

- *layout*: se calcula al principio. Si lo cambias, el mapa tiene que recalcular todo. Ej: si el texto es visible, si el icono es grande, de dónde sale la línea.
- *paint*: es solo pintura. Se puede cambiar muy rápido sin recalcular.

Qué va en layout según el tipo:

*Si tu layer es `line`:*

layout: {
 'line-cap': 'round', // punta redonda o cuadrada
 'line-join': 'round'
}

*Si tu layer es `symbol` (iconos y textos, es donde más se usa):*

layout: {
 'icon-image': 'marker', // qué icono
 'text-field': ['get', 'name'], // qué texto del properties mostrar
 'text-size': 12,
 'icon-allow-overlap': true // deja que los iconos se encimen
}

*Si tu layer es `fill` o `circle`, casi no tiene layout.* Casi todo es paint.
Dime qué `type` estás usando y te digo qué layout te sirve.
Ah, `type: fill` es el más fácil. Es para *colorear polígonos*.
Si `line` es dibujar solo el borde, `fill` es colorear por dentro.
Para `fill`, casi todo va en `paint`

map.addLayer({
 id: 'bogota_landuse',
 type: 'fill',
 source: 'bogota_landuse',
 'source-layer': 'bogota_landuse',
 paint: {
 'fill-color': 'red', // de qué color
 'fill-opacity': 0.5, // qué tan transparente 0 a 1
 'fill-outline-color': 'black' // color del borde
 },
 layout: {
 'visibility': 'visible' // casi lo único que se usa aquí, para ocultar/mostrar
 }
});

Lo importante de `fill`:

*1. `fill-color`:* puede ser fijo o según la propiedad

// todo rojo
'fill-color': '#'

// según el tipo de uso de suelo
'fill-color': [
 'match',
 ['get', 'landuse'],
 'residential', 'green',
 'commercial', 'blue',
 'park', 'yellow',
 'gray' // si no es ninguno de esos
]

*2. `fill-opacity`:*

'fill-opacity': 0.3 // medio transparente para ver el mapa de abajo

*3. `fill-outline-color`:*
Solo funciona si no usas un borde con `line` encima. Es el borde del polígono.

Si quieres un borde grueso y bonito, lo mejor es hacer 2 capas:

// 1. capa fill para el color de dentro
// 2. capa line para el borde
map.addLayer({ id: 'landuse-fill', type: 'fill', paint: {'fill-color': 'green'} });
map.addLayer({ id: 'landuse-line', type: 'line', paint: {'line-color': 'black', 'line-width': 1} });

¿Para cuál de tus fuentes lo estás usando? `bogota_landuse`, `bogota_agua`?

------------------------------------------------------------------------

Si te refieres a las propiedades del ejercicio anterior, tienes que hacerlo en 2 pasos porque ahora mismo con ese error 500 no te va a salir nada.

1. Primero verifica qué capas SÍ está sirviendo Martin
Abre en el navegador:
http://localhost:3000/catalog
http://localhost:3000/

Ahí te lista todas las fuentes disponibles. Si `bogota_calles`, `bogota_landuse`, `bogota_agua` no salen ahí, o salen con error, es que Martin no las encuentra en Postgres. Ese es tu error 500.

También puedes ver el detalle de una:

http://localhost:3000/bogota_calles

2. Cuando ya carguen las teselas (sin 500), ves las propiedades así:

Ya tienes el código, solo añade esto en la consola del navegador (F12 > Console):

## para ver qué capas tiene tu mapa
map.getStyle().layers.forEach(l => console.log(l.id))

## para ver qué sources hay
console.log(map.getStyle().sources)

## el del ejercicio, para ver las propiedades al hacer clic
map.on('click', 'edificios-fill', e => {
 if (!e.features.length) return;
 console.log(e.features[0].properties);
});

----------------------------------------------------------------------------------------
# implementar imagenes

Perfecto, ya te entendí. Lo que tienes en esa imagen no es una foto 360, es un *render 3D isométrico tipo "dollhouse"*.

Para implementar eso y que el usuario interactúe, hay 2 niveles:

Nivel 1 - Fácil y rápido [lo que usaste en esa imagen]

Eso se hace en *Blender / 3ds Max / SketchUp*. No es código, es modelado 3D.

Flujo para replicar esa imagen:

1. Modelas el apto en Blender [muros 0.15m, con las medidas del plano que te hice]
2. Pones muebles con assets de Ikea/BlenderKit
3. Cámara en *Isométrica 45°* - Ortográfica, no perspectiva
4. Render con Cycles
5. Te queda el PNG con fondo transparente como el que mandaste

Esa imagen sola NO es interactiva. Para que el usuario interactúe le pones hotspots encima:

<div style="position:relative; max-width:800px">
 <img src="tu-apto-3d.png" style="width:100%">

 <!-- Hotspot Sala -->
 <button onclick="abrir360('sala')"
 style="position:absolute; left:38%; top:52%;
 width:24px; height:24px; border-radius:50%;
 background:red; border:2px solid white">
 </button>

 <!-- Hotspot Alcoba -->
 <button onclick="abrir360('alcoba')"
 style="position:absolute; left:68%; top:68%;
 background:red; border-radius:50%">
 </button>

 <!-- Hotspot Cocina -->
 <button onclick="abrir360('cocina')"
 style="position:absolute; left:35%; top:25%">
 </button>
</div>

<div id="visor-360" style="display:none">
 <div id="panorama"></div> <!-- Aquí va Pannellum -->
</div>

Al hacer clic, abres el recorrido 360 real de esa habitación.

Nivel 2 - Pro, 100% interactivo 3D real

Si quieres que el usuario pueda *rotar* esa casita 3D, no usar una imagen fija:

1. Exportas tu modelo de Blender a `.glb`
2. Lo cargas en tu web con Three.js

import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const loader = new GLTFLoader();
loader.load('./apto.glb', (gltf) => {
 scene.add(gltf.scene);
});

// Esto permite rotar, zoom, como si fuera Google Maps 3D
const controls = new OrbitControls(camera, renderer.domElement);

Esto es lo que usan apartamentos.pro, La Haus, etc.

*¿Qué quieres implementar tú?*

A) ¿Solo poner esa imagen 3D bonita con puntos clicables que abran el 360? [Te armo el código en 5 min]
B) ¿Quieres el modelo 3D completo que el usuario pueda rotar? [Necesitas el.glb]

Dime A o B y te paso el código completo listo para tu MapLibre. Si eliges A, ya con la imagen que me mandaste te lo dejo funcionando.:w

