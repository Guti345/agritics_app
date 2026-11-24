from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from back.app.auth import verificar_clave
from back.app.database import USUARIOS, get_db
from back.app.schemas import LoginIn, UsuarioResponse

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=UsuarioResponse, summary="Iniciar sesión")
async def login(datos: LoginIn, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Si el usuario está activo y la clave coincide, devuelve sus datos (nunca la clave).
    El frontend guarda `usuario` y lo manda después en el header X-Usuario."""
    usuario = await db[USUARIOS].find_one({"usuario": datos.usuario.lower(), "activo": True})
    if usuario is None or not verificar_clave(datos.clave, usuario["clave"]):
        raise HTTPException(status_code=401, detail="Usuario o clave incorrectos")
    return UsuarioResponse.model_validate(usuario)
