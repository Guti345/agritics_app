"""DTOs de los reportes de lectura (R1 producción, R2 flujo de caja, R3 nómina, KPIs,
alertas y cronograma). Solo salida: ningún reporte escribe en la base."""

from datetime import date

from pydantic import BaseModel, Field

from .campos import FechaHoraOut, FechaOut, OidOut
from .cortes import CuadresSemana


# ─── R1: producción ───

class ProduccionDia(BaseModel):
    fecha: FechaOut
    lote_id: OidOut
    lote: str
    kg: float
    labores: int


class ReciboCafe(BaseModel):
    id: OidOut
    fecha: FechaOut
    semana: str
    tipo_producto: str
    kg_netos: float
    kg_pergamino_equivalente: float
    factor_rendimiento: float
    valor_total: float
    id_comprobante: str | None = None


class VentasCafeSemana(BaseModel):
    semana: str
    kg_mojado: float
    kg_pasilla: float
    kg_pergamino: float
    kg_pergamino_equivalente: float
    valor: float
    factor_rendimiento_promedio: float | None = None
    recibos: int


class ProduccionLote(BaseModel):
    lote_id: OidOut
    lote: str
    area_ha: float
    kg: float
    kg_ha: float
    kg_acumulado_anio: float
    kg_ha_acumulado_anio: float


class ProduccionFinca(BaseModel):
    area_ha: float
    kg: float
    kg_ha: float
    kg_acumulado_anio: float
    kg_ha_acumulado_anio: float


class PlatanoLoteSemana(BaseModel):
    semana: str
    lote_id: OidOut
    lote: str
    kg: float
    racimos: int
    cosechas: int


class R1ProduccionResponse(BaseModel):
    desde: date
    hasta: date
    cafe_por_dia: list[ProduccionDia]
    ventas_cafe_por_semana: list[VentasCafeSemana]
    ventas_por_recibo: list[ReciboCafe]
    por_lote: list[ProduccionLote]
    finca: ProduccionFinca
    platano: list[PlatanoLoteSemana]


# ─── R2: flujo de caja ───

class IngresosPeriodo(BaseModel):
    cafe: float = 0
    platano: float = 0
    total: float = 0


class GastosPeriodo(BaseModel):
    nomina: float = 0                       # calculada con reglas/nomina.py
    nomina_registrada_como_gasto: float = 0  # gastos con categoría "nomina" (ojo: doble conteo)
    insumos: float = 0                      # compras de insumos + gastos categoría "insumos"
    servicios: float = 0
    transporte: float = 0
    casa: float = 0
    otros: float = 0
    total: float = 0


class CapitalPeriodo(BaseModel):
    """Aportes, retiros y ajustes: en línea APARTE, nunca en el margen."""
    aportes: float = 0
    retiros: float = 0
    ajustes: float = 0
    neto: float = 0


class PeriodoFlujo(BaseModel):
    periodo: str
    desde: date
    hasta: date
    ingresos: IngresosPeriodo
    gastos: GastosPeriodo
    margen: float
    capital: CapitalPeriodo
    flujo_neto: float          # margen + capital neto


class LineaCaja(BaseModel):
    fecha: date
    tipo: str                  # ingreso | egreso | capital
    categoria: str
    descripcion: str
    valor: float               # con signo: + entra, - sale
    saldo: float               # saldo de caja después de esta línea


class R2FlujoCajaResponse(BaseModel):
    desde: date
    hasta: date
    saldo_inicial: float
    saldo_final: float
    semanas: list[PeriodoFlujo]
    meses: list[PeriodoFlujo]
    anios: list[PeriodoFlujo]
    total: PeriodoFlujo
    detalle: list[LineaCaja] = Field(default_factory=list)
    advertencias: list[str] = Field(default_factory=list)


# ─── R3: nómina por trabajador y semana ───

class LaborNomina(BaseModel):
    id: OidOut
    fecha: FechaOut
    lote: str
    labor: str
    unidad_avance: str | None = None
    forma_pago: str
    tipo_meta: str | None = None
    tarifa: float
    jornales: float
    avance: float
    completada: bool
    valor_pactado: float
    anticipos: float
    a_pagar: float             # jornal: jornales x tarifa; contrato: pactado - anticipos
    estado: str                # "pagada en el corte N de 2026-W48" | "por pagar" | "abierta (estimado)"
    corte: int | None = None
    corte_semana: str | None = None


