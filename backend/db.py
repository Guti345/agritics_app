"""Conexión a MongoDB local (motor, async).

La base es "agritics" en mongodb://localhost:27017. Se puede cambiar con las
variables de entorno AGRITICS_MONGO_URL y AGRITICS_DB_NAME (útil para pruebas).

Recordatorio de la regla transversal: Mongo es la SEGUNDA línea de defensa
(validadores $jsonSchema e índices únicos). Toda regla de negocio se valida antes,
en la capa de DTOs/reglas, y falla con HTTPException y mensaje en español.
"""

import os

from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)

MONGO_URL = os.getenv("AGRITICS_MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("AGRITICS_DB_NAME", "agritics")

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
            MONGO_URL,
            serverSelectionTimeoutMS=3000,  # si Mongo está apagado, fallar rápido
            tz_aware=True,
        )
    return _client


def get_db() -> AsyncIOMotorDatabase:
    """Base de datos "agritics". Sirve también como dependencia de FastAPI:
    `db: AsyncIOMotorDatabase = Depends(get_db)`."""
    return get_client()[DB_NAME]


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
