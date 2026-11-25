"""DTOs (Pydantic v2) de Agritics: un archivo por tema; aquí se reexporta todo lo público."""

# Uso:  from back.app.schemas import LoteCreate, LoteResponse, ...
#
# Convenciones:
#   * XxxCreate   -> lo que ENVÍA el cliente. extra="forbid": no puede colar campos que pone
#                    el servidor (registrado_por, fecha_captura, fecha_cierre, stock calculado...).
#                    `a_mongo()` lo deja listo para insertar (fechas a datetime UTC, *_id a ObjectId).
#   * XxxResponse -> lo que DEVUELVE la API. Lee el documento de Mongo tal cual: `_id` -> `id` (str);
#                    ningún ObjectId sale en el JSON.
#   * Los ObjectId viajan como texto de 24 hex; los campos que los llevan terminan en `_id`.
#   * Fechas de día (`fecha`): `date`. Se guardan como datetime a las 00:00 UTC (BSON no tiene
#     "solo fecha"). Fechas con hora (lluvia, captura): datetime; si llega sin zona se asume hora
#     de Colombia (UTC-5) y se guarda en UTC.
#   * Las validaciones de datos (422) lanzan ValueError con el mensaje en español; los manejadores
#     de back/app/reglas/manejadores.py lo muestran tal cual. Las reglas que dependen de la base
#     (existencia, stock, semana cerrada: 404/409) NO van aquí: van en back/app/reglas/.
#   * Los enums usan exactamente los mismos valores que los validadores $jsonSchema de init_db.py.

# ── Infraestructura ──
from .enums import (
    FormaPago,
    Calidad,
    EstadoLote,
    CategoriaGasto,
    TipoMovimientoCaja,
    SALEN_DE_CAJA,
    UnidadAvance,
    TipoMeta,
    Rol,
    TipoProductoCafe,
    Cultivo,
)
from .tiempo import BOGOTA, ahora, hoy, fmt_num, fmt_pesos
from .campos import (
    foto_obligatoria,
    Texto,
    Positivo,
    NoNegativo,
    EnteroPositivo,
    EnteroNoNegativo,
    Porcentaje,
    Jornales,
    MmLluvia,
    Fecha,
    FechaHora,
    SemanaISO,
    OidIn,
    OidOut,
    FechaOut,
    FechaHoraOut,
    Libre,
    Cultivos,
)
from .base import Entrada, Salida, SalidaCaptura, modelo_parcial

# ── Catálogos ──
from .lotes import Poligono, LoteCreate, LoteResponse, LoteUpdate
from .labores import LaborCreate, LaborResponse, LaborUpdate
from .trabajadores import TrabajadorCreate, TrabajadorResponse, TrabajadorUpdate
from .insumos import InsumoCreate, InsumoResponse, InsumoUpdate
from .unidades import UnidadCreate, UnidadResponse, UnidadUpdate
from .usuarios import UsuarioCreate, UsuarioResponse, UsuarioUpdate, LoginIn

# ── Operación ──
from .labor_diaria import (
    InsumoConsumido,
    LaborDiariaCreate,
    InsumoConsumidoResponse,
    LaborDiariaResponse,
    LaborDiariaUpdate,
    LaborCompletar,
    AnticipoLaborResponse,
)
from .pool_semana import (
    Preasignacion,
    PoolSemanaCreate,
    PreasignacionResponse,
    PoolSemanaResponse,
    PoolActivar,
    PoolDesactivar,
    PoolTrabajadorResponse,
    PoolPreasignacionUpdate,
)
from .cosecha_platano import CosechaPlatanoCreate, CosechaPlatanoResponse, CosechaPlatanoUpdate
from .venta_platano import VentaPlatanoCreate, VentaPlatanoResponse, VentaPlatanoUpdate
from .venta_cafe import (
    AnalisisCalidad,
    Descuento,
    VentaCafeCreate,
    DescuentoResponse,
    AnalisisCalidadResponse,
    VentaCafeResponse,
    VentaCafeUpdate,
)
from .compra_insumo import CompraInsumoCreate, CompraInsumoResponse, CompraInsumoUpdate
from .gasto import GastoCreate, GastoResponse, GastoUpdate
from .caja import (
    MovimientoCajaCreate,
    MovimientoCajaResponse,
    MovimientoCajaUpdate,
    ComponenteSaldo,
    CajaSaldoResponse,
)
from .lluvia import LluviaCreate, LluviaResponse, LluviaUpdate, LluviaDiaResponse
from .auditoria import AuditoriaResponse
from .cortes import (
    AnticipoCorteIn,
    CorteCreate,
    AnticipoCorteResponse,
    PagoJornal,
    PagoContrato,
    PagoAnticipos,
    FilaPagoCorte,
    CorteResponse,
    PeriodoAbierto,
    LaborAbiertaPreview,
    ContratoAbiertoPreview,
    CorteHechoPreview,
    TrabajadorPool,
    ComponenteSemana,
    CuadresSemana,
    CortePreviewResponse,
)

