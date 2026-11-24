from datetime import date

from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from back.app.auth import ADMIN, FINANZAS_LECTURA
from back.app.database import GASTO, get_db
from back.app.reglas.semana import exigir_semana_abierta, exigir_semanas_abiertas_en_correccion
from back.app.schemas import CategoriaGasto, GastoCreate, GastoResponse, GastoUpdate
from back.app.utils import buscar_o_404, campos_captura, corregir, filtro_fechas, insertar

router = APIRouter(prefix="/gastos", tags=["Gastos"])


@router.get("", response_model=list[GastoResponse], summary="Listar gastos")
async def listar(
    fecha: date | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    categoria: CategoriaGasto | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(FINANZAS_LECTURA),
):
    filtro = filtro_fechas(fecha, desde, hasta)
    if categoria:
        filtro["categoria"] = categoria.value
    docs = await db[GASTO].find(filtro).sort([("fecha", -1), ("fecha_captura", -1)]).to_list(None)
    return [GastoResponse.model_validate(d) for d in docs]


@router.get("/{id}", response_model=GastoResponse, summary="Ver un gasto")
async def ver(id: str, db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(FINANZAS_LECTURA)):
    return GastoResponse.model_validate(await buscar_o_404(db[GASTO], id, "el gasto"))


@router.post("", response_model=GastoResponse, status_code=status.HTTP_201_CREATED, summary="Registrar gasto")
async def crear(datos: GastoCreate, db: AsyncIOMotorDatabase = Depends(get_db), yo: dict = Depends(ADMIN)):
    """La categoría va en el enum; 'otros' exige descripción (lo valida el DTO)."""
    await exigir_semana_abierta(db, datos.fecha, yo["rol"])
    doc = {**datos.a_mongo(), **campos_captura(yo)}
    return GastoResponse.model_validate(await insertar(db[GASTO], doc, "Este gasto ya está registrado"))


@router.patch("/{id}", response_model=GastoResponse, summary="Corregir gasto (queda en auditoría)")
async def corregir_gasto(
    id: str, cambios: GastoUpdate, db: AsyncIOMotorDatabase = Depends(get_db), yo: dict = Depends(ADMIN)
):
    doc = await buscar_o_404(db[GASTO], id, "el gasto")
    datos = cambios.model_dump(exclude_unset=True)
    await exigir_semanas_abiertas_en_correccion(db, doc["fecha"].date(), datos.get("fecha"), yo["rol"])
    actualizado = await corregir(db, GASTO, doc, GastoCreate, datos, yo, "Este gasto ya está registrado")
    return GastoResponse.model_validate(actualizado)
