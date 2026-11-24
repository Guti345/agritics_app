from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from back.app.auth import ADMIN, CUALQUIERA
from back.app.database import LOTES, get_db
from back.app.reglas.catalogos import exigir_nombre_libre
from back.app.schemas import Cultivo, EstadoLote, LoteCreate, LoteResponse, LoteUpdate
from back.app.utils import buscar_o_404, campos_captura, corregir, insertar

router = APIRouter(prefix="/lotes", tags=["Lotes"])


def _duplicado(nombre: str) -> str:
    return f"Ya existe un lote con el nombre '{nombre}'"


@router.get("", response_model=list[LoteResponse], summary="Listar lotes")
async def listar(
    estado: EstadoLote | None = None,
    cultivo: Cultivo | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(CUALQUIERA),
):
    filtro = {}
    if estado:
        filtro["estado"] = estado.value
    if cultivo:
        filtro["cultivos"] = cultivo.value
    docs = await db[LOTES].find(filtro).sort("nombre").to_list(None)
    return [LoteResponse.model_validate(d) for d in docs]


@router.get("/{id}", response_model=LoteResponse, summary="Ver un lote")
async def ver(id: str, db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(CUALQUIERA)):
    return LoteResponse.model_validate(await buscar_o_404(db[LOTES], id, "el lote"))


@router.post("", response_model=LoteResponse, status_code=status.HTTP_201_CREATED, summary="Crear lote")
async def crear(datos: LoteCreate, db: AsyncIOMotorDatabase = Depends(get_db), yo: dict = Depends(ADMIN)):
    await exigir_nombre_libre(db[LOTES], "nombre", datos.nombre, _duplicado(datos.nombre))
    doc = {**datos.a_mongo(), **campos_captura(yo)}
    return LoteResponse.model_validate(await insertar(db[LOTES], doc, _duplicado(datos.nombre)))


@router.patch("/{id}", response_model=LoteResponse, summary="Corregir lote (queda en auditoría)")
async def corregir_lote(
    id: str, cambios: LoteUpdate, db: AsyncIOMotorDatabase = Depends(get_db), yo: dict = Depends(ADMIN)
):
    doc = await buscar_o_404(db[LOTES], id, "el lote")
    datos = cambios.model_dump(exclude_unset=True)
    if datos.get("nombre"):
        await exigir_nombre_libre(db[LOTES], "nombre", datos["nombre"], _duplicado(datos["nombre"]), doc["_id"])
    actualizado = await corregir(db, LOTES, doc, LoteCreate, datos, yo, _duplicado(datos.get("nombre", "")))
    return LoteResponse.model_validate(actualizado)
