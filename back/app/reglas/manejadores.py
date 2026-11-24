"""Manejadores globales de errores: toda respuesta de error sale en español.

1. Errores de validación de Pydantic (422): se traducen a un mensaje legible,
   p. ej. "Revise los datos: 'cantidad' debe ser mayor que 0."
   Los validadores propios de los DTOs pueden lanzar ValueError("texto en
   español") y ese texto sale tal cual.
2. HTTPException genéricas de Starlette ("Not Found", "Method Not Allowed"...)
   se traducen.
3. Red de seguridad de Mongo: si algo se escapara de la capa de reglas, el
   usuario nunca ve un error interno. Esto NO reemplaza validar antes; si uno de
   estos manejadores se dispara, falta una regla en la API.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pymongo.errors import (
    ConnectionFailure,
    DuplicateKeyError,
    PyMongoError,
    ServerSelectionTimeoutError,
    WriteError,
)
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("uvicorn.error")  # sale en la consola de uvicorn

# --- 422: traducción de errores de Pydantic -------------------------------

_MENSAJES = {
    "missing": "es obligatorio",
    "greater_than": "debe ser mayor que {gt}",
    "greater_than_equal": "debe ser mayor o igual que {ge}",
    "less_than": "debe ser menor que {lt}",
    "less_than_equal": "debe ser menor o igual que {le}",
    "multiple_of": "debe ser múltiplo de {multiple_of}",
    "string_too_short": "debe tener al menos {min_length} caracteres",
    "string_too_long": "debe tener máximo {max_length} caracteres",
    "too_short": "debe tener al menos {min_length} elementos",
    "too_long": "debe tener máximo {max_length} elementos",
    "string_type": "debe ser texto",
    "string_pattern_mismatch": "no tiene el formato esperado",
    "int_type": "debe ser un número entero",
    "int_parsing": "debe ser un número entero",
    "int_from_float": "debe ser un número entero, sin decimales",
    "float_type": "debe ser un número",
    "float_parsing": "debe ser un número",
    "decimal_parsing": "debe ser un número",
    "bool_type": "debe ser sí o no",
    "bool_parsing": "debe ser sí o no",
    "date_type": "debe ser una fecha (AAAA-MM-DD)",
    "date_parsing": "debe ser una fecha (AAAA-MM-DD)",
    "date_from_datetime_parsing": "debe ser una fecha (AAAA-MM-DD)",
    "date_from_datetime_inexact": "debe ser una fecha sin hora",
    "datetime_type": "debe ser fecha y hora (AAAA-MM-DD HH:MM)",
    "datetime_parsing": "debe ser fecha y hora (AAAA-MM-DD HH:MM)",
    "datetime_from_date_parsing": "debe ser fecha y hora (AAAA-MM-DD HH:MM)",
    "time_type": "debe ser una hora (HH:MM)",
    "time_parsing": "debe ser una hora (HH:MM)",
    "enum": "debe ser {expected}",
    "literal_error": "debe ser {expected}",
    "extra_forbidden": "no es un campo permitido",
    "dict_type": "debe ser un objeto con campos",
    "model_type": "debe ser un objeto con campos",
    "model_attributes_type": "debe ser un objeto con campos",
    "list_type": "debe ser una lista",
    "uuid_parsing": "no es un identificador válido",
    "json_invalid": "no es un JSON válido",
}

_PREFIJOS_LOC = {"body", "query", "path", "header", "cookie", "form"}


def _nombre_campo(loc: tuple) -> str:
    partes = [p for p in loc if p not in _PREFIJOS_LOC]
    if not partes:
        return "los datos enviados"
    texto = ""
    for p in partes:
        if isinstance(p, int):
            texto += f"[{p + 1}]"  # posiciones contadas desde 1, como las cuenta la gente
        else:
            texto += ("." if texto else "") + str(p)
    return f"'{texto}'"


def _mensaje_error(err: dict) -> str:
    tipo = err.get("type", "")
    campo = _nombre_campo(tuple(err.get("loc", ())))
    if tipo == "value_error":
        # Validadores propios: ValueError("mensaje en español") -> sale tal cual.
        msg = str(err.get("msg", "")).removeprefix("Value error, ")
        return msg if campo == "los datos enviados" else f"{campo}: {msg}"
    if tipo == "assertion_error":
        return str(err.get("msg", "")).removeprefix("Assertion failed, ")
    plantilla = _MENSAJES.get(tipo)
    if plantilla is None:
        return f"{campo} no es válido"
    ctx = {
        k: (int(v) if isinstance(v, float) and v.is_integer() else v)  # 0.0 -> 0
        for k, v in (err.get("ctx") or {}).items()
    }
    if tipo in ("enum", "literal_error") and isinstance(ctx.get("expected"), str):
        # Pydantic: "'kg', 'racimos' or 'ninguna'" -> "'kg', 'racimos' o 'ninguna'"
        antes, sep, ultimo = ctx["expected"].rpartition(" or ")
        if sep:
            ctx["expected"] = f"{antes} o {ultimo}"
    try:
        return f"{campo} " + plantilla.format(**ctx)
    except (KeyError, IndexError):
        return f"{campo} " + plantilla.split("{")[0].rstrip(": ")


async def _validacion(_: Request, exc: RequestValidationError) -> JSONResponse:
    mensajes = list(dict.fromkeys(_mensaje_error(e) for e in exc.errors()))
    detalle = "Revise los datos: " + "; ".join(mensajes) + "."
    return JSONResponse(
        status_code=422,
        content={"detail": detalle, "errores": mensajes},
    )


# --- HTTPException genéricas ----------------------------------------------

_GENERICOS = {
    "Not Found": "No se encontró lo que busca.",
    "Method Not Allowed": "Esta operación no está permitida aquí.",
    "Unauthorized": "Debe iniciar sesión.",
    "Forbidden": "No tiene permiso para hacer esto.",
    "Internal Server Error": "Ocurrió un error inesperado. Intente de nuevo.",
}


async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    detalle = _GENERICOS.get(exc.detail, exc.detail) if isinstance(exc.detail, str) else exc.detail
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": detalle},
        headers=getattr(exc, "headers", None),
    )


# --- Red de seguridad de Mongo ---------------------------------------------

async def _mongo(request: Request, exc: PyMongoError) -> JSONResponse:
    if isinstance(exc, DuplicateKeyError):
        log.warning("DuplicateKeyError no atajado por las reglas en %s: %s", request.url.path, exc)
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": "Ese registro ya existe; no se guardó de nuevo."},
        )
    if isinstance(exc, WriteError) and exc.code == 121:  # falló el $jsonSchema
        log.warning("Validador $jsonSchema rechazó un documento en %s: %s", request.url.path, exc)
        return JSONResponse(
            status_code=422,
            content={"detail": "Los datos no tienen el formato esperado; revise y vuelva a intentar."},
        )
    if isinstance(exc, (ServerSelectionTimeoutError, ConnectionFailure)):
        log.error("Sin conexión a MongoDB: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "No hay conexión con la base de datos. Verifique que MongoDB esté encendido."},
        )
    log.exception("Error de MongoDB no controlado en %s", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Ocurrió un error al guardar o consultar los datos. Intente de nuevo."},
    )


def registrar_manejadores(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, _validacion)
    app.add_exception_handler(StarletteHTTPException, _http)
    app.add_exception_handler(PyMongoError, _mongo)
