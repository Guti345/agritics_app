from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from back.app.auth import ADMIN, CUALQUIERA
from back.app.reglas.mensajes import LABOR_REPETIDA
from back.app.database import LABORES, get_db
from back.app.reglas.catalogos import exigir_nombre_libre, regla_labor
from back.app.schemas import Cultivo, LaborCreate, LaborResponse, LaborUpdate
from back.app.utils import buscar_o_404, campos_captura, corregir, insertar

router = APIRouter(prefix="/labores", tags=["Labores"])


@router.get("", response_model=list[LaborResponse], summary="Listar labores")
async def listar(
    cultivo: Cultivo | None = None,
    activa: bool | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(CUALQUIERA),
):
    filtro = {}
    if cultivo:
        filtro["cultivos"] = cultivo.value
    if activa is not None:
        filtro["activa"] = activa
    docs = await db[LABORES].find(filtro).sort("nombre").to_list(None)
    return [LaborResponse.model_validate(d) for d in docs]


@router.get("/{id}", response_model=LaborResponse, summary="Ver una labor")
async def ver(id: str, db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(CUALQUIERA)):
    return LaborResponse.model_validate(await buscar_o_404(db[LABORES], id, "la labor"))


@router.post("", response_model=LaborResponse, status_code=status.HTTP_201_CREATED, summary="Crear labor")
async def crear(datos: LaborCreate, db: AsyncIOMotorDatabase = Depends(get_db), yo: dict = Depends(ADMIN)):
    regla_labor(datos)
    await exigir_nombre_libre(db[LABORES], "nombre", datos.nombre, LABOR_REPETIDA)
    doc = {**datos.a_mongo(), **campos_captura(yo)}
    return LaborResponse.model_validate(await insertar(db[LABORES], doc, LABOR_REPETIDA))


@router.patch("/{id}", response_model=LaborResponse, summary="Corregir labor (queda en auditoría)")
async def corregir_labor(
    id: str, cambios: LaborUpdate, db: AsyncIOMotorDatabase = Depends(get_db), yo: dict = Depends(ADMIN)
):
    doc = await buscar_o_404(db[LABORES], id, "la labor")
    datos = cambios.model_dump(exclude_unset=True)
    if datos.get("nombre"):
        await exigir_nombre_libre(db[LABORES], "nombre", datos["nombre"], LABOR_REPETIDA, doc["_id"])
    actualizado = await corregir(
        db, LABORES, doc, LaborCreate, datos, yo, LABOR_REPETIDA, reglas=regla_labor
    )
    return LaborResponse.model_validate(actualizado)
