"""Piezas compartidas por todas las pantallas: marca, encabezado, semana en curso,
formato colombiano de cifras, tablas y el patrón de envío de formularios.

Reglas de UX que se aplican desde aquí:
- Voz de la finca (lote, labor, recolección, jornal, insumo, caja); un verbo por botón.
- Si la API responde 409/422, st.error con el `detail` tal cual y lo digitado se queda
  (los formularios usan clear_on_submit=False y solo se limpian tras guardar).
- Dinero "$ 125.000", kilos con coma decimal solo si aplica, cifras alineadas a la derecha.
"""

from collections.abc import Callable, Iterable
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

import api

ASSETS = Path(__file__).resolve().parent / "assets"
LOGO = ASSETS / "marca" / "agritics_claro.png"
ICONO_APP = ASSETS / "marca" / "icono_app.png"
SEPARADOR = ASSETS / "fondos" / "separador_hojas.svg"

BOGOTA = timezone(timedelta(hours=-5))   # misma convención que la API (UTC-5, sin horario de verano)

ROLES = {
    "administrador": "Administrador",
    "mayordomo": "Mayordomo",
    "junta": "Junta familiar",
    "superusuario": "Superusuario",
}

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

CSS = """
<style>
.ag-semana {text-align: right; font-weight: 600;}
.ag-semana span {background: #EBE2DD; border-radius: 8px; padding: .35rem .8rem; white-space: nowrap;}
.ag-usuario {line-height: 1.3;}
.ag-usuario small {font-size: 14px; opacity: .85;}
.ag-nota {background: #EBE2DD; border-radius: 8px; padding: .8rem 1rem; font-weight: 600;}
</style>
"""


# ── fechas ─────────────────────────────────────────────────────────────────────

def hoy() -> date:
    return datetime.now(BOGOTA).date()


def semana_en_curso(dia: date | None = None) -> str:
    """'Semana 48: 23-29 nov' (ISO, lunes a domingo). Si cruza de mes: 'Semana 49: 30 nov-6 dic'."""
    dia = dia or hoy()
    lunes = dia - timedelta(days=dia.weekday())
    domingo = lunes + timedelta(days=6)
    numero = dia.isocalendar().week
    if lunes.month == domingo.month:
        rango = f"{lunes.day}-{domingo.day} {MESES[domingo.month - 1]}"
    else:
        rango = f"{lunes.day} {MESES[lunes.month - 1]}-{domingo.day} {MESES[domingo.month - 1]}"
    return f"Semana {numero}: {rango}"


def fecha_corta(dia: date) -> str:
    """'24 nov 2026'."""
    return f"{dia.day} {MESES[dia.month - 1]} {dia.year}"


# ── números en formato colombiano ──────────────────────────────────────────────

def numero(valor: float | None, decimales: int = 0) -> str:
    """1234567.5 -> '1.234.567,5' (punto de miles, coma decimal)."""
    if valor is None:
        return ""
    texto = f"{valor:,.{decimales}f}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


def pesos(valor: float | None) -> str:
    """125000 -> '$ 125.000'; negativos '-$ 1.250.000'. Sin centavos."""
    if valor is None:
        return ""
    texto = f"$ {numero(abs(round(valor)))}"
    return f"-{texto}" if round(valor) < 0 else texto


def kg(valor: float | None, decimales: int = 1) -> str:
    """54638 -> '54.638 kg'; 12.5 -> '12,5 kg' (coma decimal solo si aplica)."""
    if valor is None:
        return ""
    redondo = round(valor, decimales)
    return f"{numero(redondo, 0 if redondo == int(redondo) else decimales)} kg"


def tabla(df: pd.DataFrame, dinero: Iterable[str] = (), kilos: Iterable[str] = (),
          cifras: Iterable[str] = (), **kwargs) -> None:
    """st.dataframe con dinero ($ 125.000), kilos y otras cifras en formato colombiano,
    alineadas a la derecha. `cifras`: números sin unidad (jornales, mm, ha)."""
    df = df.copy()
    config = dict(kwargs.pop("column_config", {}) or {})
    for columnas, formato in ((dinero, pesos), (kilos, kg), (cifras, lambda v: numero(v, 1).removesuffix(",0"))):
        for col in columnas:
            df[col] = df[col].map(lambda v: "" if pd.isna(v) else formato(v))
            config.setdefault(col, st.column_config.TextColumn(col, alignment="right"))
    st.dataframe(df, hide_index=True, column_config=config, **kwargs)


# ── encabezado y pantallas ─────────────────────────────────────────────────────

def estilos() -> None:
    st.html(CSS)


def encabezado(usuario: dict) -> None:
    """Encabezado permanente: logo pequeño, usuario y rol, y la semana en curso."""
    logo, persona, semana = st.columns([1.2, 2.3, 2], vertical_alignment="center")
    logo.image(str(LOGO), width=160)
    persona.html(f"<div class='ag-usuario'><b>{usuario['nombre']}</b><br>"
                 f"<small>{ROLES.get(usuario['rol'], usuario['rol'])}</small></div>")
    semana.html(f"<div class='ag-semana'><span>{semana_en_curso()}</span></div>")
    st.image(str(SEPARADOR), width="stretch")


def en_construccion(titulo: str, para_que: str) -> None:
    st.title(titulo)
    st.write(para_que)
    st.html("<div class='ag-nota'>Pantalla en construcción.</div>")


# ── envío de formularios ───────────────────────────────────────────────────────

_AVISO = "_aviso_guardado"


def aviso_guardado() -> None:
    """Muestra (una vez) el 'Registro guardado' que dejó enviar() antes de recargar."""
    mensaje = st.session_state.pop(_AVISO, None)
    if mensaje:
        st.success(mensaje, icon=":material/check_circle:")


def enviar(accion: Callable[[], object], limpiar: Iterable[str] = (),
           exito: str = "Registro guardado"):
    """Ejecuta la escritura. Si la API la rechaza (409/422/...), st.error con su `detail` tal
    cual y NO se borra nada de lo digitado. Si sale bien, se limpian las claves `limpiar` de
    st.session_state (los campos del formulario), se deja el aviso y se recarga."""
    try:
        resultado = accion()
    except api.ErrorApi as e:
        st.error(e.detalle, icon=":material/error:")
        return None
    for clave in limpiar:
        st.session_state.pop(clave, None)
    st.session_state[_AVISO] = exito
    st.rerun()
    return resultado
