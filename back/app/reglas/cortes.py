"""Cortes de nómina: cierran PERIODOS dentro de la semana ISO; los cortes se apilan.

Un corte va desde el día siguiente al último corte de la semana (o el lunes) hasta
`hasta`. Paga las labores completadas sin corte con fecha <= hasta (jornal: jornales x
tarifa; contrato: pactado - anticipos) más los anticipos nuevos sobre contratos abiertos.
Pago selectivo (`trabajador_ids`): solo las de esos trabajadores; las demás quedan sin corte
y las paga un corte posterior (el filtro de pago no mira el `desde` del periodo).
Las labores pagadas quedan marcadas con su corte; la nómina no se guarda: se recalcula.
"""

from datetime import date, datetime, timedelta, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from back.app.database import (
    CIERRES,
    GASTO,
    LABOR_DIARIA,
    LABORES,
    LOTES,
    POOL_SEMANA,
    TRABAJADORES,
    VENTA_CAFE,
    VENTA_PLATANO,
)
from back.app.reglas.errores import conflicto, datos_invalidos, no_encontrado
from back.app.reglas.nomina import anticipos_acumulados, pago_de_corte, rango_semana, valor_pactado
from back.app.schemas import CorteCreate, ahora, fmt_num, fmt_pesos, hoy

SOLO_CONTRATO_ABIERTO = "Solo se adelanta plata de labores a contrato que sigan abiertas"


def _utc(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)  # así se guardan las fechas de día


async def cortes_de_semana(db: AsyncIOMotorDatabase, semana: str) -> list[dict]:
    return await db[CIERRES].find({"semana": semana}).sort("corte", 1).to_list(None)


def periodo_abierto(semana: str, cortes: list[dict]) -> tuple[date, date] | None:
    """(desde, hasta máximo) del periodo que falta por cortar; None si la semana ya se cortó
    completa o todavía no empieza. `hasta` máximo = hoy, sin pasar del domingo."""
    lunes, domingo = rango_semana(semana)
    desde = cortes[-1]["hasta"].date() + timedelta(days=1) if cortes else lunes
    hasta = min(hoy(), domingo)
    if desde > domingo or hasta < desde:
        return None
    return desde, hasta


async def _validar_anticipos(db: AsyncIOMotorDatabase, anticipos) -> list[tuple[dict, float]]:
    """Cada anticipo: labor A CONTRATO y ABIERTA; no supera lo pactado menos lo adelantado
    (sumando los anticipos repetidos de la misma labor en este mismo corte)."""
    nuevos, ya_en_este_corte = [], {}
    for a in anticipos:
        labor = await db[LABOR_DIARIA].find_one({"_id": ObjectId(a.labor_diaria_id)})
        if labor is None:
            raise no_encontrado(f"No existe la labor diaria con id {a.labor_diaria_id}")
        if labor["forma_pago"] != "contrato" or labor["completada"]:
            raise conflicto(SOLO_CONTRATO_ABIERTO)
        previo = anticipos_acumulados(labor) + ya_en_este_corte.get(labor["_id"], 0)
        quedan = valor_pactado(labor) - previo
        if a.valor > quedan + 0.5:  # tolerancia de redondeo en pesos
            raise conflicto(f"El anticipo supera lo que falta por pagar de esa labor: quedan {fmt_pesos(max(quedan, 0))}")
        ya_en_este_corte[labor["_id"]] = ya_en_este_corte.get(labor["_id"], 0) + a.valor
        nuevos.append((labor, a.valor))
    return nuevos