# ── Reportes (solo lectura) ──
from .reportes import (
    ProduccionDia,
    ReciboCafe,
    VentasCafeSemana,
    ProduccionLote,
    ProduccionFinca,
    PlatanoLoteSemana,
    R1ProduccionResponse,
    IngresosPeriodo,
    GastosPeriodo,
    CapitalPeriodo,
    PeriodoFlujo,
    LineaCaja,
    R2FlujoCajaResponse,
    LaborNomina,
    AnticipoRecibido,
    RendimientoTrabajador,
    TrabajadorNomina,
    R3NominaResponse,
    AdopcionDigital,
    KpiLote,
    RoiSimple,
    KpisResponse,
    InsumoBajoUmbral,
    AlertasResponse,
    LaborPlaneada,
    LaborReal,
    LoteDelDia,
    DiaCronograma,
    CronogramaResponse,
)

# ── Archivos ──
from .uploads import FotoSubidaResponse

__all__ = [
    # Infraestructura
    "FormaPago", "Calidad", "EstadoLote", "CategoriaGasto", "TipoMovimientoCaja", "SALEN_DE_CAJA", "UnidadAvance",
    "TipoMeta", "Rol", "TipoProductoCafe", "Cultivo",
    "BOGOTA", "ahora", "hoy", "fmt_num", "fmt_pesos",
    "foto_obligatoria", "Texto", "Positivo", "NoNegativo", "EnteroPositivo", "EnteroNoNegativo",
    "Porcentaje", "Jornales", "MmLluvia", "Fecha", "FechaHora", "SemanaISO", "OidIn", "OidOut",
    "FechaOut", "FechaHoraOut", "Libre", "Cultivos",
    "Entrada", "Salida", "SalidaCaptura", "modelo_parcial",
    # Catálogos
    "Poligono", "LoteCreate", "LoteResponse", "LoteUpdate",
    "LaborCreate", "LaborResponse", "LaborUpdate",
    "TrabajadorCreate", "TrabajadorResponse", "TrabajadorUpdate",
    "InsumoCreate", "InsumoResponse", "InsumoUpdate",
    "UnidadCreate", "UnidadResponse", "UnidadUpdate",
    "UsuarioCreate", "UsuarioResponse", "UsuarioUpdate", "LoginIn",
    # Operación
    "InsumoConsumido", "LaborDiariaCreate", "InsumoConsumidoResponse", "LaborDiariaResponse",
    "LaborDiariaUpdate", "LaborCompletar", "AnticipoLaborResponse",
    "Preasignacion", "PoolSemanaCreate", "PreasignacionResponse", "PoolSemanaResponse",
    "PoolActivar", "PoolDesactivar", "PoolTrabajadorResponse", "PoolPreasignacionUpdate",
    "CosechaPlatanoCreate", "CosechaPlatanoResponse", "CosechaPlatanoUpdate",
    "VentaPlatanoCreate", "VentaPlatanoResponse", "VentaPlatanoUpdate",
    "AnalisisCalidad", "Descuento", "VentaCafeCreate", "DescuentoResponse",
    "AnalisisCalidadResponse", "VentaCafeResponse",
    "VentaCafeUpdate",
    "CompraInsumoCreate", "CompraInsumoResponse", "CompraInsumoUpdate",
    "GastoCreate", "GastoResponse", "GastoUpdate",
    "MovimientoCajaCreate", "MovimientoCajaResponse", "MovimientoCajaUpdate", "ComponenteSaldo",
    "CajaSaldoResponse",
    "LluviaCreate", "LluviaResponse", "LluviaUpdate", "LluviaDiaResponse",
    "AuditoriaResponse",
    "AnticipoCorteIn", "CorteCreate", "AnticipoCorteResponse", "PagoJornal", "PagoContrato",
    "PagoAnticipos", "FilaPagoCorte", "CorteResponse", "PeriodoAbierto", "LaborAbiertaPreview",
    "ContratoAbiertoPreview", "CorteHechoPreview", "TrabajadorPool", "ComponenteSemana", "CuadresSemana",
    "CortePreviewResponse",
    # Reportes
    "ProduccionDia", "ReciboCafe", "VentasCafeSemana", "ProduccionLote", "ProduccionFinca",
    "PlatanoLoteSemana", "R1ProduccionResponse", "IngresosPeriodo", "GastosPeriodo",
    "CapitalPeriodo", "PeriodoFlujo", "LineaCaja", "R2FlujoCajaResponse", "LaborNomina",
    "AnticipoRecibido", "RendimientoTrabajador", "TrabajadorNomina", "R3NominaResponse",
    "AdopcionDigital", "KpiLote", "RoiSimple", "KpisResponse", "InsumoBajoUmbral",
    "AlertasResponse", "LaborPlaneada", "LaborReal", "LoteDelDia", "DiaCronograma",
    "CronogramaResponse",
    # Archivos
    "FotoSubidaResponse",
]
