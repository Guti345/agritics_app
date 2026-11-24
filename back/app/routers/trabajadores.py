import re

from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from back.app.auth import ADMIN_O_MAYORDOMO, CUALQUIERA
from back.app.database import TRABAJADORES, get_db
from back.app.schemas import TrabajadorCreate, TrabajadorResponse, TrabajadorUpdate
from back.app.utils import buscar_o_404, campos_captura, corregir, insertar

router = APIRouter(prefix="/trabajadores", tags=["Trabajadores"])

# El documento puede ir vacío (varios trabajadores sin documento). Si viene y ya existe,
# lo frena el índice único parcial de Mongo y aquí se traduce a 409 en español.
DOCUMENTO_REPETIDO = "Ya hay un trabajador con ese documento"


@router.get("", response_model=list[TrabajadorResponse], summary="Listar trabajadores")
async def listar(
    buscar: str | None = None,
    documento: str | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(CUALQUIERA),
):
    """`buscar`: parte del nombre, sin distinguir mayúsculas."""
    filtro = {}
    if buscar:
        filtro["nombre"] = {"$regex": re.escape(buscar.strip()), "$options": "i"}
    if documento:
        filtro["documento"] = documento.strip()
    docs = await db[TRABAJADORES].find(filtro).sort("nombre").to_list(None)
    return [TrabajadorResponse.model_validate(d) for d in docs]


@router.get("/{id}", response_model=TrabajadorResponse, summary="Ver un trabajador")
async def ver(id: str, db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(CUALQUIERA)):
    return TrabajadorResponse.model_validate(await buscar_o_404(db[TRABAJADORES], id, "el trabajador"))


@router.post("", response_model=TrabajadorResponse, status_code=status.HTTP_201_CREATED, summary="Crear trabajador")
async def crear(
    datos: TrabajadorCreate, db: AsyncIOMotorDatabase = Depends(get_db), yo: dict = Depends(ADMIN_O_MAYORDOMO)
):
    doc = {**datos.a_mongo(), **campos_captura(yo)}
    return TrabajadorResponse.model_validate(await insertar(db[TRABAJADORES], doc, DOCUMENTO_REPETIDO))


@router.patch("/{id}", response_model=TrabajadorResponse, summary="Corregir trabajador (queda en auditoría)")
async def corregir_trabajador(
    id: str,
    cambios: TrabajadorUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    yo: dict = Depends(ADMIN_O_MAYORDOMO),
):
    doc = await buscar_o_404(db[TRABAJADORES], id, "el trabajador")
    actualizado = await corregir(
        db, TRABAJADORES, doc, TrabajadorCreate, cambios.model_dump(exclude_unset=True), yo, DOCUMENTO_REPETIDO
    )
    return TrabajadorResponse.model_validate(actualizado)