async def _validar_seleccion(db: AsyncIOMotorDatabase, trabajador_ids: list[str] | None,
                             anticipos: list[tuple[dict, float]]) -> list[ObjectId] | None:
    """Pago selectivo: los trabajadores deben existir y los anticipos del corte ser de ellos."""
    if trabajador_ids is None:
        return None
    ids = list(dict.fromkeys(ObjectId(t) for t in trabajador_ids))
    existen = {t["_id"] async for t in db[TRABAJADORES].find({"_id": {"$in": ids}}, {"_id": 1})}
    for t in ids:
        if t not in existen:
            raise no_encontrado(f"No existe el trabajador con id {t}")
    for labor, _ in anticipos:
        if labor["trabajador_id"] not in existen:
            raise datos_invalidos("Hay un anticipo para un trabajador que no está en la selección de este corte: "
                                  "agrégalo a la selección o quita ese anticipo")
    return ids


async def crear_corte(db: AsyncIOMotorDatabase, datos: CorteCreate, usuario: dict) -> dict:
    """Valida, calcula y registra el corte. Devuelve el documento del corte con su nómina."""
    semana = datos.semana
    lunes, domingo = rango_semana(semana)
    if lunes > hoy():
        raise datos_invalidos(f"La semana {semana} todavía no empieza (arranca el {lunes:%Y-%m-%d})")
    cortes = await cortes_de_semana(db, semana)
    ultimo = cortes[-1] if cortes else None
    desde = ultimo["hasta"].date() + timedelta(days=1) if ultimo else lunes
    if desde > domingo:
        raise conflicto(f"La semana {semana} ya quedó cortada completa (hasta el domingo {domingo:%Y-%m-%d})")
    hasta = datos.hasta or min(hoy(), domingo)
    if not lunes <= hasta <= domingo:
        raise datos_invalidos(f"El corte debe ir hasta un día de la semana {semana} ({lunes:%Y-%m-%d} a {domingo:%Y-%m-%d})")
    if hasta > hoy():
        raise datos_invalidos("No puedes cortar días que todavía no pasan")
    if hasta < desde:
        raise conflicto(
            f"Hasta el {hasta:%Y-%m-%d} ya quedó dentro del corte {ultimo['corte']} de la semana {semana}: "
            f"el siguiente corte va desde el {desde:%Y-%m-%d}"
        )
    nuevos = await _validar_anticipos(db, datos.anticipos)
    seleccion = await _validar_seleccion(db, datos.trabajador_ids, nuevos)

    # c. La nómina del corte (antes de escribir nada).
    filas, ids_pagados = await pago_de_corte(db, hasta=hasta, anticipos=nuevos, trabajador_ids=seleccion)

    # e. El documento del corte se inserta PRIMERO: el índice único (semana, corte) aparta
    #    el número; si otro corte de la misma semana se registró a la vez, no se escribe nada.
    numero = (ultimo["corte"] + 1) if ultimo else 1
    momento = ahora()
    doc = {
        "semana": semana,
        "corte": numero,
        "desde": _utc(desde),
        "hasta": _utc(hasta),
        "cerrada_por": usuario["usuario"],
        "fecha": momento,
        "anticipos": [
            {"labor_diaria_id": labor["_id"], "trabajador_id": labor["trabajador_id"], "valor": valor}
            for labor, valor in nuevos
        ],
    }
    try:
        r = await db[CIERRES].insert_one(doc)
    except DuplicateKeyError:
        raise conflicto("Se registró otro corte de esta semana al mismo tiempo: revisa el preview y vuelve a intentarlo") from None
    doc["_id"] = r.inserted_id

    # b. Anticipos embebidos en su labor (siguen abiertas).
    for labor, valor in nuevos:
        await db[LABOR_DIARIA].update_one(
            {"_id": labor["_id"]},
            {"$push": {"anticipos": {"corte": numero, "semana": semana, "valor": valor, "fecha": momento}}},
        )
    # d. Marca las completadas pagadas (exactamente las que entraron en la cuenta).
    if ids_pagados:
        await db[LABOR_DIARIA].update_many(
            {"_id": {"$in": ids_pagados}, "corte": {"$exists": False}},
            {"$set": {"corte": numero, "corte_semana": semana}},
        )
    return _con_totales(doc, filas)


