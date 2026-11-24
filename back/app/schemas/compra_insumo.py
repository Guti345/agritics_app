"""DTOs de compra de insumos."""

from .campos import Fecha, FechaOut, OidIn, OidOut, Positivo, foto_obligatoria
from .base import Entrada, SalidaCaptura, modelo_parcial


class CompraInsumoCreate(Entrada):
    fecha: Fecha
    insumo_id: OidIn
    cantidad: Positivo
    valor: Positivo
    comprobante_ruta: foto_obligatoria("Adjunta la foto del comprobante de la compra") = None


class CompraInsumoResponse(SalidaCaptura):
    fecha: FechaOut
    insumo_id: OidOut
    cantidad: float
    valor: float
    comprobante_ruta: str | None = None


CompraInsumoUpdate = modelo_parcial(CompraInsumoCreate)
