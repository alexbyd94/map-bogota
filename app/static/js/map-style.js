// ## 8. Rendimiento

// October 30, 2026 

// 1. Marcadores HTML vs capas. Cada `Marker` es un elemento DOM, 
// y con más de unos cientos la app se pone lenta. Una capa `circle` o `symbol` 
// dibuja miles en WebGL. Es el cambio más importante que puedes hacer en tu proyecto.

// 2. **Clustering** gratis con GeoJSON:Luego una capa para `['has','point_count']`
//  (los clusters) y otra para `['!',['has','point_count']]` (casas sueltas).
    
//     ```jsx
//     map.addSource('casas', { type:'geojson', data:'/casas.geojson',  cluster:true, clusterMaxZoom:14, clusterRadius:50 });
//     ```
    
// 3. **Pon `minzoom` en las capas pesadas** (edificios, comercio) para que no se pidan teselas innecesarias. Ya lo haces bien a nivel de source.
// 4. **Menos capas, mejores filtros.** Cada capa es un pase de dibujo. Tus tres capas de calles podrían ser una sola con `match` en el color y el ancho.
// 5. **Reduce propiedades** en las teselas: cada atributo extra pesa en cada tesela.
// 6. **`maxzoom` de source realista.** Si tus datos no ganan detalle después del zoom 16, no sirvas más.
// 7. **Iconos en sprite.** Para `symbol` con emojis o imágenes, regístralos con `map.addImage()` una vez, no uno por feature.


// -------------------------------------------------------------------------------------------------------------------
// ===================================================================================================================

// Paleta: manzanas crema, calles gris‑beige, parques verde lima, agua celeste.
// Uso: buildStyle(MARTIN) devuelve el objeto "style" de MapLibre.
const POI_MIN_ZOOM = 16;   // desde este zoom aparecen iconos y nombres de servicios y comercios
const COLOR = {
    bg:        '#f5f6fa',   // manzanas / fondo
    park:      '#cae6a6',
    water:     '#a9d8f0',
    waterLine: '#9ccfea',
    cemetery:  '#e4e6da',
    building:  '#e4e5e9',   // edificios / casas (gris Google)
    buildingLn:'#d5d7dd',
    commerce:  '#fdf1cd',   // comercio (crema Google)
    commerceLn:'#f0daa0',
    roadMinor: '#d0d2d9',   // relleno calles locales
    roadMinorC:'#a6a8ad',   // borde calles locales
    roadMid:   '#d0d2d9',
    roadMidC:  '#dcdfe5',
    roadMajor: '#d0d2d9',
    roadMajorC:'#3b3f52',
    path:      '#d9cfb0',   // senderos peatonales (punteado)
    label:     '#6f6c63',
    labelPark: '#7a9a55',
    halo:      '#f8f5ec',
};

// ── Servicios / equipamientos: grupos, colores, etiquetas e iconos ───────────
// Cada grupo agrupa varios valores del campo 'amenity' de la capa equipamiento.
const POI_GROUPS = {
    salud:     { amenities: ['hospital', 'clinic'],
                 color: '#d93025', fill: '#fbe0dd', line: '#efbdb8', emoji: '🏥' },
    educacion: { amenities: ['school', 'college', 'university', 'kindergarten'],
                 color: '#4f6b8a', fill: '#dfe6ef', line: '#c6d1e0', emoji: '🎓' },
    gobierno:  { amenities: ['townhall', 'courthouse', 'police', 'fire_station', 'public_building', 'post_office'],
                 color: '#4f6b8a', fill: '#dfe6ef', line: '#c6d1e0', emoji: '' },
    cultura:   { amenities: ['museum', 'library', 'theatre', 'arts_centre', 'cinema', 'community_centre'],
                 color: '#8e4ec6', fill: '#ece1f6', line: '#d8c4ec', emoji: '' },
    culto:     { amenities: ['place_of_worship'],
                 color: '#5f6368', fill: '#e6e7ea', line: '#d3d5da', emoji: '⛪︎'},
    transporte:{ amenities: ['bus_station'],
                 color: '#1a73e8', fill: '#dde8f8', line: '#bcd2f1', emoji: '' },
    gasolina:  { amenities: ['fuel'],
                 color: '#5f6368', fill: '#e4e5e9', line: '#d5d7dd', emoji: '' },
    otros:     { amenities: [],
                 color: '#5f6368', fill: '#e4e5e9', line: '#d5d7dd', emoji: '' },
};
const POI_COMERCIO = { color: '#1a73e8', emoji: '' };

