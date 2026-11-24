"""DTOs de venta de café (recibo de la Cooperativa, un solo documento)."""

from pydantic import BaseModel, Field, model_validator

from .enums import TipoProductoCafe
from .tiempo import fmt_num
from .campos import (
    EnteroNoNegativo,
    Fecha,
    FechaOut,
    NoNegativo,
    Porcentaje,
    Positivo,
    Texto,
    foto_obligatoria,
)
from .base import Entrada, SalidaCaptura, modelo_parcial


class AnalisisCalidad(Entrada):
    almendra_sana: Porcentaje
    pasilla: Porcentaje
    broca: Porcentaje


class Descuento(Entrada):
    concepto: Texto
    valor: NoNegativo


class VentaCafeCreate(Entrada):
    fecha: Fecha
    almacen: Texto
    tipo_producto: TipoProductoCafe
    sacos: EnteroNoNegativo
    kg_brutos: Positivo
    destare: NoNegativo = 0
    kg_netos: Positivo
    kg_pergamino_equivalente: NoNegativo
    analisis_calidad: AnalisisCalidad
    factor_rendimiento: Positivo
    precio_base: Positivo
    descuentos: list[Descuento] = Field(default_factory=list)
    valor_total: NoNegativo
    numero_pedido: str = ""
    id_comprobante: str | None = None
    foto_ruta: foto_obligatoria("Adjunta la foto del recibo de la Cooperativa") = None

    @model_validator(mode="after")
    def _netos_cuadran(self):
        esperado = self.kg_brutos - self.destare
        if abs(self.kg_netos - esperado) > 0.01:
            raise ValueError(
                f"Los kilos netos no cuadran: brutos menos destare debería ser {fmt_num(esperado)}"
            )
        return self


class DescuentoResponse(BaseModel):
    concepto: str
    valor: float


class AnalisisCalidadResponse(BaseModel):
    almendra_sana: float
    pasilla: float
    broca: float


class VentaCafeResponse(SalidaCaptura):
    fecha: FechaOut
    almacen: str
    tipo_producto: TipoProductoCafe
    sacos: int
    kg_brutos: float
    destare: float
    kg_netos: float
    kg_pergamino_equivalente: float
    analisis_calidad: AnalisisCalidadResponse
    factor_rendimiento: float
    precio_base: float
    descuentos: list[DescuentoResponse] = Field(default_factory=list)
    valor_total: float
    numero_pedido: str = ""
    id_comprobante: str | None = None
    foto_ruta: str


VentaCafeUpdate = modelo_parcial(VentaCafeCreate)
