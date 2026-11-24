from datetime import date

from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from back.app.auth import ADMIN, FINANZAS_LECTURA
from back.app.database import VENTA_CAFE, get_db
from back.app.reglas.catalogos import exigir_nombre_libre
from back.app.reglas.fotos import exigir_foto
from back.app.reglas.semana import exigir_semana_abierta, exigir_semanas_abiertas_en_correccion
from back.app.schemas import TipoProductoCafe, VentaCafeCreate, VentaCafeResponse, VentaCafeUpdate
from back.app.utils import buscar_o_404, campos_captura, corregir, filtro_fechas, insertar

router = APIRouter(prefix="/ventas-cafe", tags=["Venta de café"])


def _duplicado(comprobante: str) -> str:
    return f"Ya hay un recibo registrado con el comprobante '{comprobante}'"


@router.get("", response_model=list[VentaCafeResponse], summary="Listar ventas de café (recibos)")
async def listar(
    fecha: date | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    tipo_producto: TipoProductoCafe | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(FINANZAS_LECTURA),
):
    filtro = filtro_fechas(fecha, desde, hasta)
    if tipo_producto:
        filtro["tipo_producto"] = tipo_producto.value
    docs = await db[VENTA_CAFE].find(filtro).sort([("fecha", -1), ("fecha_captura", -1)]).to_list(None)
    return [VentaCafeResponse.model_validate(d) for d in docs]


@router.get("/{id}", response_model=VentaCafeResponse, summary="Ver un recibo de venta de café")
async def ver(id: str, db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(FINANZAS_LECTURA)):
    return VentaCafeResponse.model_validate(await buscar_o_404(db[VENTA_CAFE], id, "la venta de café"))


@router.post("", response_model=VentaCafeResponse, status_code=status.HTTP_201_CREATED,
             summary="Registrar recibo de la Cooperativa")
async def crear(datos: VentaCafeCreate, db: AsyncIOMotorDatabase = Depends(get_db), yo: dict = Depends(ADMIN)):
    """El recibo va completo en un solo documento. La aritmética (netos = brutos - destare),
    los porcentajes de calidad y la foto obligatoria los valida el DTO."""
    exigir_foto(datos.foto_ruta)
    if datos.id_comprobante:
        await exigir_nombre_libre(db[VENTA_CAFE], "id_comprobante", datos.id_comprobante, _duplicado(datos.id_comprobante))
    await exigir_semana_abierta(db, datos.fecha, yo["rol"])
    doc = {**datos.a_mongo(), **campos_captura(yo)}
    return VentaCafeResponse.model_validate(
        await insertar(db[VENTA_CAFE], doc, _duplicado(datos.id_comprobante or ""))
    )


@router.patch("/{id}", response_model=VentaCafeResponse, summary="Corregir recibo de café (queda en auditoría)")
async def corregir_venta(
    id: str, cambios: VentaCafeUpdate, db: AsyncIOMotorDatabase = Depends(get_db), yo: dict = Depends(ADMIN)
):
    doc = await buscar_o_404(db[VENTA_CAFE], id, "la venta de café")
    datos = cambios.model_dump(exclude_unset=True)
    await exigir_semanas_abiertas_en_correccion(db, doc["fecha"].date(), datos.get("fecha"), yo["rol"])
    if datos.get("foto_ruta"):
        exigir_foto(datos["foto_ruta"])
    if datos.get("id_comprobante"):
        await exigir_nombre_libre(
            db[VENTA_CAFE], "id_comprobante", datos["id_comprobante"], _duplicado(datos["id_comprobante"]), doc["_id"]
        )
    actualizado = await corregir(
        db, VENTA_CAFE, doc, VentaCafeCreate, datos, yo, _duplicado(datos.get("id_comprobante", ""))
    )
    return VentaCafeResponse.model_validate(actualizado)
