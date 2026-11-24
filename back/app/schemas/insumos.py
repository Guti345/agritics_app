"""DTOs de insumos."""

from .campos import NoNegativo, Texto
from .base import Entrada, Salida, modelo_parcial


class InsumoCreate(Entrada):
    nombre: Texto
    unidad: Texto
    stock_actual: NoNegativo = 0
    umbral_alerta: NoNegativo = 0


class InsumoResponse(Salida):
    nombre: str
    unidad: str
    stock_actual: float
    umbral_alerta: float


# El stock NO se corrige a mano: sube con las compras y baja con el consumo en las labores.
InsumoUpdate = modelo_parcial(InsumoCreate, ["nombre", "unidad", "umbral_alerta"], "InsumoUpdate")
