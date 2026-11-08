#!/usr/bin/env bash
# =============================================================================
# 02_preparar_osrm.sh
# Preprocesa bogota.osm.pbf para OSRM (vehículo y caminata)
# Solo necesario la primera vez o cuando se actualice el PBF
# =============================================================================
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR/.."
DATA_DIR="$ROOT/data"
BOGOTA_PBF="$DATA_DIR/bogota.osm.pbf"

[ -f "$BOGOTA_PBF" ] || error "bogota.osm.pbf no encontrado. Ejecuta primero:
  bash scripts/01_preparar_datos.sh"

mkdir -p "$DATA_DIR/osrm"
mkdir -p "$DATA_DIR/osrm-foot"

# Copiar pbf a cada directorio de perfil
cp "$BOGOTA_PBF" "$DATA_DIR/osrm/bogota.osm.pbf"
cp "$BOGOTA_PBF" "$DATA_DIR/osrm-foot/bogota.osm.pbf"

# ── Perfil vehículo (driving) ─────────────────────────────────────────────────
if [ -f "$DATA_DIR/osrm/bogota.osrm" ]; then
    warn "OSRM driving ya procesado — saltando."
else
    info "Preprocesando OSRM perfil vehículo (driving)…"
    docker run --rm \
        -v "$(cd "$DATA_DIR/osrm" && pwd):/data" \
        ghcr.io/project-osrm/osrm-backend:latest \
        sh -c 'osrm-extract -p /opt/car.lua /data/bogota.osm.pbf &&
               osrm-partition /data/bogota.osrm &&
               osrm-customize /data/bogota.osrm'
    info "OSRM driving listo."
fi

# ── Perfil caminata (walking) ─────────────────────────────────────────────────
if [ -f "$DATA_DIR/osrm-foot/bogota.osrm" ]; then
    warn "OSRM walking ya procesado — saltando."
else
    info "Preprocesando OSRM perfil caminata (walking)…"
    docker run --rm \
        -v "$(cd "$DATA_DIR/osrm-foot" && pwd):/data" \
        ghcr.io/project-osrm/osrm-backend:latest \
        sh -c 'osrm-extract -p /opt/foot.lua /data/bogota.osm.pbf &&
               osrm-partition /data/bogota.osrm &&
               osrm-customize /data/bogota.osrm'
    info "OSRM walking listo."
fi

info ""
info "✅ Ambos perfiles OSRM listos."
info "   Levanta el stack: docker compose up -d"
