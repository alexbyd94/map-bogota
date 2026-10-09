#!/usr/bin/env bash
# =============================================================================
# 04_deploy_produccion.sh
# Deploy en servidor remoto (Ubuntu/Debian)
# Ejecutar en el SERVIDOR, no en local
# =============================================================================
set -euo pipefail
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info() { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $*"; }

# ── 1. Docker ─────────────────────────────────────────────────────────────────
info "Instalando Docker..."
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# ── 2. osmium-tool ────────────────────────────────────────────────────────────
info "Instalando osmium-tool..."
sudo apt-get update -qq
sudo apt-get install -y osmium-tool

# ── 3. Clonar proyecto ────────────────────────────────────────────────────────
warn "Copia el proyecto al servidor con:"
warn "  rsync -avz bogota-map/ usuario@tuservidor:~/bogota-map/"
warn "O: git clone <repo> ~/bogota-map"

# ── 4. Variables de entorno de producción ─────────────────────────────────────
warn "IMPORTANTE: antes de levantar, edita docker-compose.yml y ajusta:"
warn "  MARTIN_PUBLIC=http://TU_IP_O_DOMINIO:3000"
warn "  (El browser del usuario necesita llegar a Martin directamente para los tiles)"

# ── 5. Preparar datos ─────────────────────────────────────────────────────────
info "Pasos de preparación:"
info "  cd ~/bogota-map"
info "  bash scripts/01_preparar_datos.sh"
info "  bash scripts/02_preparar_osrm.sh"
info "  bash scripts/03_descargar_assets.sh"

# ── 6. Levantar ───────────────────────────────────────────────────────────────
info "Levantar producción:"
info "  docker compose up -d"
info "  docker compose logs -f app   # verificar arranque"

# ── 7. SSL con Let's Encrypt ──────────────────────────────────────────────────
info "Para SSL gratuito con Certbot:"
info "  sudo apt install certbot python3-certbot-nginx"
info "  sudo certbot --nginx -d tudominio.com"
