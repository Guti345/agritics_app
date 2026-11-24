from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from back.app.auth import SUPERUSUARIO, hashear_clave
from back.app.database import USUARIOS, get_db
from back.app.reglas.catalogos import exigir_nombre_libre
from back.app.reglas.errores import conflicto
from back.app.schemas import Rol, UsuarioCreate, UsuarioResponse, UsuarioUpdate
from back.app.utils import buscar_o_404, campos_captura, corregir, insertar

router = APIRouter(prefix="/usuarios", tags=["Usuarios (superusuario)"])


@router.get("", response_model=list[UsuarioResponse], summary="Listar usuarios")
async def listar(
    rol: Rol | None = None,
    activo: bool | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(SUPERUSUARIO),
):
    filtro = {}
    if rol:
        filtro["rol"] = rol.value
    if activo is not None:
        filtro["activo"] = activo
    docs = await db[USUARIOS].find(filtro).sort("usuario").to_list(None)
    return [UsuarioResponse.model_validate(d) for d in docs]


@router.post("", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED, summary="Crear usuario")
async def crear(
    datos: UsuarioCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    yo: dict = Depends(SUPERUSUARIO),
):
    mensaje = f"Ya existe el usuario '{datos.usuario}'"
    await exigir_nombre_libre(db[USUARIOS], "usuario", datos.usuario, mensaje)
    doc = datos.a_mongo()
    doc["clave"] = hashear_clave(datos.clave)  # nunca se guarda la clave en claro
    doc.update(campos_captura(yo))
    return UsuarioResponse.model_validate(await insertar(db[USUARIOS], doc, mensaje))


@router.patch("/{id}", response_model=UsuarioResponse, summary="Activar/inactivar o cambiar la clave")
async def corregir_usuario(
    id: str,
    cambios: UsuarioUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    yo: dict = Depends(SUPERUSUARIO),
):
    doc = await buscar_o_404(db[USUARIOS], id, "el usuario")
    datos = cambios.model_dump(exclude_unset=True)
    if datos.get("activo") is False and doc["_id"] == yo["_id"]:
        raise conflicto("No puede inactivar su propio usuario")
    transformar = (lambda nuevo: {**nuevo, "clave": hashear_clave(nuevo["clave"])}) if "clave" in datos else None
    actualizado = await corregir(
        db, USUARIOS, doc, UsuarioCreate, datos, yo,
        mensaje_duplicado=f"Ya existe el usuario '{doc['usuario']}'",
        transformar=transformar, ocultar=("clave",),
    )
    return UsuarioResponse.model_validate(actualizado)
