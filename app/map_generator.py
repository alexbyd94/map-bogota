import os
import json
from typing import Protocol, Sequence

class CasaLike(Protocol):

    id: int
    nombre: str
    direccion: str
    descripcion: str
    lat: float
    lng: float
    tipo: str
    telefono: str
    fotos: list[str]

MAPLIBRE_JS  = "/static/libs/maplibre-gl.js"
MAPLIBRE_CSS = "/static/libs/maplibre-gl.css"

def build_map(casas: Sequence[CasaLike]) -> str:

    MARTIN_PUBLIC = os.getenv("MARTIN_PUBLIC", "http://localhost:3000")
    OSRM_CAR_URL  = os.getenv("OSRM_CAR_URL",  "http://localhost:5010")
    OSRM_FOOT_URL = os.getenv("OSRM_FOOT_URL", "http://localhost:5011")
    
    casas_json = json.dumps([
        {
            "id":          c.id,
            "propietario_id": c.propietario_id,
            "nombre":      c.nombre,
            "direccion":   c.direccion,
            "descripcion": c.descripcion,
            "lat":         c.lat,
            "lng":         c.lng,
            "tipo":        c.tipo,
            "telefono":    c.telefono,
            "fotos":       c.fotos,
        }
        for c in casas
    ], ensure_ascii=False,)
    casas_json = casas_json.replace("</", "<\\/")

    return f"""
    <link href='{MAPLIBRE_CSS}' rel='stylesheet' />
    <script src='{MAPLIBRE_JS}'></script>
    <script src='/static/js/map-style.js'></script>
    <link rel='stylesheet' href='/static/css/map.css' />

    <div id="ml-map"></div>
    <div id="toast"></div>
    <div id="overlay" onclick="cerrarSheet()"></div>

    <div id="zoom-info" style="position:absolute; top:10px; left:10px; background:white; padding:5px; z-index:999;"></div>

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

            <div id="ubicacion-manual-wrap" style="display:none">
                <label style="display:flex;gap:8px;align-items:center;margin:0 0 14px;color:#555;font-size:.9rem">
                    <input id="ubicacion-manual" type="checkbox" onchange="alternarUbicacionManual()">
                    Ingresar ubicación de la propiedad
                </label>
                <label class="field-label" for="inp-direccion">Dirección de la propiedad</label>
                <input id="inp-direccion" type="text" placeholder="Ej: Calle 80 # 15-20" oninput="actualizarBotonGuardar()">
                <div class="coords-row">
                    <div><label class="field-label" for="inp-lat">Latitud</label><input id="inp-lat" type="number" step="any" placeholder="4.65" oninput="actualizarBotonGuardar()"></div>
                    <div><label class="field-label" for="inp-lng">Longitud</label><input id="inp-lng" type="number" step="any" placeholder="-74.06" oninput="actualizarBotonGuardar()"></div>
                </div>
            </div>

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
    const CASAS_DATA = {casas_json};
    </script>
    <script src='/static/js/map.js'></script>
    """
