from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from back.app.auth import ADMIN
from back.app.database import AUDITORIA, get_db
from back.app.schemas import AuditoriaResponse
from back.app.utils import a_oid

router = APIRouter(prefix="/auditoria", tags=["Auditoría"])


@router.get("", response_model=list[AuditoriaResponse], summary="Correcciones registradas (más recientes primero)")
async def listar(
    coleccion: str | None = None,
    documento_id: str | None = None,
    limite: int = Query(100, ge=1, le=1000),
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(ADMIN),
):
    filtro = {}
    if coleccion:
        filtro["coleccion"] = coleccion
    if documento_id:
        filtro["documento_id"] = a_oid(documento_id)
    docs = await db[AUDITORIA].find(filtro).sort("fecha", -1).limit(limite).to_list(None)
    return [AuditoriaResponse.model_validate(d) for d in docs]
