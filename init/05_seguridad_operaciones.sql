-- =============================================================================
-- 05_seguridad_operaciones.sql
-- Usuarios, permisos de publicación, sesiones, idempotencia, outbox.
-- =============================================================================

-- ── Usuarios ──────────────────────────────────────────────────────────────────
-- Sin columna `estado`: todo el que se registra está activo.
-- El "rol" (básico / autorizado / admin) se deriva de permisos_publicacion.
CREATE TABLE IF NOT EXISTS usuarios (
    id          SERIAL PRIMARY KEY,
    google_id   TEXT UNIQUE NOT NULL,
    email       TEXT UNIQUE NOT NULL,
    nombre      TEXT,
    foto_url    TEXT,
    creado_en   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Permisos de publicación ───────────────────────────────────────────────────
-- Asociación 1:0..1 con usuarios.
--   - Sin fila          → básico (1 publicación).
--   - max = N           → autorizado (N publicaciones).
--   - max = NULL        → admin (sin límite).
--   - expira_en pasado  → el permiso se ignora (vuelve a básico).
CREATE TABLE IF NOT EXISTS permisos_publicacion (
    usuario_id          INTEGER PRIMARY KEY
                        REFERENCES usuarios(id) ON DELETE CASCADE,
    max_publicaciones   INTEGER,
    concedido_por       INTEGER REFERENCES usuarios(id),
    concedido_en        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expira_en           TIMESTAMPTZ
);

-- ── Casas → usuarios ──────────────────────────────────────────────────────────
ALTER TABLE casas
    ADD COLUMN IF NOT EXISTS usuario_id INTEGER REFERENCES usuarios(id);
ALTER TABLE casas
    ADD COLUMN IF NOT EXISTS direccion TEXT NOT NULL DEFAULT '';

CREATE INDEX IF NOT EXISTS idx_casas_usuario ON casas(usuario_id);

-- ── Sesiones de autenticación ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS auth_sessions (
    id          BIGSERIAL PRIMARY KEY,
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    jti_hash    CHAR(64) NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked_at  TIMESTAMPTZ
);

-- ── Idempotencia ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS idempotency_keys (
    usuario_id    INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    idem_key      VARCHAR(128) NOT NULL,
    request_hash  CHAR(64) NOT NULL,
    response_json JSONB,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (usuario_id, idem_key)
);

-- ── Outbox (eventos pendientes de publicar) ───────────────────────────────────
CREATE TABLE IF NOT EXISTS outbox_events (
    id               BIGSERIAL PRIMARY KEY,
    event_type       TEXT NOT NULL,
    aggregate_id     BIGINT NOT NULL,
    payload          JSONB NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at     TIMESTAMPTZ,
    attempts         INTEGER NOT NULL DEFAULT 0,
    next_attempt_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_error       TEXT
);

CREATE INDEX IF NOT EXISTS idx_outbox_pending
    ON outbox_events(next_attempt_at)
    WHERE processed_at IS NULL;

-- Historial permanente de cambios relevantes en publicaciones.
CREATE TABLE IF NOT EXISTS auditoria_publicaciones (
    id               BIGSERIAL PRIMARY KEY,
    casa_id          BIGINT NOT NULL,
    accion           TEXT NOT NULL,
    realizada_por    INTEGER NOT NULL REFERENCES usuarios(id),
    propietario_id   INTEGER REFERENCES usuarios(id),
    realizada_en     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    detalle          JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_auditoria_publicaciones_casa
    ON auditoria_publicaciones(casa_id, realizada_en DESC);
