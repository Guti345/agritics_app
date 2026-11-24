"""DTOs de cosecha de plátano."""

from .enums import Calidad
from .campos import EnteroPositivo, Fecha, FechaOut, OidIn, OidOut, Positivo
from .base import Entrada, SalidaCaptura, modelo_parcial


class CosechaPlatanoCreate(Entrada):
    fecha: Fecha
    lote_id: OidIn
    kg: Positivo
    racimos: EnteroPositivo
    calidad: Calidad


class CosechaPlatanoResponse(SalidaCaptura):
    fecha: FechaOut
    lote_id: OidOut
    kg: float
    racimos: int
    calidad: Calidad


CosechaPlatanoUpdate = modelo_parcial(CosechaPlatanoCreate)
