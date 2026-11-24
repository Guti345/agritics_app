from datetime import date

from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from back.app.auth import ADMIN, FINANZAS_LECTURA
from back.app.database import COSECHA_PLATANO, VENTA_PLATANO, get_db
from back.app.reglas.semana import (
    auditar_escritura_en_periodo_cerrado,
    exigir_periodo_abierto,
    exigir_periodos_abiertos_en_correccion,
)
from back.app.schemas import Calidad, VentaPlatanoCreate, VentaPlatanoResponse, VentaPlatanoUpdate
from back.app.utils import buscar_o_404, campos_captura, corregir, filtro_fechas, insertar

router = APIRouter(prefix="/ventas-platano", tags=["Venta de plátano"])


@router.get("", response_model=list[VentaPlatanoResponse], summary="Listar ventas de plátano")
async def listar(
    fecha: date | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    comprador: str | None = None,
    calidad: Calidad | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(FINANZAS_LECTURA),
):
    filtro = filtro_fechas(fecha, desde, hasta)
    if comprador:
        filtro["comprador"] = comprador.strip()
    if calidad:
        filtro["calidad"] = calidad.value
    docs = await db[VENTA_PLATANO].find(filtro).sort([("fecha", -1), ("fecha_captura", -1)]).to_list(None)
    return [VentaPlatanoResponse.model_validate(d) for d in docs]


@router.get("/{id}", response_model=VentaPlatanoResponse, summary="Ver una venta de plátano")
async def ver(id: str, db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(FINANZAS_LECTURA)):
    return VentaPlatanoResponse.model_validate(await buscar_o_404(db[VENTA_PLATANO], id, "la venta de plátano"))


@router.post("", response_model=VentaPlatanoResponse, status_code=status.HTTP_201_CREATED,
             summary="Registrar venta de plátano")
async def crear(datos: VentaPlatanoCreate, db: AsyncIOMotorDatabase = Depends(get_db), yo: dict = Depends(ADMIN)):
    """valor_total = kg x precio_kg lo verifica el DTO. cosecha_id (opcional) debe existir."""
    if datos.cosecha_id:
        await buscar_o_404(db[COSECHA_PLATANO], datos.cosecha_id, "la cosecha")
    corte = await exigir_periodo_abierto(db, datos.fecha, yo["rol"])
    doc = {**datos.a_mongo(), **campos_captura(yo)}
    guardado = await insertar(db[VENTA_PLATANO], doc, "Esta venta ya está registrada")
    await auditar_escritura_en_periodo_cerrado(db, corte, yo, VENTA_PLATANO, guardado["_id"])
    return VentaPlatanoResponse.model_validate(guardado)


@router.patch("/{id}", response_model=VentaPlatanoResponse, summary="Corregir venta de plátano (queda en auditoría)")
async def corregir_venta(
    id: str, cambios: VentaPlatanoUpdate, db: AsyncIOMotorDatabase = Depends(get_db), yo: dict = Depends(ADMIN)
):
    doc = await buscar_o_404(db[VENTA_PLATANO], id, "la venta de plátano")
    datos = cambios.model_dump(exclude_unset=True)
    await exigir_periodos_abiertos_en_correccion(db, doc["fecha"].date(), datos.get("fecha"), yo["rol"])
    if datos.get("cosecha_id"):
        await buscar_o_404(db[COSECHA_PLATANO], datos["cosecha_id"], "la cosecha")
    actualizado = await corregir(db, VENTA_PLATANO, doc, VentaPlatanoCreate, datos, yo, "Esta venta ya está registrada")
    return VentaPlatanoResponse.model_validate(actualizado)
