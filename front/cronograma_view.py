"""Cronograma de la finca (componente compartido: Programación del mayordomo y
«Cronograma» del administrador).

    import cronograma_view
    cronograma_view.cronograma_finca(clave="cr")

Histórico con zoom día / semana / mes, como un mapa: se acerca o se aleja de nivel y se
avanza o retrocede con las flechas. La API da el cronograma por semana; el mes junta sus
4-5 semanas (las semanas cuyo jueves cae en el mes, norma ISO). El resumen es el de la API
(en el mes, la suma de sus semanas).

Sin estados duplicados: cada labor aparece una vez con su estado de mayor rango
(completada > abierta > planeada); ver campo.unificar.
"""

from datetime import date, timedelta
from html import escape

import streamlit as st

import api
import campo
import ui

NIVELES = ["Día", "Semana", "Mes"]
MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre",
         "Noviembre", "Diciembre"]
def mes_de(dia: date) -> tuple[int, int]:
    j = campo.jueves(dia)
    return j.year, j.month


def semanas_del_mes(anio: int, mes: int) -> list[str]:
    """Semanas ISO cuyo jueves cae en el mes (4 o 5)."""
    lunes = date(anio, mes, 1) - timedelta(days=date(anio, mes, 1).weekday())
    semanas = []
    while lunes <= date(anio + mes // 12, mes % 12 + 1, 1):
        if (lunes + timedelta(days=3)).month == mes:
            semanas.append(ui.semana_iso(lunes))
        lunes += timedelta(weeks=1)
    return semanas


def zoom(clave: str, paso: int) -> None:
    """-1 acerca (mes -> semana -> día), +1 aleja."""
    i = NIVELES.index(st.session_state[f"{clave}_nivel"]) + paso
    st.session_state[f"{clave}_nivel"] = NIVELES[max(0, min(len(NIVELES) - 1, i))]


def mover(clave: str, paso: int) -> None:
    hoy = ui.hoy()
    ancla, nivel = st.session_state[f"{clave}_ancla"], st.session_state[f"{clave}_nivel"]
    if nivel == "Día":
        ancla += timedelta(days=paso)
    elif nivel == "Semana":
        ancla += timedelta(weeks=paso)
    else:
        anio, mes = mes_de(ancla)
        mes += paso
        anio, mes = anio + (mes - 1) // 12, (mes - 1) % 12 + 1
        ancla = hoy if mes_de(hoy) == (anio, mes) else date(anio, mes, 15)
    st.session_state[f"{clave}_ancla"] = ancla


def volver_a_hoy(clave: str) -> None:
    st.session_state[f"{clave}_ancla"] = ui.hoy()


def cronograma_finca(clave: str = "cr") -> None:
    """Dibuja el cronograma completo. `clave`: prefijo de las claves de sus controles en
    st.session_state (cada pantalla que lo use conserva su propia fecha, zoom y lote)."""
    hoy = ui.hoy()
    st.session_state.setdefault(f"{clave}_ancla", hoy)
    st.session_state.setdefault(f"{clave}_nivel", "Semana")
    lotes_finca = [l["nombre"] for l in ui.leer(lambda: api.lista("/lotes")) if set(l["cultivos"]) & {"cafe", "platano"}]
    TODOS = "Todos los lotes"

    c_nav, c_fecha, c_nivel, c_zoom = st.columns([2.3, 1.7, 2.3, 2.6], vertical_alignment="bottom")
    with c_nav:
        a, b, c = st.columns([1, 1.4, 1])
        a.button("", icon=":material/chevron_left:", key=f"{clave}_atras", on_click=mover, args=(clave, -1), help="Anterior",
                 width="stretch")
        b.button("Hoy", key=f"{clave}_hoy", on_click=volver_a_hoy, args=(clave,), width="stretch")
        c.button("", icon=":material/chevron_right:", key=f"{clave}_adelante", on_click=mover, args=(clave, 1), help="Siguiente",
                 width="stretch")
    c_fecha.date_input("Ir a la fecha", key=f"{clave}_ancla", format="DD/MM/YYYY")
    c_nivel.segmented_control("Ver", NIVELES, key=f"{clave}_nivel", required=True)
    with c_zoom:
        z1, z2 = st.columns(2)
        z1.button("Acercar", icon=":material/zoom_in:", key=f"{clave}_acercar", on_click=zoom, args=(clave, -1), width="stretch",
                  disabled=st.session_state[f"{clave}_nivel"] == NIVELES[0], help="Mes → semana → día")
        z2.button("Alejar", icon=":material/zoom_out:", key=f"{clave}_alejar", on_click=zoom, args=(clave, 1), width="stretch",
                  disabled=st.session_state[f"{clave}_nivel"] == NIVELES[-1], help="Día → semana → mes")
    c_lote, _ = st.columns([1, 2])
    lote = c_lote.selectbox("Lote", [TODOS, *lotes_finca], key=f"{clave}_lote")
    filtro = None if lote == TODOS else lote

    nivel, ancla = st.session_state[f"{clave}_nivel"], st.session_state[f"{clave}_ancla"]
    semanas = semanas_del_mes(*mes_de(ancla)) if nivel == "Mes" else [ui.semana_iso(ancla)]
    cronos = [campo.cronograma(s) for s in semanas]

    # ── resumen: el de la API (en el mes, la suma de sus semanas) ──
    planeadas = sum(c["planeadas"] for c in cronos)
    cumplidas = sum(c["planeadas_cumplidas"] for c in cronos)
    reales = sum(c["reales"] for c in cronos)
    abiertas = sum(1 for c in cronos for d in c["dias"] for l in d["lotes"] for r in l["reales"] if not r["completada"])
    pct = cronos[0]["cumplimiento_pct"] if len(cronos) == 1 else (100 * cumplidas / planeadas if planeadas else None)

    if nivel == "Día":
        titulo = f"{ui.DIAS[ancla.weekday()]} {ancla.day} {ui.MESES[ancla.month - 1]} {ancla.year}"
        alcance = f"de la {ui.rotulo_semana(semanas[0])} (la API lo da por semana)"
    elif nivel == "Semana":
        titulo = ui.rotulo_semana(semanas[0])
        alcance = "de la semana"
    else:
        anio, mes = mes_de(ancla)
        titulo = f"{MESES[mes - 1]} {anio}"
        alcance = (f"de las semanas {int(semanas[0][6:])} a {int(semanas[-1][6:])} "
                   f"({len(semanas)} semanas: las que tienen su jueves en {MESES[mes - 1].lower()})")
    st.subheader(titulo)
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Cumplimiento", "Sin planeadas" if pct is None else f"{ui.numero(pct, 0)} %", border=True,
              help="Planeadas cumplidas / planeadas")
    k2.metric("Planeadas", planeadas, border=True)
    k3.metric("Reales", reales, border=True)
    k4.metric("Planeadas cumplidas", cumplidas, border=True)
    k5.metric("Reales abiertas", abiertas, border=True)
    st.caption(f"Resumen {alcance}" + ("; el calendario muestra solo el lote elegido." if filtro else "."))

    dias = {d["fecha"] if isinstance(d["fecha"], str) else d["fecha"].isoformat(): d for c in cronos for d in c["dias"]}

    if nivel == "Día":
        grupos = campo.lotes_del_dia(dias[ancla.isoformat()], filtro)
        tarjetas = "".join(
            f"<div class='ag-dia'><div class='ag-dia-titulo'>{escape(nombre)}</div>"
            + "".join(campo.ficha(f"{f['trabajador']} · {f['labor']}", f) for f in fichas) + "</div>"
            for nombre, fichas in grupos)
        st.html(campo.LEYENDA + (f"<div class='ag-lotes'>{tarjetas}</div>" if tarjetas
                                 else "<div class='ag-vacio'>Sin labores este día.</div>"))

    elif nivel == "Semana":
        columnas = []
        for dia in ui.dias_de(semanas[0]):
            bloques = "".join(
                f"<div class='ag-lote'>{escape(nombre)}</div>"
                + "".join(campo.ficha(f"{f['trabajador']} · {f['labor']}", f) for f in fichas)
                for nombre, fichas in campo.lotes_del_dia(dias[dia.isoformat()], filtro))
            columnas.append(f"<div class='ag-dia{' hoy' if dia == hoy else ''}'>"
                            f"<div class='ag-dia-titulo'>{ui.dia_corto(dia)}</div>"
                            f"{bloques or '<div class=ag-vacio>Sin labores</div>'}</div>")
        st.html(campo.LEYENDA + f"<div class='ag-crono'>{''.join(columnas)}</div>")

    else:
        anio, mes = mes_de(ancla)
        celdas = ["<div class='cab'></div>"] + [f"<div class='cab'>{d}</div>" for d in ui.DIAS]
        for s in semanas:
            celdas.append(f"<div class='sem'>S{int(s[6:])}</div>")
            for dia in ui.dias_de(s):
                # Una línea por (labor, estado) con cuántas fichas tiene; el lote se nombra si es uno
                # solo (con varios, quedan en la ventanita al pasar el mouse).
                grupos: dict[tuple, list[str]] = {}
                for nombre, fichas in campo.lotes_del_dia(dias[dia.isoformat()], filtro):
                    for f in fichas:
                        grupos.setdefault((f["labor"], f["estado"]), []).append(nombre)
                lineas = "".join(
                    f"<span class='ag-mini {estado}' title='{escape(', '.join(sorted(set(lotes))))}'>{escape(labor)}"
                    + (f" ×{len(lotes)}" if len(lotes) > 1 else ("" if filtro else f" · {escape(lotes[0])}"))
                    + "</span>"
                    for (labor, estado), lotes in sorted(grupos.items(), key=lambda x: (-campo.RANGO[x[0][1]], x[0][0])))
                clase = "celda" + (" fuera" if dia.month != mes else "") + (" hoy" if dia == hoy else "")
                celdas.append(f"<div class='{clase}'><div class='num'>{dia.day} {ui.MESES[dia.month - 1]}</div>"
                              f"{lineas}</div>")
        st.html(campo.LEYENDA + f"<div class='ag-mes'>{''.join(celdas)}</div>")
        st.caption("Acerca el zoom (o elige «Semana» o «Día») para ver quién hizo cada labor.")