// Nombre en español cuando el elemento no trae 'name'
const POI_LABEL_ES = {
    hospital: 'Hospital', clinic: 'Clínica',
    school: 'Colegio', college: 'Colegio', university: 'Universidad', kindergarten: 'Jardín infantil',
    townhall: 'Alcaldía', courthouse: 'Juzgado', police: 'Policía', fire_station: 'Bomberos',
    public_building: 'Entidad pública', post_office: 'Correo',
    museum: 'Museo', library: 'Biblioteca', theatre: 'Teatro', arts_centre: 'Centro cultural',
    cinema: 'Cine', community_centre: 'Salón comunal', place_of_worship: 'Iglesia',
    bus_station: 'Estación de buses', fuel: 'Gasolinera',
};

// ['match', ['get','amenity'], ...] → valor por grupo (fn recibe el grupo y su clave)
function matchByGroup(fn) {
    const expr = ['match', ['get', 'amenity']];
    for (const [key, g] of Object.entries(POI_GROUPS)) {
        if (g.amenities.length) expr.push(g.amenities, fn(g, key));
    }
    expr.push(fn(POI_GROUPS.otros, 'otros'));
    return expr;
}
function categoryLabelExpr() {
    const expr = ['match', ['get', 'amenity']];
    for (const [k, v] of Object.entries(POI_LABEL_ES)) expr.push(k, v);
    expr.push('Servicio');
    return expr;
}

// Dibuja los iconos (círculo blanco con borde de color + emoji) cuando MapLibre los pide.
function registerPoiIcons(map) {
    const defs = { 'poi-comercio': POI_COMERCIO };
    for (const [key, g] of Object.entries(POI_GROUPS)) defs[`poi-${key}`] = g;

    map.on('styleimagemissing', (e) => {
        const d = defs[e.id];
        if (!d) return;
        const size = 30, ratio = 2;
        const c = document.createElement('canvas');
        c.width = c.height = size * ratio;
        const ctx = c.getContext('2d');
        ctx.scale(ratio, ratio);
        // Solo el emoji (sin círculo), con un halo blanco para que se lea sobre cualquier fondo
        ctx.font = '20px "Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji",sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.shadowColor = '#ffffff';
        ctx.shadowBlur = 4;
        ctx.fillText(d.emoji, size / 2, size / 2 + 1);   // halo
        ctx.shadowBlur = 0;
        ctx.shadowColor = 'transparent';
        ctx.fillText(d.emoji, size / 2, size / 2 + 1);   // emoji nítido encima
        if (!map.hasImage(e.id)) {
            map.addImage(e.id, ctx.getImageData(0, 0, c.width, c.height), { pixelRatio: ratio });
        }
    });
}


