#!/usr/bin/env bash
# =============================================================================
# 03_descargar_assets.sh
# Descarga MapLibre GL para servir 100% local (sin CDN externo)
# =============================================================================
set -euo pipefail
GREEN='\033[0;32m'; NC='\033[0m'
info() { echo -e "${GREEN}[INFO]${NC}  $*"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIBS="$SCRIPT_DIR/../app/static/libs"
mkdir -p "$LIBS"

MAPLIBRE_VERSION="4.1.2"

info "Descargando MapLibre GL JS v${MAPLIBRE_VERSION}..."
curl -L "https://unpkg.com/maplibre-gl@${MAPLIBRE_VERSION}/dist/maplibre-gl.js"  -o "$LIBS/maplibre-gl.js"
curl -L "https://unpkg.com/maplibre-gl@${MAPLIBRE_VERSION}/dist/maplibre-gl.css" -o "$LIBS/maplibre-gl.css"

info "Tamaños descargados:"
ls -lh "$LIBS"
info "✅ Assets listos. Reinicia la app:"
info "   docker compose restart app"
