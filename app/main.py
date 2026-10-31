

import os
import json
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Set, List, Optional
from urllib.parse import urlencode

import httpx
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, Depends, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# ── Config ────────────────────────────────────────────────────────────────────
DATABASE_URL         = os.getenv("DATABASE_URL", "postgresql://bogota_user:bogota_pass@localhost:5433/bogota_map")
GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI  = os.getenv("GOOGLE_REDIRECT_URI")
JWT_SECRET           = os.getenv("JWT_SECRET", "dev_secret_change_in_prod")
JWT_ALGORITHM        = "HS256"
JWT_EXPIRE_DAYS      = 30

engine    = create_engine(DATABASE_URL, pool_pre_ping=True)
templates = Jinja2Templates(directory="templates")

# ── JWT helpers ───────────────────────────────────────────────────────────────
def crear_jwt(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(days=JWT_EXPIRE_DAYS)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verificar_jwt(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None

def usuario_actual(auth_token: str | None = Cookie(default=None)) -> dict | None:
    if not auth_token:
        return None
    return verificar_jwt(auth_token)

def requiere_auth(usuario: dict | None = Depends(usuario_actual)):
    if not usuario:
        raise HTTPException(401, "Debes iniciar sesión para publicar.")
    return usuario

# ── DB init ───────────────────────────────────────────────────────────────────
def init_db():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id        SERIAL PRIMARY KEY,
                google_id TEXT UNIQUE NOT NULL,
                email     TEXT UNIQUE NOT NULL,
                nombre    TEXT,
                foto_url  TEXT,
                creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            ALTER TABLE casas ADD COLUMN IF NOT EXISTS usuario_id INTEGER REFERENCES usuarios(id);
            ALTER TABLE casas ADD COLUMN IF NOT EXISTS direccion TEXT NOT NULL DEFAULT '';
            CREATE TABLE IF NOT EXISTS permisos_publicacion (
                usuario_id INTEGER PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
                max_publicaciones INTEGER,
                concedido_por INTEGER REFERENCES usuarios(id),
                concedido_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                expira_en TIMESTAMPTZ
            );
            CREATE TABLE IF NOT EXISTS outbox_events (
                id BIGSERIAL PRIMARY KEY,
                event_type TEXT NOT NULL,
                aggregate_id BIGINT NOT NULL,
                payload JSONB NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                processed_at TIMESTAMPTZ,
                attempts INTEGER NOT NULL DEFAULT 0,
                next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_error TEXT
            );
            CREATE TABLE IF NOT EXISTS auditoria_publicaciones (
                id BIGSERIAL PRIMARY KEY,
                casa_id BIGINT NOT NULL,
                accion TEXT NOT NULL,
                realizada_por INTEGER NOT NULL REFERENCES usuarios(id),
                propietario_id INTEGER REFERENCES usuarios(id),
                realizada_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                detalle JSONB NOT NULL DEFAULT '{}'::jsonb
            );
        """))
        conn.commit()

# ── WebSocket manager ─────────────────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.add(ws)

    def disconnect(self, ws: WebSocket):
        self.active.discard(ws)

    async def broadcast(self, data: dict):
        dead = set()
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.add(ws)
        self.active -= dead

manager = ConnectionManager()

# ── Modelos ───────────────────────────────────────────────────────────────────
class CasaIn(BaseModel):
    nombre:      str
    direccion:   str       = ""
    descripcion: str       = ""
    lat:         float
    lng:         float
    tipo:        str       = "casa"
    telefono:    str       = ""
    fotos:       List[str] = []

class CasaOut(BaseModel):
    id:          int
    propietario_id: int | None = None
    nombre:      str
    direccion:   str = ""
    descripcion: str
    lat:         float
    lng:         float
    tipo:        str
    telefono:    str
    fotos:       List[str]

# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    with engine.connect() as conn:
        conn.execute(text("SELECT PostGIS_Version()"))
    init_db()
    print("PostGIS conectado")
    yield

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="Bogotá Arriendos", lifespan=lifespan)

static_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# ── Helpers DB ────────────────────────────────────────────────────────────────
def _limite_publicaciones(session: Session, usuario_id: int) -> int | None:
    """Devuelve el máximo de publicaciones (1 básico; None sin límite)."""
    row = session.execute(text("""
        SELECT max_publicaciones
        FROM permisos_publicacion
        WHERE usuario_id = :uid
          AND (expira_en IS NULL OR expira_en > NOW())
    """), {"uid": usuario_id}).fetchone()
    return 1 if row is None else row.max_publicaciones

def _es_admin(session: Session, usuario_id: int) -> bool:
    return session.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM permisos_publicacion
            WHERE usuario_id = :uid
              AND max_publicaciones IS NULL
              AND (expira_en IS NULL OR expira_en > NOW())
        )
    """), {"uid": usuario_id}).scalar_one()

