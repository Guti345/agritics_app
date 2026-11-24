"""Clases base Entrada/Salida y conversión a documento de Mongo."""

from datetime import date, datetime, timezone
from typing import Any

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, create_model

from .tiempo import BOGOTA
from .campos import FechaHoraOut, OidOut


def _a_mongo(v: Any, clave: str = "") -> Any:
    if isinstance(v, dict):
        return {k: _a_mongo(x, k) for k, x in v.items()}
    if isinstance(v, list):
        return [_a_mongo(x, clave) for x in v]
    if isinstance(v, datetime):
        return (v if v.tzinfo else v.replace(tzinfo=BOGOTA)).astimezone(timezone.utc)
    if isinstance(v, date):
        return datetime(v.year, v.month, v.day, tzinfo=timezone.utc)
    if isinstance(v, str) and clave.endswith("_id"):
        return ObjectId(v)
    return v


class Entrada(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        use_enum_values=True,   # en el modelo quedan los textos ("jornal"), no el Enum
        validate_default=True,  # los defaults también se validan (p. ej. foto obligatoria)
    )

    def a_mongo(self) -> dict:
        """Documento listo para insertar: sin None, fechas en UTC y *_id como ObjectId."""
        return _a_mongo(self.model_dump(exclude_none=True))


class Salida(BaseModel):
    # Lee "_id" desde Mongo y lo expone como "id" (texto) en el JSON.
    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)
    id: OidOut = Field(validation_alias="_id")


class SalidaCaptura(Salida):
    """Registros de operación: quién y cuándo se capturó (lo pone el servidor)."""
    registrado_por: str
    fecha_captura: FechaHoraOut


def modelo_parcial(create: type[BaseModel], campos: list[str] | None = None, nombre: str | None = None):
    """Cuerpo de un PATCH generado a partir del Create: los mismos campos (o los indicados),
    todos opcionales. Aquí solo se revisa el tipo; las reglas completas se aplican al
    revalidar el documento corregido con el Create (ver `corregir` en back/app/utils.py)."""
    campos = campos or list(create.model_fields)
    definiciones = {
        c: (create.model_fields[c].annotation | None, None) for c in campos
    }
    return create_model(
        nombre or create.__name__.replace("Create", "Update"),
        __config__=ConfigDict(extra="forbid", str_strip_whitespace=True, use_enum_values=True),
        **definiciones,
    )
