"""DTOs de unidades."""

from pydantic import Field

from .campos import Positivo, Texto
from .base import Entrada, Salida, modelo_parcial


class UnidadCreate(Entrada):
    nombre: Texto
    equivalencias: dict[str, Positivo] = Field(
        default_factory=dict, examples=[{"arroba": 12.5, "carga": 125, "bulto": 62.5}]
    )


class UnidadResponse(Salida):
    nombre: str
    equivalencias: dict[str, float]


# Lista cerrada (kg, racimos, jornales, hectareas): el nombre no se corrige, solo las equivalencias.
UnidadUpdate = modelo_parcial(UnidadCreate, ["equivalencias"], "UnidadUpdate")