def _con_totales(doc: dict, filas: list[dict]) -> dict:
    total_anticipos = sum(a["valor"] for a in doc.get("anticipos", []))
    total = sum(f["total"] for f in filas)
    return {**doc, "nomina": filas, "total_labores": total - total_anticipos,
            "total_anticipos": total_anticipos, "total": total}


async def recalcular_corte(db: AsyncIOMotorDatabase, doc: dict) -> dict:
    """Totales de un corte ya hecho: labores marcadas con él + sus anticipos."""
    anticipos = []
    for a in doc.get("anticipos", []):
        anticipos.append(({"trabajador_id": a["trabajador_id"]}, a["valor"]))
    filas, _ = await pago_de_corte(db, corte=(doc["semana"], doc["corte"]), anticipos=anticipos)
    return _con_totales(doc, filas)


# ── Preview ──

async def _nombres(db, coleccion, ids) -> dict:
    return {d["_id"]: d["nombre"] async for d in db[coleccion].find({"_id": {"$in": list(set(ids))}}, {"nombre": 1})}


async def _sumar(db, coleccion, campo, filtro, kg: str | None = None) -> dict:
    g = await db[coleccion].aggregate([{"$match": filtro}, {"$group": {
        "_id": None, "n": {"$sum": 1}, "valor": {"$sum": f"${campo}"}, "kg": {"$sum": f"${kg}" if kg else 0}}}]).to_list(1)
    g = g[0] if g else {"n": 0, "valor": 0, "kg": 0}
    return {"registros": g["n"], "valor": g["valor"], **({"kg": g["kg"]} if kg else {})}


