"""Regla de semana cerrada: lo de una semana cerrada solo lo corrige el administrador.

La colección `cierres` la escribe el cierre de semana (paso posterior). Cada documento
cerrado lleva al menos {"semana": "2026-W48"}. Todavía no está en init_db.py ni en las
constantes de database.py: cuando llegue el cierre de semana hay que agregarla allí
(con índice único en `semana`).
"""

from datetime import date

from motor.motor_asyncio import AsyncIOMotorDatabase

from back.app.reglas.errores import conflicto

CIERRES = "cierres"


def semana_iso(fecha: date) -> str:
    """date -> "2026-W48". Recibe la fecha del evento (la del DTO, en hora de Colombia)."""
    anio, semana, _ = fecha.isocalendar()
    return f"{anio}-W{semana:02d}"


async def semana_cerrada(db: AsyncIOMotorDatabase, semana: str) -> bool:
    return await db[CIERRES].find_one({"semana": semana, "cerrada": {"$ne": False}}) is not None


async def exigir_semana_abierta(db: AsyncIOMotorDatabase, fecha: date, rol: str) -> None:
    """409 si la semana de `fecha` está cerrada y quien escribe no es administrador.

    Úsese en todo POST/PATCH que reciba fecha. En un PATCH que cambia la fecha, llamar
    con la fecha vieja y con la nueva: no se puede sacar ni meter un registro a una
    semana cerrada. Para fechas leídas de Mongo (datetime a las 00:00 UTC) pasar
    `doc["fecha"].date()`, no convertir a hora de Colombia.
    """
    if rol == "administrador":
        return
    semana = semana_iso(fecha)
    if await semana_cerrada(db, semana):
        raise conflicto(f"La semana {semana} ya está cerrada; solo el administrador puede corregirla")


async def exigir_semanas_abiertas_en_correccion(
    db: AsyncIOMotorDatabase, fecha_vieja: date, fecha_nueva: date | None, rol: str
) -> None:
    """PATCH: revisa la semana de la fecha vieja y, si cambia, la de la nueva."""
    await exigir_semana_abierta(db, fecha_vieja, rol)
    if fecha_nueva and fecha_nueva != fecha_vieja:
        await exigir_semana_abierta(db, fecha_nueva, rol)
