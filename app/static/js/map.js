// ── Estado global ─────────────────────────────────────────────────────────────
let casas            = CASAS_DATA;   // inyectado por map_generator.py
let tipoSeleccionado = null;
let fotosData        = [null, null, null, null];
let fotoSlotActivo   = null;
let userLocation     = null;
let permiteUbicacionManual = false;
let markersMap       = {};
let targetCasa       = null;
let usuarioActualId = null;
let usuarioEsAdmin = false;

const TIPO_ICON  = { apartamento:'🏢', habitacion:'🛏', apartaestudio:'🏠', casa:'🏡' };
const TIPO_LABEL = { apartamento:'Apartamento', habitacion:'Habitación', apartaestudio:'Apartaestudio', casa:'Casa' };
const BOGOTA_BOUNDS = [
[-74.244, 4.456], // Suroeste - Bosa / Soacha
[-73.866, 4.836] // Noreste - Usaquén / La Calera
];
// ── Mapa ──────────────────────────────────────────────────────────────────────
const map = new maplibregl.Map({
    container: 'ml-map',
    style: buildStyle(MARTIN),
    center: [-74.057, 4.677],
    zoom: 14.2,
    minZoom: 10.33, 
    maxZoom: 16.8,
    maxBounds: BOGOTA_BOUNDS,
    renderWorldCopies: false, 
    pitch: 0,
    bearing: 0,
    attributionControl: true,
});


async function cargarUsuarioActual() {
    try {
        const res = await fetch('/auth/me');
        const user = await res.json();
        if (user.autenticado) {
            usuarioActualId = Number(user.id);
            usuarioEsAdmin = user.es_admin === true;
        }
    } catch (err) {
        usuarioActualId = null;
        usuarioEsAdmin = false;
    }
}


registerPoiIcons(map),
// Sin zoom, sin brújula: el zoom debe ser con gestos de los dedos igual la brujula 
map.addControl(new maplibregl.NavigationControl({ showZoom: false, showCompass: true }));



const zoomInfo = document.getElementById('zoom-info');
// Zoom en pantalla
map.on('move', () => {
  zoomInfo.innerHTML = 'Zoom: ' + map.getZoom().toFixed(2);
 });


map.on('load', async () => {
    map.addSource('ruta', { type:'geojson', data:{ type:'FeatureCollection', features:[] } });
    map.addLayer({
        id: 'ruta-line', type: 'line', source: 'ruta',
        paint: { 'line-color':'#e63946', 'line-width':5, 'line-opacity':0.85 }
    });

    await cargarUsuarioActual();
    casas.forEach(c => agregarPin(c, false));
});

// ── Pins ──────────────────────────────────────────────────────────────────────
function agregarPin(casa, animado) {

    const el = document.createElement('div');
    el.textContent = TIPO_ICON[casa.tipo] || '🏠';
    el.style.cssText =
    'font-size:26px;cursor:pointer;' +
    'filter:drop-shadow(0 2px 4px rgba(0,0,0,.35));';
// ---------------------------------------------------------------------------------------------------------
	
    let fotosHTML = '';
    if (casa.fotos && casa.fotos.length) {
        fotosHTML = '<div class="popup-fotos">' +
            casa.fotos.slice(0,4).map(f => `<img src="${f}">`).join('') +
        '</div>';
    }

    const puedeEliminar =
    usuarioEsAdmin ||
    (usuarioActualId !== null &&
     Number(casa.propietario_id) === usuarioActualId);

const botonEliminar = puedeEliminar
    ? `<button onclick="eliminarCasa(${casa.id})"
          style="background:#ffeef0;color:#e63946;border:2px solid #ffd0d3;padding:9px 12px;border-radius:8px;cursor:pointer;font-size:.85rem;">
          🗑
       </button>`
    : '';

    const popup = new maplibregl.Popup({ offset:28, maxWidth:'270px' })
        .setHTML(`
            <div class="casa-popup">
                ${fotosHTML}
                <span class="tipo-badge">${TIPO_LABEL[casa.tipo] || casa.tipo}</span>
                ${casa.descripcion ? `<p class="desc">${casa.descripcion}</p>` : ''}
                ${casa.direccion ? `<p class="desc">📍 ${casa.direccion}</p>` : ''}
                <p class="tel">📞 ${casa.telefono || 'Sin contacto'}</p>
                <div style="display:flex;gap:6px;margin-top:10px;">
                    <button onclick="iniciarRuta(${casa.id},${casa.lat},${casa.lng},'${casa.nombre}')"
                        style="flex:1;background:#1d3557;color:#fff;border:none;padding:9px;border-radius:8px;cursor:pointer;font-size:.82rem;">
                        🗺 Ruta
                    </button>
                    ${botonEliminar}
                </div>
            </div>
        `);

    const marker = new maplibregl.Marker({ element: el }) // Toca configurar una ubicacion aproximeda per seguridad y no la exacta
        .setLngLat([casa.lng, casa.lat])
        .setPopup(popup)
        .addTo(map);
    markersMap[casa.id] = marker;
}

