from fastapi import APIRouter, Depends, Response, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from back.app.auth import ADMIN_O_MAYORDOMO, CUALQUIERA
from back.app.database import LABOR_DIARIA, POOL_SEMANA, TRABAJADORES, get_db
from back.app.reglas.auditoria import registrar_correccion
from back.app.reglas.errores import conflicto
from back.app.reglas.operacion import exigir_labor_activa, exigir_lote_activo
from back.app.reglas.semana import semana_cortada_completa, semana_iso
from back.app.schemas import (
    PoolActivar,
    PoolDesactivar,
    PoolSemanaCreate,
    PoolSemanaResponse,
    PoolTrabajadorResponse,
    ahora,
    hoy,
)
from back.app.utils import a_oid, buscar_o_404, campos_captura, insertar, semana_de_query, validar_o_422

router = APIRouter(prefix="/pool", tags=["Pool de la semana"])

YA_ACTIVO = "Este trabajador ya está activo en la semana"


async def _exigir_semana_no_cortada(db: AsyncIOMotorDatabase, semana: str, rol: str) -> None:
    """Un corte cierra un periodo, no la semana: el pool se puede mover mientras queden
    días sin cortar. Solo si la semana ya quedó cortada completa, únicamente el administrador."""
    corte = await semana_cortada_completa(db, semana)
    if corte is not None and rol != "administrador":
        raise conflicto(
            f"La semana {semana} ya quedó cortada completa (corte {corte['corte']}); "
            "solo el administrador puede cambiar su pool"
        )


@router.post("/activar", response_model=PoolSemanaResponse, status_code=status.HTTP_201_CREATED,
             summary="Activar (o reactivar) un trabajador en la semana")
async def activar(
    datos: PoolActivar,
    response: Response,
    db: AsyncIOMotorDatabase = Depends(get_db),
    yo: dict = Depends(ADMIN_O_MAYORDOMO),
):
    """Crea el registro del pool (201) o reactiva uno inactivo (200). Se puede activar a
    mitad de semana: `fecha_activacion` es la hora real y la pone el servidor."""
    entrada = validar_o_422(PoolSemanaCreate, {**datos.model_dump(), "activo": True})  # reglas del DTO del pool
    await buscar_o_404(db[TRABAJADORES], datos.trabajador_id, "el trabajador")
    for p in datos.preasignacion:
        await exigir_lote_activo(db, p.lote_id)
        await exigir_labor_activa(db, p.labor_id)
    await _exigir_semana_no_cortada(db, datos.semana, yo["rol"])

    tid = a_oid(datos.trabajador_id)
    existente = await db[POOL_SEMANA].find_one({"trabajador_id": tid, "semana": datos.semana})
    if existente is None:
        doc = {**entrada.a_mongo(), "fecha_activacion": ahora(), **campos_captura(yo)}
        return PoolSemanaResponse.model_validate(await insertar(db[POOL_SEMANA], doc, YA_ACTIVO))
    if existente["activo"]:
        raise conflicto(YA_ACTIVO)

    # Reactivación: queda en auditoría (nada se borra).
    poner = {"activo": True, "fecha_activacion": ahora()}
    cambios = [("activo", False, True)]
    if "preasignacion" in datos.model_fields_set:
        poner["preasignacion"] = entrada.a_mongo()["preasignacion"]
        cambios.append(("preasignacion", existente.get("preasignacion", []), poner["preasignacion"]))
    actualizado = await db[POOL_SEMANA].find_one_and_update(
        {"_id": existente["_id"], "activo": False}, {"$set": poner}, return_document=ReturnDocument.AFTER
    )
    if actualizado is None:  # otro usuario lo activó entre medio
        raise conflicto(YA_ACTIVO)
    await registrar_correccion(db, yo["usuario"], POOL_SEMANA, existente["_id"], cambios)
    response.status_code = status.HTTP_200_OK
    return PoolSemanaResponse.model_validate(actualizado)


@router.post("/desactivar", response_model=PoolSemanaResponse, summary="Sacar a un trabajador del pool de la semana")
async def desactivar(
    datos: PoolDesactivar,
    db: AsyncIOMotorDatabase = Depends(get_db),
    yo: dict = Depends(ADMIN_O_MAYORDOMO),
):
    tid = a_oid(datos.trabajador_id)
    existente = await db[POOL_SEMANA].find_one({"trabajador_id": tid, "semana": datos.semana, "activo": True})
    if existente is None:
        raise conflicto(f"Este trabajador no está activo en la semana {datos.semana}")
    await _exigir_semana_no_cortada(db, datos.semana, yo["rol"])
    if await db[LABOR_DIARIA].find_one({"trabajador_id": tid, "completada": False}, {"_id": 1}):
        raise conflicto("Este trabajador tiene una labor abierta; complétala antes de sacarlo del pool")
    actualizado = await db[POOL_SEMANA].find_one_and_update(
        {"_id": existente["_id"], "activo": True},
        {"$set": {"activo": False, "fecha_desactivacion": ahora()}},
        return_document=ReturnDocument.AFTER,
    )
    if actualizado is None:
        raise conflicto(f"Este trabajador no está activo en la semana {datos.semana}")
    await registrar_correccion(db, yo["usuario"], POOL_SEMANA, existente["_id"], [("activo", True, False)])
    return PoolSemanaResponse.model_validate(actualizado)


@router.get("", response_model=list[PoolTrabajadorResponse], summary="Pool de la semana (lista desplegable)")
async def listar(
    semana: str | None = None,
    activo: bool | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(CUALQUIERA),
):
    """Sin `semana`, la semana en curso. Ordenado por nombre del trabajador."""
    semana = semana_de_query(semana) if semana else semana_iso(hoy())
    filtro = {"semana": semana}
    if activo is not None:
        filtro["activo"] = activo
    filas = await db[POOL_SEMANA].aggregate([
        {"$match": filtro},
        {"$lookup": {"from": TRABAJADORES, "localField": "trabajador_id", "foreignField": "_id", "as": "t"}},
        {"$addFields": {"trabajador_nombre": {"$ifNull": [{"$first": "$t.nombre"}, "(sin nombre)"]}}},
        {"$project": {"t": 0}},
        {"$sort": {"trabajador_nombre": 1}},
    ]).to_list(None)
    return [PoolTrabajadorResponse.model_validate(f) for f in filas]