def _row_to_out(r) -> CasaOut:
    fotos = r.fotos if r.fotos else []
    if isinstance(fotos, str):
        try:
            fotos = json.loads(fotos)
        except Exception:
            fotos = []
    return CasaOut(
        id=r.id,
        propietario_id=r.propietario_id,
        nombre=r.nombre,
        direccion=r.direccion or "",
        descripcion=r.descripcion,
        lat=r.lat,
        lng=r.lng,
        tipo=r.tipo or "casa",
        telefono=r.telefono or "",
        fotos=fotos,
    )

def _get_casas(session: Session) -> list[CasaOut]:
    rows = session.execute(text("""
        SELECT id, nombre, direccion, descripcion, tipo, telefono, fotos,
               usuario_id AS propietario_id,
               ST_Y(ubicacion::geometry) AS lat,
               ST_X(ubicacion::geometry) AS lng
        FROM casas ORDER BY creado_en DESC
    """)).fetchall()
    return [_row_to_out(r) for r in rows]

# ── Auth endpoints ────────────────────────────────────────────────────────────
@app.get("/auth/google")
async def login_google():
    params = {
        "client_id":     GOOGLE_CLIENT_ID,
        "redirect_uri":  GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope":         "openid email profile",
        "prompt":        "select_account",
    }
    return RedirectResponse("https://accounts.google.com/o/oauth2/auth?" + urlencode(params))

@app.get("/auth/google/callback")
async def google_callback(code: str):
    async with httpx.AsyncClient() as client:
        token_res = await client.post("https://oauth2.googleapis.com/token", data={
            "code":          code,
            "client_id":     GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri":  GOOGLE_REDIRECT_URI,
            "grant_type":    "authorization_code",
        })
        tokens = token_res.json()
        user_res = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        guser = user_res.json()

    with Session(engine) as session:
        row = session.execute(text("""
            INSERT INTO usuarios (google_id, email, nombre, foto_url)
            VALUES (:gid, :email, :nombre, :foto)
            ON CONFLICT (google_id) DO UPDATE
                SET nombre=EXCLUDED.nombre, foto_url=EXCLUDED.foto_url
            RETURNING id, nombre, email, foto_url
        """), {
            "gid":    guser["id"],
            "email":  guser["email"],
            "nombre": guser.get("name"),
            "foto":   guser.get("picture"),
        }).fetchone()
        session.commit()

    token = crear_jwt({
        "sub":    str(row.id),
        "email":  row.email,
        "nombre": row.nombre,
        "foto":   row.foto_url,
    })
    response = RedirectResponse("/")
    response.set_cookie("auth_token", token, httponly=True, samesite="lax", max_age=60*60*24*30)
    return response

@app.get("/auth/me")
async def me(usuario: dict | None = Depends(usuario_actual)):
    if not usuario:
        return {"autenticado": False}
    with Session(engine) as session:
            uid = int(usuario["sub"])
            limite = _limite_publicaciones(session, uid)
            es_admin = _es_admin(session, uid)

    return {
            "autenticado": True,
            "id": uid,
            "es_admin": es_admin,
            "limite_publicaciones": limite,
            **usuario,
    }

@app.get("/auth/logout")
async def logout():
    response = RedirectResponse("/")
    response.delete_cookie("auth_token")
    return response