function buildStyle(MARTIN) {
    const vec = (name, minzoom, maxzoom = 16) => ({
        type: 'vector',
        tiles: [`${MARTIN}/bogota_${name}/{z}/{x}/{y}`],
        minzoom,
        maxzoom,
    });

    // Clases de vía: [id, valores de 'highway', ancho z12, ancho z16, relleno, borde]
    const ROAD_CLASSES = [
        ['minor', ['residential', 'unclassified', 'living_street', 'service', 'road'], 1,   9, COLOR.roadMinor, COLOR.roadMinorC],
        ['mid',   ['tertiary', 'tertiary_link', 'secondary', 'secondary_link'],        2.5, 14, COLOR.roadMid,   COLOR.roadMidC],
        ['major', ['primary', 'primary_link', 'trunk', 'trunk_link', 'motorway', 'motorway_link'], 4, 20, COLOR.roadMajor, COLOR.roadMajorC],
    ];

    // Las clases mid/major se filtran por 'highway'. 'minor' es "todo lo demás",
    // así que las calles se pintan aunque el tile no traiga la columna 'highway'.
    const HW = ['coalesce', ['get', 'highway'], ''];
    const NOT_MINOR = ROAD_CLASSES.slice(1).flatMap(c => c[1]);
    const roadFilter = (values, id) => id === 'minor'
        ? ['!', ['in', HW, ['literal', NOT_MINOR]]]
        : ['in', HW, ['literal', values]];
    const roadWidth  = (w12, w16, extra = 0) => [
        'interpolate', ['linear'], ['zoom'],
        10, Math.max(0.6, w12 * 0.4) + extra,
        12, w12 + extra,
        16, w16 + extra,
        19, (w16 + extra) * 2.2,
    ];

    const roadCasings = ROAD_CLASSES.map(([id, values, w12, w16, , casing]) => ({
        id: `calles-casing-${id}`,
        type: 'line',
        source: 'calles',
        'source-layer': 'bogota_calles',
        minzoom: id === 'minor' ? 13 : 10,
        filter: roadFilter(values, id),
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': casing, 'line-width': roadWidth(w12, w16, 1.6) },
    }));

    const roadFills = ROAD_CLASSES.map(([id, values, w12, w16, fill]) => ({
        id: `calles-fill-${id}`,
        type: 'line',
        source: 'calles',
        'source-layer': 'bogota_calles',
        minzoom: id === 'minor' ? 13 : 10,
        filter: roadFilter(values, id),
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': fill, 'line-width': roadWidth(w12, w16) },
    }));

    const parkLabel = (id, source) => ({
        id,
        type: 'symbol',
        source,
        'source-layer': `bogota_${source}`,
        minzoom: 14.5,
        filter: ['has', 'name'],
        layout: {
            'text-field': ['get', 'name'],
            'text-font': ['Open Sans Regular', 'Arial Unicode MS Regular'],
            'text-size': ['interpolate', ['linear'], ['zoom'], 14.5, 11, 18, 16],
            'text-letter-spacing': 0.25,
            'text-max-width': 8,
        },
        paint: {
            'text-color': COLOR.labelPark,
            'text-halo-color': COLOR.halo,
            'text-halo-width': 1.2,
        },
    });

    return {
        version: 8,
        glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf', // TODO: servir en local
        sources: {
            landuse:      vec('landuse', 11),
            leisure:      vec('leisure', 12),
            parques:      vec('parques', 12),
            agua:         vec('agua', 10),
            edificios:    vec('edificios', 14),
            comercio:     vec('comercio', 14),
            equipamiento: vec('equipamiento', 13),
            calles:       vec('calles', 10),
            ciclovias:    vec('ciclovias', 13),
            peatonal:     vec('peatonal', 14),
        },
        layers: [
            { id: 'bg', type: 'background', paint: { 'background-color': COLOR.bg } },

            // ── Áreas verdes (solo las clases verdes; lo demás NO se pinta) ──
            {
                id: 'landuse-fill', type: 'fill', source: 'landuse', 'source-layer': 'bogota_landuse', minzoom: 11,
                filter: ['in', ['get', 'landuse'], ['literal', ['grass', 'forest', 'meadow', 'recreation_ground', 'cemetery']]],
                paint: {
                    'fill-color': ['match', ['get', 'landuse'], 'cemetery', COLOR.cemetery, COLOR.park],
                    'fill-antialias': false,
                },
            },
            { id: 'leisure-fill', type: 'fill', source: 'leisure', 'source-layer': 'bogota_leisure',
              paint: { 'fill-color': COLOR.park, 'fill-antialias': false } },
            { id: 'parques-fill', type: 'fill', source: 'parques', 'source-layer': 'bogota_parques',
              paint: { 'fill-color': COLOR.park, 'fill-antialias': false } },

            // ── Agua ──
            { id: 'agua-fill', type: 'fill', source: 'agua', 'source-layer': 'bogota_agua',
              paint: { 'fill-color': COLOR.water } },
            { id: 'agua-line', type: 'line', source: 'agua', 'source-layer': 'bogota_agua',
              paint: {
                  'line-color': COLOR.waterLine,
                  'line-width': ['interpolate', ['linear'], ['zoom'], 10, 1, 16, 4],
              } },

            // ── Edificios y casas (gris Google) ──
            {
                id: 'edificios-fill', type: 'fill', source: 'edificios', 'source-layer': 'bogota_edificios', minzoom: 14.5,
                paint: {
                    'fill-color': COLOR.building,
                    'fill-outline-color': COLOR.buildingLn,
                    'fill-opacity': ['interpolate', ['linear'], ['zoom'], 14.5, 0, 15.5, 1],
                },
            },

            // ── Comercio (crema Google) ──
            {
                id: 'comercio-fill', type: 'fill', source: 'comercio', 'source-layer': 'bogota_comercio', minzoom: 14.5,
                paint: {
                    'fill-color': COLOR.commerce,
                    'fill-outline-color': COLOR.commerceLn,
                    'fill-opacity': ['interpolate', ['linear'], ['zoom'], 14.5, 0, 15.5, 1],
                },
            },

            // ── Servicios: hospitales, colegios, entidades… tinte según categoría ──
            {
                id: 'equipamiento-fill', type: 'fill', source: 'equipamiento', 'source-layer': 'bogota_equipamiento', minzoom: 14,
                paint: {
                    'fill-color': matchByGroup(g => g.fill),
                    'fill-outline-color': matchByGroup(g => g.line),
		    'fill-opacity': 0.6,
                },
            },
		// docker exec -it bogota_db psql -U bogota_user -d bogota_map -c \
		// "SELECT count(*) FILTER (WHERE building IS NOT NULL) AS con_building,
        	// count(*) FILTER (WHERE building IS NULL AND 
		// (amenity IS NOT NULL OR shop IS NOT NULL OR tourism IS NOT NULL OR office IS NOT NULL)) AS con_uso_sin_building
 		// FROM planet_osm_polygon;"

            // ── Senderos peatonales punteados ──
            {
                id: 'peatonal-line', type: 'line', source: 'peatonal', 'source-layer': 'bogota_peatonal', minzoom: 14,
                layout: { 'line-cap': 'round' },
                paint: {
                    'line-color': COLOR.path,
                    'line-width': ['interpolate', ['linear'], ['zoom'], 14, 1.5, 18, 4],
                    'line-dasharray': [0.6, 1.6],
                },
            },

            // ── Calles: primero todos los bordes, luego los rellenos ──
            ...roadCasings,
            ...roadFills,

            // ── Etiquetas ──
            parkLabel('parques-labels', 'parques'),
            parkLabel('leisure-labels', 'leisure'),
            {
                id: 'equipamiento-labels', type: 'symbol', source: 'equipamiento', 'source-layer': 'bogota_equipamiento', minzoom: POI_MIN_ZOOM,
                layout: {
                    'icon-image': matchByGroup((g, key) => `poi-${key}`),
                    'icon-allow-overlap': false,
                    'text-field': ['case', ['has', 'name'],
                        ['format', ['get', 'name'], {}, '\n', {}, categoryLabelExpr(), { 'font-scale': 0.85 }],
                        ['format', categoryLabelExpr(), {}]],
                    'text-font': ['Open Sans Regular', 'Arial Unicode MS Regular'],
                    'text-size': ['interpolate', ['linear'], ['zoom'], 15, 11, 18, 14],
                    'text-anchor': 'top',
                    'text-offset': [0, 1.0],
                    'text-max-width': 9,
                    'text-optional': true,
                },
                paint: {
                    'text-color': matchByGroup(g => g.color),
                    'text-halo-color': '#ffffff',
                    'text-halo-width': 1.4,
                },
            },
            {
                id: 'comercio-labels', type: 'symbol', source: 'comercio', 'source-layer': 'bogota_comercio', minzoom: POI_MIN_ZOOM,
                filter: ['has', 'name'],
                layout: {
                    'icon-image': 'poi-comercio',
                    'text-field': ['get', 'name'],
                    'text-font': ['Open Sans Regular', 'Arial Unicode MS Regular'],
                    'text-size': 12,
                    'text-anchor': 'top',
                    'text-offset': [0, 1.0],
                    'text-max-width': 9,
                    'text-optional': true,
                },
                paint: {
                    'text-color': POI_COMERCIO.color,
                    'text-halo-color': '#ffffff',
                    'text-halo-width': 1.4,
                },
            },
            {
                id: 'calles-labels', type: 'symbol', source: 'calles', 'source-layer': 'bogota_calles', minzoom: 14.5,
                filter: ['has', 'name'],
                layout: {
                    'symbol-placement': 'line',
                    'text-field': ['get', 'name'],
                    'text-font': ['Open Sans Regular', 'Arial Unicode MS Regular'],
                    'text-size': ['interpolate', ['linear'], ['zoom'], 14.5, 11, 18, 14],
                    'text-letter-spacing': 0.12,
                    'symbol-spacing': 280,
                },
                paint: {
                    'text-color': COLOR.label,
                    'text-halo-color': COLOR.halo,
                    'text-halo-width': 1.2,
                },
            },
        ],
    };
}
