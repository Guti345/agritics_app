from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from back.app.auth import ADMIN_O_MAYORDOMO, CUALQUIERA
from back.app.database import LABOR_DIARIA, TRABAJADORES, get_db
from back.app.reglas.errores import conflicto, datos_invalidos
from back.app.reglas.nomina import rango_semana
from back.app.reglas.operacion import (
    descontar_insumo,
    devolver_insumo,
    exigir_admite_contrato,
    exigir_en_pool,
    exigir_labor_activa,
    exigir_lote_activo,
    exigir_sin_labor_abierta,
)
from back.app.reglas.semana import exigir_semana_abierta
from back.app.schemas import (
    LaborCompletar,
    LaborDiariaCreate,
    LaborDiariaResponse,
    LaborDiariaUpdate,
    ahora,
)
from back.app.utils import a_oid, buscar_o_404, campos_captura, corregir, insertar, semana_de_query

router = APIRouter(prefix="/labores-diarias", tags=["Labor diaria"])


def _utc(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)  # así se guardan las fechas de día


@router.post("", response_model=LaborDiariaResponse, status_code=status.HTTP_201_CREATED,
             summary="Abrir una labor (trabajador x día x lote x labor)")
async def abrir(
    datos: LaborDiariaCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    yo: dict = Depends(ADMIN_O_MAYORDOMO),
):
    """La labor se abre SIN completar; los jornales entran estimados y se corrigen en
    /completar. Tarifa y forma de pago quedan copiadas (congeladas) en el registro.
    Todas las reglas se revisan antes de escribir; el stock del insumo se descuenta en
    una sola operación que solo pasa si alcanza."""
    if datos.completada:
        raise datos_invalidos("Una labor se abre sin completar: complétala después con /completar")
    await buscar_o_404(db[TRABAJADORES], datos.trabajador_id, "el trabajador")
    await exigir_lote_activo(db, datos.lote_id)
    labor = await exigir_labor_activa(db, datos.labor_id)
    exigir_admite_contrato(labor, datos.forma_pago)
    await exigir_semana_abierta(db, datos.fecha, yo["rol"])
    tid = a_oid(datos.trabajador_id)
    await exigir_en_pool(db, tid, datos.fecha)
    await exigir_sin_labor_abierta(db, tid, datos.fecha)

    doc = {**datos.a_mongo(), "completada": False, "fecha_cierre": None, **campos_captura(yo)}
    consumo = datos.insumo_consumido
    if consumo:
        await descontar_insumo(db, consumo.insumo_id, consumo.cantidad)  # 409 si no alcanza: nada se escribe
    try:
        guardado = await insertar(db[LABOR_DIARIA], doc, "Esta labor ya está registrada")
    except Exception:
        if consumo:
            await devolver_insumo(db, consumo.insumo_id, consumo.cantidad)
        raise
    return LaborDiariaResponse.model_validate(guardado)


@router.post("/{id}/completar", response_model=LaborDiariaResponse, summary="Completar una labor con los valores reales")
async def completar(
    id: str,
    datos: LaborCompletar,
    db: AsyncIOMotorDatabase = Depends(get_db),
    yo: dict = Depends(ADMIN_O_MAYORDOMO),
):
    doc = await buscar_o_404(db[LABOR_DIARIA], id, "la labor diaria")
    if doc["completada"]:
        raise conflicto("Esta labor ya está completada")
    await exigir_semana_abierta(db, doc["fecha"].date(), yo["rol"])
    actualizado = await db[LABOR_DIARIA].find_one_and_update(
        {"_id": doc["_id"], "completada": False},
        {"$set": {
            "completada": True,
            "fecha_cierre": ahora(),
            "avance": datos.avance,
            "jornales": datos.jornales,
            "completada_por": yo["usuario"],
        }},
        return_document=ReturnDocument.AFTER,
    )
    if actualizado is None:
        raise conflicto("Esta labor ya está completada")
    return LaborDiariaResponse.model_validate(actualizado)


@router.get("", response_model=list[LaborDiariaResponse], summary="Listar labores diarias")
async def listar(
    fecha: date | None = None,
    semana: str | None = None,
    trabajador_id: str | None = None,
    lote_id: str | None = None,
    labor_id: str | None = None,
    completada: bool | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(CUALQUIERA),
):
    condiciones = []
    if fecha:
        condiciones.append({"fecha": _utc(fecha)})
    if semana:
        lunes, domingo = rango_semana(semana_de_query(semana))
        condiciones.append({"fecha": {"$gte": _utc(lunes), "$lte": _utc(domingo)}})
    for campo, valor in (("trabajador_id", trabajador_id), ("lote_id", lote_id), ("labor_id", labor_id)):
        if valor:
            condiciones.append({campo: a_oid(valor)})
    if completada is not None:
        condiciones.append({"completada": completada})
    filtro = {"$and": condiciones} if condiciones else {}
    docs = await db[LABOR_DIARIA].find(filtro).sort([("fecha", -1), ("fecha_captura", -1)]).to_list(None)
    return [LaborDiariaResponse.model_validate(d) for d in docs]


@router.get("/{id}", response_model=LaborDiariaResponse, summary="Ver una labor diaria")
async def ver(id: str, db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(CUALQUIERA)):
    return LaborDiariaResponse.model_validate(await buscar_o_404(db[LABOR_DIARIA], id, "la labor diaria"))


@router.patch("/{id}", response_model=LaborDiariaResponse, summary="Corregir una labor diaria (queda en auditoría)")
async def corregir_labor_diaria(
    id: str,
    cambios: LaborDiariaUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    yo: dict = Depends(ADMIN_O_MAYORDOMO),
):
    """Mismas reglas que al abrir, sobre el registro ya corregido. Semana cerrada: se
    revisa la fecha vieja y la nueva (no se saca ni se mete nada a una semana cerrada)."""
    doc = await buscar_o_404(db[LABOR_DIARIA], id, "la labor diaria")
    datos = cambios.model_dump(exclude_unset=True)
    fecha_vieja = doc["fecha"].date()
    fecha = datos.get("fecha") or fecha_vieja
    await exigir_semana_abierta(db, fecha_vieja, yo["rol"])
    if fecha != fecha_vieja:
        await exigir_semana_abierta(db, fecha, yo["rol"])

    trabajador_id = datos.get("trabajador_id") or str(doc["trabajador_id"])
    if "trabajador_id" in datos:
        await buscar_o_404(db[TRABAJADORES], trabajador_id, "el trabajador")
    if datos.get("lote_id"):
        await exigir_lote_activo(db, datos["lote_id"])
    if datos.get("labor_id") or datos.get("forma_pago"):
        labor = await exigir_labor_activa(db, datos.get("labor_id") or str(doc["labor_id"]))
        exigir_admite_contrato(labor, datos.get("forma_pago") or doc["forma_pago"])
    if "trabajador_id" in datos or "fecha" in datos:
        await exigir_en_pool(db, a_oid(trabajador_id), fecha)
        if not doc["completada"]:
            await exigir_sin_labor_abierta(db, a_oid(trabajador_id), fecha, excluir_id=doc["_id"])

    actualizado = await corregir(
        db, LABOR_DIARIA, doc, LaborDiariaCreate, datos, yo, mensaje_duplicado="Esta labor ya está registrada"
    )
    return LaborDiariaResponse.model_validate(actualizado)
