"""DTOs de gastos."""

from pydantic import model_validator

from .enums import CategoriaGasto
from .campos import Fecha, FechaOut, Positivo
from .base import Entrada, SalidaCaptura, modelo_parcial


class GastoCreate(Entrada):
    fecha: Fecha
    categoria: CategoriaGasto
    descripcion: str | None = None
    valor: Positivo

    @model_validator(mode="after")
    def _otros_con_descripcion(self):
        if self.categoria == CategoriaGasto.otros and not self.descripcion:
            raise ValueError("Los gastos en 'otros' necesitan una descripción")
        return self


class GastoResponse(SalidaCaptura):
    fecha: FechaOut
    categoria: CategoriaGasto
    descripcion: str | None = None
    valor: float


GastoUpdate = modelo_parcial(GastoCreate)
