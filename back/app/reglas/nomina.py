"""Nómina: NUNCA se guarda; sale de agregar labor_diaria (la usan cortes, caja y reportes).

Modelo de cierre: la semana ISO (lunes-domingo) es solo el contenedor; dentro hay cortes
de nómina que cierran periodos. La nómina se calcula por RANGO de fechas.

Valor PACTADO de una labor:
  * jornal:                         jornales x tarifa  (al jornal se paga el día completo)
  * contrato, meta "completada":    tarifa             (precio de la labor entera)
  * contrato, meta "kilos"/"horas": avance x tarifa    (tarifa por kilo u hora)

Dos vistas, sin contar nada dos veces:
  1. `nomina(desde, hasta)` — lo CAUSADO en el rango (saldo de caja, reportes):
     - labores COMPLETADAS con fecha en el rango: su valor pactado completo (en un
       contrato eso ya incluye lo que se adelantó: los anticipos no se suman aparte);
     - contratos ABIERTOS: solo los anticipos pagados en el rango (plata que ya salió);
     - las abiertas sin anticipo no suman: van aparte como `estimado_abiertas`.
  2. `pago_de_corte(...)` — lo que se PAGA en un corte:
     - jornal completadas sin corte:   jornales x tarifa
     - contrato completadas sin corte: pactado - anticipos acumulados de esa labor
     - + los anticipos nuevos registrados en ese corte.
"""

from datetime import date, datetime, timedelta, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from back.app.database import LABOR_DIARIA, TRABAJADORES
from back.app.reglas.operacion import lunes_de
from back.app.schemas import BOGOTA


def rango_semana(semana: str) -> tuple[date, date]:
    """Lunes y domingo de la semana ISO (el contenedor de los cortes)."""
    lunes = lunes_de(semana)
    return lunes, lunes + timedelta(days=6)


def _utc(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)  # así se guardan las fechas de día


def _inicio_dia_colombia(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=BOGOTA)


# ── Expresiones de agregación ──
PACTADO = {
    "$cond": [
        {"$eq": ["$forma_pago", "jornal"]},
        {"$multiply": ["$jornales", "$tarifa"]},
        {"$cond": [
            {"$eq": ["$tipo_meta", "completada"]},
            "$tarifa",
            {"$multiply": ["$avance", "$tarifa"]},
        ]},
    ]
}
ANTICIPOS_TOTAL = {"$sum": {"$ifNull": ["$anticipos.valor", []]}}


def valor_pactado(labor: dict) -> float:
    """Lo mismo que PACTADO, para validar en Python (por ejemplo, el tope de un anticipo)."""
    if labor["forma_pago"] == "jornal":
        return labor["jornales"] * labor["tarifa"]
    if labor.get("tipo_meta") == "completada":
        return labor["tarifa"]
    return labor.get("avance", 0) * labor["tarifa"]


def anticipos_acumulados(labor: dict) -> float:
    return sum(a["valor"] for a in labor.get("anticipos", []))


def _si(cond, valor):
    return {"$sum": {"$cond": [cond, valor, 0]}}


async def _nombres(db: AsyncIOMotorDatabase, ids) -> dict:
    return {d["_id"]: d["nombre"] async for d in db[TRABAJADORES].find({"_id": {"$in": list(ids)}}, {"nombre": 1})}


# ── 1. Nómina causada por rango ──

