"""DTOs de labor diaria (trabajador x día x lote x labor)."""

from pydantic import BaseModel, model_validator

from .enums import FormaPago, TipoMeta
from .campos import Fecha, FechaHoraOut, FechaOut, Jornales, NoNegativo, OidIn, OidOut, Positivo
from .base import Entrada, SalidaCaptura, modelo_parcial


class InsumoConsumido(Entrada):
    insumo_id: OidIn
    cantidad: Positivo


class LaborDiariaCreate(Entrada):
    fecha: Fecha
    trabajador_id: OidIn
    lote_id: OidIn
    labor_id: OidIn
    # Lo pactado va COPIADO (congelado) en el registro, no referenciado:
    forma_pago: FormaPago
    tarifa: Positivo
    tipo_meta: TipoMeta | None = None
    jornales: Jornales
    avance: NoNegativo = 0
    completada: bool = False
    insumo_consumido: InsumoConsumido | None = None

    @model_validator(mode="after")
    def _contrato_con_meta(self):
        if self.forma_pago == FormaPago.contrato and self.tipo_meta is None:
            raise ValueError("Los contratos necesitan su tipo de meta: kilos, horas o labor completada")
        return self


class InsumoConsumidoResponse(BaseModel):
    insumo_id: OidOut
    cantidad: float


class LaborDiariaResponse(SalidaCaptura):
    fecha: FechaOut
    trabajador_id: OidOut
    lote_id: OidOut
    labor_id: OidOut
    forma_pago: FormaPago
    tarifa: float
    tipo_meta: TipoMeta | None = None
    jornales: float
    avance: float
    completada: bool
    insumo_consumido: InsumoConsumidoResponse | None = None
    fecha_cierre: FechaHoraOut | None = None


# PATCH: se corrige todo menos `completada` (va por /completar) e `insumo_consumido`
# (cambiar el consumo exige devolver/descontar stock: no se corrige con un PATCH).
LaborDiariaUpdate = modelo_parcial(
    LaborDiariaCreate,
    ["fecha", "trabajador_id", "lote_id", "labor_id", "forma_pago", "tarifa", "tipo_meta", "jornales", "avance"],
    "LaborDiariaUpdate",
)


class LaborCompletar(Entrada):
    """Cuerpo de POST /labores-diarias/{id}/completar: los valores reales del día."""
    avance: NoNegativo
    jornales: Jornales