// ── Sheet ─────────────────────────────────────────────────────────────────────
//
async function abrirSheet() {
    // Verificar si está autenticado
    const res = await fetch('/auth/me');
    const user = await res.json();
    console.log('autenticado:', user.autenticado);
    if (!user.autenticado) {
        // Guardar intención y redirigir a Google
         console.log('redirigiendo...');
        sessionStorage.setItem('pendiente_publicar', '1');
        window.location.href = '/auth/google';
        return;
    }
    permiteUbicacionManual = user.limite_publicaciones === null || user.limite_publicaciones > 1;

    // Mostrar foto del usuario en el botón
    if (user.foto) {
        document.getElementById('btn-add').innerHTML =
            `<img src="${user.foto}" style="width:36px;height:36px;border-radius:50%;object-fit:cover;">`;
    }

    _abrirSheetInterno();
}

function _abrirSheetInterno() {
    tipoSeleccionado = null;
    fotosData = [null,null,null,null];
    document.querySelectorAll('.tipo-chip').forEach(c => c.classList.remove('selected'));
    document.getElementById('inp-telefono').value = '';
    document.getElementById('inp-descripcion').value = '';
    document.getElementById('inp-direccion').value = '';
    document.getElementById('inp-lat').value = '';
    document.getElementById('inp-lng').value = '';
    document.getElementById('ubicacion-manual').checked = false;
    document.getElementById('ubicacion-manual-wrap').style.display = permiteUbicacionManual ? 'block' : 'none';
    [0,1,2,3].forEach(resetSlot);
    document.getElementById('btn-guardar').disabled = true;
    document.getElementById('btn-guardar').textContent = 'Publicar arriendo';
    alternarUbicacionManual();
    document.getElementById('sheet').style.display  = 'flex';
    document.getElementById('overlay').style.display = 'block';
}

function alternarUbicacionManual() {
    const manual = permiteUbicacionManual && document.getElementById('ubicacion-manual').checked;
    document.getElementById('gps-status').style.display = manual ? 'none' : 'flex';
    for (const id of ['inp-direccion', 'inp-lat', 'inp-lng']) {
        document.getElementById(id).disabled = !manual;
    }
    if (!manual) obtenerGPS();
    else actualizarBotonGuardar();
}

// Al cargar la página, verificar si venía a publicar
window.addEventListener('load', async () => {
    if (sessionStorage.getItem('pendiente_publicar')) {
        sessionStorage.removeItem('pendiente_publicar');
        const res = await fetch('/auth/me');
        const user = await res.json();
        if (user.autenticado) {
            permiteUbicacionManual = user.limite_publicaciones === null || user.limite_publicaciones > 1;
            _abrirSheetInterno();
        }
    }
});
function cerrarSheet() {
    document.getElementById("sheet").style.display  = "none";
    document.getElementById("overlay").style.display = "none";
}

// ── GPS ───────────────────────────────────────────────────────────────────────
function obtenerGPS() {
    const statusEl = document.getElementById('gps-status');
    const textEl   = document.getElementById('gps-text');
    statusEl.className = '';
    textEl.textContent  = 'Obteniendo ubicación…';

    if (!navigator.geolocation) {
        statusEl.classList.add('error');
        textEl.textContent = 'Tu navegador no soporta geolocalización';
        return;
    }

    navigator.geolocation.getCurrentPosition(
        pos => {
            userLocation = { lat: pos.coords.latitude, lng: pos.coords.longitude };
            statusEl.classList.add('ok');
            textEl.textContent = 'Ubicación obtenida ✓';
            actualizarBotonGuardar();
        },
        err => {
            statusEl.classList.add('error');
            textEl.textContent = 'No se pudo obtener tu ubicación';
        },
        { enableHighAccuracy: true, timeout: 10000 }
    );
}

