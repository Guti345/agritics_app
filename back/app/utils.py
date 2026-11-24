"""Utilidades compartidas por los routers: ids, búsquedas, altas y correcciones auditadas."""

from typing import Any, Callable

from bson import ObjectId
from fastapi.exceptions import RequestValidationError
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pydantic import BaseModel, TypeAdapter, ValidationError
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from back.app.reglas.auditoria import registrar_correccion
from back.app.reglas.errores import conflicto, datos_invalidos, no_encontrado
from back.app.schemas import Entrada, SemanaISO, ahora


def a_oid(id: str) -> ObjectId:
    """Los ids viajan como texto; se convierten a ObjectId solo para hablar con Mongo."""
    if not ObjectId.is_valid(id):
        raise datos_invalidos(f"El id '{id}' no es válido (se esperan 24 caracteres hexadecimales)")
    return ObjectId(id)


async def buscar_o_404(coleccion: AsyncIOMotorCollection, id: str, que: str) -> dict:
    """`que` con artículo: "el lote", "la labor"..."""
    doc = await coleccion.find_one({"_id": a_oid(id)})
    if doc is None:
        raise no_encontrado(f"No existe {que} con id {id}")
    return doc


def validar_o_422(modelo: type[BaseModel], datos: dict) -> BaseModel:
    """Valida dentro del router con los mismos mensajes en español que un 422 normal."""
    try:
        return modelo.model_validate(datos)
    except ValidationError as e:
        raise RequestValidationError(e.errors()) from None


def campos_captura(usuario: dict) -> dict:
    return {"registrado_por": usuario["usuario"], "fecha_captura": ahora()}


async def insertar(coleccion: AsyncIOMotorCollection, doc: dict, mensaje_duplicado: str) -> dict:
    """Inserta y devuelve el documento guardado. Si un índice único lo rechaza (carrera
    entre dos capturas), responde 409 con el mensaje de negocio, nunca un error interno."""
    try:
        r = await coleccion.insert_one(doc)
    except DuplicateKeyError:
        raise conflicto(mensaje_duplicado) from None
    return await coleccion.find_one({"_id": r.inserted_id})


def _como_entrada(v: Any) -> Any:
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, dict):
        return {k: _como_entrada(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_como_entrada(x) for x in v]
    return v


async def corregir(
    db: AsyncIOMotorDatabase,
    coleccion: str,
    doc: dict,
    create: type[Entrada],
    cambios: dict,
    usuario: dict,
    mensaje_duplicado: str,
    reglas: Callable[[Entrada], None] | None = None,
    transformar: Callable[[dict], dict] | None = None,
    ocultar: tuple[str, ...] = (),
) -> dict:
    """PATCH auditado. Fusiona `cambios` con el documento actual, revalida TODO con el
    Create (mismas reglas y mensajes que al crear), aplica `reglas` de negocio, guarda
    solo lo que cambió y deja una fila en auditoría por cada campo. Nada se borra."""
    base = {k: _como_entrada(doc[k]) for k in create.model_fields if k in doc}
    fusion = {k: v for k, v in {**base, **cambios}.items() if v is not None}
    validado = validar_o_422(create, fusion)
    if reglas:
        reglas(validado)
    nuevo = validado.a_mongo()
    if transformar:
        nuevo = transformar(nuevo)

    poner, quitar, diferencias = {}, {}, []
    for campo in cambios:
        antes, despues = doc.get(campo), nuevo.get(campo)
        if antes == despues:
            continue
        if despues is None:
            quitar[campo] = ""
        else:
            poner[campo] = despues
        diferencias.append((campo, antes, despues))
    if not diferencias:
        return doc

    operacion = {}
    if poner:
        operacion["$set"] = poner
    if quitar:
        operacion["$unset"] = quitar
    try:
        actualizado = await db[coleccion].find_one_and_update(
            {"_id": doc["_id"]}, operacion, return_document=ReturnDocument.AFTER
        )
    except DuplicateKeyError:
        raise conflicto(mensaje_duplicado) from None
    await registrar_correccion(db, usuario["usuario"], coleccion, doc["_id"], diferencias, ocultar)
    return actualizado


_SEMANA_ISO = TypeAdapter(SemanaISO)


def semana_de_query(semana: str) -> str:
    """Valida un parámetro ?semana= con la misma regla del DTO (422 en español si no)."""
    try:
        return _SEMANA_ISO.validate_python(semana)
    except ValidationError as e:
        raise RequestValidationError([{**err, "loc": ("query", "semana")} for err in e.errors()]) from None
