"""DTOs de cortes de nómina (periodos cerrados dentro de la semana ISO) y su preview."""

from datetime import date

from pydantic import BaseModel, Field

from .enums import FormaPago, TipoMeta
from .campos import FechaHoraOut, FechaOut, OidIn, OidOut, Positivo, SemanaISO
from .base import Entrada, Salida


class AnticipoCorteIn(Entrada):
    """Plata adelantada en el corte sobre una labor A CONTRATO que sigue abierta."""
    labor_diaria_id: OidIn
    valor: Positivo


class CorteCreate(Entrada):
    """Cuerpo de POST /cortes. `hasta` por defecto es hoy (o el domingo si la semana ya pasó)."""
    semana: SemanaISO
    hasta: date | None = None
    anticipos: list[AnticipoCorteIn] = Field(default_factory=list)


class AnticipoCorteResponse(BaseModel):
    labor_diaria_id: OidOut
    trabajador_id: OidOut
    valor: float


class PagoJornal(BaseModel):
    labores: int = 0
    jornales: float = 0
    valor: float = 0


class PagoContrato(BaseModel):
    """Contratos completados: se paga lo pactado menos lo ya adelantado."""
    labores: int = 0
    pactado: float = 0
    anticipos_descontados: float = 0
    valor: float = 0


class PagoAnticipos(BaseModel):
    labores: int = 0
    valor: float = 0


class FilaPagoCorte(BaseModel):
    """Lo que se le paga a un trabajador en un corte."""
    trabajador_id: OidOut
    nombre: str
    jornal: PagoJornal
    contrato: PagoContrato
    anticipos: PagoAnticipos
    total: float


class CorteResponse(Salida):
    semana: str
    corte: int
    desde: FechaOut
    hasta: FechaOut
    cerrada_por: str
    fecha: FechaHoraOut
    anticipos: list[AnticipoCorteResponse] = Field(default_factory=list)
    nomina: list[FilaPagoCorte] = Field(default_factory=list)
    total_labores: float = 0
    total_anticipos: float = 0
    total: float = 0


# ─── Preview (antes de cortar) ───

class PeriodoAbierto(BaseModel):
    desde: date
    hasta: date


class LaborAbiertaPreview(BaseModel):
    id: OidOut
    fecha: FechaOut
    trabajador: str
    labor: str
    lote: str
    forma_pago: FormaPago
    tipo_meta: TipoMeta | None = None
    jornales: float
    estimado: float          # lo que valdría si se completara así (NO entra al pago del corte)
    anticipos: float


class ContratoAbiertoPreview(BaseModel):
    id: OidOut
    fecha: FechaOut
    trabajador: str
    labor: str
    tipo_meta: TipoMeta | None = None
    tarifa: float
    avance: float
    pactado: float
    anticipos: float
    saldo_adelantable: float  # pactado - anticipos acumulados: tope del próximo anticipo


class CorteHechoPreview(BaseModel):
    corte: int
    desde: FechaOut
    hasta: FechaOut
    cerrada_por: str
    fecha: FechaHoraOut
    anticipos: list[AnticipoCorteResponse] = Field(default_factory=list)
    total_labores: float
    total_anticipos: float
    total: float


class TrabajadorPool(BaseModel):
    trabajador_id: OidOut
    nombre: str


class ComponenteSemana(BaseModel):
    registros: int = 0
    valor: float = 0
    kg: float | None = None


class CuadresSemana(BaseModel):
    jornales_registrados: float       # jornales de labores a jornal con fecha en la semana
    jornales_en_nomina: float         # de esos, los pagados en cortes o listos para el próximo
    kg_cereza_recogidos: float        # avance en kg de labores de café completadas en la semana
    kg_cafe_vendidos: float           # kg netos de los recibos de la semana
    kg_pergamino_equivalente_vendidos: float
    relacion_cereza_pergamino: float | None = None


class CortePreviewResponse(BaseModel):
    semana: str
    periodo_abierto: PeriodoAbierto | None = None
    nomina_periodo_abierto: list[FilaPagoCorte] = Field(default_factory=list)
    total_periodo_abierto: float = 0
    labores_abiertas: list[LaborAbiertaPreview] = Field(default_factory=list)
    advertencia_abiertas: str | None = None
    contratos_abiertos: list[ContratoAbiertoPreview] = Field(default_factory=list)
    cortes: list[CorteHechoPreview] = Field(default_factory=list)
    pool_activo: list[TrabajadorPool] = Field(default_factory=list)
    ventas_cafe: ComponenteSemana
    ventas_platano: ComponenteSemana
    gastos: ComponenteSemana
    cuadres: CuadresSemana
    alertas: list[str] = Field(default_factory=list)