// ── Centrar el mapa en la ubicación actual ────────────────────────────────────
function centrarUbicacion() {
    if (!navigator.geolocation) {
        showToast('Este navegador no permite obtener la ubicación.');
        return;
    }

    const boton = document.getElementById('btn-locate');
    boton.disabled = true;
    boton.title = 'Buscando ubicación…';

    navigator.geolocation.getCurrentPosition(
        pos => {
            userLocation = { lat: pos.coords.latitude, lng: pos.coords.longitude };
            map.flyTo({ center: [userLocation.lng, userLocation.lat], zoom: 15 });
            boton.disabled = false;
            boton.title = 'Mi ubicación';
            actualizarBotonGuardar();
        },
        err => {
            boton.disabled = false;
            boton.title = 'Mi ubicación';
            if (err.code === err.PERMISSION_DENIED) {
                showToast('Permite el acceso a la ubicación en tu navegador para usar esta función.');
            } else if (err.code === err.TIMEOUT) {
                showToast('No se pudo obtener la ubicación a tiempo. Inténtalo de nuevo.');
            } else {
                showToast('No se pudo obtener tu ubicación. Revisa el GPS y los permisos del navegador.');
            }
        },
        { enableHighAccuracy: true, timeout: 15000, maximumAge: 30000 }
    );
}

// ── Tipo de vivienda ─────────────────────────────────────────────────────────
function selTipo(el) {
    document.querySelectorAll('.tipo-chip').forEach(c => c.classList.remove('selected'));
    el.classList.add('selected');
    tipoSeleccionado = el.dataset.tipo;
    actualizarBotonGuardar();
}

function actualizarBotonGuardar() {
    const manual = permiteUbicacionManual && document.getElementById('ubicacion-manual').checked;
    const lat = document.getElementById('inp-lat').value;
    const lng = document.getElementById('inp-lng').value;
    const ubicacionLista = manual
        ? !!document.getElementById('inp-direccion').value.trim() && lat !== '' && lng !== ''
        : !!userLocation;
    document.getElementById('btn-guardar').disabled = !(tipoSeleccionado && ubicacionLista);
}

// ── Fotos ─────────────────────────────────────────────────────────────────────
function clickFoto(idx) {
    fotoSlotActivo = idx;
    const input = document.getElementById('foto-input');
    input.value = '';
    input.click();
}

function onFotoSelected(e) {
    const file = e.target.files[0];
    if (!file || fotoSlotActivo === null) return;
    const reader = new FileReader();
    reader.onload = ev => {
        const img = new Image();
        img.onload = () => {
            const canvas = document.createElement('canvas');
            const MAX = 800;
            let w = img.width, h = img.height;
            if (w > MAX || h > MAX) {
                if (w > h) { h = Math.round(h * MAX / w); w = MAX; }
                else       { w = Math.round(w * MAX / h); h = MAX; }
            }
            canvas.width = w; canvas.height = h;
            canvas.getContext('2d').drawImage(img, 0, 0, w, h);
            const data = canvas.toDataURL('image/jpeg', 0.75);
            fotosData[fotoSlotActivo] = data;
            renderSlot(fotoSlotActivo, data);
        };
        img.src = ev.target.result;
    };
    reader.readAsDataURL(file);
}

function renderSlot(idx, src) {
    const slot = document.getElementById('slot-'+idx);
    slot.innerHTML = `<img src="${src}"><button class="remove-foto" onclick="event.stopPropagation();quitarFoto(${idx})">✕</button>`;
    slot.onclick = () => clickFoto(idx);
}

function quitarFoto(idx) {
    fotosData[idx] = null;
    resetSlot(idx);
}

function resetSlot(idx) {
    const slot = document.getElementById('slot-'+idx);
    slot.innerHTML = '📷';
    slot.onclick = () => clickFoto(idx);
}

// ── Guardar ───────────────────────────────────────────────────────────────────
// Un usuario qeu no sea root no puede agragar mas de (1) publicacion, debe contratar nuestros servicios
// para que un usuario publique debe validar su numero de telefono mediante un sms o whatsapp
function guardarArriendo() {
    const manual = permiteUbicacionManual && document.getElementById('ubicacion-manual').checked;
    if (!tipoSeleccionado || (!manual && !userLocation)) return;
    const telefono    = document.getElementById('inp-telefono').value.trim();
    const descripcion = document.getElementById('inp-descripcion').value.trim();
    const fotos       = fotosData.filter(Boolean);

    const payload = {
        nombre:      TIPO_LABEL[tipoSeleccionado] || tipoSeleccionado,
        descripcion,
        lat:         manual ? Number(document.getElementById('inp-lat').value) : userLocation.lat,
        lng:         manual ? Number(document.getElementById('inp-lng').value) : userLocation.lng,
        direccion:   manual ? document.getElementById('inp-direccion').value.trim() : '',
        tipo:        tipoSeleccionado,
        telefono,
        fotos,
    };

    const btn = document.getElementById('btn-guardar');
    btn.disabled    = true;
    btn.textContent = 'Publicando…';

    fetch('/casas', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    })
    .then(r => r.ok ? r.json() : r.json().then(e => { throw new Error(e.detail) }))
    .then(casa => {
        cerrarSheet();
        if (!markersMap[casa.id]) {
            agregarPin(casa, true);
            casas.push(casa);
        }
        map.flyTo({ center: [casa.lng, casa.lat], zoom: 15 });
        showToast('✅ Arriendo publicado'); // toca corregir porque tambien puede ser una venta o si yo administro esta publicacion debe destacar ya que yo soy el usuario root admin con capacidad para eliminar cualquier publicacion
    })
    .catch(err => {
        btn.disabled    = false;
        btn.textContent = 'Publicar arriendo';
        showToast('❌ ' + err.message);
    });
}

