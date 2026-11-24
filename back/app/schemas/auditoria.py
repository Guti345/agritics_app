"""DTO de auditoría (solo lectura: la escribe el servidor al corregir)."""

from .campos import FechaHoraOut, Libre, OidOut
from .base import Salida


class AuditoriaResponse(Salida):
    fecha: FechaHoraOut
    usuario: str
    coleccion: str
    documento_id: OidOut
    campo: str
    valor_anterior: Libre = None
    valor_nuevo: Libre = None
