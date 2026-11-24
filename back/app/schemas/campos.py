"""Validadores de campo y tipos anotados de entrada y salida."""

import re
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Any

from bson import ObjectId
from pydantic import AfterValidator, BeforeValidator, Field

from .enums import Cultivo
from .tiempo import BOGOTA, ahora, hoy


def _positivo(v):
    if v <= 0:
        raise ValueError("debe ser mayor que 0")
    return v


def _no_negativo(v):
    if v < 0:
        raise ValueError("no puede ser negativo")
    return v


def _texto(v: str) -> str:
    if not v:
        raise ValueError("no puede ir vacío")
    return v


def _oid(v: str) -> str:
    if not ObjectId.is_valid(v):
        raise ValueError("no es un identificador válido (se esperan 24 caracteres hexadecimales)")
    return v


def _porcentaje(v: float) -> float:
    if not 0 <= v <= 100:
        raise ValueError("el porcentaje debe estar entre 0 y 100")
    return v


def _jornales(v: float) -> float:
    if v <= 0:
        raise ValueError("Los jornales deben ser mayores que 0")
    if not (v * 2).is_integer():
        raise ValueError("Los jornales van en pasos de 0,5: 0,5 / 1 / 1,5...")
    return v


def _mm_lluvia(v: float) -> float:
    if v < 0:
        raise ValueError("La lectura de lluvia no puede ser negativa")
    if v > 500:
        raise ValueError("La lectura de lluvia no puede pasar de 500 mm: revisa el dato")
    return v


def _fecha_no_futura(v: date) -> date:
    if v > hoy():
        raise ValueError("No puedes registrar algo de una fecha futura")
    return v


def _fecha_hora_no_futura(v: datetime) -> datetime:
    if v.tzinfo is None:
        v = v.replace(tzinfo=BOGOTA)  # sin zona = hora de Colombia
    if v > ahora() + timedelta(minutes=5):  # margen por relojes desfasados
        raise ValueError("No puedes registrar algo de una fecha futura")
    return v


_SEMANA_ISO = re.compile(r"^(\d{4})-W(\d{2})$")


def _semana_iso(v: str) -> str:
    v = v.upper()
    m = _SEMANA_ISO.match(v)
    try:
        if not m:
            raise ValueError
        date.fromisocalendar(int(m[1]), int(m[2]), 1)  # ¿existe esa semana en ese año?
    except ValueError:
        raise ValueError("La semana va en formato ISO, por ejemplo 2026-W48") from None
    return v


def foto_obligatoria(mensaje: str):
    """Ruta de foto obligatoria con mensaje propio (también si el campo no viene)."""
    def _validar(v: str | None) -> str:
        if v is None or not v.strip():
            raise ValueError(mensaje)
        return v.strip()
    return Annotated[str | None, AfterValidator(_validar), Field(description="Ruta de la foto en /fotos")]


Texto = Annotated[str, AfterValidator(_texto)]


Positivo = Annotated[float, AfterValidator(_positivo), Field(json_schema_extra={"exclusiveMinimum": 0})]


NoNegativo = Annotated[float, AfterValidator(_no_negativo), Field(json_schema_extra={"minimum": 0})]


EnteroPositivo = Annotated[int, AfterValidator(_positivo), Field(json_schema_extra={"minimum": 1})]


EnteroNoNegativo = Annotated[int, AfterValidator(_no_negativo), Field(json_schema_extra={"minimum": 0})]


Porcentaje = Annotated[float, AfterValidator(_porcentaje), Field(json_schema_extra={"minimum": 0, "maximum": 100})]


Jornales = Annotated[float, AfterValidator(_jornales), Field(json_schema_extra={"multipleOf": 0.5}, examples=[1])]


MmLluvia = Annotated[float, AfterValidator(_mm_lluvia), Field(json_schema_extra={"minimum": 0, "maximum": 500})]


Fecha = Annotated[date, AfterValidator(_fecha_no_futura)]          # fecha del evento, no futura


FechaHora = Annotated[datetime, AfterValidator(_fecha_hora_no_futura)]


SemanaISO = Annotated[str, AfterValidator(_semana_iso), Field(examples=["2026-W48"])]


OidIn = Annotated[str, AfterValidator(_oid), Field(examples=["6560f1a2b3c4d5e6f7a8b9c0"])]


# Salida: convierte lo que viene de Mongo a tipos JSON.
def _a_fecha(v: Any) -> Any:
    return v.date() if isinstance(v, datetime) else v


def _a_hora_colombia(v: Any) -> Any:
    if isinstance(v, datetime):
        return (v if v.tzinfo else v.replace(tzinfo=timezone.utc)).astimezone(BOGOTA)
    return v


def _limpiar(v: Any) -> Any:
    """ObjectId -> str y datetime -> hora de Colombia, en cualquier profundidad."""
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, datetime):
        return _a_hora_colombia(v)
    if isinstance(v, dict):
        return {k: _limpiar(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_limpiar(x) for x in v]
    return v


OidOut = Annotated[str, BeforeValidator(str)]


FechaOut = Annotated[date, BeforeValidator(_a_fecha)]


FechaHoraOut = Annotated[datetime, BeforeValidator(_a_hora_colombia)]


Libre = Annotated[Any, BeforeValidator(_limpiar)]


def _cultivos_sin_repetir(v: list) -> list:
    if len(v) != len(set(v)):
        raise ValueError("no repitas cultivos")
    return v


Cultivos = Annotated[list[Cultivo], Field(min_length=1), AfterValidator(_cultivos_sin_repetir)]
