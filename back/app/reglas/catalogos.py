"""Reglas de negocio de los catálogos que no caben en el DTO (dependen del estado o de la base)."""

import re

from motor.motor_asyncio import AsyncIOMotorCollection

from back.app.reglas.errores import conflicto, datos_invalidos
from back.app.schemas import InsumoCreate, LaborCreate, UnidadCreate

UNIDADES_PERMITIDAS = ("kg", "racimos", "jornales", "hectareas")  # lista cerrada


def regla_labor(labor: LaborCreate) -> None:
    if labor.admite_contrato and labor.tipo_meta is None:
        raise datos_invalidos("Los contratos necesitan su tipo de meta: kilos, horas o labor completada")


def regla_insumo_nuevo(insumo: InsumoCreate) -> None:
    if insumo.stock_actual != 0:
        raise datos_invalidos(
            "El stock de un insumo nuevo arranca en 0: se suma registrando una compra"
        )


def regla_unidad(unidad: UnidadCreate) -> None:
    if unidad.nombre not in UNIDADES_PERMITIDAS:
        raise datos_invalidos(f"La unidad debe ser una de estas: {', '.join(UNIDADES_PERMITIDAS)}")


async def exigir_nombre_libre(
    coleccion: AsyncIOMotorCollection, campo: str, valor: str, mensaje: str, excluir_id=None
) -> None:
    """409 si ya existe otro documento con ese valor (sin distinguir mayúsculas):
    "Urea" y "urea" se toman como el mismo insumo."""
    filtro = {campo: {"$regex": f"^{re.escape(valor)}$", "$options": "i"}}
    if excluir_id is not None:
        filtro["_id"] = {"$ne": excluir_id}
    if await coleccion.find_one(filtro, {"_id": 1}):
        raise conflicto(mensaje)
