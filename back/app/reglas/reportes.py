"""Reportes de LECTURA: pipelines de agregación sobre la operación. Ningún reporte escribe.

Reutiliza, sin duplicar:
  * reglas/nomina.py   -> nomina() (por trabajador), nomina_por_dia() (flujo de caja),
                          PACTADO / ANTICIPOS_TOTAL (valor de cada labor)
  * reglas/caja.py     -> calcular_saldo() (saldo inicial y advertencias de doble conteo)
  * reglas/cortes.py   -> preview() (cuadres de jornales y de café de la semana)

"Recolección de café" = labores del catálogo con unidad_avance "kg" y cultivo "cafe";
su `avance` son los kg de cereza recogidos.
"""

from datetime import date, datetime, timedelta, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from back.app.database import (
    CIERRES,
    COMPRA_INSUMO,
    COSECHA_PLATANO,
    GASTO,
    INSUMOS,
    LABOR_DIARIA,
    LABORES,
    LLUVIA,
    LOTES,
    MOVIMIENTO_CAJA,
    POOL_SEMANA,
    TRABAJADORES,
    VENTA_CAFE,
    VENTA_PLATANO,
)
from back.app.reglas.caja import calcular_saldo
from back.app.reglas.cortes import preview
from back.app.reglas.errores import datos_invalidos
from back.app.reglas.nomina import ANTICIPOS_TOTAL, PACTADO, nomina, nomina_por_dia, rango_semana
from back.app.reglas.semana import semana_iso
from back.app.schemas import BOGOTA, fmt_num, hoy

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
SEMANA_DE = lambda campo: {"$dateToString": {"format": "%G-W%V", "date": campo}}  # noqa: E731  ISO "2026-W48"

# Tipo de trabajador (se calcula, nunca se guarda). Semana activa = estuvo en el pool o
# tuvo alguna labor esa semana.
VENTANA_TIPO = 8          # semanas que se miran hacia atrás (incluida la consultada)
MIN_RECURRENTE = 4        # semanas activas dentro de la ventana para ser "recurrente"
CRITERIO_TIPO = (
    f"de una vez: activo en una sola semana de todo su historial; recurrente: activo en al menos "
    f"{MIN_RECURRENTE} de las últimas {VENTANA_TIPO} semanas; esporádico: los demás"
)


# ── Utilidades ──

def _utc(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)  # así se guardan las fechas de día


def _rango(desde: date, hasta: date) -> dict:
    return {"$gte": _utc(desde), "$lte": _utc(hasta)}


def _dia(v) -> date:
    return v.date() if isinstance(v, datetime) else v


def rango_por_defecto(desde: date | None, hasta: date | None) -> tuple[date, date]:
    """Sin fechas: del 1 de enero del año de `hasta` hasta hoy."""
    hasta = hasta or hoy()
    desde = desde or date(hasta.year, 1, 1)
    if desde > hasta:
        raise datos_invalidos("'desde' no puede ser posterior a 'hasta'")
    return desde, hasta


def semana_vigente(semana: str) -> tuple[date, date]:
    """Lunes y el último día ya transcurrido de la semana (sin pasar de hoy)."""
    lunes, domingo = rango_semana(semana)
    if lunes > hoy():
        raise datos_invalidos(f"La semana {semana} todavía no empieza (arranca el {lunes:%Y-%m-%d})")
    return lunes, min(domingo, hoy())


async def ids_recoleccion_cafe(db: AsyncIOMotorDatabase) -> list[ObjectId]:
    return [d["_id"] async for d in db[LABORES].find({"unidad_avance": "kg", "cultivos": "cafe"}, {"_id": 1})]


async def _nombres(db: AsyncIOMotorDatabase, coleccion: str, ids) -> dict:
    return {d["_id"]: d["nombre"] async for d in db[coleccion].find({"_id": {"$in": list(set(ids))}}, {"nombre": 1})}


# ═══════════════════════════ R1: producción ═══════════════════════════

