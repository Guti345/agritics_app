from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from back.app.auth import ADMIN, CUALQUIERA
from back.app.database import INSUMOS, get_db
from back.app.reglas.catalogos import exigir_nombre_libre, regla_insumo_nuevo
from back.app.schemas import InsumoCreate, InsumoResponse, InsumoUpdate
from back.app.utils import buscar_o_404, campos_captura, corregir, insertar

router = APIRouter(prefix="/insumos", tags=["Insumos"])


def _duplicado(nombre: str) -> str:
    return f"Ya existe un insumo con el nombre '{nombre}'"


@router.get("", response_model=list[InsumoResponse], summary="Listar insumos")
async def listar(
    bajo_stock: bool | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(CUALQUIERA),
):
    """`bajo_stock=true`: solo los que están en o por debajo de su umbral de alerta."""
    filtro = {}
    if bajo_stock is not None:
        comparacion = {"$lte": ["$stock_actual", "$umbral_alerta"]}
        filtro["$expr"] = comparacion if bajo_stock else {"$not": [comparacion]}
    docs = await db[INSUMOS].find(filtro).sort("nombre").to_list(None)
    return [InsumoResponse.model_validate(d) for d in docs]


@router.get("/{id}", response_model=InsumoResponse, summary="Ver un insumo")
async def ver(id: str, db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(CUALQUIERA)):
    return InsumoResponse.model_validate(await buscar_o_404(db[INSUMOS], id, "el insumo"))


@router.post("", response_model=InsumoResponse, status_code=status.HTTP_201_CREATED, summary="Crear insumo")
async def crear(datos: InsumoCreate, db: AsyncIOMotorDatabase = Depends(get_db), yo: dict = Depends(ADMIN)):
    regla_insumo_nuevo(datos)
    await exigir_nombre_libre(db[INSUMOS], "nombre", datos.nombre, _duplicado(datos.nombre))
    doc = {**datos.a_mongo(), **campos_captura(yo)}
    return InsumoResponse.model_validate(await insertar(db[INSUMOS], doc, _duplicado(datos.nombre)))


@router.patch("/{id}", response_model=InsumoResponse, summary="Corregir insumo (queda en auditoría)")
async def corregir_insumo(
    id: str, cambios: InsumoUpdate, db: AsyncIOMotorDatabase = Depends(get_db), yo: dict = Depends(ADMIN)
):
    doc = await buscar_o_404(db[INSUMOS], id, "el insumo")
    datos = cambios.model_dump(exclude_unset=True)
    if datos.get("nombre"):
        await exigir_nombre_libre(db[INSUMOS], "nombre", datos["nombre"], _duplicado(datos["nombre"]), doc["_id"])
    actualizado = await corregir(db, INSUMOS, doc, InsumoCreate, datos, yo, _duplicado(datos.get("nombre", "")))
    return InsumoResponse.model_validate(actualizado)
