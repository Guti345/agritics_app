"""Regla de periodo cerrado: lo que cae dentro de un corte solo lo corrige el administrador.

Modelo de cierre: la semana ISO (lunes-domingo, "2026-W48") es solo el contenedor.
Dentro puede haber varios cortes de nómina; cada corte cierra un PERIODO [desde, hasta]
y el trabajo sigue. Una fecha está cerrada si cae dentro del [desde, hasta] de algún
corte de su semana ISO (colección `cierres`).
"""

from datetime import date, datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from back.app.database import CIERRES
from back.app.reglas.auditoria import registrar_correccion
from back.app.reglas.errores import conflicto


def semana_iso(fecha: date) -> str:
    """date -> "2026-W48". Recibe la fecha del evento (la del DTO, en hora de Colombia)."""
    anio, semana, _ = fecha.isocalendar()
    return f"{anio}-W{semana:02d}"


def _utc(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)  # así se guardan las fechas de día


async def corte_que_contiene(db: AsyncIOMotorDatabase, fecha: date) -> dict | None:
    """El corte de la semana ISO de `fecha` cuyo periodo [desde, hasta] la contiene, si hay."""
    return await db[CIERRES].find_one(
        {"semana": semana_iso(fecha), "desde": {"$lte": _utc(fecha)}, "hasta": {"$gte": _utc(fecha)}}
    )


async def exigir_periodo_abierto(db: AsyncIOMotorDatabase, fecha: date, rol: str) -> dict | None:
    """409 si `fecha` ya quedó dentro de un corte y quien escribe no es administrador.

    Si es administrador, pasa y devuelve ese corte para que el router deje constancia en
    auditoría (`auditar_escritura_en_periodo_cerrado`). Úsese en todo POST/PATCH que
    reciba fecha. Para fechas leídas de Mongo (datetime a las 00:00 UTC) pasar
    `doc["fecha"].date()`, no convertir a hora de Colombia.
    """
    corte = await corte_que_contiene(db, fecha)
    if corte is None:
        return None
    if rol != "administrador":
        raise conflicto(
            f"Esa fecha ya quedó dentro del corte {corte['corte']} de la semana {corte['semana']}; "
            "solo el administrador puede corregirla"
        )
    return corte


async def exigir_periodos_abiertos_en_correccion(
    db: AsyncIOMotorDatabase, fecha_vieja: date, fecha_nueva: date | None, rol: str
) -> None:
    """PATCH: revisa el periodo de la fecha vieja y, si cambia, el de la nueva (no se saca
    ni se mete un registro a un periodo cerrado). El PATCH ya queda en auditoría."""
    await exigir_periodo_abierto(db, fecha_vieja, rol)
    if fecha_nueva and fecha_nueva != fecha_vieja:
        await exigir_periodo_abierto(db, fecha_nueva, rol)


async def auditar_escritura_en_periodo_cerrado(
    db: AsyncIOMotorDatabase, corte: dict | None, usuario: dict, coleccion: str, documento_id: ObjectId
) -> None:
    """Si el administrador creó un registro dentro de un periodo ya cortado, queda en auditoría."""
    if corte is None:
        return
    await registrar_correccion(
        db, usuario["usuario"], coleccion, documento_id,
        [("creado_en_periodo_cerrado", None, f"corte {corte['corte']} de la semana {corte['semana']}")],
    )


async def semana_cortada_completa(db: AsyncIOMotorDatabase, semana: str) -> dict | None:
    """El corte que llega hasta el domingo, si la semana ya quedó cortada completa."""
    domingo = date.fromisocalendar(int(semana[:4]), int(semana[6:]), 7)
    return await db[CIERRES].find_one({"semana": semana, "hasta": {"$gte": _utc(domingo)}})
