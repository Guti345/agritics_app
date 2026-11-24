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
from html import escape
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
/* calendario y cronograma: planeadas (borde punteado) vs. reales (abierta: borde vivo; completada: sólida) */
.ag-scroll {overflow-x: auto;}
table.ag-cal {border-collapse: separate; border-spacing: 0; width: 100%; background: #FFFFFF;
  border: 1px solid #EBE2DD; border-radius: 8px; font-size: 14px;}
table.ag-cal th {background: #EBE2DD; text-align: left; padding: .45rem .5rem; font-weight: 600; white-space: nowrap;}
table.ag-cal th.hoy {background: #004846; color: #FFF4E8;}
table.ag-cal td {border-top: 1px solid #EBE2DD; padding: .35rem .4rem; vertical-align: top; min-width: 105px;}
table.ag-cal td.nombre {font-weight: 600; min-width: 120px;}
table.ag-cal td.hoy {background: #FFF4E8;}
.ag-crono {display: grid; grid-template-columns: repeat(7, minmax(128px, 1fr)); gap: .5rem; overflow-x: auto;}
.ag-dia {background: #FFFFFF; border: 1px solid #EBE2DD; border-radius: 8px; padding: .45rem; min-height: 140px;}
.ag-dia.hoy {border: 2px solid #004846;}
.ag-dia-titulo {font-weight: 700; font-size: 14px; margin-bottom: .2rem;}
.ag-lote {font-weight: 600; font-size: 13px; margin: .45rem 0 .1rem; border-top: 1px solid #EBE2DD; padding-top: .3rem;}
.ag-vacio {opacity: .6; font-size: 13px;}
.ag-chip {display: block; border-radius: 6px; padding: .2rem .4rem; margin: .18rem 0; line-height: 1.3; font-size: 13px;}
.ag-chip small {display: block; font-size: 12px; opacity: .85;}
.ag-chip.plan {border: 1.5px dashed #009C48; background: #FFFFFF;}
.ag-chip.real.abierta {border: 2px solid #00C94B; background: #FFF4E8;}
.ag-chip.real.completada {background: #004846; color: #FFF4E8; border: 2px solid #004846;}
.ag-leyenda {display: flex; flex-wrap: wrap; gap: .5rem; font-size: 13px; margin: .2rem 0 .6rem;}
.ag-leyenda .ag-chip {display: inline-block; margin: 0;}
</style>
"""


# ── fechas ─────────────────────────────────────────────────────────────────────

def hoy() -> date:
    return datetime.now(BOGOTA).date()


DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


def semana_iso(dia: date | None = None) -> str:
    """'2026-W48': el formato que pide la API en ?semana=."""
    anio, numero, _ = (dia or hoy()).isocalendar()
    return f"{anio}-W{numero:02d}"


def dias_de(semana: str) -> list[date]:
    """Lunes a domingo de una semana ISO ('2026-W48')."""
    lunes = date.fromisocalendar(int(semana[:4]), int(semana[6:]), 1)
    return [lunes + timedelta(days=i) for i in range(7)]


def rotulo_semana(semana: str) -> str:
    """'2026-W48' -> 'Semana 48: 23-29 nov'. Si cruza de mes: 'Semana 49: 30 nov-6 dic'."""
    dias = dias_de(semana)
    lunes, domingo = dias[0], dias[-1]
    if lunes.month == domingo.month:
        rango = f"{lunes.day}-{domingo.day} {MESES[domingo.month - 1]}"
    else:
        rango = f"{lunes.day} {MESES[lunes.month - 1]}-{domingo.day} {MESES[domingo.month - 1]}"
    return f"Semana {int(semana[6:])}: {rango}"


def semana_en_curso(dia: date | None = None) -> str:
    """'Semana 48: 23-29 nov' (ISO, lunes a domingo), calculada de la fecha real."""
    return rotulo_semana(semana_iso(dia))


def dia_corto(dia: date) -> str:
    """'Lun 23 nov'."""
    return f"{DIAS[dia.weekday()]} {dia.day} {MESES[dia.month - 1]}"


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


def jornales(j: float) -> str:
    """1 -> '1 jornal'; 1.5 -> '1,5 jornales'."""
    return f"{numero(j, 1).removesuffix(',0')} {'jornal' if j == 1 else 'jornales'}"


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


def chip_plan(texto: str, cumplida: bool) -> str:
    """Labor planeada (preasignación del pool): borde punteado; dice si ya se cumplió."""
    estado = "planeada · cumplida ✓" if cumplida else "planeada · sin registro"
    return f"<span class='ag-chip plan'>{escape(texto)}<small>{estado}</small></span>"


def chip_real(texto: str, completada: bool, detalle: str = "") -> str:
    """Labor real (labor_diaria): abierta (borde vivo) o completada (sólida)."""
    estado = "completada" if completada else "abierta"
    extra = f" · {escape(detalle)}" if detalle else ""
    return (f"<span class='ag-chip real {estado}'>{escape(texto)}"
            f"<small>{estado}{extra}</small></span>")


LEYENDA = ("<div class='ag-leyenda'>"
           "<span class='ag-chip plan'>Planeada</span>"
           "<span class='ag-chip real abierta'>Real abierta</span>"
           "<span class='ag-chip real completada'>Real completada</span></div>")


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
           exito: str = "Registro guardado", refrescar: bool = False, donde=None):
    """Ejecuta la escritura. Si la API la rechaza (409/422/...), st.error con su `detail` tal
    cual y NO se borra nada de lo digitado. Si sale bien, se limpian las claves `limpiar` de
    st.session_state (los campos del formulario), se deja el aviso y se recarga.
    `refrescar`: limpia el caché de listas (pool, trabajadores, labores) antes de recargar.
    `donde`: contenedor para el error (por defecto, donde se llama)."""
    try:
        resultado = accion()
    except api.ErrorApi as e:
        (donde or st).error(e.detalle, icon=":material/error:")
        return None
    for clave in limpiar:
        st.session_state.pop(clave, None)
    if refrescar:
        api.refrescar_listas()
    st.session_state[_AVISO] = exito
    st.rerun()
    return resultado


def leer(accion: Callable[[], object]):
    """Lectura para pintar la pantalla: si la API falla, st.error con su `detail` y se
    detiene la pantalla (sin traceback)."""
    try:
        return accion()
    except api.ErrorApi as e:
        st.error(e.detalle, icon=":material/error:")
        st.stop()


def puede(*roles: str) -> bool:
    """¿El usuario que inició sesión tiene alguno de estos roles?"""
    return st.session_state["usuario"]["rol"] in roles
