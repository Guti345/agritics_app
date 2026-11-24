"""DTOs de usuarios (el Response nunca incluye la clave)."""

from pydantic import BaseModel, ConfigDict, field_validator

from .enums import Rol
from .campos import Texto
from .base import Entrada, Salida, modelo_parcial


class UsuarioCreate(Entrada):
    nombre: Texto
    usuario: Texto
    clave: str  # llega en claro; el router guarda solo el hash
    rol: Rol
    activo: bool = True

    @field_validator("usuario")
    @classmethod
    def _usuario(cls, v: str) -> str:
        if " " in v:
            raise ValueError("el usuario no puede tener espacios")
        return v.lower()

    @field_validator("clave")
    @classmethod
    def _clave(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("La clave debe tener al menos 6 caracteres")
        return v


class UsuarioResponse(Salida):
    """Nunca incluye la clave."""
    nombre: str
    usuario: str
    rol: Rol
    activo: bool


UsuarioUpdate = modelo_parcial(UsuarioCreate, ["activo", "clave"], "UsuarioUpdate")


class LoginIn(BaseModel):
    """Cuerpo del login (no es un recurso guardado: no tiene Response propio)."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    usuario: str
    clave: str
