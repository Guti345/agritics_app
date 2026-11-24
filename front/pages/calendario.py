"""Calendario de asignaciones de la semana en curso: trabajadores del pool x días.

Planeadas = preasignación del pool; reales = labor_diaria (vienen del cronograma).
La preasignación se REEMPLAZA completa en PATCH /pool/{id}: siempre se manda la lista
entera (la que había + la nueva, o la que había sin la que se quita).
"""

from datetime import date
from html import escape

import streamlit as st

import api
import ui

semana = ui.semana_iso()
dias = ui.dias_de(semana)
hoy = ui.hoy()

st.title("Calendario de asignaciones")
st.caption(f"{ui.rotulo_semana(semana)} · planeadas (preasignación del pool) y reales (labores registradas)")

crono = ui.leer(lambda: api.get("/reportes/cronograma", semana=semana))
pool = ui.leer(lambda: api.get("/pool", semana=semana, activo=True))
lotes = ui.leer(lambda: api.por_id("/lotes"))
labores = ui.leer(lambda: api.por_id("/labores"))

# (trabajador_id, 'AAAA-MM-DD') -> chips del día
celdas: dict[tuple[str, str], list[str]] = {}
for d in crono["dias"]:
    for lote in d["lotes"]:
        for p in lote["planeadas"]:
            celdas.setdefault((p["trabajador_id"], str(d["fecha"])), []).append(
                ui.chip_plan(f"{p['labor']} · {lote['lote']}", p["cumplida"]))
        for r in lote["reales"]:
            celdas.setdefault((r["trabajador_id"], str(d["fecha"])), []).append(
                ui.chip_real(f"{r['labor']} · {lote['lote']}", r["completada"],
                             ui.jornales(r["jornales"]) + ("" if r["planeada"] else " · sin plan")))

if not pool:
    st.info("No hay trabajadores activos en el pool de esta semana: actívalos en Pool de trabajadores.",
            icon=":material/group_off:")
else:
    clase = lambda d: " class='hoy'" if d == hoy else ""  # noqa: E731
    cabeza = "".join(f"<th{clase(d)}>{ui.dia_corto(d)}</th>" for d in dias)
    filas = []
    for p in pool:
        tds = "".join(f"<td{clase(d)}>{''.join(celdas.get((p['trabajador_id'], d.isoformat()), []))}</td>"
                      for d in dias)
        filas.append(f"<tr><td class='nombre'>{escape(p['trabajador_nombre'])}</td>{tds}</tr>")
    st.html(ui.LEYENDA + f"<div class='ag-scroll'><table class='ag-cal'><thead><tr><th>Trabajador</th>{cabeza}"
            f"</tr></thead><tbody>{''.join(filas)}</tbody></table></div>")

# ── preasignar ────────────────────────────────────────────────────────────────
st.subheader("Preasignar labor")
if pool:
    por_nombre = {p["trabajador_nombre"]: p for p in pool}
    opciones_lotes, opciones_labores = api.opciones_lotes(), api.opciones_labores()
    with st.form("preasignar"):
        c1, c2 = st.columns(2)
        trabajador = c1.selectbox("Trabajador del pool", list(por_nombre), index=None,
                                  placeholder="Elige el trabajador", key="pre_trabajador")
        dia = c2.selectbox("Día", dias, format_func=ui.dia_corto, key="pre_dia",
                           index=dias.index(hoy) if hoy in dias else 0)
        lote = c1.selectbox("Lote", list(opciones_lotes), index=None, placeholder="Elige el lote", key="pre_lote")
        labor = c2.selectbox("Labor", list(opciones_labores), index=None, placeholder="Elige la labor",
                             key="pre_labor")
        if st.form_submit_button("Guardar preasignación", type="primary", icon=":material/event_available:"):
            faltante = next((m for falta, m in [(trabajador is None, "Elige el trabajador"),
                                                (lote is None, "Elige el lote"),
                                                (labor is None, "Elige la labor")] if falta), None)
            if faltante:
                st.error(faltante, icon=":material/error:")
            else:
                fila = por_nombre[trabajador]
                actual = [{"dia": x["dia"], "lote_id": x["lote_id"], "labor_id": x["labor_id"]}
                          for x in fila["preasignacion"]]
                nueva = {"dia": dia.isoformat(), "lote_id": opciones_lotes[lote], "labor_id": opciones_labores[labor]}
                if nueva in actual:
                    st.warning(f"{trabajador} ya tiene esa labor preasignada ese día.", icon=":material/info:")
                else:
                    ui.enviar(lambda: api.patch(f"/pool/{fila['id']}", {"preasignacion": actual + [nueva]}),
                              limpiar=["pre_lote", "pre_labor"], refrescar=True,
                              exito=f"Registro guardado: {labor} en {lote} para {trabajador} el {ui.dia_corto(dia)}")

    # Quitar: se manda la lista del trabajador sin esa preasignación (vacía = quitarlas todas).
    asignadas = [(p, x) for p in pool for x in p["preasignacion"]]
    if asignadas:
        with st.expander("Quitar una preasignación"):
            def rotulo(par):
                p, x = par
                return (f"{p['trabajador_nombre']} · {ui.dia_corto(date.fromisoformat(x['dia']))} · "
                        f"{labores.get(x['labor_id'], {}).get('nombre', '?')} · "
                        f"{lotes.get(x['lote_id'], {}).get('nombre', '?')}")
            elegida = st.selectbox("Preasignación", asignadas, format_func=rotulo, index=None,
                                   placeholder="Elige cuál quitar", key="pre_quitar")
            if st.button("Quitar preasignación", icon=":material/event_busy:", disabled=elegida is None):
                p, x = elegida
                resto = [{"dia": y["dia"], "lote_id": y["lote_id"], "labor_id": y["labor_id"]}
                         for y in p["preasignacion"]]
                resto.remove({"dia": x["dia"], "lote_id": x["lote_id"], "labor_id": x["labor_id"]})
                ui.enviar(lambda: api.patch(f"/pool/{p['id']}", {"preasignacion": resto}),
                          limpiar=["pre_quitar"], refrescar=True,
                          exito=f"Registro guardado: se quitó {rotulo(elegida)}")
