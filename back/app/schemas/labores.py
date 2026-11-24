"""DTOs de labores."""

from .enums import Cultivo, TipoMeta, UnidadAvance
from .campos import Cultivos, Texto
from .base import Entrada, Salida, modelo_parcial


class LaborCreate(Entrada):
    nombre: Texto
    cultivos: Cultivos
    unidad_avance: UnidadAvance
    admite_contrato: bool = False
    tipo_meta: TipoMeta | None = None
    activa: bool = True


class LaborResponse(Salida):
    nombre: str
    cultivos: list[Cultivo]
    unidad_avance: UnidadAvance
    admite_contrato: bool
    tipo_meta: TipoMeta | None = None
    activa: bool


LaborUpdate = modelo_parcial(LaborCreate)