class AnticipoRecibido(BaseModel):
    corte: int
    labor_diaria_id: OidOut
    valor: float
    fecha: FechaHoraOut


class RendimientoTrabajador(BaseModel):
    kg_por_dia: float | None = None       # café: kg recolectados / días con recolección
    ha_por_jornal: float | None = None    # labores de área: hectáreas / jornales
    pct_completadas: float | None = None


class TrabajadorNomina(BaseModel):
    trabajador_id: OidOut
    nombre: str
    tipo: str                  # recurrente | esporádico | de una vez (calculado, nunca guardado)
    semanas_activas_total: int
    semanas_activas_ultimas: int
    labores: list[LaborNomina]
    jornales: float
    total_a_pagar: float       # labores completadas, neto de anticipos
    pagado_en_cortes: float
    pendiente_por_pagar: float
    estimado_abiertas: float
    anticipos_recibidos: list[AnticipoRecibido]
    total_anticipos_recibidos: float
    kg_recolectados: float
    costo_por_kg: float | None = None
    rendimiento: RendimientoTrabajador
    nomina_causada: float      # reglas/nomina.py: nomina(lunes, domingo)


class R3NominaResponse(BaseModel):
    semana: str
    desde: date
    hasta: date
    criterio_tipo: str
    trabajadores: list[TrabajadorNomina]
    total_a_pagar: float
    total_anticipos_recibidos: float
    total_nomina_causada: float


# ─── KPIs ───

class AdopcionDigital(BaseModel):
    """% de registros capturados el mismo día del evento (fecha del evento = fecha de captura)."""
    registros: int
    mismo_dia: int
    porcentaje: float | None = None
    por_coleccion: dict[str, dict[str, float]] = Field(default_factory=dict)


class KpiLote(BaseModel):
    lote_id: OidOut
    lote: str
    kg_cafe: float
    kg_platano: float
    racimos: int


class RoiSimple(BaseModel):
    anio: int
    desde: date
    hasta: date
    margen_acumulado: float
    gasto_acumulado: float
    roi: float | None = None


class KpisResponse(BaseModel):
    semana: str
    ingresos_semana: float
    gastos_semana: float
    margen_semana: float
    produccion_por_lote: list[KpiLote]
    roi: RoiSimple
    adopcion_semana: AdopcionDigital
    adopcion_anio: AdopcionDigital


# ─── Alertas ───

class InsumoBajoUmbral(BaseModel):
    insumo_id: OidOut
    nombre: str
    unidad: str
    stock_actual: float
    umbral_alerta: float
    faltante: float


class AlertasResponse(BaseModel):
    semana: str
    cuadres: CuadresSemana
    insumos_bajo_umbral: list[InsumoBajoUmbral]
    alertas: list[str]


# ─── Cronograma ───

class LaborPlaneada(BaseModel):
    trabajador_id: OidOut
    trabajador: str
    labor_id: OidOut
    labor: str
    cumplida: bool             # hubo una labor real del mismo trabajador, día, lote y labor


class LaborReal(BaseModel):
    id: OidOut
    trabajador_id: OidOut
    trabajador: str
    labor_id: OidOut
    labor: str
    forma_pago: str
    jornales: float
    completada: bool
    planeada: bool


class LoteDelDia(BaseModel):
    lote_id: OidOut
    lote: str
    planeadas: list[LaborPlaneada] = Field(default_factory=list)
    reales: list[LaborReal] = Field(default_factory=list)


class DiaCronograma(BaseModel):
    fecha: date
    dia: str
    lotes: list[LoteDelDia] = Field(default_factory=list)


class CronogramaResponse(BaseModel):
    semana: str
    desde: date
    hasta: date
    dias: list[DiaCronograma]
    planeadas: int
    reales: int
    planeadas_cumplidas: int
    cumplimiento_pct: float | None = None
