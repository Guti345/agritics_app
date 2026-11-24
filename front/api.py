"""Cliente HTTP de la API de Agritics (FastAPI, /api/v1).

Toda llamada lleva el header X-Usuario del usuario que inició sesión (la API lo exige
también en las lecturas). Si la API responde con error, se lanza ErrorApi con el
`detail` TAL CUAL: la API ya lo da en español claro, así que la pantalla lo muestra
sin reescribirlo.
"""

import os
from datetime import date, datetime

import requests
import streamlit as st

# 127.0.0.1 y no "localhost": en Windows "localhost" prueba primero IPv6 (::1), donde uvicorn no
# escucha, y cada llamada se demoraba ~2 s antes de caer a IPv4.
BASE = os.environ.get("AGRITICS_API", "http://127.0.0.1:8000/api/v1").rstrip("/")
ESPERA = 20  # segundos

SIN_CONEXION = "No hay conexión con la API de Agritics. Revisa que el servidor esté encendido."


class ErrorApi(Exception):
    def __init__(self, estado: int | None, detalle: str):
        super().__init__(detalle)
        self.estado = estado      # None = no hubo respuesta (servidor apagado, red)
        self.detalle = detalle


def _a_json(valor):
    """Fechas a ISO para el cuerpo JSON (los formularios devuelven date/datetime)."""
    if isinstance(valor, dict):
        return {k: _a_json(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_a_json(v) for v in valor]
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    return valor


def _cabeceras() -> dict:
    usuario = st.session_state.get("usuario")
    return {"X-Usuario": usuario["usuario"]} if usuario else {}


def _pedir(metodo: str, ruta: str, **kwargs):
    try:
        r = requests.request(metodo, f"{BASE}{ruta}", headers=_cabeceras(), timeout=ESPERA, **kwargs)
    except requests.RequestException:
        raise ErrorApi(None, SIN_CONEXION) from None
    if r.ok:
        if not r.content:
            return None
        return r.json() if "json" in r.headers.get("content-type", "") else r.content
    try:
        detalle = r.json().get("detail")
    except ValueError:
        detalle = None
    if not isinstance(detalle, str) or not detalle:
        detalle = f"La API respondió con un error ({r.status_code})."
    raise ErrorApi(r.status_code, detalle)


def get(ruta: str, **params):
    """Lectura. Los parámetros en None no se envían."""
    return _pedir("GET", ruta, params={k: v for k, v in _a_json(params).items() if v is not None})


def post(ruta: str, datos: dict | None = None, archivos: dict | None = None):
    if archivos:
        return _pedir("POST", ruta, files=archivos, data=_a_json(datos or {}))
    return _pedir("POST", ruta, json=_a_json(datos or {}))


def patch(ruta: str, datos: dict):
    return _pedir("PATCH", ruta, json=_a_json(datos))


def login(usuario: str, clave: str) -> dict:
    """Datos del usuario (sin la clave) o ErrorApi 401 'Usuario o clave incorrectos'."""
    return _pedir("POST", "/auth/login", json={"usuario": usuario, "clave": clave})


# ── listas desplegables ────────────────────────────────────────────────────────
# Cacheadas un minuto por usuario (la API exige X-Usuario en las lecturas).
# Devuelven {etiqueta: id} listo para st.selectbox(options=list(d)).

@st.cache_data(ttl=60, show_spinner=False)
def _catalogo(ruta: str, usuario: str, params: tuple = ()) -> list[dict]:
    return get(ruta, **dict(params))


def _usuario() -> str:
    return st.session_state["usuario"]["usuario"]


def lista(ruta: str, **params) -> list[dict]:
    """GET de un catálogo o del pool, cacheado un minuto (se limpia con refrescar_listas)."""
    return _catalogo(ruta, _usuario(), tuple(sorted((k, str(v)) for k, v in params.items() if v is not None)))


def por_id(ruta: str, **params) -> dict[str, dict]:
    """{id: documento} del catálogo, para poner nombres a los id que devuelve la API."""
    return {d["id"]: d for d in lista(ruta, **params)}


def opciones_lotes(cultivo: str | None = None) -> dict[str, str]:
    """Lotes en estado activo (opcionalmente de un cultivo)."""
    return {l["nombre"]: l["id"] for l in lista("/lotes", estado="activo", cultivo=cultivo)}


def opciones_labores(cultivo: str | None = None) -> dict[str, str]:
    """Labores activas (opcionalmente de un cultivo)."""
    return {l["nombre"]: l["id"] for l in lista("/labores")
            if l["activa"] and (cultivo is None or cultivo in l["cultivos"])}


def opciones_trabajadores(semana: str | None = None) -> dict[str, str]:
    """Trabajadores activos = los del pool de la semana (sin `semana`, la semana en curso)."""
    return {p["trabajador_nombre"]: p["trabajador_id"] for p in lista("/pool", activo="true", semana=semana)}


def refrescar_listas() -> None:
    """Después de crear un trabajador o labor, o de mover el pool, para que las listas lo muestren ya."""
    _catalogo.clear()
