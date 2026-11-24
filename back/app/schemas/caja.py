"""DTOs de movimientos de caja (aportes, retiros, ajustes: nunca entran al margen)."""

from datetime import date

from pydantic import BaseModel, Field, model_validator

from .enums import TipoMovimientoCaja
from .campos import Fecha, FechaOut
from .base import Entrada, SalidaCaptura, modelo_parcial


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


MovimientoCajaUpdate = modelo_parcial(MovimientoCajaCreate)


class ComponenteSaldo(BaseModel):
    """Un componente del saldo: cuántos registros y cuánto suman (en pesos, siempre positivo)."""
    registros: int
    valor: float


class CajaSaldoResponse(BaseModel):
    """Saldo = ventas de café + ventas de plátano - gastos - compras de insumos
    - nómina causada + movimientos de caja (aportes y ajustes suman, retiros restan)."""
    desde: date | None = None
    hasta: date
    ventas_cafe: ComponenteSaldo
    ventas_platano: ComponenteSaldo
    gastos: ComponenteSaldo
    gastos_por_categoria: dict[str, float]
    compras_insumos: ComponenteSaldo
    nomina_causada: ComponenteSaldo
    movimientos_caja: ComponenteSaldo
    movimientos_por_tipo: dict[str, float]
    saldo: float
    advertencias: list[str] = Field(default_factory=list)
