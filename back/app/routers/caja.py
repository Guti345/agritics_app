from datetime import date

from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from back.app.auth import ADMIN, FINANZAS_LECTURA
from back.app.database import MOVIMIENTO_CAJA, get_db
from back.app.reglas.caja import calcular_saldo
from back.app.reglas.semana import (
    auditar_escritura_en_periodo_cerrado,
    exigir_periodo_abierto,
    exigir_periodos_abiertos_en_correccion,
)
from back.app.schemas import (
    CajaSaldoResponse,
    MovimientoCajaCreate,
    MovimientoCajaResponse,
    MovimientoCajaUpdate,
    TipoMovimientoCaja,
)
from back.app.utils import buscar_o_404, campos_captura, corregir, filtro_fechas, insertar

router = APIRouter(prefix="/caja", tags=["Caja"])


@router.get("/saldo", response_model=CajaSaldoResponse, summary="Saldo de caja con el detalle por componente")
async def saldo(
    desde: date | None = None,
    hasta: date | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(FINANZAS_LECTURA),
):
    """ventas (café + plátano) - gastos - compras - nómina causada + movimientos de caja.
    Sin fechas: desde el primer registro hasta hoy."""
    return CajaSaldoResponse.model_validate(await calcular_saldo(db, desde, hasta))


@router.get("/movimientos", response_model=list[MovimientoCajaResponse], summary="Listar movimientos de caja")
async def listar(
    fecha: date | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    tipo: TipoMovimientoCaja | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(FINANZAS_LECTURA),
):
    filtro = filtro_fechas(fecha, desde, hasta)
    if tipo:
        filtro["tipo"] = tipo.value
    docs = await db[MOVIMIENTO_CAJA].find(filtro).sort([("fecha", -1), ("fecha_captura", -1)]).to_list(None)
    return [MovimientoCajaResponse.model_validate(d) for d in docs]


@router.get("/movimientos/{id}", response_model=MovimientoCajaResponse, summary="Ver un movimiento de caja")
async def ver(id: str, db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(FINANZAS_LECTURA)):
    return MovimientoCajaResponse.model_validate(await buscar_o_404(db[MOVIMIENTO_CAJA], id, "el movimiento de caja"))


@router.post("/movimientos", response_model=MovimientoCajaResponse, status_code=status.HTTP_201_CREATED,
             summary="Registrar aporte de capital, retiro o ajuste")
async def crear(datos: MovimientoCajaCreate, db: AsyncIOMotorDatabase = Depends(get_db), yo: dict = Depends(ADMIN)):
    """Las reglas de valor por tipo las valida el DTO. Entra al flujo de caja, nunca al margen."""
    corte = await exigir_periodo_abierto(db, datos.fecha, yo["rol"])
    doc = {**datos.a_mongo(), **campos_captura(yo)}
    guardado = await insertar(db[MOVIMIENTO_CAJA], doc, "Este movimiento ya está registrado")
    await auditar_escritura_en_periodo_cerrado(db, corte, yo, MOVIMIENTO_CAJA, guardado["_id"])
    return MovimientoCajaResponse.model_validate(guardado)


@router.patch("/movimientos/{id}", response_model=MovimientoCajaResponse,
              summary="Corregir movimiento de caja (queda en auditoría)")
async def corregir_movimiento(
    id: str, cambios: MovimientoCajaUpdate, db: AsyncIOMotorDatabase = Depends(get_db), yo: dict = Depends(ADMIN)
):
    doc = await buscar_o_404(db[MOVIMIENTO_CAJA], id, "el movimiento de caja")
    datos = cambios.model_dump(exclude_unset=True)
    await exigir_periodos_abiertos_en_correccion(db, doc["fecha"].date(), datos.get("fecha"), yo["rol"])
    actualizado = await corregir(db, MOVIMIENTO_CAJA, doc, MovimientoCajaCreate, datos, yo, "Este movimiento ya está registrado")
    return MovimientoCajaResponse.model_validate(actualizado)