async def preview(db: AsyncIOMotorDatabase, semana: str) -> dict:
    lunes, domingo = rango_semana(semana)
    cortes = await cortes_de_semana(db, semana)
    periodo = periodo_abierto(semana, cortes)
    hasta_pago = periodo[1] if periodo else min(hoy(), domingo)

    # Lo que se pagaría si se corta hoy (incluye completadas tarde de periodos ya cortados:
    # se muestran aunque hoy no quede periodo abierto, porque van en el próximo corte).
    filas, _ = await pago_de_corte(db, hasta=hasta_pago)

    # Labores abiertas (todas las que siguen sin completar hasta el fin del periodo).
    abiertas = await db[LABOR_DIARIA].find(
        {"completada": False, "fecha": {"$lte": _utc(hasta_pago)}}).sort("fecha", 1).to_list(None)
    t_nom = await _nombres(db, TRABAJADORES, [a["trabajador_id"] for a in abiertas])
    l_nom = await _nombres(db, LABORES, [a["labor_id"] for a in abiertas])
    lo_nom = await _nombres(db, LOTES, [a["lote_id"] for a in abiertas])
    labores_abiertas, contratos = [], []
    for a in abiertas:
        pactado, adelantado = valor_pactado(a), anticipos_acumulados(a)
        base = {"id": a["_id"], "fecha": a["fecha"], "trabajador": t_nom.get(a["trabajador_id"], "?"),
                "labor": l_nom.get(a["labor_id"], "?"), "tipo_meta": a.get("tipo_meta")}
        labores_abiertas.append({**base, "lote": lo_nom.get(a["lote_id"], "?"), "forma_pago": a["forma_pago"],
                                 "jornales": a["jornales"], "estimado": pactado, "anticipos": adelantado})
        if a["forma_pago"] == "contrato":
            contratos.append({**base, "tarifa": a["tarifa"], "avance": a.get("avance", 0), "pactado": pactado,
                              "anticipos": adelantado, "saldo_adelantable": max(pactado - adelantado, 0)})
    hay_jornal_abierto = any(a["forma_pago"] == "jornal" for a in abiertas)

    hechos = [await recalcular_corte(db, c) for c in cortes]

    pool = await db[POOL_SEMANA].find({"semana": semana, "activo": True}, {"trabajador_id": 1}).to_list(None)
    p_nom = await _nombres(db, TRABAJADORES, [p["trabajador_id"] for p in pool])
    pool_activo = sorted(({"trabajador_id": p["trabajador_id"], "nombre": p_nom.get(p["trabajador_id"], "?")} for p in pool),
                         key=lambda x: x["nombre"].lower())

    en_semana = {"fecha": {"$gte": _utc(lunes), "$lte": _utc(domingo)}}
    ventas_cafe = await _sumar(db, VENTA_CAFE, "valor_total", en_semana, kg="kg_netos")
    pergamino = (await _sumar(db, VENTA_CAFE, "kg_pergamino_equivalente", en_semana))["valor"]
    ventas_platano = await _sumar(db, VENTA_PLATANO, "valor_total", en_semana, kg="kg")
    gastos = await _sumar(db, GASTO, "valor", en_semana)

    # Cuadres: jornales registrados vs. en nómina; kg de café cereza recogidos vs. vendidos.
    jornal_semana = await db[LABOR_DIARIA].find({**en_semana, "forma_pago": "jornal"}, {"jornales": 1, "completada": 1}).to_list(None)
    jornales_registrados = sum(l["jornales"] for l in jornal_semana)
    jornales_en_nomina = sum(l["jornales"] for l in jornal_semana if l["completada"])
    labores_cafe_kg = [d["_id"] async for d in db[LABORES].find({"unidad_avance": "kg", "cultivos": "cafe"}, {"_id": 1})]
    cereza = await db[LABOR_DIARIA].aggregate([
        {"$match": {**en_semana, "completada": True, "labor_id": {"$in": labores_cafe_kg}}},
        {"$group": {"_id": None, "kg": {"$sum": "$avance"}}}]).to_list(1)
    kg_cereza = cereza[0]["kg"] if cereza else 0

    alertas = []
    if jornales_registrados != jornales_en_nomina:
        alertas.append(
            f"Jornales registrados en la semana: {fmt_num(jornales_registrados)}; en nómina: {fmt_num(jornales_en_nomina)}. "
            f"La diferencia ({fmt_num(jornales_registrados - jornales_en_nomina)}) es de labores a jornal abiertas: "
            "no se pagan hasta completarlas."
        )
    if kg_cereza > 0 and ventas_cafe["registros"] == 0:
        alertas.append(f"Se recogieron {fmt_num(kg_cereza)} kg de café cereza en la semana y no hay ventas de café registradas.")
    if ventas_cafe["registros"] > 0 and kg_cereza == 0:
        alertas.append("Hay ventas de café en la semana pero no hay kg de café cereza recogidos registrados.")
    for c in contratos:
        if c["anticipos"] > c["pactado"]:
            alertas.append(f"A {c['trabajador']} se le adelantó más de lo pactado en '{c['labor']}': revisa el avance.")

    return {
        "semana": semana,
        "periodo_abierto": {"desde": periodo[0], "hasta": periodo[1]} if periodo else None,
        "nomina_periodo_abierto": filas,
        "total_periodo_abierto": sum(f["total"] for f in filas),
        "labores_abiertas": labores_abiertas,
        "advertencia_abiertas": (
            "Las labores a jornal abiertas NO se pagan en este corte: complétalas antes de cortar "
            "o quedarán para el siguiente." if hay_jornal_abierto else None
        ),
        "contratos_abiertos": contratos,
        "cortes": hechos,
        "pool_activo": pool_activo,
        "ventas_cafe": ventas_cafe,
        "ventas_platano": ventas_platano,
        "gastos": gastos,
        "cuadres": {
            "jornales_registrados": jornales_registrados,
            "jornales_en_nomina": jornales_en_nomina,
            "kg_cereza_recogidos": kg_cereza,
            "kg_cafe_vendidos": ventas_cafe["kg"],
            "kg_pergamino_equivalente_vendidos": pergamino,
            "relacion_cereza_pergamino": (kg_cereza / pergamino) if kg_cereza and pergamino else None,
        },
        "alertas": alertas,
    }
