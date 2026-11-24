"""Cronograma de la finca: todas las labores de una semana, estilo calendario.

Planeadas (preasignación del pool) vs. reales (labor_diaria); reales abiertas vs.
completadas. Filtrable por lote. Los indicadores de arriba son los de la API.
"""

from datetime import date, timedelta
from html import escape

import streamlit as st

import api
import ui

hoy = ui.hoy()
# De la semana siguiente hacia atrás, un año.
semanas = [ui.semana_iso(hoy + timedelta(weeks=1) - timedelta(weeks=k)) for k in range(54)]

st.title("Cronograma de la finca")
c1, c2 = st.columns(2)
semana = c1.selectbox("Semana", semanas, index=1, format_func=ui.rotulo_semana, key="cr_semana")
crono = ui.leer(lambda: api.get("/reportes/cronograma", semana=semana))

nombres_lote = sorted({l["lote"] for d in crono["dias"] for l in d["lotes"]})
TODOS = "Todos los lotes"
lote = c2.selectbox("Lote", [TODOS, *nombres_lote], key=f"cr_lote_{semana}")

# ── indicadores (de la API, de toda la semana) ──
pct = crono["cumplimiento_pct"]
abiertas = sum(1 for d in crono["dias"] for l in d["lotes"] for r in l["reales"] if not r["completada"])
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Cumplimiento", "Sin planeadas" if pct is None else f"{ui.numero(pct, 0)} %", border=True,
          help="Planeadas cumplidas / planeadas")
k2.metric("Planeadas", crono["planeadas"], border=True)
k3.metric("Reales", crono["reales"], border=True)
k4.metric("Planeadas cumplidas", crono["planeadas_cumplidas"], border=True)
k5.metric("Reales abiertas", abiertas, border=True)
if lote != TODOS:
    st.caption("Los indicadores son de toda la semana; el calendario muestra solo el lote elegido.")

# ── calendario ──
columnas = []
for d in crono["dias"]:
    dia = date.fromisoformat(str(d["fecha"]))
    bloques = []
    for l in d["lotes"]:
        if lote != TODOS and l["lote"] != lote:
            continue
        chips = [ui.chip_plan(f"{p['trabajador']} · {p['labor']}", p["cumplida"]) for p in l["planeadas"]]
        chips += [ui.chip_real(f"{r['trabajador']} · {r['labor']}", r["completada"],
                               ui.jornales(r["jornales"]) + ("" if r["planeada"] else " · sin plan"))
                  for r in l["reales"]]
        bloques.append(f"<div class='ag-lote'>{escape(l['lote'])}</div>{''.join(chips)}")
    contenido = "".join(bloques) or "<div class='ag-vacio'>Sin labores</div>"
    columnas.append(f"<div class='ag-dia{' hoy' if dia == hoy else ''}'>"
                    f"<div class='ag-dia-titulo'>{ui.dia_corto(dia)}</div>{contenido}</div>")

st.html(ui.LEYENDA + f"<div class='ag-crono'>{''.join(columnas)}</div>")
st.caption(f"Fuente: labores registradas y pool de la {ui.rotulo_semana(semana)} "
           f"({ui.fecha_corta(date.fromisoformat(str(crono['desde'])))} a "
           f"{ui.fecha_corta(date.fromisoformat(str(crono['hasta'])))}).")
