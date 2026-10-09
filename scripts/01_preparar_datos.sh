#!/usr/bin/env bash
# =============================================================================
# 01_preparar_datos.sh
# Descarga Colombia OSM, recorta Bogotá con osmium, carga a PostGIS
# =============================================================================
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

command -v osmium &>/dev/null || error "osmium-tool no encontrado.
  macOS:  brew install osmium-tool
  Ubuntu: sudo apt install osmium-tool"
command -v docker  &>/dev/null || error "Docker no encontrado."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR/.."
DATA_DIR="$ROOT/data"
mkdir -p "$DATA_DIR"

COLOMBIA_PBF="$DATA_DIR/colombia-latest.osm.pbf"
BOGOTA_PBF="$DATA_DIR/bogota.osm.pbf"
BOGOTA_BBOX="-74.270,4.450,-73.980,4.850"

# FIX: realpath no existe en macOS sin coreutils — usar python como alternativa portable
abspath() { python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "$1"; }

# ── PASO 1: Descargar ─────────────────────────────────────────────────────────
if [ -f "$COLOMBIA_PBF" ]; then
    warn "colombia-latest.osm.pbf ya existe — saltando descarga."
else
    info "Descargando Colombia desde Geofabrik (~60 MB)…"
    curl -L --progress-bar \
        "https://download.geofabrik.de/south-america/colombia-latest.osm.pbf" \
        -o "$COLOMBIA_PBF"
    info "Descarga completa."
fi

# ── PASO 2: Recortar Bogotá ───────────────────────────────────────────────────
if [ -f "$BOGOTA_PBF" ]; then
    warn "bogota.osm.pbf ya existe — saltando recorte."
    warn "Para regenerar: rm $BOGOTA_PBF && bash $0"
else
    info "Recortando Bogotá con osmium (bbox=$BOGOTA_BBOX)…"
    osmium extract \
        --bbox "$BOGOTA_BBOX" \
        --strategy=smart \
        "$COLOMBIA_PBF" \
        -o "$BOGOTA_PBF" \
        --overwrite
    info "Recorte listo: $(du -sh "$BOGOTA_PBF" | cut -f1)"
fi

# ── PASO 3: Levantar DB ───────────────────────────────────────────────────────
info "Levantando PostGIS…"
cd "$ROOT"
docker compose up -d db

info "Esperando que PostGIS esté listo…"
until docker compose exec -T db pg_isready -U bogota_user -d bogota_map &>/dev/null; do
    printf '.'; sleep 1
done
echo ""
info "PostGIS listo."

# ── PASO 4: Cargar con osm2pgsql (Docker) ────────────────────────────────────
info "Cargando datos OSM a PostGIS con osm2pgsql…"
info "Esto puede tomar 3-8 minutos…"

DATA_ABS="$(abspath "$DATA_DIR")"
INIT_ABS="$(abspath "$ROOT/init")"

docker compose run --rm loader

info ""
info "✅ Todo listo. Levanta el stack completo:"
info "   docker compose up -d"
info "   Abre: http://localhost:8000"
