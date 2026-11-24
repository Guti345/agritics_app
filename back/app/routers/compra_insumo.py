from datetime import date

from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from back.app.auth import ADMIN, FINANZAS_LECTURA
from back.app.database import COMPRA_INSUMO, INSUMOS, get_db
from back.app.reglas.fotos import exigir_foto
from back.app.reglas.operacion import descontar_insumo, devolver_insumo, sumar_stock
from back.app.reglas.semana import (
    auditar_escritura_en_periodo_cerrado,
    exigir_periodo_abierto,
    exigir_periodos_abiertos_en_correccion,
)
from back.app.schemas import CompraInsumoCreate, CompraInsumoResponse, CompraInsumoUpdate
from back.app.utils import a_oid, buscar_o_404, campos_captura, corregir, filtro_fechas, fusionar, insertar

router = APIRouter(prefix="/compras-insumos", tags=["Compras de insumos"])

DUPLICADA = "Esta compra ya está registrada"


@router.get("", response_model=list[CompraInsumoResponse], summary="Listar compras de insumos")
async def listar(
    fecha: date | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    insumo_id: str | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(FINANZAS_LECTURA),
):
    filtro = filtro_fechas(fecha, desde, hasta)
    if insumo_id:
        filtro["insumo_id"] = a_oid(insumo_id)
    docs = await db[COMPRA_INSUMO].find(filtro).sort([("fecha", -1), ("fecha_captura", -1)]).to_list(None)
    return [CompraInsumoResponse.model_validate(d) for d in docs]


@router.get("/{id}", response_model=CompraInsumoResponse, summary="Ver una compra de insumo")
async def ver(id: str, db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(FINANZAS_LECTURA)):
    return CompraInsumoResponse.model_validate(await buscar_o_404(db[COMPRA_INSUMO], id, "la compra"))


@router.post("", response_model=CompraInsumoResponse, status_code=status.HTTP_201_CREATED,
             summary="Registrar compra de insumo (suma al stock)")
async def crear(datos: CompraInsumoCreate, db: AsyncIOMotorDatabase = Depends(get_db), yo: dict = Depends(ADMIN)):
    """Suma la cantidad al stock del insumo con un $inc atómico y guarda la compra en la
    misma petición. Sin transacciones (Mongo local de una sola instancia): si la compra no
    alcanza a guardarse, el stock se devuelve."""
    exigir_foto(datos.comprobante_ruta)
    await buscar_o_404(db[INSUMOS], datos.insumo_id, "el insumo")
    corte = await exigir_periodo_abierto(db, datos.fecha, yo["rol"])
    await sumar_stock(db, datos.insumo_id, datos.cantidad)
    try:
        guardada = await insertar(db[COMPRA_INSUMO], {**datos.a_mongo(), **campos_captura(yo)}, DUPLICADA)
    except Exception:
        await devolver_insumo(db, datos.insumo_id, -datos.cantidad)
        raise
    await auditar_escritura_en_periodo_cerrado(db, corte, yo, COMPRA_INSUMO, guardada["_id"])
    return CompraInsumoResponse.model_validate(guardada)


@router.patch("/{id}", response_model=CompraInsumoResponse, summary="Corregir compra (ajusta el stock; queda en auditoría)")
async def corregir_compra(
    id: str, cambios: CompraInsumoUpdate, db: AsyncIOMotorDatabase = Depends(get_db), yo: dict = Depends(ADMIN)
):
    """Si cambia la cantidad o el insumo, el stock se ajusta por la diferencia. Si ese
    insumo ya se consumió y no alcanza para devolver, 409 y no se cambia nada."""
    doc = await buscar_o_404(db[COMPRA_INSUMO], id, "la compra")
    datos = cambios.model_dump(exclude_unset=True)
    await exigir_periodos_abiertos_en_correccion(db, doc["fecha"].date(), datos.get("fecha"), yo["rol"])
    if datos.get("comprobante_ruta"):
        exigir_foto(datos["comprobante_ruta"])
    nueva = fusionar(doc, CompraInsumoCreate, datos)  # valida TODO antes de mover stock

    viejo_insumo, vieja_cant = str(doc["insumo_id"]), doc["cantidad"]
    movimientos = []  # (insumo_id, cantidad sumada) para deshacer si algo falla
    try:
        if nueva.insumo_id == viejo_insumo:
            delta = nueva.cantidad - vieja_cant
            if delta > 0:
                await sumar_stock(db, viejo_insumo, delta)
                movimientos.append((viejo_insumo, delta))
            elif delta < 0:
                await descontar_insumo(db, viejo_insumo, -delta)
                movimientos.append((viejo_insumo, delta))
        else:
            await buscar_o_404(db[INSUMOS], nueva.insumo_id, "el insumo")
            await descontar_insumo(db, viejo_insumo, vieja_cant)
            movimientos.append((viejo_insumo, -vieja_cant))
            await sumar_stock(db, nueva.insumo_id, nueva.cantidad)
            movimientos.append((nueva.insumo_id, nueva.cantidad))
        actualizado = await corregir(db, COMPRA_INSUMO, doc, CompraInsumoCreate, datos, yo, DUPLICADA)
    except Exception:
        for insumo_id, cantidad in reversed(movimientos):
            await devolver_insumo(db, insumo_id, -cantidad)
        raise
    return CompraInsumoResponse.model_validate(actualizado)
