from datetime import date

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorDatabase

from back.app.auth import CUALQUIERA, FINANZAS_LECTURA
from back.app.database import get_db
from back.app.reglas import reportes
from back.app.reglas.excel import consolidado_xlsx
from back.app.reglas.semana import semana_iso
from back.app.schemas import (
    AlertasResponse,
    CronogramaResponse,
    KpisResponse,
    R1ProduccionResponse,
    R2FlujoCajaResponse,
    R3NominaResponse,
    hoy,
)
from back.app.utils import a_oid, semana_de_query

router = APIRouter(prefix="/reportes", tags=["Reportes"])


def _semana(semana: str | None) -> str:
    """?semana= validada; sin ella, la semana en curso."""
    return semana_de_query(semana) if semana else semana_iso(hoy())


@router.get("/r1-produccion", response_model=R1ProduccionResponse, summary="R1 · Producción de café y plátano")
async def r1_produccion(
    desde: date | None = None,
    hasta: date | None = None,
    lote_id: str | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(CUALQUIERA),
):
    """Café cereza por día y lote, ventas de café por semana y por recibo (con factor de
    rendimiento), kg por lote y kg/ha (rango y acumulado del año, más la finca) y plátano
    por lote-semana. Sin fechas: del 1 de enero a hoy."""
    return R1ProduccionResponse.model_validate(
        await reportes.r1_produccion(db, desde, hasta, a_oid(lote_id) if lote_id else None))


@router.get("/r2-flujo-caja", response_model=R2FlujoCajaResponse, summary="R2 · Flujo de caja")
async def r2_flujo_caja(
    desde: date | None = None,
    hasta: date | None = None,
    detalle: bool = True,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(FINANZAS_LECTURA),
):
    """Ingresos, gastos por categoría (nómina de reglas/nomina.py) y margen por semana, mes
    y año; aportes, retiros y ajustes APARTE (nunca en el margen); detalle día a día con el
    saldo de caja resultante. Sin fechas: del 1 de enero a hoy."""
    return R2FlujoCajaResponse.model_validate(await reportes.r2_flujo_caja(db, desde, hasta, detalle))


@router.get("/r3-nomina", response_model=R3NominaResponse, summary="R3 · Nómina por trabajador y semana")
async def r3_nomina(
    semana: str | None = None,
    trabajador_id: str | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _: dict = Depends(FINANZAS_LECTURA),
):
    """Labores (lote, día), jornales, forma de pago, tarifa, a pagar (contrato: pactado -
    anticipos), corte en que se pagó cada una, anticipos recibidos en la semana, kg,
    costo por kg, rendimiento y tipo de trabajador (calculado)."""
    return R3NominaResponse.model_validate(
        await reportes.r3_nomina(db, _semana(semana), a_oid(trabajador_id) if trabajador_id else None))


@router.get("/kpis", response_model=KpisResponse, summary="KPIs de la semana")
async def kpis(semana: str | None = None, db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(FINANZAS_LECTURA)):
    """Margen de la semana, producción por lote, ROI simple del año (margen acumulado /
    gasto acumulado) y adopción digital (% capturado el mismo día del evento)."""
    return KpisResponse.model_validate(await reportes.kpis(db, _semana(semana)))


@router.get("/alertas", response_model=AlertasResponse, summary="Alertas: cuadres e insumos bajo el umbral")
async def alertas(semana: str | None = None, db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(CUALQUIERA)):
    return AlertasResponse.model_validate(await reportes.alertas(db, _semana(semana)))


@router.get("/cronograma", response_model=CronogramaResponse, summary="Cronograma: planeadas (pool) vs. reales")
async def cronograma(semana: str | None = None, db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(CUALQUIERA)):
    return CronogramaResponse.model_validate(await reportes.cronograma(db, _semana(semana)))


@router.get(
    "/consolidado-semanal/{semana}",
    summary="Excel consolidado (Ingresos vs Egresos por semana)",
    response_class=Response,
    responses={200: {"content": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}},
                     "description": "Archivo .xlsx para descargar"}},
)
async def consolidado_semanal(semana: str, db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(FINANZAS_LECTURA)):
    """Una fila por semana ISO del año hasta `semana` (ingresos, gastos por categoría y
    margen; capital aparte), más el detalle diario y la nómina de esa semana."""
    semana = semana_de_query(semana)
    lunes, hasta = reportes.semana_vigente(semana)
    primera = date.fromisocalendar(int(semana[:4]), 1, 1)
    flujo_anio = await reportes.r2_flujo_caja(db, primera, hasta, detalle=False)
    flujo_semana = await reportes.r2_flujo_caja(db, lunes, hasta, detalle=True)
    nomina = await reportes.r3_nomina(db, semana)
    contenido = consolidado_xlsx(semana, flujo_anio, flujo_semana, nomina)
    nombre = f"Agritics_consolidado_{semana}.xlsx"
    return Response(
        content=contenido,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )
