"""DTOs de lotes."""

from typing import Literal

from .enums import Cultivo, EstadoLote
from .campos import Cultivos, Positivo, Texto
from .base import Entrada, Salida, modelo_parcial


class Poligono(Entrada):
    """Geometría GeoJSON del lote (para el mapa)."""
    type: Literal["Polygon", "MultiPolygon"]
    coordinates: list


class LoteCreate(Entrada):
    nombre: Texto
    cultivos: Cultivos
    variedad: str = ""
    area_ha: Positivo
    poligono: Poligono | None = None
    estado: EstadoLote = EstadoLote.activo


class LoteResponse(Salida):
    nombre: str
    cultivos: list[Cultivo]
    variedad: str = ""
    area_ha: float
    poligono: dict | None = None
    estado: EstadoLote


LoteUpdate = modelo_parcial(LoteCreate)