async def nomina(db: AsyncIOMotorDatabase, desde: date, hasta: date) -> list[dict]:
    """Nómina CAUSADA por trabajador entre dos fechas (inclusive), ordenada por nombre.
    `total` = jornal + contrato (completadas, valor pactado) + anticipos de contratos
    abiertos pagados en el rango. `estimado_abiertas` NO entra al total."""
    en_rango = {"$and": [{"$gte": ["$fecha", _utc(desde)]}, {"$lte": ["$fecha", _utc(hasta)]}]}
    ini, fin = _inicio_dia_colombia(desde), _inicio_dia_colombia(hasta) + timedelta(days=1)
    jornal, contrato = {"$eq": ["$forma_pago", "jornal"]}, {"$eq": ["$forma_pago", "contrato"]}
    filas = await db[LABOR_DIARIA].aggregate([
        {"$match": {"$or": [
            {"fecha": {"$gte": _utc(desde), "$lte": _utc(hasta)}},
            {"completada": False, "forma_pago": "contrato", "anticipos.fecha": {"$gte": ini, "$lt": fin}},
        ]}},
        {"$addFields": {
            "_pactado": PACTADO,
            "_en_rango": en_rango,
            "_anticipos_rango": {"$sum": {"$map": {
                "input": {"$filter": {"input": {"$ifNull": ["$anticipos", []]}, "as": "a", "cond": {
                    "$and": [{"$gte": ["$$a.fecha", ini]}, {"$lt": ["$$a.fecha", fin]}]}}},
                "as": "a", "in": "$$a.valor"}}},
        }},
        {"$group": {
            "_id": "$trabajador_id",
            "jornal_labores": _si({"$and": ["$completada", "$_en_rango", jornal]}, 1),
            "jornal_jornales": _si({"$and": ["$completada", "$_en_rango", jornal]}, "$jornales"),
            "jornal_valor": _si({"$and": ["$completada", "$_en_rango", jornal]}, "$_pactado"),
            "contrato_labores": _si({"$and": ["$completada", "$_en_rango", contrato]}, 1),
            "contrato_jornales": _si({"$and": ["$completada", "$_en_rango", contrato]}, "$jornales"),
            "contrato_valor": _si({"$and": ["$completada", "$_en_rango", contrato]}, "$_pactado"),
            "anticipos_labores": _si({"$and": [{"$not": ["$completada"]}, {"$gt": ["$_anticipos_rango", 0]}]}, 1),
            "anticipos_valor": _si({"$not": ["$completada"]}, "$_anticipos_rango"),
            "abiertas": _si({"$and": [{"$not": ["$completada"]}, "$_en_rango"]}, 1),
            "estimado": _si({"$and": [{"$not": ["$completada"]}, "$_en_rango"]}, "$_pactado"),
        }},
    ]).to_list(None)
    nombres = await _nombres(db, (f["_id"] for f in filas))
    resultado = []
    for f in filas:
        t = {
            "trabajador_id": str(f["_id"]),
            "nombre": nombres.get(f["_id"], "(trabajador no encontrado)"),
            "jornal": {"labores": f["jornal_labores"], "jornales": f["jornal_jornales"], "valor": f["jornal_valor"]},
            "contrato": {"labores": f["contrato_labores"], "jornales": f["contrato_jornales"], "valor": f["contrato_valor"]},
            "anticipos": {"labores": f["anticipos_labores"], "valor": f["anticipos_valor"]},
            "labores_abiertas": f["abiertas"],
            "estimado_abiertas": f["estimado"],
        }
        t["total"] = t["jornal"]["valor"] + t["contrato"]["valor"] + t["anticipos"]["valor"]
        resultado.append(t)
    return sorted(resultado, key=lambda t: t["nombre"].lower())


async def nomina_semana(db: AsyncIOMotorDatabase, semana: str) -> list[dict]:
    """Lo causado en la semana ISO (lunes a domingo)."""
    return await nomina(db, *rango_semana(semana))


# ── 2. Pago de un corte ──

