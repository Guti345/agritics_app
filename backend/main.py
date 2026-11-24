"""Agritics API.

Correr desde la raíz del repo:
    uvicorn backend.main:app --reload
Swagger en http://localhost:8000/docs

Regla transversal: ninguna validación de negocio llega a Mongo como error
interno. Toda regla se valida antes (DTOs + backend/reglas) y falla con
HTTPException y detail en español claro (ver backend/reglas/errores.py):
201 al crear, 404 si no existe, 409 si se incumple una regla de estado,
422 si los datos son inválidos.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend import db
from backend.reglas.manejadores import registrar_manejadores
from backend.routers import health

API_PREFIX = "/api/v1"

log = logging.getLogger("uvicorn.error")  # sale en la consola de uvicorn


@asynccontextmanager
async def lifespan(_: FastAPI):
    if await db.ping():
        log.info("MongoDB conectado: %s / base '%s'", db.MONGO_URL, db.DB_NAME)
    else:
        log.warning(
            "MongoDB no responde en %s. La API arranca, pero las operaciones con datos "
            "fallarán hasta que Mongo esté encendido.", db.MONGO_URL,
        )
    yield
    db.close_client()


app = FastAPI(
    title="Agritics API",
    version="1.0",
    description="Mi finca en datos - API del sistema de información de la Finca Portugal.",
    docs_url="/docs",
    lifespan=lifespan,
)

registrar_manejadores(app)

# Todos los routers se montan con el mismo prefijo.
app.include_router(health.router, prefix=API_PREFIX)
