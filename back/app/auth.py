"""Autenticación del MVP: claves con hash PBKDF2 y usuario en el header X-Usuario.

Sin JWT: tras el login, el frontend guarda el usuario en sesión y lo manda en cada
petición como `X-Usuario: <usuario>`. Cada endpoint resuelve ese usuario (activo) con
la dependencia `usuario_actual`, o exige un rol con `requiere_rol(...)`.
Es un esquema de MVP local: cualquiera que conozca un nombre de usuario podría
mandarlo en el header, así que no sirve para exponer la API a internet.
"""

import hashlib
import hmac
import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from back.app.database import USUARIOS, get_db

_ITERACIONES = 200_000


def hashear_clave(clave: str) -> str:
    sal = secrets.token_bytes(16)
    h = hashlib.pbkdf2_hmac("sha256", clave.encode(), sal, _ITERACIONES)
    return f"pbkdf2_sha256${_ITERACIONES}${sal.hex()}${h.hex()}"


def verificar_clave(clave: str, guardada: str) -> bool:
    try:
        algoritmo, iteraciones, sal, h = guardada.split("$")
        if algoritmo != "pbkdf2_sha256":
            return False
        calculado = hashlib.pbkdf2_hmac("sha256", clave.encode(), bytes.fromhex(sal), int(iteraciones))
        return hmac.compare_digest(calculado.hex(), h)
    except (ValueError, AttributeError):
        return False


async def usuario_actual(
    x_usuario: Annotated[str | None, Header(description="Usuario que inició sesión")] = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    if not x_usuario or not x_usuario.strip():
        raise HTTPException(status_code=401, detail="Debe iniciar sesión")
    usuario = await db[USUARIOS].find_one({"usuario": x_usuario.strip().lower(), "activo": True})
    if usuario is None:
        raise HTTPException(status_code=401, detail="Su usuario no existe o está inactivo: inicie sesión de nuevo")
    return usuario


def requiere_rol(*roles: str):
    """Dependencia: deja pasar solo a los roles indicados (403 en español si no)."""
    async def _dep(usuario: dict = Depends(usuario_actual)) -> dict:
        if usuario["rol"] not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"No tiene permiso para hacer esto: es solo para {' o '.join(roles)}",
            )
        return usuario
    return _dep


# Atajos de rol para los routers
CUALQUIERA = usuario_actual
ADMIN = requiere_rol("administrador", "superusuario")
ADMIN_O_MAYORDOMO = requiere_rol("administrador", "superusuario", "mayordomo")
SUPERUSUARIO = requiere_rol("superusuario")
FINANZAS_LECTURA = requiere_rol("administrador", "superusuario", "junta")
