# Roles y límite de publicaciones

Fecha: 2026-10-11.

## Contexto

`main.py::crear` no limita cuántas casas puede publicar un usuario. Cualquier
cuenta autenticada con Google puede crear infinitas publicaciones. El
requisito de negocio es distinto:

> Un usuario que no sea root no puede agregar más de (1) publicación.
> Debe contratar nuestros servicios.
> Para que un usuario publique debe validar su número de teléfono mediante
un codigo de estos que se envian via WhatsApp.

- **Root / admin** → sin límite.
- **Usuario autorizado** → N publicaciones, donde N lo decide el admin.
- **Usuario normal (recién registrado)** → 1 publicaciones.

La verificación por SMS/WhatsApp queda fuera del alcance de esta
iteración.

## Modelo de datos

1. **Rol del usuario** (`admin`, `autorizado`, `basico`) — qué tipo de cuenta es.
2. **Cuota de publicaciones** — cuántas puede crear. Se deriva del rol.
3. **Estado de la cuenta** (`activo`) — ya existe en `usuarios`.

```sql
CREATE TABLE IF NOT EXISTS roles (
    nombre              TEXT PRIMARY KEY,
    max_publicaciones   INTEGER,          -- NULL = sin límite
    descripcion         TEXT DEFAULT ''
);

INSERT INTO roles (nombre, max_publicaciones, descripcion) VALUES
    ('basico',     1,    'Usuario recién registrado, 1 puede publicar'),
    ('autorizado', N,    'Usuario autorizado por admin, hasta N publicaciones'),
    ('admin',      NULL, 'Administrador, publicaciones ilimitadas')
ON CONFLICT (nombre) DO NOTHING;

ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS rol TEXT NOT NULL DEFAULT 'basico'
    REFERENCES roles(nombre)
    ON UPDATE CASCADE
    ON DELETE RESTRICT;

-- Índice para el JOIN de "cuántas publicaciones tiene este usuario".
-- idx_casas_usuario ya existe en 05_seguridad_operaciones.sql.