async def r1_produccion(db: AsyncIOMotorDatabase, desde: date | None, hasta: date | None, lote_id: ObjectId | None = None) -> dict:
    desde, hasta = rango_por_defecto(desde, hasta)
    recoleccion = await ids_recoleccion_cafe(db)
    por_lote = {"lote_id": lote_id} if lote_id else {}
    cosecha_cafe = {"completada": True, "labor_id": {"$in": recoleccion}, **por_lote}

    cafe_por_dia = await db[LABOR_DIARIA].aggregate([
        {"$match": {**cosecha_cafe, "fecha": _rango(desde, hasta)}},
        {"$group": {"_id": {"fecha": "$fecha", "lote_id": "$lote_id"}, "kg": {"$sum": "$avance"}, "labores": {"$sum": 1}}},
        {"$lookup": {"from": LOTES, "localField": "_id.lote_id", "foreignField": "_id", "as": "l"}},
        {"$project": {"_id": 0, "fecha": "$_id.fecha", "lote_id": "$_id.lote_id",
                      "lote": {"$ifNull": [{"$first": "$l.nombre"}, "?"]}, "kg": 1, "labores": 1}},
        {"$sort": {"fecha": 1, "lote": 1}},
    ]).to_list(None)

    # kg por lote: en el rango y acumulado del año (1 de enero -> hasta)
    kg_lote = await db[LABOR_DIARIA].aggregate([
        {"$match": {**cosecha_cafe, "fecha": _rango(min(desde, date(hasta.year, 1, 1)), hasta)}},
        {"$group": {
            "_id": "$lote_id",
            "kg": {"$sum": {"$cond": [{"$gte": ["$fecha", _utc(desde)]}, "$avance", 0]}},
            "kg_anio": {"$sum": {"$cond": [{"$gte": ["$fecha", _utc(date(hasta.year, 1, 1))]}, "$avance", 0]}},
        }},
    ]).to_list(None)
    kg_lote = {k["_id"]: k for k in kg_lote}
    lotes = await db[LOTES].find({"cultivos": "cafe", **({"_id": lote_id} if lote_id else {})}).sort("nombre").to_list(None)
    filas_lote = []
    for l in lotes:
        k = kg_lote.get(l["_id"], {"kg": 0, "kg_anio": 0})
        filas_lote.append({"lote_id": l["_id"], "lote": l["nombre"], "area_ha": l["area_ha"], "kg": k["kg"],
                           "kg_ha": k["kg"] / l["area_ha"], "kg_acumulado_anio": k["kg_anio"],
                           "kg_ha_acumulado_anio": k["kg_anio"] / l["area_ha"]})
    area = sum(f["area_ha"] for f in filas_lote)
    kg, kg_anio = sum(f["kg"] for f in filas_lote), sum(f["kg_acumulado_anio"] for f in filas_lote)
    finca = {"area_ha": area, "kg": kg, "kg_ha": kg / area if area else 0,
             "kg_acumulado_anio": kg_anio, "kg_ha_acumulado_anio": kg_anio / area if area else 0}

    def kg_tipo(tipo):
        return {"$sum": {"$cond": [{"$eq": ["$tipo_producto", tipo]}, "$kg_netos", 0]}}
    ventas = (await db[VENTA_CAFE].aggregate([
        {"$match": {"fecha": _rango(desde, hasta)}},
        {"$facet": {
            "recibos": [
                {"$project": {"_id": 0, "id": "$_id", "fecha": 1, "semana": SEMANA_DE("$fecha"), "tipo_producto": 1, "kg_netos": 1,
                              "kg_pergamino_equivalente": 1, "factor_rendimiento": 1, "valor_total": 1, "id_comprobante": 1}},
                {"$sort": {"fecha": 1}},
            ],
            "por_semana": [
                {"$group": {"_id": SEMANA_DE("$fecha"), "kg_mojado": kg_tipo("mojado"), "kg_pasilla": kg_tipo("pasilla"),
                            "kg_pergamino": kg_tipo("pergamino"), "kg_pergamino_equivalente": {"$sum": "$kg_pergamino_equivalente"},
                            "valor": {"$sum": "$valor_total"}, "factor_rendimiento_promedio": {"$avg": "$factor_rendimiento"},
                            "recibos": {"$sum": 1}}},
                {"$addFields": {"semana": "$_id"}},
                {"$sort": {"_id": 1}},
            ],
        }},
    ]).to_list(1))[0]

    platano = await db[COSECHA_PLATANO].aggregate([
        {"$match": {"fecha": _rango(desde, hasta), **por_lote}},
        {"$group": {"_id": {"semana": SEMANA_DE("$fecha"), "lote_id": "$lote_id"},
                    "kg": {"$sum": "$kg"}, "racimos": {"$sum": "$racimos"}, "cosechas": {"$sum": 1}}},
        {"$lookup": {"from": LOTES, "localField": "_id.lote_id", "foreignField": "_id", "as": "l"}},
        {"$project": {"_id": 0, "semana": "$_id.semana", "lote_id": "$_id.lote_id",
                      "lote": {"$ifNull": [{"$first": "$l.nombre"}, "?"]}, "kg": 1, "racimos": 1, "cosechas": 1}},
        {"$sort": {"semana": 1, "lote": 1}},
    ]).to_list(None)

    return {"desde": desde, "hasta": hasta, "cafe_por_dia": cafe_por_dia,
            "ventas_cafe_por_semana": ventas["por_semana"], "ventas_por_recibo": ventas["recibos"],
            "por_lote": filas_lote, "finca": finca, "platano": platano}


