"""DTOs de trabajadores."""

from .campos import Texto
from .base import Entrada, Salida, modelo_parcial


# El tipo (recurrente / esporádico / de una vez) y el rendimiento NO se guardan: se calculan.
class TrabajadorCreate(Entrada):
    nombre: Texto
    documento: str | None = None   # puede ir vacío
    telefono: str | None = None


class TrabajadorResponse(Salida):
    nombre: str
    documento: str | None = None
    telefono: str | None = None


TrabajadorUpdate = modelo_parcial(TrabajadorCreate)
