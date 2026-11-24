"""Nómina: NUNCA se guarda; sale de agregar labor_diaria (la usan los reportes).

Valor de cada registro:
  * jornal:   jornales x tarifa  (al jornal se paga el día completo)
  * contrato: meta cumplida x tarifa
      - tipo_meta "kilos" u "horas": avance x tarifa
      - tipo_meta "completada":      tarifa si la labor quedó completada, 0 si no

Calendario (README): lo de lunes a viernes se paga ese sábado; lo del fin de semana se
causa y se paga el sábado siguiente. `rango_semana` da lo CAUSADO en la semana (lunes a
domingo); `rango_pago` da lo que se PAGA el sábado de esa semana (sábado y domingo de la
semana anterior + lunes a viernes de esta).
"""

from datetime import date, datetime, timedelta, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from back.app.database import LABOR_DIARIA, TRABAJADORES
from back.app.reglas.operacion import lunes_de


def rango_semana(semana: str) -> tuple[date, date]:
    lunes = lunes_de(semana)
    return lunes, lunes + timedelta(days=6)


def rango_pago(semana: str) -> tuple[date, date]:
    lunes = lunes_de(semana)
    return lunes - timedelta(days=2), lunes + timedelta(days=4)


def _utc(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)  # así se guardan las fechas de día


VALOR_REGISTRO = {
    "$cond": [
        {"$eq": ["$forma_pago", "jornal"]},
        {"$multiply": ["$jornales", "$tarifa"]},
        {"$cond": [
            {"$eq": ["$tipo_meta", "completada"]},
            {"$cond": ["$completada", "$tarifa", 0]},
            {"$multiply": ["$avance", "$tarifa"]},
        ]},
    ]
}


def pipeline_nomina(desde: date, hasta: date) -> list[dict]:
    return [
        {"$match": {"fecha": {"$gte": _utc(desde), "$lte": _utc(hasta)}}},
        {"$group": {
            "_id": {"trabajador_id": "$trabajador_id", "forma_pago": "$forma_pago"},
            "labores": {"$sum": 1},
            "abiertas": {"$sum": {"$cond": ["$completada", 0, 1]}},
            "jornales": {"$sum": "$jornales"},
            "valor": {"$sum": VALOR_REGISTRO},
        }},
    ]


async def nomina(db: AsyncIOMotorDatabase, desde: date, hasta: date) -> list[dict]:
    """Nómina por trabajador entre dos fechas (inclusive), ordenada por nombre.
    `labores_abiertas` > 0 avisa que hay jornales todavía estimados (sin completar)."""
    filas = await db[LABOR_DIARIA].aggregate(pipeline_nomina(desde, hasta)).to_list(None)
    por_trabajador: dict = {}
    for f in filas:
        tid, forma = f["_id"]["trabajador_id"], f["_id"]["forma_pago"]
        t = por_trabajador.setdefault(tid, {
            "trabajador_id": str(tid),
            "jornal": {"labores": 0, "jornales": 0, "valor": 0},
            "contrato": {"labores": 0, "jornales": 0, "valor": 0},
            "labores_abiertas": 0,
        })
        t[forma] = {"labores": f["labores"], "jornales": f["jornales"], "valor": f["valor"]}
        t["labores_abiertas"] += f["abiertas"]
    nombres = {
        d["_id"]: d["nombre"]
        async for d in db[TRABAJADORES].find({"_id": {"$in": list(por_trabajador)}}, {"nombre": 1})
    }
    resultado = []
    for tid, t in por_trabajador.items():
        t["nombre"] = nombres.get(tid, "(trabajador no encontrado)")
        t["total"] = t["jornal"]["valor"] + t["contrato"]["valor"]
        resultado.append(t)
    return sorted(resultado, key=lambda t: t["nombre"].lower())


async def nomina_semana(db: AsyncIOMotorDatabase, semana: str) -> list[dict]:
    """Lo causado en la semana ISO (lunes a domingo)."""
    return await nomina(db, *rango_semana(semana))
