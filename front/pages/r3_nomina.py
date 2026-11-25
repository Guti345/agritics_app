"""R3 · Nómina y labores del periodo (solo lectura). Periodo (semana, mes, año o rango) y
trabajador van a la API (/reportes/r3-nomina?desde=&hasta=); labor y lote filtran aquí sobre
lo ya cargado. La nómina no se guarda: la API la calcula.

Las labores día por día se ven por semana, en carrusel: flechas para recorrer las semanas que
caen dentro del periodo (con una sola semana no hay flechas)."""

from datetime import timedelta
from html import escape

import pandas as pd
import streamlit as st

import api
import ui

st.title("Nómina y labores")
f1, f2 = st.columns([5.2, 1.4], vertical_alignment="bottom")
desde, hasta, rotulo = ui.elegir_periodo("r3", donde=f1)
trabajadores = ui.leer(lambda: api.lista("/trabajadores"))
TODOS = "Todos los trabajadores"
quien = f2.selectbox("Trabajador", [TODOS, *sorted(t["nombre"] for t in trabajadores)], key="r3_trabajador")
trabajador_id = next((t["id"] for t in trabajadores if t["nombre"] == quien), None)
r3 = ui.leer(lambda: api.get("/reportes/r3-nomina", desde=desde, hasta=hasta, trabajador_id=trabajador_id))

st.caption(f"Finca Portugal · {rotulo} · cifras en COP")
t1, t2, t3 = st.columns(3)
t1.metric("Total a pagar", ui.pesos(r3["total_a_pagar"]), border=True,
          help="Labores completadas del periodo; en contratos, lo pactado menos los anticipos")
t2.metric("Nómina pagada", ui.pesos(r3["nomina_pagada"]), border=True,
          help="Lo efectivamente pagado en los pagos de nómina hechos dentro del periodo (puede incluir labores "
               "de días anteriores que se pagaron en esos pagos)")
pct = r3["pct_gastos_nomina"]
t3.metric("% de los gastos que es nómina", "—" if pct is None else f"{ui.numero(pct, 1)} %", border=True,
          help="Nómina causada del periodo / gastos totales del periodo (flujo de caja)"
               + ("" if pct is not None else ". Sin gastos en el periodo."))

filas = r3["trabajadores"]
if not filas:
    ui.sin_datos("Sin labores registradas en el periodo.")
    st.stop()

# ── lista para pagar (agregada al periodo) ──
st.subheader("Lista para pagar")
ui.tabla(pd.DataFrame([{
    "Trabajador": t["nombre"], "Tipo": t["tipo"].capitalize(), "Jornales": t["jornales"],
    "Total a pagar": t["total_a_pagar"], "Ya pagado": t["pagado_en_cortes"],
    "Pendiente por pagar": t["pendiente_por_pagar"], "Estimado abiertas": t["estimado_abiertas"],
    "Anticipos recibidos": t["total_anticipos_recibidos"], "Kg recolectados": t["kg_recolectados"],
    "Costo por kg": t["costo_por_kg"],
} for t in filas]), dinero=["Total a pagar", "Ya pagado", "Pendiente por pagar", "Estimado abiertas",
                            "Anticipos recibidos", "Costo por kg"], kilos=["Kg recolectados"], cifras=["Jornales"])
st.caption(f"Tipo de trabajador: {r3['criterio_tipo']}. «Estimado abiertas» no entra al pago hasta completarlas.")

# ── promedios por tipo de labor (agrega lo ya cargado del periodo) ──
st.subheader("Promedios por tipo de labor")
por_labor: dict[str, list[dict]] = {}
for t in filas:
    for l in t["labores"]:
        if l["completada"]:                   # las abiertas aún no tienen su valor final
            por_labor.setdefault(l["labor"], []).append(l)
if not por_labor:
    ui.sin_datos("Sin labores completadas en el periodo.")
else:
    resumen = sorted(({"Labor": labor, "N labores": len(ls),
                       "Valor pactado promedio": sum(l["valor_pactado"] for l in ls) / len(ls),
                       "Total pagado": sum(l["a_pagar"] for l in ls)} for labor, ls in por_labor.items()),
                     key=lambda f: -f["Total pagado"])
    ui.tabla(pd.DataFrame(resumen), dinero=["Valor pactado promedio", "Total pagado"], cifras=["N labores"])
    st.caption("Solo labores completadas. Valor pactado = lo que vale cada labor en COP (jornales x tarifa, o el "
               "contrato); total pagado = su «a pagar» (en contratos, neto de anticipos), el mismo de la lista.")

# ── labores día por día: una semana a la vez (carrusel por las semanas del periodo) ──
st.subheader("Labores día por día")
labores = [(t, l) for t in filas for l in t["labores"]]
c1, c2 = st.columns(2)
filtro_labor = c1.multiselect("Labor", sorted({l["labor"] for _, l in labores}), key=f"r3_labor_{desde}_{hasta}",
                              placeholder="Todas las labores")
