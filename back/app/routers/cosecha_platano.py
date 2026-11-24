from datetime import date

from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from back.app.auth import ADMIN_O_MAYORDOMO, CUALQUIERA
from back.app.database import COSECHA_PLATANO, get_db
from back.app.reglas.operacion import exigir_cultivo, exigir_lote_activo
from back.app.reglas.semana import (
    auditar_escritura_en_periodo_cerrado,
    exigir_periodo_abierto,
    exigir_periodos_abiertos_en_correccion,
)
from back.app.schemas import Calidad, CosechaPlatanoCreate, CosechaPlatanoResponse, CosechaPlatanoUpdate
from back.app.utils import a_oid, buscar_o_404, campos_captura, corregir, filtro_fechas, insertar

router = APIRouter(prefix="/cosechas-platano", tags=["Cosecha de plátano"])


async def _lote_con_platano(db: AsyncIOMotorDatabase, lote_id: str) -> None:
    exigir_cultivo(await exigir_lote_activo(db, lote_id), "platano")


@router.get("", response_model=list[CosechaPlatanoResponse], summary="Listar cosechas de plátano")
async def listar(
    fecha: date | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    lote_id: str | None = None,
    calidad: Calidad | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(CUALQUIERA),
):
    filtro = filtro_fechas(fecha, desde, hasta)
    if lote_id:
        filtro["lote_id"] = a_oid(lote_id)
    if calidad:
        filtro["calidad"] = calidad.value
    docs = await db[COSECHA_PLATANO].find(filtro).sort([("fecha", -1), ("fecha_captura", -1)]).to_list(None)
    return [CosechaPlatanoResponse.model_validate(d) for d in docs]


@router.get("/{id}", response_model=CosechaPlatanoResponse, summary="Ver una cosecha de plátano")
async def ver(id: str, db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(CUALQUIERA)):
    return CosechaPlatanoResponse.model_validate(await buscar_o_404(db[COSECHA_PLATANO], id, "la cosecha"))


@router.post("", response_model=CosechaPlatanoResponse, status_code=status.HTTP_201_CREATED,
             summary="Registrar cosecha de plátano")
async def crear(
    datos: CosechaPlatanoCreate, db: AsyncIOMotorDatabase = Depends(get_db), yo: dict = Depends(ADMIN_O_MAYORDOMO)
):
    await _lote_con_platano(db, datos.lote_id)
    corte = await exigir_periodo_abierto(db, datos.fecha, yo["rol"])
    doc = {**datos.a_mongo(), **campos_captura(yo)}
    guardado = await insertar(db[COSECHA_PLATANO], doc, "Esta cosecha ya está registrada")
    await auditar_escritura_en_periodo_cerrado(db, corte, yo, COSECHA_PLATANO, guardado["_id"])
    return CosechaPlatanoResponse.model_validate(guardado)


@router.patch("/{id}", response_model=CosechaPlatanoResponse, summary="Corregir cosecha (queda en auditoría)")
async def corregir_cosecha(
    id: str,
    cambios: CosechaPlatanoUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    yo: dict = Depends(ADMIN_O_MAYORDOMO),
):
    doc = await buscar_o_404(db[COSECHA_PLATANO], id, "la cosecha")
    datos = cambios.model_dump(exclude_unset=True)
    await exigir_periodos_abiertos_en_correccion(db, doc["fecha"].date(), datos.get("fecha"), yo["rol"])
    if datos.get("lote_id"):
        await _lote_con_platano(db, datos["lote_id"])
    actualizado = await corregir(db, COSECHA_PLATANO, doc, CosechaPlatanoCreate, datos, yo, "Esta cosecha ya está registrada")
    return CosechaPlatanoResponse.model_validate(actualizado)
