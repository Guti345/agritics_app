"""Piezas compartidas por todas las pantallas: marca, encabezado, semana en curso,
formato colombiano de cifras, tablas y el patrón de envío de formularios.

Reglas de UX que se aplican desde aquí:
- Voz de la finca (lote, labor, recolección, jornal, insumo, caja); un verbo por botón.
- Si la API responde 409/422, st.error con el `detail` tal cual y lo digitado se queda
  (los formularios usan clear_on_submit=False y solo se limpian tras guardar).
- Dinero "$ 125.000", kilos con coma decimal solo si aplica, cifras alineadas a la derecha.
"""

from collections.abc import Callable, Iterable
from datetime import date, datetime, time, timedelta, timezone
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
/* cronograma: vista día (un recuadro por lote) y vista mes (semanas x días, fichas compactas) */
.ag-lotes {display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: .5rem;}
.ag-mes {display: grid; grid-template-columns: 44px repeat(7, minmax(118px, 1fr)); gap: .35rem; overflow-x: auto;}
.ag-mes .cab {font-weight: 700; font-size: 13px; padding: 0 .2rem;}
.ag-mes .sem {font-weight: 700; font-size: 12px; opacity: .75; padding-top: .35rem;}
.ag-mes .celda {background: #FFFFFF; border: 1px solid #EBE2DD; border-radius: 8px; padding: .3rem; min-height: 96px;}
.ag-mes .celda.fuera {opacity: .45;}
.ag-mes .celda.hoy {border: 2px solid #004846;}
.ag-mes .num {font-weight: 700; font-size: 13px; margin-bottom: .1rem;}
.ag-mini {display: block; border-radius: 5px; padding: .06rem .3rem; margin: .12rem 0; font-size: 11.5px; line-height: 1.25;}
.ag-mini.planeada {border: 1.5px dashed #009C48; background: #FFFFFF;}
.ag-mini.abierta {border: 1.5px solid #00C94B; background: #FFF4E8;}
.ag-mini.completada {background: #004846; color: #FFF4E8; border: 1.5px solid #004846;}
/* programación: quitar preasignación, grande y a la vista */
.st-key-pg_quitar {background: #FFFFFF;}
.st-key-pg_quitar button {min-height: 3.2rem; font-size: 1.05rem;}
/* inicio del mayordomo: tarjetas de acceso */
.ag-tarjeta {display: flex; gap: .9rem; align-items: center; min-height: 92px;}
.ag-tarjeta img {flex: none; width: 52px; height: 52px; padding: 10px; border-radius: 14px; background: #FFF4E8;}
.ag-tarjeta b {font-size: 22px; display: block; line-height: 1.2;}
.ag-tarjeta small {font-size: 14px; opacity: .85;}
[class*="st-key-tarjeta_"] {background: #FFFFFF; border-left: 6px solid #009C48 !important;}
[class*="st-key-tarjeta_"] a[data-testid="stPageLink-NavLink"] {background: #004846; justify-content: center;
  border-radius: 8px; padding: .55rem .8rem;}
[class*="st-key-tarjeta_"] a[data-testid="stPageLink-NavLink"] * {color: #FFF4E8 !important; font-weight: 600;}
.ag-cifra {background: #FFFFFF; border: 1px solid #EBE2DD; border-radius: 8px; padding: .8rem 1rem;}
.ag-cifra div {font-size: 32px; font-weight: 700; line-height: 1.2;}
.ag-cifra small {font-size: 14px; opacity: .85;}
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


def elegir_semana(rotulo: str = "Semana", key: str = "semana", donde=None,
                  adelante: int = 0, atras: int = 53) -> str:
    """Selector de semana ISO (por defecto la semana en curso). Devuelve '2026-W48'."""
    base = hoy()
    opciones = [semana_iso(base + timedelta(weeks=adelante - k)) for k in range(adelante + atras + 1)]
    return (donde or st).selectbox(rotulo, opciones, index=adelante, format_func=rotulo_semana, key=key)


def a_fecha(valor) -> date:
    """'2026-11-24' (o date) -> date."""
    return valor if isinstance(valor, date) else date.fromisoformat(str(valor)[:10])


def dia_bogota(valor: str) -> date:
    """'2026-11-25T03:15:00Z' -> date(2026, 11, 24): el día en hora de Colombia."""
    momento = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    return (momento.astimezone(BOGOTA) if momento.tzinfo else momento).date()


def fecha_hora(valor: str) -> str:
    """'2026-11-24T22:15:00Z' -> '24 nov 2026 17:15' (hora de Colombia)."""
    momento = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    if momento.tzinfo is not None:
        momento = momento.astimezone(BOGOTA)
    return f"{fecha_corta(momento.date())} {momento:%H:%M}"


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
            # Ancho explícito: el automático se calcula antes de cargar Montserrat (más ancha) y recorta cifras.
            ancho = max([len(col), *(len(x) for x in df[col])]) * 9 + 28
            config.setdefault(col, st.column_config.TextColumn(col, alignment="right", width=ancho))
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


# ── envío de formularios ───────────────────────────────────────────────────────

_AVISO = "_aviso_guardado"
_LIMPIAR = "_campos_por_limpiar"


def aviso_guardado() -> None:
    """Al empezar cada recarga, antes de la pantalla: vacía los campos que dejó enviar() y
    muestra (una vez) su 'Registro guardado'."""
    for clave, vacio in st.session_state.pop(_LIMPIAR, {}).items():
        st.session_state[clave] = vacio
    mensaje = st.session_state.pop(_AVISO, None)
    if mensaje:
        st.success(mensaje, icon=":material/check_circle:")


def enviar(accion: Callable[[], object], limpiar: Iterable[str] = (),
           exito: str | Callable[[object], str] = "Registro guardado", refrescar: bool = False, donde=None):
    """Ejecuta la escritura. Si la API la rechaza (409/422/...), st.error con su `detail` tal
    cual y NO se borra nada de lo digitado. Si sale bien, se limpian las claves `limpiar` de
    st.session_state (los campos del formulario), se deja el aviso y se recarga.
    `exito`: el aviso, o una función que lo arma con lo que devolvió `accion`.
    `refrescar`: limpia el caché de listas (pool, trabajadores, labores) antes de recargar.
    `donde`: contenedor para el error (por defecto, donde se llama)."""
    try:
        resultado = accion()
    except api.ErrorApi as e:
        (donde or st).error(e.detalle, icon=":material/error:")
        return None
    # Borrar la clave no basta: el navegador seguiría mostrando el valor viejo. Se deja el valor
    # vacío pendiente y app.py lo asigna al empezar la recarga, ANTES de dibujar los campos.
    pendientes = {}
    for clave in limpiar:
        if clave not in st.session_state:
            continue
        valor = st.session_state[clave]
        if isinstance(valor, bool):
            pendientes[clave] = False
        elif isinstance(valor, str):
            pendientes[clave] = ""
        elif isinstance(valor, (list, tuple)):
            pendientes[clave] = []
        elif isinstance(valor, (date, time, dict)):     # fechas: vuelven a su valor por defecto
            st.session_state.pop(clave)
        else:
            pendientes[clave] = None
    st.session_state[_LIMPIAR] = pendientes
    if refrescar:
        api.refrescar_listas()
    st.session_state[_AVISO] = exito(resultado) if callable(exito) else exito
    st.rerun()
    return resultado


FORMATOS_FOTO = ["jpg", "jpeg", "png", "webp", "heic", "heif"]


def foto(clave: str, rotulo: str) -> str | None:
    """Foto obligatoria de un registro (recibo, comprobante...). Se sube a la API apenas se
    elige, UNA vez por archivo, y su ruta queda en la sesión: si el registro falla, al
    reintentar no se vuelve a subir. Devuelve la ruta (o None si no hay foto)."""
    n = st.session_state.setdefault(f"{clave}_n", 0)
    archivo = st.file_uploader(rotulo, type=FORMATOS_FOTO, key=f"{clave}_archivo_{n}")
    subida = st.session_state.get(f"{clave}_foto")
    if archivo is None:
        st.session_state.pop(f"{clave}_foto", None)
        return None
    if subida is None or subida["archivo"] != archivo.file_id:
        try:
            r = api.post("/uploads/foto", archivos={"archivo": (archivo.name, archivo.getvalue(), archivo.type)})
        except api.ErrorApi as e:
            st.session_state.pop(f"{clave}_foto", None)
            st.error(e.detalle, icon=":material/error:")
            return None
        subida = st.session_state[f"{clave}_foto"] = {"archivo": archivo.file_id, "ruta": r["ruta"]}
    if archivo.type in ("image/jpeg", "image/png", "image/webp"):
        st.image(archivo, width=200, caption="Foto adjunta")
    else:
        st.caption(f":material/check_circle: Foto adjunta: {archivo.name}")
    return subida["ruta"]


def foto_nueva(clave: str) -> None:
    """Tras guardar: el uploader vuelve a quedar vacío para el siguiente registro."""
    st.session_state[f"{clave}_n"] = st.session_state.get(f"{clave}_n", 0) + 1
    st.session_state.pop(f"{clave}_foto", None)


def boton_excel(semana: str, donde=None) -> None:
    """«Descargar Excel» del consolidado semanal. El archivo se genera al pulsar; el usuario va
    explícito porque st.download_button llama a su función por fuera de la sesión."""
    quien = st.session_state["usuario"]["usuario"]
    (donde or st).download_button(
        "Descargar Excel", data=lambda: api.archivo(f"/reportes/consolidado-semanal/{semana}", quien),
        file_name=f"Agritics_consolidado_{semana}.xlsx", type="primary", icon=":material/download:",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"excel_{semana}")


def cifra_grande(rotulo: str, valor: str, nota: str = "") -> None:
    """Indicador destacado (guía: Bold 28-32 px, unidad al lado)."""
    st.html(f"<div class='ag-cifra'><small>{escape(rotulo)}</small><div>{escape(valor)}</div>"
            f"{f'<small>{escape(nota)}</small>' if nota else ''}</div>")


def sin_datos(texto: str = "Sin registros") -> None:
    st.caption(texto)


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
