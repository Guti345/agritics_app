"""Un solo texto por regla. Las reglas que se revisan en más de un sitio (la revisión en la
API antes de escribir y la traducción del DuplicateKeyError cuando un índice de la base la
frena) toman su mensaje de aquí, para que digan siempre EXACTAMENTE lo mismo.
"""

from datetime import date, datetime

# ── Regla estrella: una labor abierta a la vez (API + índice unica_labor_abierta) ──
LABOR_ABIERTA = "Este trabajador ya tiene una labor abierta; complétala antes de abrir otra"


# ── Periodo cerrado (cortes de nómina) ──
def periodo_cerrado(corte: int, semana: str) -> str:
    return f"Esa fecha ya quedó dentro del corte {corte} de la semana {semana}; solo el administrador puede corregirla"


# ── Duplicados de catálogo: "Ya hay <un/una> <cosa> con ese <campo>" (API + índice único) ──
LOTE_REPETIDO = "Ya hay un lote con ese nombre"
LABOR_REPETIDA = "Ya hay una labor con ese nombre"
INSUMO_REPETIDO = "Ya hay un insumo con ese nombre"
UNIDAD_REPETIDA = "Ya hay una unidad con ese nombre"
USUARIO_REPETIDO = "Ya hay un usuario con ese nombre de usuario"
TRABAJADOR_REPETIDO = "Ya hay un trabajador con ese documento"
RECIBO_REPETIDO = "Ya hay un recibo con ese comprobante"


# ── Lectura de lluvia repetida a la misma hora (API + índice único fecha_hora) ──
def lectura_lluvia_repetida(hora: datetime, dia: date) -> str:
    return f"Ya hay una lectura de lluvia a las {hora:%H:%M} del {dia:%Y-%m-%d}"
