"""Conexión a MongoDB local (motor, async).

La conexión se configura con las variables MONGO_URI y MONGO_DB, que son
obligatorias (no hay valores por defecto). Van en el entorno o en un archivo .env
en la raíz del repo (copiar .env.example). El .env no se sube a git. Si una
variable está en el entorno y también en el .env, gana la del entorno.

Recordatorio de la regla transversal: Mongo es la SEGUNDA línea de defensa
(validadores $jsonSchema e índices únicos). Toda regla de negocio se valida antes,
en la capa de DTOs/reglas, y falla con HTTPException y mensaje en español.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)

# .env de la raíz del repo, sin importar desde qué carpeta se lance uvicorn.
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)



def _variable_obligatoria(nombre: str) -> str:
    valor = os.getenv(nombre, "").strip()
    if not valor:
        raise RuntimeError(
            f"Falta la variable {nombre}. Defínala en el archivo .env de la raíz del "
            f"repo (vea .env.example) o en el entorno antes de arrancar la API."
        )
    return valor


MONGO_URI = _variable_obligatoria("MONGO_URI")
MONGO_DB = _variable_obligatoria("MONGO_DB")

# --- Nombres de colecciones -------------------------------------------------
# Catálogos
LOTES = "lotes"
LABORES = "labores"
TRABAJADORES = "trabajadores"
INSUMOS = "insumos"
UNIDADES = "unidades"
USUARIOS = "usuarios"
# Operación
LABOR_DIARIA = "labor_diaria"
POOL_SEMANA = "pool_semana"
COSECHA_PLATANO = "cosecha_platano"
VENTA_PLATANO = "venta_platano"
VENTA_CAFE = "venta_cafe"
COMPRA_INSUMO = "compra_insumo"
GASTO = "gasto"
MOVIMIENTO_CAJA = "movimiento_caja"
LLUVIA = "lluvia"
# Correcciones (nada se borra: los cambios quedan aquí)
AUDITORIA = "auditoria"

COLECCIONES = (
    LOTES, LABORES, TRABAJADORES, INSUMOS, UNIDADES, USUARIOS,
    LABOR_DIARIA, POOL_SEMANA, COSECHA_PLATANO, VENTA_PLATANO, VENTA_CAFE,
    COMPRA_INSUMO, GASTO, MOVIMIENTO_CAJA, LLUVIA, AUDITORIA,
)

# --- Cliente ----------------------------------------------------------------
_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    """Cliente único del proceso. Motor conecta de forma perezosa (al primer uso)."""
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(
            MONGO_URI,
            serverSelectionTimeoutMS=3000,  # si Mongo está apagado, fallar rápido
            tz_aware=True,
        )
    return _client


def get_db() -> AsyncIOMotorDatabase:
    """Base de datos "agritics". Sirve también como dependencia de FastAPI:
    `db: AsyncIOMotorDatabase = Depends(get_db)`."""
    return get_client()[MONGO_DB]


def coleccion(nombre: str) -> AsyncIOMotorCollection:
    """Referencia a una colección por nombre, p. ej. `coleccion(LOTES)`."""
    return get_db()[nombre]


async def ping() -> bool:
    """True si Mongo responde."""
    try:
        await get_client().admin.command("ping")
        return True
    except Exception:
        return False


def close_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None
