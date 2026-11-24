from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from back.app.auth import ADMIN, CUALQUIERA
from back.app.database import UNIDADES, get_db
from back.app.reglas.catalogos import exigir_nombre_libre, regla_unidad
from back.app.schemas import UnidadCreate, UnidadResponse, UnidadUpdate
from back.app.utils import buscar_o_404, campos_captura, corregir, insertar

router = APIRouter(prefix="/unidades", tags=["Unidades"])


def _duplicado(nombre: str) -> str:
    return f"La unidad '{nombre}' ya está registrada"


@router.get("", response_model=list[UnidadResponse], summary="Listar unidades")
async def listar(db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(CUALQUIERA)):
    docs = await db[UNIDADES].find().sort("nombre").to_list(None)
    return [UnidadResponse.model_validate(d) for d in docs]


@router.get("/{id}", response_model=UnidadResponse, summary="Ver una unidad")
async def ver(id: str, db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(CUALQUIERA)):
    return UnidadResponse.model_validate(await buscar_o_404(db[UNIDADES], id, "la unidad"))


@router.post("", response_model=UnidadResponse, status_code=status.HTTP_201_CREATED, summary="Registrar unidad")
async def crear(datos: UnidadCreate, db: AsyncIOMotorDatabase = Depends(get_db), yo: dict = Depends(ADMIN)):
    regla_unidad(datos)
    await exigir_nombre_libre(db[UNIDADES], "nombre", datos.nombre, _duplicado(datos.nombre))
    doc = {**datos.a_mongo(), **campos_captura(yo)}
    return UnidadResponse.model_validate(await insertar(db[UNIDADES], doc, _duplicado(datos.nombre)))


@router.patch("/{id}", response_model=UnidadResponse, summary="Corregir equivalencias (queda en auditoría)")
async def corregir_unidad(
    id: str, cambios: UnidadUpdate, db: AsyncIOMotorDatabase = Depends(get_db), yo: dict = Depends(ADMIN)
):
    doc = await buscar_o_404(db[UNIDADES], id, "la unidad")
    actualizado = await corregir(
        db, UNIDADES, doc, UnidadCreate, cambios.model_dump(exclude_unset=True), yo, _duplicado(doc["nombre"])
    )
    return UnidadResponse.model_validate(actualizado)
