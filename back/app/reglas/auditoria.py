"""Auditoría: toda corrección deja una fila por campo cambiado (nada se borra)."""

from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from back.app.database import AUDITORIA
from back.app.schemas import ahora

OCULTO = "***"  # lo que se guarda en vez del valor de campos sensibles (la clave)


async def registrar_correccion(
    db: AsyncIOMotorDatabase,
    usuario: str,
    coleccion: str,
    documento_id: ObjectId,
    cambios: list[tuple[str, Any, Any]],
    ocultar: tuple[str, ...] = (),
) -> None:
    """cambios: [(campo, valor_anterior, valor_nuevo), ...]."""
    if not cambios:
        return
    fecha = ahora()
    await db[AUDITORIA].insert_many([
        {
            "fecha": fecha,
            "usuario": usuario,
            "coleccion": coleccion,
            "documento_id": documento_id,
            "campo": campo,
            "valor_anterior": OCULTO if campo in ocultar else antes,
            "valor_nuevo": OCULTO if campo in ocultar else despues,
        }
        for campo, antes, despues in cambios
    ])