# ═══════════════════════════ R2: flujo de caja ═══════════════════════════

def _proyectar(tipo: str, categoria, descripcion, valor, orden: int) -> dict:
    return {"$project": {"_id": 0, "fecha": 1, "tipo": {"$literal": tipo}, "categoria": categoria,
                         "descripcion": descripcion, "valor": valor, "orden": {"$literal": orden}}}


async def lineas_caja(db: AsyncIOMotorDatabase, desde: date, hasta: date) -> list[dict]:
    """Formato largo: cada venta, gasto, compra y movimiento de caja del rango (un solo
    pipeline con $unionWith) + una línea de nómina causada por día (reglas/nomina.py)."""
    en_rango = {"$match": {"fecha": _rango(desde, hasta)}}
    menos = lambda campo: {"$multiply": [campo, -1]}  # noqa: E731
    lineas = await db[VENTA_CAFE].aggregate([
        en_rango,
        _proyectar("ingreso", {"$literal": "cafe"},
                   {"$concat": ["Venta de café ", "$tipo_producto",
                                {"$cond": [{"$ifNull": ["$id_comprobante", False]}, {"$concat": [" (", "$id_comprobante", ")"]}, ""]}]},
                   "$valor_total", 1),
        {"$unionWith": {"coll": VENTA_PLATANO, "pipeline": [
            en_rango, _proyectar("ingreso", {"$literal": "platano"}, {"$concat": ["Venta de plátano a ", "$comprador"]}, "$valor_total", 1)]}},
        {"$unionWith": {"coll": GASTO, "pipeline": [
            en_rango,
            _proyectar("egreso",
                       {"$cond": [{"$eq": ["$categoria", "nomina"]}, "nomina_registrada_como_gasto", "$categoria"]},
                       {"$cond": [{"$gt": [{"$strLenCP": {"$ifNull": ["$descripcion", ""]}}, 0]}, "$descripcion", "$categoria"]},
                       menos("$valor"), 2)]}},
        {"$unionWith": {"coll": COMPRA_INSUMO, "pipeline": [
            en_rango,
            {"$lookup": {"from": INSUMOS, "localField": "insumo_id", "foreignField": "_id", "as": "i"}},
            _proyectar("egreso", {"$literal": "insumos"},
                       {"$concat": ["Compra de ", {"$ifNull": [{"$first": "$i.nombre"}, "insumo"]}]}, menos("$valor"), 2)]}},
        {"$unionWith": {"coll": MOVIMIENTO_CAJA, "pipeline": [
            en_rango,
            _proyectar("capital", "$tipo",
                       {"$cond": [{"$gt": [{"$strLenCP": {"$ifNull": ["$nota", ""]}}, 0]}, "$nota", "$tipo"]},
                       {"$cond": [{"$eq": ["$tipo", "retiro"]}, menos("$valor"), "$valor"]}, 0)]}},  # capital primero: con el aporte se paga
    ]).to_list(None)
    for l in lineas:
        l["fecha"] = _dia(l["fecha"])
    for dia, valor in (await nomina_por_dia(db, desde, hasta)).items():
        lineas.append({"fecha": dia, "tipo": "egreso", "categoria": "nomina",
                       "descripcion": "Nómina causada del día", "valor": -valor, "orden": 3})
    return sorted(lineas, key=lambda l: (l["fecha"], l["orden"]))


