"""Hora de Colombia y formato de números y pesos para los mensajes."""

from datetime import date, datetime, timedelta, timezone


BOGOTA = timezone(timedelta(hours=-5), "America/Bogota")  # Colombia no tiene horario de verano


def ahora() -> datetime:
    return datetime.now(BOGOTA)


def hoy() -> date:
    return ahora().date()


def fmt_num(x: float, decimales: int = 2) -> str:
    """1234567.5 -> '1.234.567,5' (formato colombiano, sin ceros sobrantes)."""
    entero, _, dec = f"{x:,.{decimales}f}".partition(".")
    entero = entero.replace(",", ".")
    dec = dec.rstrip("0")
    return f"{entero},{dec}" if dec else entero


def fmt_pesos(x: float) -> str:
    return "$" + fmt_num(x, 0)
