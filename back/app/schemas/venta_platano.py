"""DTOs de venta de plátano."""

from pydantic import model_validator

from .enums import Calidad
from .tiempo import fmt_pesos
from .campos import EnteroPositivo, Fecha, FechaOut, OidIn, OidOut, Positivo, Texto
from .base import Entrada, SalidaCaptura, modelo_parcial


class VentaPlatanoCreate(Entrada):
    fecha: Fecha
    comprador: Texto
    kg: Positivo
    racimos: EnteroPositivo
    calidad: Calidad
    precio_kg: Positivo
    valor_total: Positivo
    cosecha_id: OidIn | None = None

    @model_validator(mode="after")
    def _valor_total_cuadra(self):
        esperado = self.kg * self.precio_kg
        if abs(self.valor_total - esperado) > 1:  # tolerancia de $1 por redondeo
            raise ValueError(f"El valor total no cuadra: kilos por precio debería ser {fmt_pesos(esperado)}")
        return self


class VentaPlatanoResponse(SalidaCaptura):
    fecha: FechaOut
    comprador: str
    kg: float
    racimos: int
    calidad: Calidad
    precio_kg: float
    valor_total: float
    cosecha_id: OidOut | None = None


VentaPlatanoUpdate = modelo_parcial(VentaPlatanoCreate)
