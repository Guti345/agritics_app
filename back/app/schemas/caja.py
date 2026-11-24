"""DTOs de movimientos de caja (aportes, retiros, ajustes: nunca entran al margen)."""

from pydantic import Field, model_validator

from .enums import TipoMovimientoCaja
from .campos import Fecha, FechaOut
from .base import Entrada, SalidaCaptura


class MovimientoCajaCreate(Entrada):
    fecha: Fecha
    tipo: TipoMovimientoCaja
    valor: float = Field(description="Aporte y retiro: positivo (el tipo dice si entra o sale). Ajuste: puede ser negativo.")
    nota: str = ""

    @model_validator(mode="after")
    def _valor_segun_tipo(self):
        if self.tipo == TipoMovimientoCaja.ajuste:
            if self.valor == 0:
                raise ValueError("Un ajuste de 0 no cambia nada en la caja")
        elif self.valor <= 0:
            raise ValueError("El valor debe ser mayor que 0: el tipo ya dice si la plata entra o sale")
        return self


class MovimientoCajaResponse(SalidaCaptura):
    fecha: FechaOut
    tipo: TipoMovimientoCaja
    valor: float
    nota: str = ""