def _periodo(clave: str, desde: date, hasta: date) -> dict:
    return {"periodo": clave, "desde": desde, "hasta": hasta,
            "ingresos": {"cafe": 0, "platano": 0, "total": 0},
            "gastos": {"nomina": 0, "nomina_registrada_como_gasto": 0, "insumos": 0, "servicios": 0,
                       "transporte": 0, "casa": 0, "otros": 0, "total": 0},
            "capital": {"aportes": 0, "retiros": 0, "ajustes": 0, "neto": 0}, "margen": 0, "flujo_neto": 0}


def _acumular(p: dict, l: dict) -> None:
    if l["tipo"] == "ingreso":
        p["ingresos"][l["categoria"]] += l["valor"]
    elif l["tipo"] == "egreso":
        p["gastos"][l["categoria"]] += -l["valor"]
    else:
        clave = {"aporte_capital": "aportes", "retiro": "retiros", "ajuste": "ajustes"}[l["categoria"]]
        p["capital"][clave] += -l["valor"] if clave == "retiros" else l["valor"]


def _cerrar(p: dict) -> dict:
    p["ingresos"]["total"] = p["ingresos"]["cafe"] + p["ingresos"]["platano"]
    p["gastos"]["total"] = sum(v for k, v in p["gastos"].items() if k != "total")
    p["margen"] = p["ingresos"]["total"] - p["gastos"]["total"]          # sin aportes ni retiros
    c = p["capital"]
    c["neto"] = c["aportes"] - c["retiros"] + c["ajustes"]
    p["flujo_neto"] = p["margen"] + c["neto"]
    return p


