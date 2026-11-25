"""DTOs de movimientos de caja: aportes, retiros, ajustes, préstamos recibidos, abonos a
deudas y pagos de intereses. NUNCA entran al margen (no son ingreso ni gasto operacional).
No hay módulo de deudas ni saldos de deuda: el detalle (acreedor, plazo...) va en la nota."""

from datetime import date

from pydantic import BaseModel, Field, model_validator

from .enums import TipoMovimientoCaja
from .campos import Fecha, FechaOut
from .base import Entrada, SalidaCaptura, modelo_parcial


class MovimientoCajaCreate(Entrada):
    fecha: Fecha
    tipo: TipoMovimientoCaja
    valor: float = Field(description="Positivo en todos los tipos menos el ajuste (el tipo dice si la plata entra o "
                                     "sale: entran aporte_capital y prestamo_recibido; salen retiro, abono_deuda y "
                                     "pago_intereses). Ajuste: puede ser negativo.")
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
    - nómina causada + movimientos de caja (aportes, préstamos recibidos y ajustes suman;
    retiros, abonos a deudas y pagos de intereses restan)."""
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