// ── Routing ───────────────────────────────────────────────────────────────────
function iniciarRuta(id, lat, lng, nombre) {
    if (!userLocation) { showToast('📍 Activa tu GPS primero'); return; }
    targetCasa = { id, lat, lng, nombre };
    calcularRuta('driving');
}

function calcularRuta(modo) {
    if (!targetCasa || !userLocation) return;
    const perfil = (modo === 'walking') ? 'walking' : 'driving';
    const base   = (modo === 'walking') ? OSRM_FOOT : OSRM_CAR;
    const url    = `${base}/route/v1/${perfil}/${userLocation.lng},${userLocation.lat};${targetCasa.lng},${targetCasa.lat}?overview=full&geometries=geojson`;

    fetch(url)
        .then(r => r.json())
        .then(data => {
            if (!data.routes?.length) { showToast('❌ Sin ruta disponible'); return; }
            const route  = data.routes[0];
            map.getSource('ruta').setData({
                type: 'FeatureCollection',
                features: [{ type:'Feature', properties:{}, geometry: route.geometry }]
            });
            const coords = route.geometry.coordinates;
            const bounds = coords.reduce(
                (b, c) => b.extend(c),
                new maplibregl.LngLatBounds(coords[0], coords[0])
            );
            map.fitBounds(bounds, { padding: 80 });
            const dist = (route.distance/1000).toFixed(1);
            const mins = Math.round(route.duration/60);
            showToast(`${modo==='walking'?'🚶':'🚗'} ${dist} km · ~${mins} min`);
        })
        .catch(() => showToast('❌ Error al calcular ruta'));
}

// ── Eliminar ──────────────────────────────────────────────────────────────────
function eliminarCasa(id) {
    if (!confirm('¿Eliminar este arriendo?')) return;
    fetch('/casas/' + id, { method: 'DELETE' })
        .then(r => {
            if (r.status === 204) {
                markersMap[id]?.remove();
                delete markersMap[id];
                casas = casas.filter(c => c.id !== id);
            } else return r.json().then(e => { throw new Error(e.detail || 'No se pudo eliminar la publicación.'); });
        })
        .catch(err => showToast('❌ ' + err.message));
}
// toca añadir un contador para que se eliminen automatica mente cada 45 dias 
// ── WebSocket ─────────────────────────────────────────────────────────────────
// Porque estamos usando websockets??????
function conectarWS() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const ws    = new WebSocket(proto + '://' + location.host + '/ws');
    ws.onmessage = e => {
        const msg = JSON.parse(e.data);
        if (msg.tipo === 'nuevo_pin') {
            const c = msg.casa;
            if (!markersMap[c.id]) {
                casas.push(c);
                agregarPin(c, true);
                showToast('🏠 Nuevo arriendo: ' + (TIPO_LABEL[c.tipo] || c.tipo));
            }
        } else if (msg.tipo === 'pin_eliminado') {
            markersMap[msg.id]?.remove();
            delete markersMap[msg.id];
            casas = casas.filter(c => c.id !== msg.id);
        }
    };
    ws.onclose = () => setTimeout(conectarWS, 3000);
    ws.onerror = () => ws.close();
}
conectarWS();

// Reposicionar sheet cuando el teclado virtual aparece (iOS/Android)
if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', () => {
        const sheet = document.getElementById('sheet');
        if (sheet.style.display === 'flex') {
            const offset = window.innerHeight - window.visualViewport.height;
            sheet.style.maxHeight = (window.visualViewport.height * 0.92) + 'px';
            sheet.style.bottom    = offset + 'px';
        }
    });
}

// ── Toast ─────────────────────────────────────────────────────────────────────
let toastTimer = null;
function showToast(msg) {
    const el = document.getElementById('toast');
    el.textContent   = msg;
    el.style.display = 'block';
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.style.display = 'none', 3000);
}
