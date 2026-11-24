"""Saldo de caja (una sola caja: Portugal). Se calcula, nunca se guarda.

saldo = ventas de café + ventas de plátano
        - gastos - compras de insumos - nómina causada (reglas/nomina.py)
        + movimientos de caja (aporte_capital y ajuste con su signo suman; retiro resta)

Los aportes de capital entran al flujo de caja pero NUNCA al margen (eso es de los reportes).
"""

from datetime import date

from motor.motor_asyncio import AsyncIOMotorDatabase

from back.app.database import COMPRA_INSUMO, GASTO, MOVIMIENTO_CAJA, VENTA_CAFE, VENTA_PLATANO
from back.app.reglas.nomina import nomina
from back.app.schemas import fmt_pesos, hoy
from back.app.utils import filtro_fechas

_INICIO = date(1900, 1, 1)  # "desde siempre" para la nómina cuando no hay fecha inicial


async def _sumar(db: AsyncIOMotorDatabase, coleccion: str, campo: str, filtro: dict, por: str | None = None):
    """(registros, total) y, si `por`, el total agrupado por ese campo."""
    grupos = await db[coleccion].aggregate([
        {"$match": filtro},
        {"$group": {"_id": f"${por}" if por else None, "n": {"$sum": 1}, "valor": {"$sum": f"${campo}"}}},
    ]).to_list(None)
    registros = sum(g["n"] for g in grupos)
    total = sum(g["valor"] for g in grupos)
    return registros, total, {str(g["_id"]): g["valor"] for g in grupos} if por else {}


async def calcular_saldo(db: AsyncIOMotorDatabase, desde: date | None = None, hasta: date | None = None) -> dict:
    hasta = hasta or hoy()
    filtro = filtro_fechas(None, desde, hasta)

    n_cafe, cafe, _ = await _sumar(db, VENTA_CAFE, "valor_total", filtro)
    n_platano, platano, _ = await _sumar(db, VENTA_PLATANO, "valor_total", filtro)
    n_gastos, gastos, gastos_cat = await _sumar(db, GASTO, "valor", filtro, por="categoria")
    n_compras, compras, _ = await _sumar(db, COMPRA_INSUMO, "valor", filtro)
    n_mov, _, mov_tipo = await _sumar(db, MOVIMIENTO_CAJA, "valor", filtro, por="tipo")
    movimientos = sum(-v if tipo == "retiro" else v for tipo, v in mov_tipo.items())

    filas_nomina = await nomina(db, desde or _INICIO, hasta)
    nomina_total = sum(t["total"] for t in filas_nomina)
    n_labores = sum(t["jornal"]["labores"] + t["contrato"]["labores"] for t in filas_nomina)

    advertencias = []
    if gastos_cat.get("nomina"):
        advertencias.append(
            f"Hay gastos en la categoría 'nomina' por {fmt_pesos(gastos_cat['nomina'])}: la nómina ya se resta "
            "como nómina causada; si esos gastos son pagos de jornales, se están restando dos veces."
        )
    if gastos_cat.get("insumos"):
        advertencias.append(
            f"Hay gastos en la categoría 'insumos' por {fmt_pesos(gastos_cat['insumos'])}: las compras de insumos "
            "ya se restan aparte; si son las mismas compras, se están restando dos veces."
        )

    return {
        "desde": desde,
        "hasta": hasta,
        "ventas_cafe": {"registros": n_cafe, "valor": cafe},
        "ventas_platano": {"registros": n_platano, "valor": platano},
        "gastos": {"registros": n_gastos, "valor": gastos},
        "gastos_por_categoria": gastos_cat,
        "compras_insumos": {"registros": n_compras, "valor": compras},
        "nomina_causada": {"registros": n_labores, "valor": nomina_total},
        "movimientos_caja": {"registros": n_mov, "valor": movimientos},
        "movimientos_por_tipo": mov_tipo,
        "saldo": cafe + platano - gastos - compras - nomina_total + movimientos,
        "advertencias": advertencias,
    }