def _periodos(desde: date, hasta: date, lineas: list[dict]) -> tuple[list, list, list, dict]:
    semanas, meses, anios = {}, {}, {}
    lunes = desde - timedelta(days=desde.weekday())
    while lunes <= hasta:                                   # todas las semanas ISO, recortadas al rango
        semanas[semana_iso(lunes)] = _periodo(semana_iso(lunes), max(lunes, desde), min(lunes + timedelta(days=6), hasta))
        lunes += timedelta(days=7)
    mes = date(desde.year, desde.month, 1)
    while mes <= hasta:
        siguiente = date(mes.year + mes.month // 12, mes.month % 12 + 1, 1)
        meses[f"{mes:%Y-%m}"] = _periodo(f"{mes:%Y-%m}", max(mes, desde), min(siguiente - timedelta(days=1), hasta))
        mes = siguiente
    for anio in range(desde.year, hasta.year + 1):
        anios[str(anio)] = _periodo(str(anio), max(date(anio, 1, 1), desde), min(date(anio, 12, 31), hasta))
    total = _periodo(f"{desde:%Y-%m-%d} a {hasta:%Y-%m-%d}", desde, hasta)
    for l in lineas:
        for p in (semanas[semana_iso(l["fecha"])], meses[f"{l['fecha']:%Y-%m}"], anios[str(l["fecha"].year)], total):
            _acumular(p, l)
    return ([_cerrar(p) for p in semanas.values()], [_cerrar(p) for p in meses.values()],
            [_cerrar(p) for p in anios.values()], _cerrar(total))


async def r2_flujo_caja(db: AsyncIOMotorDatabase, desde: date | None, hasta: date | None, detalle: bool = True) -> dict:
    desde, hasta = rango_por_defecto(desde, hasta)
    lineas = await lineas_caja(db, desde, hasta)
    saldo_inicial = (await calcular_saldo(db, None, desde - timedelta(days=1)))["saldo"]
    saldo = saldo_inicial
    for l in lineas:
        saldo += l["valor"]
        l["saldo"] = saldo
    semanas, meses, anios, total = _periodos(desde, hasta, lineas)
    return {"desde": desde, "hasta": hasta, "saldo_inicial": saldo_inicial, "saldo_final": saldo,
            "semanas": semanas, "meses": meses, "anios": anios, "total": total,
            "detalle": lineas if detalle else [],
            "advertencias": (await calcular_saldo(db, desde, hasta))["advertencias"]}


# ═══════════════════════════ R3: nómina por trabajador ═══════════════════════════

async def _semanas_activas(db: AsyncIOMotorDatabase, ids: list[ObjectId], hasta_semana: str) -> dict:
    """Semanas ISO en que cada trabajador estuvo en el pool o tuvo labores (hasta la consultada)."""
    activas: dict = {i: set() for i in ids}
    async for p in db[POOL_SEMANA].find({"trabajador_id": {"$in": ids}}, {"trabajador_id": 1, "semana": 1}):
        activas[p["trabajador_id"]].add(p["semana"])
    for f in await db[LABOR_DIARIA].aggregate([
        {"$match": {"trabajador_id": {"$in": ids}}},
        {"$group": {"_id": "$trabajador_id", "semanas": {"$addToSet": SEMANA_DE("$fecha")}}},
    ]).to_list(None):
        activas[f["_id"]].update(f["semanas"])
    return {i: {s for s in sem if s <= hasta_semana} for i, sem in activas.items()}


def _tipo(semanas: set, ultimas: set) -> tuple[str, int]:
    recientes = len(semanas & ultimas)
    if len(semanas) <= 1:
        return "de una vez", recientes
    return ("recurrente" if recientes >= MIN_RECURRENTE else "esporádico"), recientes


async def r3_nomina(db: AsyncIOMotorDatabase, semana: str, trabajador_id: ObjectId | None = None) -> dict:
    lunes, domingo = rango_semana(semana)
    del_trabajador = {"trabajador_id": trabajador_id} if trabajador_id else {}
    recoleccion = await ids_recoleccion_cafe(db)
    labores = await db[LABOR_DIARIA].aggregate([
        {"$match": {"fecha": _rango(lunes, domingo), **del_trabajador}},
        {"$lookup": {"from": LOTES, "localField": "lote_id", "foreignField": "_id", "as": "lt"}},
        {"$lookup": {"from": LABORES, "localField": "labor_id", "foreignField": "_id", "as": "lb"}},
        {"$addFields": {
            "_pactado": PACTADO, "_anticipos": ANTICIPOS_TOTAL,
            "lote": {"$ifNull": [{"$first": "$lt.nombre"}, "?"]},
            "labor": {"$ifNull": [{"$first": "$lb.nombre"}, "?"]},
            "unidad_avance": {"$first": "$lb.unidad_avance"},
            "es_recoleccion": {"$in": ["$labor_id", recoleccion]},
        }},
        {"$project": {"lt": 0, "lb": 0}},
        {"$sort": {"fecha": 1, "fecha_captura": 1}},
    ]).to_list(None)

    en_pool = [p["trabajador_id"] async for p in db[POOL_SEMANA].find({"semana": semana, "activo": True, **del_trabajador})]
    ids = list({*(l["trabajador_id"] for l in labores), *en_pool})
    nombres = await _nombres(db, TRABAJADORES, ids)
    causada = {t["trabajador_id"]: t["total"] for t in await nomina(db, lunes, domingo)}
    anticipos = {}
    async for c in db[CIERRES].find({"semana": semana}).sort("corte", 1):
        for a in c.get("anticipos", []):
            anticipos.setdefault(a["trabajador_id"], []).append(
                {"corte": c["corte"], "labor_diaria_id": a["labor_diaria_id"], "valor": a["valor"], "fecha": c["fecha"]})
    activas = await _semanas_activas(db, ids, semana)
    ultimas = {semana_iso(lunes - timedelta(weeks=i)) for i in range(VENTANA_TIPO)}

    trabajadores = []
    for tid in ids:
        propias = [l for l in labores if l["trabajador_id"] == tid]
        filas = []
        for l in propias:
            a_pagar = l["_pactado"] - (l["_anticipos"] if l["forma_pago"] == "contrato" else 0)
            if not l["completada"]:
                estado = "abierta (estimado)"
            elif l.get("corte"):
                estado = f"pagada en el corte {l['corte']} de {l['corte_semana']}"
            else:
                estado = "por pagar en el próximo corte"
            filas.append({"id": l["_id"], "fecha": l["fecha"], "lote": l["lote"], "labor": l["labor"],
                          "unidad_avance": l.get("unidad_avance"), "forma_pago": l["forma_pago"],
                          "tipo_meta": l.get("tipo_meta"), "tarifa": l["tarifa"], "jornales": l["jornales"],
                          "avance": l.get("avance", 0), "completada": l["completada"], "valor_pactado": l["_pactado"],
                          "anticipos": l["_anticipos"], "a_pagar": a_pagar, "estado": estado,
                          "corte": l.get("corte"), "corte_semana": l.get("corte_semana")})
        completadas = [f for f in filas if f["completada"]]
        total = sum(f["a_pagar"] for f in completadas)
        pagado = sum(f["a_pagar"] for f in completadas if f["corte"])
        recol = [l for l in propias if l["completada"] and l["es_recoleccion"]]
        kg = sum(l["avance"] for l in recol)
        area = [l for l in propias if l["completada"] and l.get("unidad_avance") == "hectareas"]
        jornales_area = sum(l["jornales"] for l in area)
        recibidos = anticipos.get(tid, [])
        tipo, recientes = _tipo(activas.get(tid, set()), ultimas)
        trabajadores.append({
            "trabajador_id": tid, "nombre": nombres.get(tid, "?"), "tipo": tipo,
            "semanas_activas_total": len(activas.get(tid, set())), "semanas_activas_ultimas": recientes,
            "labores": filas, "jornales": sum(f["jornales"] for f in filas),
            "total_a_pagar": total, "pagado_en_cortes": pagado, "pendiente_por_pagar": total - pagado,
            "estimado_abiertas": sum(f["a_pagar"] for f in filas if not f["completada"]),
            "anticipos_recibidos": recibidos, "total_anticipos_recibidos": sum(a["valor"] for a in recibidos),
            "kg_recolectados": kg,
            "costo_por_kg": sum(l["_pactado"] for l in recol) / kg if kg else None,
            "rendimiento": {
                "kg_por_dia": kg / len({l["fecha"] for l in recol}) if kg else None,
                "ha_por_jornal": sum(l["avance"] for l in area) / jornales_area if jornales_area else None,
                "pct_completadas": 100 * len(completadas) / len(filas) if filas else None,
            },
            "nomina_causada": causada.get(str(tid), 0),
        })
    trabajadores.sort(key=lambda t: t["nombre"].lower())
    return {"semana": semana, "desde": lunes, "hasta": domingo, "criterio_tipo": CRITERIO_TIPO,
            "trabajadores": trabajadores, "total_a_pagar": sum(t["total_a_pagar"] for t in trabajadores),
            "total_anticipos_recibidos": sum(t["total_anticipos_recibidos"] for t in trabajadores),
            "total_nomina_causada": sum(t["nomina_causada"] for t in trabajadores)}


# ═══════════════════════════ KPIs ═══════════════════════════

ADOPCION = {  # colección -> campo con la fecha del evento
    LABOR_DIARIA: "fecha", COSECHA_PLATANO: "fecha", VENTA_PLATANO: "fecha", VENTA_CAFE: "fecha",
    COMPRA_INSUMO: "fecha", GASTO: "fecha", MOVIMIENTO_CAJA: "fecha", LLUVIA: "fecha_hora",
}


async def adopcion_digital(db: AsyncIOMotorDatabase, desde: date, hasta: date) -> dict:
    """% de registros cuya fecha de captura (hora de Colombia) es el mismo día del evento."""
    por_coleccion, n_total, mismo_total = {}, 0, 0
    captura = {"$dateToString": {"format": "%Y-%m-%d", "date": "$fecha_captura", "timezone": "-05:00"}}
    for coleccion, campo in ADOPCION.items():
        if campo == "fecha":   # fecha de día: guardada a las 00:00 UTC
            filtro = {"fecha": _rango(desde, hasta)}
            evento = {"$dateToString": {"format": "%Y-%m-%d", "date": "$fecha"}}
        else:                  # fecha con hora real: el día es el de Colombia
            ini = datetime(desde.year, desde.month, desde.day, tzinfo=BOGOTA)
            filtro = {campo: {"$gte": ini, "$lt": datetime(hasta.year, hasta.month, hasta.day, tzinfo=BOGOTA) + timedelta(days=1)}}
            evento = {"$dateToString": {"format": "%Y-%m-%d", "date": f"${campo}", "timezone": "-05:00"}}
        r = await db[coleccion].aggregate([
            {"$match": filtro},
            {"$group": {"_id": None, "n": {"$sum": 1}, "mismo": {"$sum": {"$cond": [{"$eq": [evento, captura]}, 1, 0]}}}},
        ]).to_list(1)
        if r:
            por_coleccion[coleccion] = {"registros": r[0]["n"], "mismo_dia": r[0]["mismo"],
                                        "porcentaje": 100 * r[0]["mismo"] / r[0]["n"]}
            n_total += r[0]["n"]
            mismo_total += r[0]["mismo"]
    return {"registros": n_total, "mismo_dia": mismo_total,
            "porcentaje": 100 * mismo_total / n_total if n_total else None, "por_coleccion": por_coleccion}


async def kpis(db: AsyncIOMotorDatabase, semana: str) -> dict:
    lunes, hasta = semana_vigente(semana)
    flujo_semana = await r2_flujo_caja(db, lunes, hasta, detalle=False)
    inicio_anio = date(hasta.year, 1, 1)
    flujo_anio = await r2_flujo_caja(db, inicio_anio, hasta, detalle=False)
    produccion = await r1_produccion(db, lunes, hasta)
    platano = {}
    for p in produccion["platano"]:
        t = platano.setdefault(p["lote_id"], {"kg": 0, "racimos": 0})
        t["kg"] += p["kg"]
        t["racimos"] += p["racimos"]
    lotes = await db[LOTES].find().sort("nombre").to_list(None)
    cafe = {f["lote_id"]: f["kg"] for f in produccion["por_lote"]}
    margen_anio, gasto_anio = flujo_anio["total"]["margen"], flujo_anio["total"]["gastos"]["total"]
    return {
        "semana": semana,
        "ingresos_semana": flujo_semana["total"]["ingresos"]["total"],
        "gastos_semana": flujo_semana["total"]["gastos"]["total"],
        "margen_semana": flujo_semana["total"]["margen"],
        "produccion_por_lote": [{"lote_id": l["_id"], "lote": l["nombre"], "kg_cafe": cafe.get(l["_id"], 0),
                                 "kg_platano": platano.get(l["_id"], {}).get("kg", 0),
                                 "racimos": platano.get(l["_id"], {}).get("racimos", 0)} for l in lotes],
        "roi": {"anio": hasta.year, "desde": inicio_anio, "hasta": hasta, "margen_acumulado": margen_anio,
                "gasto_acumulado": gasto_anio, "roi": margen_anio / gasto_anio if gasto_anio else None},
        "adopcion_semana": await adopcion_digital(db, lunes, hasta),
        "adopcion_anio": await adopcion_digital(db, inicio_anio, hasta),
    }


# ═══════════════════════════ Alertas ═══════════════════════════

async def alertas(db: AsyncIOMotorDatabase, semana: str) -> dict:
    """Cuadres de la semana (los mismos del preview de cortes) + insumos bajo su umbral."""
    pr = await preview(db, semana)
    bajos = await db[INSUMOS].aggregate([
        {"$match": {"$expr": {"$lte": ["$stock_actual", "$umbral_alerta"]}}},
        {"$project": {"_id": 0, "insumo_id": "$_id", "nombre": 1, "unidad": 1, "stock_actual": 1, "umbral_alerta": 1,
                      "faltante": {"$subtract": ["$umbral_alerta", "$stock_actual"]}}},
        {"$sort": {"nombre": 1}},
    ]).to_list(None)
    textos = list(pr["alertas"])
    for i in bajos:
        textos.append(f"Stock bajo de {i['nombre']}: quedan {fmt_num(i['stock_actual'])} {i['unidad']} "
                      f"(umbral {fmt_num(i['umbral_alerta'])} {i['unidad']})")
    return {"semana": semana, "cuadres": pr["cuadres"], "insumos_bajo_umbral": bajos, "alertas": textos}


# ═══════════════════════════ Cronograma ═══════════════════════════

async def cronograma(db: AsyncIOMotorDatabase, semana: str) -> dict:
    """Planeadas (preasignación del pool) vs. reales (labor_diaria), por día y lote."""
    lunes, domingo = rango_semana(semana)
    planeadas = await db[POOL_SEMANA].aggregate([
        {"$match": {"semana": semana, "activo": True}},
        {"$unwind": "$preasignacion"},
        {"$project": {"_id": 0, "trabajador_id": 1, "fecha": "$preasignacion.dia",
                      "lote_id": "$preasignacion.lote_id", "labor_id": "$preasignacion.labor_id"}},
    ]).to_list(None)
    reales = await db[LABOR_DIARIA].aggregate([
        {"$match": {"fecha": _rango(lunes, domingo)}},
        {"$project": {"trabajador_id": 1, "fecha": 1, "lote_id": 1, "labor_id": 1, "forma_pago": 1,
                      "jornales": 1, "completada": 1}},
        {"$sort": {"fecha": 1, "fecha_captura": 1}},
    ]).to_list(None)
    todos = planeadas + reales
    t_nom = await _nombres(db, TRABAJADORES, [x["trabajador_id"] for x in todos])
    l_nom = await _nombres(db, LOTES, [x["lote_id"] for x in todos])
    lb_nom = await _nombres(db, LABORES, [x["labor_id"] for x in todos])
    clave = lambda x: (x["trabajador_id"], _dia(x["fecha"]), x["lote_id"], x["labor_id"])  # noqa: E731
    claves_reales, claves_plan = {clave(r) for r in reales}, {clave(p) for p in planeadas}

    dias = []
    for i in range(7):
        dia = lunes + timedelta(days=i)
        lotes: dict = {}
        for p in (p for p in planeadas if _dia(p["fecha"]) == dia):
            lote = lotes.setdefault(p["lote_id"], {"lote_id": p["lote_id"], "lote": l_nom.get(p["lote_id"], "?"), "planeadas": [], "reales": []})
            lote["planeadas"].append({"trabajador_id": p["trabajador_id"], "trabajador": t_nom.get(p["trabajador_id"], "?"),
                                      "labor_id": p["labor_id"], "labor": lb_nom.get(p["labor_id"], "?"),
                                      "cumplida": clave(p) in claves_reales})
        for r in (r for r in reales if _dia(r["fecha"]) == dia):
            lote = lotes.setdefault(r["lote_id"], {"lote_id": r["lote_id"], "lote": l_nom.get(r["lote_id"], "?"), "planeadas": [], "reales": []})
            lote["reales"].append({"id": r["_id"], "trabajador_id": r["trabajador_id"], "trabajador": t_nom.get(r["trabajador_id"], "?"),
                                   "labor_id": r["labor_id"], "labor": lb_nom.get(r["labor_id"], "?"), "forma_pago": r["forma_pago"],
                                   "jornales": r["jornales"], "completada": r["completada"], "planeada": clave(r) in claves_plan})
        dias.append({"fecha": dia, "dia": DIAS[i], "lotes": sorted(lotes.values(), key=lambda l: l["lote"])})
    cumplidas = sum(1 for p in planeadas if clave(p) in claves_reales)
    return {"semana": semana, "desde": lunes, "hasta": domingo, "dias": dias, "planeadas": len(planeadas),
            "reales": len(reales), "planeadas_cumplidas": cumplidas,
            "cumplimiento_pct": 100 * cumplidas / len(planeadas) if planeadas else None}
