## Diseño de roles

1. **Rol del usuario** (`admin`, `autorizado`, `basico`) — qué tipo de cuenta es.
2. **Cuota de publicaciones** — cuántas puede crear.
3. **Estado de la cuenta** activo: mas de 1 publicacion, inactivo para quienes no estan autorizados a mas de 1 publicacion, bloqueado para quien incumpla las reglas de la compañia debe ser blocked

Los tres son independientes:

- Un `admin` tiene cuota `NULL` (ilimitada).
- Un `autorizado` puede tener cuota `N`.
- Un `basico` tiene cuota `1` o `0` (según política).

## Tabla de permisos por usuario

Si los permisos pueden variar **por usuario**:

```sql
CREATE TABLE IF NOT EXISTS permisos_publicacion (
    usuario_id          INTEGER PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
    max_publicaciones   INTEGER,          -- NULL = sin límite
    concedido_por       INTEGER REFERENCES usuarios(id),
    concedido_en        TIMESTAMPTZ DEFAULT NOW(),
    estado              varchar(10)
    expira_en           TIMESTAMPTZ       -- NULL = no expira
);
```
- Cada usuario tiene su propio límite.
- Los permisos pueden expirar.
- necesito permisos personalizados por usuario.

## Cómo queda el esquema

┌─────────────────────────────────┐
│  usuarios                       │
│  ├─ id (PK)                     │
│  ├─ google_id (UNIQUE)          │
│  ├─ email (UNIQUE)              │
│  ├─ nombre                      │
│  ├─ foto_url                    │
│  ├─ rol (FK → roles.nombre)     │  ← NUEVO
│  ├─ activo                      │
│  └─ creado_en                   │
└─────────────────────────────────┘
           │
           │ rol
           ▼
┌─────────────────────────────────┐
│  roles                          │  ← NUEVA TABLA
│  ├─ nombre (PK)                 │
│  ├─ max_publicaciones (NULL=∞)  │
│  └─ descripcion                 │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│  casas                          │
│  ├─ id (PK)                     │
│  ├─ usuario_id (FK)             │
│  └─ ...                         │
└─────────────────────────────────┘

# El flujo completo

### 1. Usuario nuevo se registra

### 2. Tú (admin) lo autorizas
`rol = 'admin'` → `max_publicaciones = NULL` → `limite is None` → no hay chequeo.
### Endpoint admin 

```python
def requiere_admin(usuario: dict = Depends(requiere_auth)) -> dict:
    """Extiende requiere_auth exigiendo rol admin."""
    with Session(engine) as session:
        rol = session.execute(
            text("SELECT rol FROM usuarios WHERE id = :uid"),
            {"uid": int(usuario["sub"])},
        ).scalar()

    if rol != "admin":
        raise HTTPException(403, "Solo administradores.")
    return usuario
```
-------------------------------------------------------

## @app.post("/admin/autorizar/{usuario_id}")

```python

@app.post("/admin/autorizar/{usuario_id}")
async def autorizar_usuario(
    usuario_id: int,
    rol: str = "autorizado",
    admin: dict = Depends(requiere_admin),
):
    with Session(engine) as session:
        session.execute(
            text("UPDATE usuarios SET rol = :rol WHERE id = :uid"),
            {"rol": rol, "uid": usuario_id},
        )
        session.commit()
    return {"ok": True}
```

### El usuario publica

```python
# main.py::crear
with Session(engine) as session:
    # Cuántas tiene
    actuales = session.execute(
        text("SELECT COUNT(*) FROM casas WHERE usuario_id = :uid"),
        {"uid": usuario_id}
    ).scalar()

    # Cuál es su límite
    limite = session.execute(
        text("""
            SELECT r.max_publicaciones
            FROM usuarios u
            JOIN roles r ON r.nombre = u.rol
            WHERE u.id = :uid
        """),
        {"uid": usuario_id}
    ).scalar()

    if limite is not None and actuales >= limite:
        raise HTTPException(403, f"Has alcanzado tu límite de {limite} publicaciones.")
```

## Plan de implementación (sesión aparte)

1. **Migración SQL** en `05_seguridad_operaciones.sql`:
   - `CREATE TABLE roles`
   - `INSERT INTO roles` con los 3 valores iniciales
   - `ALTER TABLE usuarios ADD COLUMN rol ...`
2. **Aplicar la migración**: `docker compose down -v && docker compose up -d`
   (o manualmente con `psql` si ya tienes datos que no quieres perder).
3. **Promoverte a admin**:
   ```sql
   UPDATE usuarios SET rol = 'admin' WHERE email = '<tu-email>';
   ```
4. **Añadir helpers _obtener_limite_usuario, _contar_publicaciones_usuario**

```python
def _obtener_limite_usuario(session: Session, usuario_id: int) -> int | None:
    """Devuelve el máximo de publicaciones del usuario.

    None = sin límite (admin).
    0    = no puede publicar.
    N    = máximo N publicaciones.
    """
    return session.execute(
        text("""
            SELECT r.max_publicaciones
            FROM usuarios u
            JOIN roles r ON r.nombre = u.rol
            WHERE u.id = :uid
        """),
        {"uid": usuario_id},
    ).scalar()


def _contar_publicaciones_usuario(session: Session, usuario_id: int) -> int:
    """Cuenta cuántas casas ha publicado el usuario."""
    return session.execute(
        text("SELECT COUNT(*) FROM casas WHERE usuario_id = :uid"),
        {"uid": usuario_id},
    ).scalar() or 0
```
5. **Modificar `crear`** para verificar el límite.

Cambio en crear
Añadir, antes del INSERT:

```python
usuario_id = int(usuario["sub"])

with Session(engine) as session:
    limite = _obtener_limite_usuario(session, usuario_id)
    actuales = _contar_publicaciones_usuario(session, usuario_id)

    if limite is not None and actuales >= limite:
        raise HTTPException(
            403,
            f"Has alcanzado tu límite de {limite} publicaciones. "
            f"Contacta al administrador para ampliarlo.",
        )

    # ... el resto del INSERT
```

6. **Escribir tests** (TDD: rojo → verde):
   - Usuario `basico` (límite 0) que intenta publicar → 403.
   - Usuario `autorizado` con límite 5 que tiene 4 → 201.
   - Usuario `autorizado` con límite 5 que tiene 5 → 403.
   - Usuario `admin` (límite NULL) con 100 publicaciones → 201.
7. **Verificar en producción** que el flujo funciona con tu cuenta admin.

## Fuera del alcance

- **Verificación por SMS/WhatsApp.** Requiere un proveedor (Twilio,  MessageBird). 
-------------------------------------------------------------------------------
