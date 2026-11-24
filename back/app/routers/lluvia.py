from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from back.app.auth import ADMIN_O_MAYORDOMO, CUALQUIERA
from back.app.database import LLUVIA, get_db
from back.app.reglas.errores import conflicto
from back.app.reglas.fotos import exigir_foto
from back.app.reglas.semana import (
    auditar_escritura_en_periodo_cerrado,
    exigir_periodo_abierto,
    exigir_periodos_abiertos_en_correccion,
)
from back.app.schemas import (
    BOGOTA,
    LluviaCreate,
    LluviaDiaResponse,
    LluviaResponse,
    LluviaUpdate,
    fmt_num,
)
from back.app.utils import buscar_o_404, campos_captura, corregir, fusionar, insertar

router = APIRouter(prefix="/lluvia", tags=["Lluvia"])

MAX_LECTURAS_DIA = 2
TOPE_MM_DIA = 500


def _dia(momento: datetime) -> date:
    """Día en hora de Colombia de una lectura (sin zona = hora de Colombia)."""
    return (momento if momento.tzinfo else momento.replace(tzinfo=BOGOTA)).astimezone(BOGOTA).date()


def _rango_dias(desde: date, hasta: date) -> dict:
    """Filtro de fecha_hora para días completos de Colombia (de 00:00 a 00:00, en UTC)."""
    inicio = datetime(desde.year, desde.month, desde.day, tzinfo=BOGOTA)
    fin = datetime(hasta.year, hasta.month, hasta.day, tzinfo=BOGOTA) + timedelta(days=1)
    return {"fecha_hora": {"$gte": inicio, "$lt": fin}}


async def _exigir_cupo_del_dia(db: AsyncIOMotorDatabase, momento: datetime, mm: float, excluir_id=None) -> None:
    """Máximo 2 lecturas por día, el día no pasa de 500 mm y no hay dos lecturas a la misma hora."""
    dia = _dia(momento)
    filtro = _rango_dias(dia, dia)
    if excluir_id is not None:
        filtro["_id"] = {"$ne": excluir_id}
    lecturas = await db[LLUVIA].find(filtro, {"fecha_hora": 1, "mm": 1}).to_list(None)
    hora = momento.astimezone(BOGOTA)
    if any(l["fecha_hora"] == hora for l in lecturas):
        raise conflicto(f"Ya hay una lectura de lluvia a las {hora:%H:%M} del {dia:%Y-%m-%d}")
    if len(lecturas) >= MAX_LECTURAS_DIA:
        raise conflicto(f"Ya hay {len(lecturas)} lecturas de lluvia el {dia:%Y-%m-%d}: el máximo es {MAX_LECTURAS_DIA} por día")
    total = sum(l["mm"] for l in lecturas) + mm
    if total > TOPE_MM_DIA:
        raise conflicto(
            f"Con esta lectura el {dia:%Y-%m-%d} sumaría {fmt_num(total)} mm: el tope es {TOPE_MM_DIA} mm por día; revisa el dato"
        )


@router.get("", response_model=list[LluviaResponse], summary="Lecturas de lluvia por fecha o por rango")
async def listar(
    fecha: date | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(CUALQUIERA),
):
    """`fecha`: un día; `desde`/`hasta`: un rango de días (hora de Colombia)."""
    if fecha:
        filtro = _rango_dias(fecha, fecha)
    elif desde or hasta:
        filtro = _rango_dias(desde or date(1900, 1, 1), hasta or date(2999, 12, 31))
    else:
        filtro = {}
    docs = await db[LLUVIA].find(filtro).sort("fecha_hora", -1).to_list(None)
    return [LluviaResponse.model_validate(d) for d in docs]


@router.get("/dia/{fecha}", response_model=LluviaDiaResponse, summary="Lluvia del día: suma de sus lecturas")
async def del_dia(fecha: date, db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(CUALQUIERA)):
    docs = await db[LLUVIA].find(_rango_dias(fecha, fecha)).sort("fecha_hora", 1).to_list(None)
    return LluviaDiaResponse(
        fecha=fecha,
        lecturas=len(docs),
        mm=sum(d["mm"] for d in docs),
        detalle=[LluviaResponse.model_validate(d) for d in docs],
    )


@router.get("/{id}", response_model=LluviaResponse, summary="Ver una lectura de lluvia")
async def ver(id: str, db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(CUALQUIERA)):
    return LluviaResponse.model_validate(await buscar_o_404(db[LLUVIA], id, "la lectura de lluvia"))


@router.post("", response_model=LluviaResponse, status_code=status.HTTP_201_CREATED, summary="Registrar lectura de lluvia")
async def crear(datos: LluviaCreate, db: AsyncIOMotorDatabase = Depends(get_db), yo: dict = Depends(ADMIN_O_MAYORDOMO)):
    """fecha_hora es la hora REAL de la lectura (sin zona = hora de Colombia); mm de 0 a 500;
    foto del pluviómetro obligatoria (la valida el DTO y aquí se revisa que esté subida)."""
    exigir_foto(datos.foto_ruta)
    corte = await exigir_periodo_abierto(db, _dia(datos.fecha_hora), yo["rol"])
    await _exigir_cupo_del_dia(db, datos.fecha_hora, datos.mm)
    doc = {**datos.a_mongo(), **campos_captura(yo)}
    guardado = await insertar(db[LLUVIA], doc, "Ya hay una lectura de lluvia a esa hora")
    await auditar_escritura_en_periodo_cerrado(db, corte, yo, LLUVIA, guardado["_id"])
    return LluviaResponse.model_validate(guardado)


@router.patch("/{id}", response_model=LluviaResponse, summary="Corregir lectura de lluvia (queda en auditoría)")
async def corregir_lectura(
    id: str, cambios: LluviaUpdate, db: AsyncIOMotorDatabase = Depends(get_db), yo: dict = Depends(ADMIN_O_MAYORDOMO)
):
    doc = await buscar_o_404(db[LLUVIA], id, "la lectura de lluvia")
    datos = cambios.model_dump(exclude_unset=True)
    nueva = fusionar(doc, LluviaCreate, datos)
    await exigir_periodos_abiertos_en_correccion(db, _dia(doc["fecha_hora"]), _dia(nueva.fecha_hora), yo["rol"])
    if datos.get("foto_ruta"):
        exigir_foto(datos["foto_ruta"])
    if "fecha_hora" in datos or "mm" in datos:
        await _exigir_cupo_del_dia(db, nueva.fecha_hora, nueva.mm, excluir_id=doc["_id"])
    actualizado = await corregir(db, LLUVIA, doc, LluviaCreate, datos, yo, "Ya hay una lectura de lluvia a esa hora")
    return LluviaResponse.model_validate(actualizado)
