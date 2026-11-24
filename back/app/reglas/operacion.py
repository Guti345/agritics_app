"""Reglas de la operación diaria (pool y labor diaria): todas fallan ANTES de escribir."""

from datetime import date

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from back.app.database import INSUMOS, LABOR_DIARIA, LABORES, LOTES, POOL_SEMANA
from back.app.reglas.errores import conflicto, no_encontrado
from back.app.reglas.semana import semana_iso
from back.app.schemas import fmt_num
from back.app.utils import buscar_o_404

# Regla estrella: el texto vive en reglas/mensajes.py (también lo usa la traducción del
# DuplicateKeyError del índice "unica_labor_abierta"). Se reexporta aquí para los routers.
from back.app.reglas.mensajes import LABOR_ABIERTA  # noqa: E402,F401


def lunes_de(semana: str) -> date:
    """"2026-W48" -> lunes de esa semana (sirve para aplicar la regla de semana cerrada)."""
    return date.fromisocalendar(int(semana[:4]), int(semana[6:]), 1)


async def exigir_lote_activo(db: AsyncIOMotorDatabase, lote_id: str) -> dict:
    lote = await buscar_o_404(db[LOTES], lote_id, "el lote")
    if lote["estado"] != "activo":
        raise conflicto(f"El lote '{lote['nombre']}' no está activo (estado: {lote['estado']})")
    return lote


async def exigir_labor_activa(db: AsyncIOMotorDatabase, labor_id: str) -> dict:
    labor = await buscar_o_404(db[LABORES], labor_id, "la labor")
    if not labor.get("activa", False):
        raise conflicto(f"La labor '{labor['nombre']}' está inactiva")
    return labor


def exigir_admite_contrato(labor: dict, forma_pago: str) -> None:
    if forma_pago == "contrato" and not labor.get("admite_contrato", False):
        raise conflicto(f"La labor '{labor['nombre']}' no admite contrato: regístrala a jornal")


async def exigir_en_pool(db: AsyncIOMotorDatabase, trabajador_id: ObjectId, fecha: date) -> None:
    pool = await db[POOL_SEMANA].find_one(
        {"trabajador_id": trabajador_id, "semana": semana_iso(fecha), "activo": True}, {"_id": 1}
    )
    if pool is None:
        raise conflicto("Este trabajador no está activo en la semana; actívalo primero en el pool")


async def exigir_sin_labor_abierta(
    db: AsyncIOMotorDatabase, trabajador_id: ObjectId, fecha: date, excluir_id: ObjectId | None = None
) -> None:
    """REGLA ESTRELLA: un trabajador no puede tener dos labores abiertas a la vez.
    Completadas sí puede repetir la misma labor en el mismo lote el mismo día."""
    filtro = {"trabajador_id": trabajador_id, "completada": False}
    if excluir_id is not None:
        filtro["_id"] = {"$ne": excluir_id}
    if await db[LABOR_DIARIA].find_one(filtro, {"_id": 1}) is not None:
        raise conflicto(LABOR_ABIERTA)


async def descontar_insumo(db: AsyncIOMotorDatabase, insumo_id: str, cantidad: float) -> dict:
    """UNA sola operación: descuenta solo si el stock alcanza ($inc con filtro). Si no
    alcanza no se escribe nada y responde 409 con lo que queda."""
    oid = ObjectId(insumo_id)
    insumo = await db[INSUMOS].find_one_and_update(
        {"_id": oid, "stock_actual": {"$gte": cantidad}},
        {"$inc": {"stock_actual": -cantidad}},
        return_document=ReturnDocument.AFTER,
    )
    if insumo is not None:
        return insumo
    actual = await db[INSUMOS].find_one({"_id": oid})
    if actual is None:
        raise no_encontrado(f"No existe el insumo con id {insumo_id}")
    raise conflicto(
        f"No hay stock suficiente de {actual['nombre']}: quedan {fmt_num(actual['stock_actual'])} {actual['unidad']}"
    )


async def devolver_insumo(db: AsyncIOMotorDatabase, insumo_id: str, cantidad: float) -> None:
    """Compensación si la labor no alcanzó a guardarse después de descontar el stock."""
    await db[INSUMOS].update_one({"_id": ObjectId(insumo_id)}, {"$inc": {"stock_actual": cantidad}})


def exigir_cultivo(lote: dict, cultivo: str) -> None:
    if cultivo not in lote.get("cultivos", []):
        nombre = {"platano": "plátano", "cafe": "café"}.get(cultivo, cultivo)
        raise conflicto(f"El lote '{lote['nombre']}' no tiene {nombre}")


async def sumar_stock(db: AsyncIOMotorDatabase, insumo_id: str, cantidad: float) -> dict:
    """Suma al stock en una sola operación ($inc). 404 si el insumo no existe."""
    insumo = await db[INSUMOS].find_one_and_update(
        {"_id": ObjectId(insumo_id)}, {"$inc": {"stock_actual": cantidad}}, return_document=ReturnDocument.AFTER
    )
    if insumo is None:
        raise no_encontrado(f"No existe el insumo con id {insumo_id}")
    return insumo
