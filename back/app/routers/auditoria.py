from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from back.app.auth import ADMIN
from back.app.database import AUDITORIA, get_db
from back.app.schemas import BOGOTA, AuditoriaResponse
from back.app.utils import a_oid

router = APIRouter(prefix="/auditoria", tags=["Auditoría"])


def _inicio_dia(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=BOGOTA)


@router.get("", response_model=list[AuditoriaResponse], summary="Correcciones registradas (más recientes primero)")
async def listar(
    usuario: str | None = None,
    coleccion: str | None = None,
    documento_id: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    limite: int = Query(100, ge=1, le=1000),
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(ADMIN),
):
    """Solo administrador y superusuario. `desde`/`hasta`: días completos en hora de Colombia."""
    filtro = {}
    if usuario:
        filtro["usuario"] = usuario.strip().lower()
    if coleccion:
        filtro["coleccion"] = coleccion
    if documento_id:
        filtro["documento_id"] = a_oid(documento_id)
    if desde or hasta:
        filtro["fecha"] = {}
        if desde:
            filtro["fecha"]["$gte"] = _inicio_dia(desde)
        if hasta:
            filtro["fecha"]["$lt"] = _inicio_dia(hasta) + timedelta(days=1)
    docs = await db[AUDITORIA].find(filtro).sort("fecha", -1).limit(limite).to_list(None)
    return [AuditoriaResponse.model_validate(d) for d in docs]
