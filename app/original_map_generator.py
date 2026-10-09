import os
import json

MARTIN_PUBLIC = os.getenv("MARTIN_PUBLIC", "http://localhost:3000")
# FIX: URLs internas Docker (no localhost)
OSRM_CAR_URL  = os.getenv("OSRM_CAR_URL",  "http://bogota_osrm_car:5000")
OSRM_FOOT_URL = os.getenv("OSRM_FOOT_URL", "http://bogota_osrm_foot:5000")

MAPLIBRE_JS  = "/static/libs/maplibre-gl.js"
MAPLIBRE_CSS = "/static/libs/maplibre-gl.css"


def build_map(casas: list) -> str:
    casas_json = json.dumps([
        {
            "id":          c.id,
            "nombre":      c.nombre,
            "descripcion": c.descripcion,
            "lat":         c.lat,
            "lng":         c.lng,
            "tipo":        c.tipo,
            "telefono":    c.telefono,
            "fotos":       c.fotos,
        }
        for c in casas
    ])

    return f"""
    <link href='{MAPLIBRE_CSS}' rel='stylesheet' />
    <script src='{MAPLIBRE_JS}'></script>
    <style>
        /* ── Ocultar controles MapLibre no deseados ── */
        .maplibregl-ctrl-zoom-in,
        .maplibregl-ctrl-zoom-out,
        .maplibregl-ctrl-compass  {{ display: none !important; }}
        .maplibregl-ctrl-attrib   {{ display: none !important; }}
        .maplibregl-ctrl-logo     {{ display: none !important; }}

        #ml-map {{ position: absolute; inset: 0; }}

        /* ── Botón + publicar ── */
        #btn-add {{
            position: absolute; bottom: 32px; right: 24px;
            width: 58px; height: 58px; border-radius: 50%;
            background: #e63946; color: white;
            font-size: 2rem; border: none; cursor: pointer;
            box-shadow: 0 6px 24px rgba(230,57,70,.45);
            z-index: 900; display: flex;
            align-items: center; justify-content: center;
            transition: transform .15s, box-shadow .15s;
            -webkit-tap-highlight-color: transparent;
            touch-action: manipulation;
        }}
        #btn-add:active {{ transform: scale(.92); box-shadow: 0 2px 10px rgba(230,57,70,.3); }}

        /* ── Botón ubicación ── */
        #btn-locate {{
            position: absolute; bottom: 32px; left: 24px;
            width: 46px; height: 46px; border-radius: 50%;
            background: white; border: none; cursor: pointer;
            box-shadow: 0 4px 16px rgba(0,0,0,.18);
            z-index: 900; display: flex;
            align-items: center; justify-content: center;
            font-size: 1.4rem;
            -webkit-tap-highlight-color: transparent;
            touch-action: manipulation;
            transition: transform .15s;
        }}
        #btn-locate:active {{ transform: scale(.92); }}

        /* ── Overlay ── */
        #overlay {{
            display: none; position: fixed; inset: 0;
            background: rgba(0,0,0,.45); z-index: 1400;
            animation: fadeIn .2s ease;
        }}
        @keyframes fadeIn {{ from {{ opacity:0; }} to {{ opacity:1; }} }}

        /* ── Bottom sheet ── */
        #sheet {{
            display: none; position: fixed;
            left: 0; right: 0; bottom: 0;
            background: #fff; border-radius: 24px 24px 0 0;
            box-shadow: 0 -8px 40px rgba(0,0,0,.22);
            z-index: 1500; flex-direction: column;
            max-height: 92dvh; overflow: hidden;
            animation: slideUp .28s cubic-bezier(.32,1,.44,1);
            font-family: 'Segoe UI', system-ui, sans-serif;
        }}
        @keyframes slideUp {{
            from {{ transform: translateY(100%); }}
            to   {{ transform: translateY(0); }}
        }}
        .sheet-handle {{
            width: 40px; height: 4px; background: #e0e0e0;
            border-radius: 2px; margin: 12px auto 0; flex-shrink: 0;
        }}
        .sheet-inner {{
            overflow-y: auto; padding: 16px 20px 32px;
            flex: 1; -webkit-overflow-scrolling: touch;
        }}
        .sheet-inner h2 {{
            font-size: 1.05rem; font-weight: 700;
            color: #1d1d1d; margin-bottom: 18px;
        }}

        /* Chips tipo vivienda */
        .tipo-grid {{
            display: grid; grid-template-columns: 1fr 1fr;
            gap: 10px; margin-bottom: 20px;
        }}
        .tipo-chip {{
            padding: 12px 10px; border: 2px solid #e8e8e8;
            border-radius: 12px; background: #fafafa;
            cursor: pointer; text-align: center;
            font-size: .83rem; font-weight: 600; color: #444;
            transition: all .15s;
            -webkit-tap-highlight-color: transparent;
            touch-action: manipulation;
        }}
        .tipo-chip .icon {{ font-size: 1.5rem; display: block; margin-bottom: 4px; }}
        .tipo-chip.selected {{ border-color: #e63946; background: #fff0f1; color: #e63946; }}

        /* Inputs */
        .field-label {{
            font-size: .75rem; font-weight: 700; color: #777;
            text-transform: uppercase; letter-spacing: .04em;
            margin-bottom: 6px; display: block;
        }}
        #inp-telefono, #inp-descripcion {{
            width: 100%; border: 1.5px solid #e8e8e8;
            border-radius: 12px; padding: 12px 14px;
            font-size: 16px; font-family: inherit; color: #1d1d1d;
            margin-bottom: 20px; transition: border-color .15s;
            box-sizing: border-box;
        }}
        #inp-telefono:focus, #inp-descripcion:focus {{
            outline: none; border-color: #e63946;
        }}
        #inp-descripcion {{ resize: vertical; min-height: 64px; }}

        /* Fotos */
        .fotos-grid {{
            display: grid; grid-template-columns: repeat(4, 1fr);
            gap: 8px; margin-bottom: 20px;
        }}
        .foto-slot {{
            aspect-ratio: 1; border-radius: 12px;
            border: 2px dashed #e8e8e8; background: #fafafa;
            display: flex; align-items: center; justify-content: center;
            font-size: 1.5rem; cursor: pointer; overflow: hidden;
            position: relative;
            -webkit-tap-highlight-color: transparent;
            transition: border-color .15s;
        }}
        .foto-slot:hover {{ border-color: #e63946; }}
        .foto-slot img {{
            position: absolute; inset: 0;
            width: 100%; height: 100%; object-fit: cover;
        }}
        .foto-slot .remove-foto {{
            position: absolute; top: 3px; right: 3px;
            background: rgba(0,0,0,.55); color: white;
            border: none; border-radius: 50%;
            width: 20px; height: 20px; font-size: .7rem;
            cursor: pointer; display: flex;
            align-items: center; justify-content: center; z-index: 2;
        }}
        #foto-input {{ display: none; }}

        /* Estado GPS */
        #gps-status {{
            display: flex; align-items: center; gap: 8px;
            font-size: .8rem; color: #777; margin-bottom: 20px;
            background: #f5f5f5; padding: 10px 14px; border-radius: 10px;
        }}
        #gps-status .dot {{
            width: 8px; height: 8px; border-radius: 50%;
            background: #ccc; flex-shrink: 0;
            transition: background .3s;
        }}
        #gps-status.ok  .dot {{ background: #2ecc71; }}
        #gps-status.err .dot {{ background: #e63946; }}

        /* Botón guardar */
        #btn-guardar {{
            width: 100%; padding: 16px; background: #e63946;
            color: white; border: none; border-radius: 14px;
            font-size: 1rem; font-weight: 700; cursor: pointer;
            -webkit-tap-highlight-color: transparent;
            touch-action: manipulation;
            transition: background .15s, transform .1s;
        }}
        #btn-guardar:active {{ transform: scale(.98); background: #c0303c; }}
        #btn-guardar:disabled {{ background: #ccc; cursor: not-allowed; }}

        /* ── Toast ── */
        #toast {{
            display: none; position: fixed;
            top: 20px; left: 50%; transform: translateX(-50%);
            background: rgba(20,20,20,.88); color: white;
            padding: 10px 20px; border-radius: 24px;
            font-size: .83rem; z-index: 2000; pointer-events: none;
            white-space: nowrap;
            font-family: 'Segoe UI', system-ui, sans-serif;
            backdrop-filter: blur(8px);
        }}

        /* ── Popup ── */
        .casa-popup {{ font-family: 'Segoe UI', system-ui, sans-serif; padding: 2px; }}
        .casa-popup .popup-fotos {{ display: flex; gap: 4px; margin-bottom: 8px; flex-wrap: wrap; }}
        .casa-popup .popup-fotos img {{
            width: 54px; height: 54px; object-fit: cover; border-radius: 6px;
        }}
        .casa-popup .tipo-badge {{
            display: inline-block; background: #fff0f1; color: #e63946;
            font-size: .72rem; font-weight: 700;
            padding: 2px 8px; border-radius: 10px; margin-bottom: 5px;
        }}
        .casa-popup .desc {{ font-size: .82rem; color: #555; margin: 3px 0; }}
        .casa-popup .tel  {{ font-size: .85rem; color: #1d3557; font-weight: 600; margin-top: 4px; }}

        @keyframes pinPop {{
            0%   {{ transform: scale(0) translateY(-10px); opacity: 0; }}
            70%  {{ transform: scale(1.3) translateY(-3px); }}
            100% {{ transform: scale(1) translateY(0); opacity: 1; }}
        }}
    </style>

    <div id="ml-map"></div>
    <div id="toast"></div>
    <div id="overlay" onclick="cerrarSheet()"></div>

    <button id="btn-locate" onclick="centrarUbicacion()" title="Mi ubicación">📍</button>
    <button id="btn-add"    onclick="abrirSheet()"       title="Publicar arriendo">+</button>

    <!-- Bottom Sheet -->
    <div id="sheet">
        <div class="sheet-handle"></div>
        <div class="sheet-inner">
            <h2>Publicar arriendo</h2>

            <span class="field-label">Tipo de vivienda</span>
            <div class="tipo-grid">
                <div class="tipo-chip" data-tipo="apartamento"   onclick="selTipo(this)"><span class="icon">🏢</span>Apartamento</div>
                <div class="tipo-chip" data-tipo="habitacion"    onclick="selTipo(this)"><span class="icon">🛏</span>Habitación</div>
                <div class="tipo-chip" data-tipo="apartaestudio" onclick="selTipo(this)"><span class="icon">🏠</span>Apartaestudio</div>
                <div class="tipo-chip" data-tipo="casa"          onclick="selTipo(this)"><span class="icon">🏡</span>Casa</div>
            </div>

            <label class="field-label" for="inp-telefono">Número de contacto</label>
            <input id="inp-telefono" type="tel" placeholder="Ej: 300 123 4567" inputmode="tel">

            <label class="field-label" for="inp-descripcion">Descripción (opcional)</label>
            <textarea id="inp-descripcion" placeholder="Ej: 2 hab, cerca al parque, $1.200.000…"></textarea>

            <span class="field-label">Fotos (máx. 4)</span>
            <div class="fotos-grid">
                <div class="foto-slot" id="slot-0" onclick="clickFoto(0)">📷</div>
                <div class="foto-slot" id="slot-1" onclick="clickFoto(1)">📷</div>
                <div class="foto-slot" id="slot-2" onclick="clickFoto(2)">📷</div>
                <div class="foto-slot" id="slot-3" onclick="clickFoto(3)">📷</div>
            </div>
            <input type="file" id="foto-input" accept="image/*" onchange="onFotoSelected(event)">

            <div id="gps-status">
                <div class="dot"></div>
                <span id="gps-text">Obteniendo ubicación…</span>
            </div>

            <button id="btn-guardar" onclick="guardarArriendo()" disabled>Publicar arriendo</button>
        </div>
    </div>

    <script>
    const MARTIN    = "{MARTIN_PUBLIC}";
    const OSRM_CAR  = "{OSRM_CAR_URL}";
    const OSRM_FOOT = "{OSRM_FOOT_URL}";
    let casas            = {casas_json};
    let tipoSeleccionado = null;
    let fotosData        = [null, null, null, null];
    let fotoSlotActivo   = null;
    let userLocation     = null;
    let markersMap       = {{}};
    let targetCasa       = null;

    // ── Mapa ──────────────────────────────────────────────────────────────────
    const map = new maplibregl.Map({{
        container: 'ml-map',
        style: {{
            version: 8,
            sources: {{
                calles:    {{ type:'vector', tiles:[MARTIN+'/bogota_calles/{{z}}/{{x}}/{{y}}'],    minzoom:10, maxzoom:16 }},
                edificios: {{ type:'vector', tiles:[MARTIN+'/bogota_edificios/{{z}}/{{x}}/{{y}}'], minzoom:14, maxzoom:16 }},
                parques:   {{ type:'vector', tiles:[MARTIN+'/bogota_parques/{{z}}/{{x}}/{{y}}'],   minzoom:12, maxzoom:16 }},
                agua:      {{ type:'vector', tiles:[MARTIN+'/bogota_agua/{{z}}/{{x}}/{{y}}'],      minzoom:10, maxzoom:16 }},
            }},
            layers: [
                {{ id:'bg',             type:'background', paint:{{'background-color':'#f0ebe3'}} }},
                {{ id:'parques-fill',   type:'fill',   source:'parques',   'source-layer':'bogota_parques',
                   paint:{{'fill-color':'#c8e6c9','fill-opacity':0.7}} }},
                {{ id:'agua-line',      type:'line',   source:'agua',      'source-layer':'bogota_agua',
                   paint:{{'line-color':'#90caf9','line-width':1.5}} }},
                {{ id:'edificios-fill', type:'fill',   source:'edificios', 'source-layer':'bogota_edificios',
                   paint:{{'fill-color':'#e0e0e0','fill-opacity':0.8}} }},
                {{ id:'edificios-line', type:'line',   source:'edificios', 'source-layer':'bogota_edificios',
                   paint:{{'line-color':'#bdbdbd','line-width':0.5}} }},
                {{ id:'calles-minor',   type:'line',   source:'calles',    'source-layer':'bogota_calles',
                   filter:['in',['get','highway'],['literal',['residential','unclassified','service','living_street']]],
                   paint:{{'line-color':'#ffffff','line-width':1.5}} }},
                {{ id:'calles-main',    type:'line',   source:'calles',    'source-layer':'bogota_calles',
                   filter:['in',['get','highway'],['literal',['primary','secondary','tertiary','trunk','motorway']]],
                   paint:{{'line-color':'#ffffff','line-width':3}} }},
            ]
        }},
        center: [-74.0721, 4.7110],
        zoom: 12,
        attributionControl: false,
    }});

    // Sin zoom, sin brújula
    map.addControl(new maplibregl.NavigationControl({{ showZoom: false, showCompass: false }}));

    map.on('load', () => {{
        // Capa ruta
        map.addSource('ruta', {{ type:'geojson', data:{{ type:'FeatureCollection', features:[] }} }});
        map.addLayer({{
            id: 'ruta-line', type: 'line', source: 'ruta',
            paint: {{ 'line-color':'#e63946', 'line-width':5, 'line-opacity':0.85 }}
        }});
        casas.forEach(c => agregarPin(c, false));
    }});

    // ── Pins ──────────────────────────────────────────────────────────────────
    const TIPO_ICON  = {{ apartamento:'🏢', habitacion:'🛏', apartaestudio:'🏠', casa:'🏡' }};
    const TIPO_LABEL = {{ apartamento:'Apartamento', habitacion:'Habitación', apartaestudio:'Apartaestudio', casa:'Casa' }};

    function agregarPin(casa, animado) {{
        const el = document.createElement('div');
        el.innerHTML = TIPO_ICON[casa.tipo] || '🏠';
        el.style.cssText = 'font-size:26px;cursor:pointer;filter:drop-shadow(0 2px 4px rgba(0,0,0,.35));transition:transform .15s;';
        if (animado) el.style.animation = 'pinPop .4s ease forwards';
        el.onmouseenter = () => el.style.transform = 'scale(1.25)';
        el.onmouseleave = () => el.style.transform = 'scale(1)';

        let fotosHTML = '';
        if (casa.fotos && casa.fotos.length) {{
            fotosHTML = '<div class="popup-fotos">' +
                casa.fotos.slice(0,4).map(f => `<img src="${{f}}">`).join('') +
            '</div>';
        }}

        const popup = new maplibregl.Popup({{ offset:28, maxWidth:'270px' }})
            .setHTML(`
                <div class="casa-popup">
                    ${{fotosHTML}}
                    <span class="tipo-badge">${{TIPO_LABEL[casa.tipo] || casa.tipo}}</span>
                    ${{casa.descripcion ? `<p class="desc">${{casa.descripcion}}</p>` : ''}}
                    <p class="tel">📞 ${{casa.telefono || 'Sin contacto'}}</p>
                    <div style="display:flex;gap:6px;margin-top:10px;">
                        <button onclick="iniciarRuta(${{casa.id}},${{casa.lat}},${{casa.lng}},'${{casa.nombre}}')"
                            style="flex:1;background:#1d3557;color:#fff;border:none;padding:9px;border-radius:8px;cursor:pointer;font-size:.82rem;">
                            🗺 Ruta
                        </button>
                        <button onclick="eliminarCasa(${{casa.id}})"
                            style="background:#ffeef0;color:#e63946;border:2px solid #ffd0d3;padding:9px 12px;border-radius:8px;cursor:pointer;font-size:.85rem;">
                            🗑
                        </button>
                    </div>
                </div>
            `);

        const marker = new maplibregl.Marker({{ element: el }})
            .setLngLat([casa.lng, casa.lat])
            .setPopup(popup)
            .addTo(map);
        markersMap[casa.id] = marker;
    }}

    // ── Sheet ─────────────────────────────────────────────────────────────────
    function abrirSheet() {{
        tipoSeleccionado = null;
        fotosData = [null,null,null,null];
        document.querySelectorAll('.tipo-chip').forEach(c => c.classList.remove('selected'));
        document.getElementById('inp-telefono').value = '';
        document.getElementById('inp-descripcion').value = '';
        [0,1,2,3].forEach(resetSlot);
        document.getElementById('btn-guardar').disabled = true;
        document.getElementById('btn-guardar').textContent = 'Publicar arriendo';
        obtenerGPS();
        document.getElementById('sheet').style.display  = 'flex';
        document.getElementById('overlay').style.display = 'block';
    }}

    function cerrarSheet() {{
        document.getElementById('sheet').style.display  = 'none';
        document.getElementById('overlay').style.display = 'none';
    }}

    // ── GPS — se pide justo al abrir el formulario ────────────────────────────
    function obtenerGPS() {{
        const statusEl = document.getElementById('gps-status');
        const textEl   = document.getElementById('gps-text');
        statusEl.className = '';
        textEl.textContent  = 'Obteniendo ubicación…';
        userLocation = null;
        actualizarBotonGuardar();

        if (!navigator.geolocation) {{
            statusEl.className = 'err';
            textEl.textContent  = 'GPS no disponible en este dispositivo';
            return;
        }}
        navigator.geolocation.getCurrentPosition(
            pos => {{
                userLocation = {{ lat: pos.coords.latitude, lng: pos.coords.longitude }};
                statusEl.className = 'ok';
                textEl.textContent  = `📍 ${{userLocation.lat.toFixed(5)}}, ${{userLocation.lng.toFixed(5)}}`;
                actualizarBotonGuardar();
            }},
            () => {{
                statusEl.className = 'err';
                textEl.textContent  = 'No se pudo obtener la ubicación';
                actualizarBotonGuardar();
            }},
            {{ enableHighAccuracy: true, timeout: 10000 }}
        );
    }}

    function centrarUbicacion() {{
        if (!navigator.geolocation) {{ showToast('GPS no disponible'); return; }}
        navigator.geolocation.getCurrentPosition(
            pos => map.flyTo({{ center: [pos.coords.longitude, pos.coords.latitude], zoom: 15 }}),
            ()  => showToast('No se pudo obtener ubicación')
        );
    }}

    // ── Tipo ──────────────────────────────────────────────────────────────────
    function selTipo(el) {{
        document.querySelectorAll('.tipo-chip').forEach(c => c.classList.remove('selected'));
        el.classList.add('selected');
        tipoSeleccionado = el.dataset.tipo;
        actualizarBotonGuardar();
    }}

    function actualizarBotonGuardar() {{
        document.getElementById('btn-guardar').disabled = !(tipoSeleccionado && userLocation);
    }}

    // ── Fotos ─────────────────────────────────────────────────────────────────
    function clickFoto(idx) {{
        fotoSlotActivo = idx;
        const input = document.getElementById('foto-input');
        input.value = '';
        input.click();
    }}

    function onFotoSelected(e) {{
        const file = e.target.files[0];
        if (!file || fotoSlotActivo === null) return;
        // Comprimir/redimensionar antes de guardar (máx 800px)
        const reader = new FileReader();
        reader.onload = ev => {{
            const img = new Image();
            img.onload = () => {{
                const canvas = document.createElement('canvas');
                const MAX = 800;
                let w = img.width, h = img.height;
                if (w > MAX || h > MAX) {{
                    if (w > h) {{ h = Math.round(h * MAX / w); w = MAX; }}
                    else       {{ w = Math.round(w * MAX / h); h = MAX; }}
                }}
                canvas.width = w; canvas.height = h;
                canvas.getContext('2d').drawImage(img, 0, 0, w, h);
                const data = canvas.toDataURL('image/jpeg', 0.75);
                fotosData[fotoSlotActivo] = data;
                renderSlot(fotoSlotActivo, data);
            }};
            img.src = ev.target.result;
        }};
        reader.readAsDataURL(file);
    }}

    function renderSlot(idx, src) {{
        const slot = document.getElementById('slot-'+idx);
        slot.innerHTML = `<img src="${{src}}"><button class="remove-foto" onclick="event.stopPropagation();quitarFoto(${{idx}})">✕</button>`;
        slot.onclick = () => clickFoto(idx);
    }}

    function quitarFoto(idx) {{
        fotosData[idx] = null;
        resetSlot(idx);
    }}

    function resetSlot(idx) {{
        const slot = document.getElementById('slot-'+idx);
        slot.innerHTML = '📷';
        slot.onclick = () => clickFoto(idx);
    }}

    // ── Guardar ───────────────────────────────────────────────────────────────
    function guardarArriendo() {{
        if (!tipoSeleccionado || !userLocation) return;
        const telefono    = document.getElementById('inp-telefono').value.trim();
        const descripcion = document.getElementById('inp-descripcion').value.trim();
        const fotos       = fotosData.filter(Boolean);

        const payload = {{
            nombre:      TIPO_LABEL[tipoSeleccionado] || tipoSeleccionado,
            descripcion,
            lat:         userLocation.lat,
            lng:         userLocation.lng,
            tipo:        tipoSeleccionado,
            telefono,
            fotos,
        }};

        const btn = document.getElementById('btn-guardar');
        btn.disabled    = true;
        btn.textContent = 'Publicando…';

        fetch('/casas', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify(payload),
        }})
        .then(r => r.ok ? r.json() : r.json().then(e => {{ throw new Error(e.detail) }}))
        .then(casa => {{
            cerrarSheet();
            // FIX 2: pin inmediato desde la respuesta, sin esperar WS
            if (!markersMap[casa.id]) {{
                agregarPin(casa, true);
                casas.push(casa);
            }}
            map.flyTo({{ center: [casa.lng, casa.lat], zoom: 15 }});
            showToast('✅ Arriendo publicado');
        }})
        .catch(err => {{
            btn.disabled    = false;
            btn.textContent = 'Publicar arriendo';
            showToast('❌ ' + err.message);
        }});
    }}

    // ── Routing — FIX 4: perfiles OSRM correctos (driving/walking) ───────────
    function iniciarRuta(id, lat, lng, nombre) {{
        if (!userLocation) {{ showToast('📍 Activa tu GPS primero'); return; }}
        targetCasa = {{ id, lat, lng, nombre }};
        calcularRuta('driving');
    }}

    function calcularRuta(modo) {{
        if (!targetCasa || !userLocation) return;
        // FIX: 'driving' y 'walking' son los perfiles válidos de OSRM
        const perfil = (modo === 'walking') ? 'walking' : 'driving';
        const base   = (modo === 'walking') ? OSRM_FOOT : OSRM_CAR;
        const url    = `${{base}}/route/v1/${{perfil}}/${{userLocation.lng}},${{userLocation.lat}};${{targetCasa.lng}},${{targetCasa.lat}}?overview=full&geometries=geojson`;

        fetch(url)
            .then(r => r.json())
            .then(data => {{
                if (!data.routes?.length) {{ showToast('❌ Sin ruta disponible'); return; }}
                const route  = data.routes[0];
                map.getSource('ruta').setData({{
                    type: 'FeatureCollection',
                    features: [{{ type:'Feature', properties:{{}}, geometry: route.geometry }}]
                }});
                const coords = route.geometry.coordinates;
                const bounds = coords.reduce(
                    (b, c) => b.extend(c),
                    new maplibregl.LngLatBounds(coords[0], coords[0])
                );
                map.fitBounds(bounds, {{ padding: 80 }});
                const dist = (route.distance/1000).toFixed(1);
                const mins = Math.round(route.duration/60);
                showToast(`${{modo==='walking'?'🚶':'🚗'}} ${{dist}} km · ~${{mins}} min`);
            }})
            .catch(() => showToast('❌ Error al calcular ruta'));
    }}

    // ── Eliminar ──────────────────────────────────────────────────────────────
    function eliminarCasa(id) {{
        if (!confirm('¿Eliminar este arriendo?')) return;
        fetch('/casas/' + id, {{ method: 'DELETE' }})
            .then(r => {{
                if (r.status === 204) {{
                    markersMap[id]?.remove();
                    delete markersMap[id];
                    casas = casas.filter(c => c.id !== id);
                }}
            }});
    }}

    // ── WebSocket ─────────────────────────────────────────────────────────────
    function conectarWS() {{
        const proto = location.protocol === 'https:' ? 'wss' : 'ws';
        const ws    = new WebSocket(proto + '://' + location.host + '/ws');
        ws.onmessage = e => {{
            const msg = JSON.parse(e.data);
            if (msg.tipo === 'nuevo_pin') {{
                const c = msg.casa;
                if (!markersMap[c.id]) {{  // evitar duplicado si ya lo agregamos localmente
                    casas.push(c);
                    agregarPin(c, true);
                    showToast('🏠 Nuevo arriendo: ' + (TIPO_LABEL[c.tipo] || c.tipo));
                }}
            }} else if (msg.tipo === 'pin_eliminado') {{
                markersMap[msg.id]?.remove();
                delete markersMap[msg.id];
                casas = casas.filter(c => c.id !== msg.id);
            }}
        }};
        ws.onclose = () => setTimeout(conectarWS, 3000);
        ws.onerror = () => ws.close();
    }}
    conectarWS();

    // FIX 3: reposicionar sheet cuando el teclado virtual aparece (iOS/Android)
    if (window.visualViewport) {{
        window.visualViewport.addEventListener('resize', () => {{
            const sheet = document.getElementById('sheet');
            if (sheet.style.display === 'flex') {{
                const offset = window.innerHeight - window.visualViewport.height;
                sheet.style.maxHeight = (window.visualViewport.height * 0.92) + 'px';
                sheet.style.bottom    = offset + 'px';
            }}
        }});
    }}

    // ── Toast ─────────────────────────────────────────────────────────────────
    let toastTimer = null;
    function showToast(msg) {{
        const el = document.getElementById('toast');
        el.textContent   = msg;
        el.style.display = 'block';
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => el.style.display = 'none', 3000);
    }}
    </script>
    """
