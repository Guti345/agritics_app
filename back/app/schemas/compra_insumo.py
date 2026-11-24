"""DTOs de compra de insumos."""

from .campos import Fecha, FechaOut, OidIn, OidOut, Positivo
from .base import Entrada, SalidaCaptura


class CompraInsumoCreate(Entrada):
    fecha: Fecha
    insumo_id: OidIn
    cantidad: Positivo
    valor: Positivo
    comprobante_ruta: str | None = None


class CompraInsumoResponse(SalidaCaptura):
    fecha: FechaOut
    insumo_id: OidOut
    cantidad: float
    valor: float
    comprobante_ruta: str | None = None