filtro_lote = c2.multiselect("Lote", sorted({l["lote"] for _, l in labores}), key=f"r3_lote_{desde}_{hasta}",
                             placeholder="Todos los lotes")
visibles = [(t, l) for t, l in labores
            if (not filtro_labor or l["labor"] in filtro_labor) and (not filtro_lote or l["lote"] in filtro_lote)]

semanas, lunes = [], desde - timedelta(days=desde.weekday())
while lunes <= hasta:                                   # semanas que tocan el periodo (fechas reales)
    semanas.append(ui.semana_iso(lunes))
    lunes += timedelta(days=7)
clave = f"r3_carrusel_{desde}_{hasta}"
st.session_state.setdefault(clave, 0)


def mover(paso: int) -> None:
    st.session_state[clave] = max(0, min(len(semanas) - 1, st.session_state[clave] + paso))


i = st.session_state[clave]
semana = semanas[i]
if len(semanas) > 1:
    a, centro, b = st.columns([0.6, 8, 0.6], vertical_alignment="center")
    a.button("", icon=":material/chevron_left:", key="r3_atras", on_click=mover, args=(-1,), disabled=i == 0,
             help="Semana anterior", width="stretch")
    centro.html(f"<div style='text-align:center;font-weight:600'>{escape(ui.rotulo_semana(semana))}"
                f"<br><small style='font-weight:400;opacity:.8'>semana {i + 1} de {len(semanas)} del periodo</small></div>")
    b.button("", icon=":material/chevron_right:", key="r3_adelante", on_click=mover, args=(1,),
             disabled=i == len(semanas) - 1, help="Semana siguiente", width="stretch")

dias = ui.dias_de(semana)
hoy = ui.hoy()
celdas: dict[tuple[str, str], list[str]] = {}
for t, l in visibles:
    detalle = f"{l['forma_pago']} · {ui.pesos(l['tarifa'])} · {ui.sin_corte(l['estado'])}"
    celdas.setdefault((t["trabajador_id"], str(l["fecha"])[:10]), []).append(
        ui.chip_real(f"{l['labor']} · {l['lote']}", l["completada"], detalle))
con_labores = [t for t in filas if any((t["trabajador_id"], d.isoformat()) in celdas for d in dias)]
en_semana = sum(len(celdas.get((t["trabajador_id"], d.isoformat()), [])) for t in filas for d in dias)
if not con_labores:
    ui.sin_datos("Sin labores con esos filtros en esta semana." if filtro_labor or filtro_lote
                 else "Sin labores registradas en esta semana.")
else:
    def clase(d) -> str:
        """Hoy resaltado; los días de la semana que quedan fuera del periodo, atenuados."""
        clases = (["hoy"] if d == hoy else []) + (["fuera"] if not desde <= d <= hasta else [])
        return f" class='{' '.join(clases)}'" if clases else ""
    cabeza = "".join(f"<th{clase(d)}>{ui.dia_corto(d)}</th>" for d in dias)
    cuerpo = "".join(
        f"<tr><td class='nombre'>{escape(t['nombre'])}</td>"
        + "".join(f"<td{clase(d)}>{''.join(celdas.get((t['trabajador_id'], d.isoformat()), []))}</td>" for d in dias)
        + "</tr>" for t in con_labores)
    st.html("<div class='ag-leyenda'><span class='ag-chip real abierta'>Abierta (estimado)</span>"
            "<span class='ag-chip real completada'>Completada</span></div>"
            f"<div class='ag-scroll'><table class='ag-cal'><thead><tr><th>Trabajador</th>{cabeza}</tr></thead>"
            f"<tbody>{cuerpo}</tbody></table></div>")
st.caption(f"{en_semana} labores en esta semana"
           + (f" ({len(visibles)} en todo el periodo)" if len(semanas) > 1 else "")
           + ". Cada una dice su forma de pago, la tarifa y en qué pago de nómina se pagó.")

with st.expander("Ver las labores del periodo (tabla)"):
    if not visibles:
        ui.sin_datos("Sin labores con esos filtros.")
    else:
        ui.tabla(pd.DataFrame([{
            "Día": ui.dia_corto(ui.a_fecha(l["fecha"])), "Trabajador": t["nombre"], "Lote": l["lote"],
            "Labor": l["labor"], "Forma de pago": l["forma_pago"], "Jornales": l["jornales"], "Tarifa": l["tarifa"],
            "A pagar": l["a_pagar"], "Estado": ui.sin_corte(l["estado"])} for t, l in sorted(visibles, key=lambda x: x[1]["fecha"])]),
            dinero=["Tarifa", "A pagar"], cifras=["Jornales"])
