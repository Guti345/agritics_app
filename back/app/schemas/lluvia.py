"""DTOs de lluvia (1 o 2 lecturas al día; los mm del día son la suma)."""

from .campos import FechaHora, FechaHoraOut, MmLluvia, Texto, foto_obligatoria
from .base import Entrada, Salida


class LluviaCreate(Entrada):
    fecha_hora: FechaHora
    mm: MmLluvia
    foto_ruta: foto_obligatoria("Adjunta la foto del pluviómetro") = None
    leida_por: Texto


class LluviaResponse(Salida):
    fecha_hora: FechaHoraOut
    mm: float
    foto_ruta: str
    leida_por: str
    fecha_captura: FechaHoraOut
