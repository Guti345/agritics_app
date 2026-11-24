"""R3 · Nómina y labores de la semana (solo lectura). Semana y trabajador van a la API;
labor y lote filtran aquí sobre lo ya cargado. La nómina no se guarda: la API la calcula."""

from html import escape

import pandas as pd
import streamlit as st

import api
import ui

st.title("Nómina y labores")
f1, f2 = st.columns(2)
semana = ui.elegir_semana(key="r3_semana", donde=f1)
trabajadores = ui.leer(lambda: api.lista("/trabajadores"))
TODOS = "Todos los trabajadores"
quien = f2.selectbox("Trabajador", [TODOS, *sorted(t["nombre"] for t in trabajadores)], key="r3_trabajador")
trabajador_id = next((t["id"] for t in trabajadores if t["nombre"] == quien), None)
r3 = ui.leer(lambda: api.get("/reportes/r3-nomina", semana=semana, trabajador_id=trabajador_id))

st.caption(f"Finca Portugal · {ui.rotulo_semana(semana)} · cifras en COP")
t1, t2, t3 = st.columns(3)
t1.metric("Total a pagar", ui.pesos(r3["total_a_pagar"]), border=True,
          help="Labores completadas; en contratos, lo pactado menos los anticipos")
t2.metric("Anticipos recibidos", ui.pesos(r3["total_anticipos_recibidos"]), border=True)
t3.metric("Nómina causada", ui.pesos(r3["total_nomina_causada"]), border=True,
          help="Lo que cuesta la semana: es lo que entra al flujo de caja")

filas = r3["trabajadores"]
if not filas:
    ui.sin_datos("Sin labores registradas en esta semana.")
    st.stop()

# ── lista para pagar ──
st.subheader("Lista para pagar")
ui.tabla(pd.DataFrame([{
    "Trabajador": t["nombre"], "Tipo": t["tipo"].capitalize(), "Jornales": t["jornales"],
    "Total a pagar": t["total_a_pagar"], "Pagado en cortes": t["pagado_en_cortes"],
    "Pendiente por pagar": t["pendiente_por_pagar"], "Estimado abiertas": t["estimado_abiertas"],
    "Anticipos recibidos": t["total_anticipos_recibidos"], "Kg recolectados": t["kg_recolectados"],
    "Costo por kg": t["costo_por_kg"],
} for t in filas]), dinero=["Total a pagar", "Pagado en cortes", "Pendiente por pagar", "Estimado abiertas",
                            "Anticipos recibidos", "Costo por kg"], kilos=["Kg recolectados"], cifras=["Jornales"])
st.caption(f"Tipo de trabajador: {r3['criterio_tipo']}. «Estimado abiertas» no entra al pago hasta completarlas.")

# ── calendario de labores (trazabilidad) ──
st.subheader("Labores de la semana día por día")
labores = [(t, l) for t in filas for l in t["labores"]]
c1, c2 = st.columns(2)
filtro_labor = c1.multiselect("Labor", sorted({l["labor"] for _, l in labores}), key=f"r3_labor_{semana}",
                              placeholder="Todas las labores")
filtro_lote = c2.multiselect("Lote", sorted({l["lote"] for _, l in labores}), key=f"r3_lote_{semana}",
                             placeholder="Todos los lotes")
visibles = [(t, l) for t, l in labores
            if (not filtro_labor or l["labor"] in filtro_labor) and (not filtro_lote or l["lote"] in filtro_lote)]

dias = ui.dias_de(semana)
hoy = ui.hoy()
celdas: dict[tuple[str, str], list[str]] = {}
for t, l in visibles:
    detalle = f"{l['forma_pago']} · {ui.pesos(l['tarifa'])} · {l['estado']}"
    celdas.setdefault((t["trabajador_id"], str(l["fecha"])[:10]), []).append(
        ui.chip_real(f"{l['labor']} · {l['lote']}", l["completada"], detalle))
con_labores = [t for t in filas if any((t["trabajador_id"], d.isoformat()) in celdas for d in dias)]
if not con_labores:
    ui.sin_datos("Ninguna labor coincide con los filtros.")
else:
    clase = lambda d: " class='hoy'" if d == hoy else ""  # noqa: E731
    cabeza = "".join(f"<th{clase(d)}>{ui.dia_corto(d)}</th>" for d in dias)
    cuerpo = "".join(
        f"<tr><td class='nombre'>{escape(t['nombre'])}</td>"
        + "".join(f"<td{clase(d)}>{''.join(celdas.get((t['trabajador_id'], d.isoformat()), []))}</td>" for d in dias)
        + "</tr>" for t in con_labores)
    st.html("<div class='ag-leyenda'><span class='ag-chip real abierta'>Abierta (estimado)</span>"
            "<span class='ag-chip real completada'>Completada</span></div>"
            f"<div class='ag-scroll'><table class='ag-cal'><thead><tr><th>Trabajador</th>{cabeza}</tr></thead>"
            f"<tbody>{cuerpo}</tbody></table></div>")
    st.caption(f"{len(visibles)} labores. Cada una dice su forma de pago, la tarifa y en qué corte se pagó.")

    with st.expander("Ver las labores (tabla)"):
        ui.tabla(pd.DataFrame([{
            "Día": ui.dia_corto(ui.a_fecha(l["fecha"])), "Trabajador": t["nombre"], "Lote": l["lote"],
            "Labor": l["labor"], "Forma de pago": l["forma_pago"], "Jornales": l["jornales"], "Tarifa": l["tarifa"],
            "A pagar": l["a_pagar"], "Estado": l["estado"]} for t, l in visibles]),
            dinero=["Tarifa", "A pagar"], cifras=["Jornales"])