async def pago_de_corte(
    db: AsyncIOMotorDatabase,
    *,
    hasta: date | None = None,
    corte: tuple[str, int] | None = None,
    anticipos: list[tuple[dict, float]] = (),
    trabajador_ids: list[ObjectId] | None = None,
) -> tuple[list[dict], list[ObjectId]]:
    """Filas de pago por trabajador y los ids de las labores que se pagan.

    - Corte nuevo / preview: `hasta` -> completadas SIN corte con fecha <= hasta.
    - Corte ya hecho (para recalcular): `corte=(semana, numero)` -> las marcadas con él.
    - `anticipos`: [(labor, valor)] nuevos de este corte; suman al pago.
    - `trabajador_ids` (corte nuevo, pago selectivo): solo las labores de esos trabajadores;
      las de los demás quedan sin corte para un corte posterior. None = todos.
    """
    if corte is not None:
        filtro = {"corte_semana": corte[0], "corte": corte[1]}
    else:
        filtro = {"completada": True, "corte": {"$exists": False}, "fecha": {"$lte": _utc(hasta)}}
        if trabajador_ids is not None:
            filtro["trabajador_id"] = {"$in": trabajador_ids}
    jornal, contrato = {"$eq": ["$forma_pago", "jornal"]}, {"$eq": ["$forma_pago", "contrato"]}
    filas = await db[LABOR_DIARIA].aggregate([
        {"$match": filtro},
        {"$addFields": {"_pactado": PACTADO, "_anticipos": ANTICIPOS_TOTAL}},
        {"$group": {
            "_id": "$trabajador_id",
            "ids": {"$push": "$_id"},
            "jornal_labores": _si(jornal, 1),
            "jornal_jornales": _si(jornal, "$jornales"),
            "jornal_valor": _si(jornal, "$_pactado"),
            "contrato_labores": _si(contrato, 1),
            "contrato_pactado": _si(contrato, "$_pactado"),
            "contrato_anticipos": _si(contrato, "$_anticipos"),
        }},
    ]).to_list(None)

    por_trabajador: dict = {}
    ids_pagados: list[ObjectId] = []
    for f in filas:
        ids_pagados += f["ids"]
        por_trabajador[f["_id"]] = {
            "jornal": {"labores": f["jornal_labores"], "jornales": f["jornal_jornales"], "valor": f["jornal_valor"]},
            "contrato": {
                "labores": f["contrato_labores"],
                "pactado": f["contrato_pactado"],
                "anticipos_descontados": f["contrato_anticipos"],
                "valor": f["contrato_pactado"] - f["contrato_anticipos"],
            },
            "anticipos": {"labores": 0, "valor": 0},
        }
    vacia = lambda: {  # noqa: E731
        "jornal": {"labores": 0, "jornales": 0, "valor": 0},
        "contrato": {"labores": 0, "pactado": 0, "anticipos_descontados": 0, "valor": 0},
        "anticipos": {"labores": 0, "valor": 0},
    }
    for labor, valor in anticipos:
        t = por_trabajador.setdefault(labor["trabajador_id"], vacia())
        t["anticipos"]["labores"] += 1
        t["anticipos"]["valor"] += valor

    nombres = await _nombres(db, por_trabajador)
    resultado = []
    for tid, t in por_trabajador.items():
        t["trabajador_id"] = str(tid)
        t["nombre"] = nombres.get(tid, "(trabajador no encontrado)")
        t["total"] = t["jornal"]["valor"] + t["contrato"]["valor"] + t["anticipos"]["valor"]
        resultado.append(t)
    return sorted(resultado, key=lambda t: t["nombre"].lower()), ids_pagados


async def nomina_por_dia(db: AsyncIOMotorDatabase, desde: date, hasta: date) -> dict[date, float]:
    """La MISMA nómina causada de `nomina()` (mismas expresiones y reglas), repartida por día:
    labores completadas en su fecha (valor pactado) y anticipos de contratos abiertos en el
    día en que se pagaron (hora de Colombia). La suma sobre el rango = total de `nomina()`.
    La usa el flujo de caja (detalle diario y periodos)."""
    ini, fin = _inicio_dia_colombia(desde), _inicio_dia_colombia(hasta) + timedelta(days=1)
    r = await db[LABOR_DIARIA].aggregate([{"$facet": {
        "completadas": [
            {"$match": {"completada": True, "fecha": {"$gte": _utc(desde), "$lte": _utc(hasta)}}},
            {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$fecha"}}, "valor": {"$sum": PACTADO}}},
        ],
        "anticipos": [
            {"$match": {"completada": False, "forma_pago": "contrato", "anticipos.fecha": {"$gte": ini, "$lt": fin}}},
            {"$unwind": "$anticipos"},
            {"$match": {"anticipos.fecha": {"$gte": ini, "$lt": fin}}},
            {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$anticipos.fecha", "timezone": "-05:00"}},
                        "valor": {"$sum": "$anticipos.valor"}}},
        ],
    }}]).to_list(1)
    por_dia: dict[date, float] = {}
    for fila in r[0]["completadas"] + r[0]["anticipos"]:
        dia = date.fromisoformat(fila["_id"])
        por_dia[dia] = por_dia.get(dia, 0) + fila["valor"]
    return dict(sorted(por_dia.items()))