# ── Casas endpoints ───────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    from map_generator import build_map
    with Session(engine) as session:
        casas = _get_casas(session)
    return templates.TemplateResponse(
        "index.html", {"request": request, "map_html": build_map(casas)}
    )

@app.get("/casas", response_model=list[CasaOut])
async def listar():
    with Session(engine) as session:
        return _get_casas(session)

@app.post("/casas", response_model=CasaOut, status_code=201)
async def crear(casa: CasaIn, usuario: dict = Depends(requiere_auth)):
    if not (4.45 <= casa.lat <= 4.85 and -74.27 <= casa.lng <= -73.98):
        raise HTTPException(422, "Coordenadas fuera de Bogotá.")
    if len(casa.fotos) > 4:
        raise HTTPException(422, "Máximo 4 fotos permitidas.")

    fotos_json = json.dumps(casa.fotos)

    with Session(engine) as session:
        usuario_id = int(usuario["sub"])
        # Serializa publicaciones del mismo usuario para no exceder el límite en paralelo.
        session.execute(text(
            "SELECT id FROM usuarios WHERE id = :uid FOR UPDATE"
        ), {"uid": usuario_id}).fetchone()
        limite = _limite_publicaciones(session, usuario_id)
        if limite is not None:
            publicadas = session.execute(text(
                "SELECT COUNT(*) FROM casas WHERE usuario_id = :uid"
            ), {"uid": usuario_id}).scalar_one()
            if publicadas >= limite:
                raise HTTPException(403, "Has alcanzado tu límite de publicaciones.")

        row = session.execute(text("""
            INSERT INTO casas (nombre, direccion, descripcion, ubicacion, tipo, telefono, fotos, usuario_id)
            VALUES (:nombre, :direccion, :descripcion,
                    ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
                    :tipo, :telefono, cast(:fotos as jsonb), :usuario_id)
            RETURNING id, nombre, direccion, descripcion, tipo, telefono, fotos,
                      usuario_id AS propietario_id,
                      ST_Y(ubicacion::geometry) AS lat,
                      ST_X(ubicacion::geometry) AS lng
        """), {
            "nombre":      casa.nombre,
            "direccion":   casa.direccion,
            "descripcion": casa.descripcion,
            "lat":         casa.lat,
            "lng":         casa.lng,
            "tipo":        casa.tipo,
            "telefono":    casa.telefono,
            "fotos":       fotos_json,
            "usuario_id":  usuario_id,
        }).fetchone()
        session.commit()

    nueva = _row_to_out(row)
    await manager.broadcast({"tipo": "nuevo_pin", "casa": nueva.model_dump()})
    return nueva

@app.delete("/casas/{casa_id}", status_code=204)
async def eliminar(casa_id: int, usuario: dict = Depends(requiere_auth)):
    with Session(engine) as session:
        uid = int(usuario["sub"])
        casa = session.execute(text(
            "SELECT usuario_id FROM casas WHERE id = :id FOR UPDATE"
        ), {"id": casa_id}).fetchone()
        if casa is None:
            raise HTTPException(404, "Publicación no encontrada.")
        if casa.usuario_id != uid and not _es_admin(session, uid):
            raise HTTPException(403, "Solo el propietario o un administrador puede eliminar esta publicación.")
        session.execute(text("""
            INSERT INTO auditoria_publicaciones
                (casa_id, accion, realizada_por, propietario_id, detalle)
            VALUES (:id, 'eliminacion', :uid, :propietario_id,
                    jsonb_build_object('origen', 'api'))
        """), {"id": casa_id, "uid": uid, "propietario_id": casa.usuario_id})
        session.execute(text("""
            INSERT INTO outbox_events (event_type, aggregate_id, payload)
            VALUES ('casa.eliminada', :id,
                    jsonb_build_object('casa_id', :id, 'eliminada_por', :uid,
                                       'propietario_id', :propietario_id))
        """), {"id": casa_id, "uid": uid, "propietario_id": casa.usuario_id})
        session.execute(text("DELETE FROM casas WHERE id=:id"), {"id": casa_id})
        session.commit()
    await manager.broadcast({"tipo": "pin_eliminado", "id": casa_id})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
