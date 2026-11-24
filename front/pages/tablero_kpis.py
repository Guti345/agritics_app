"""Junta familiar: resultados del periodo (solo lectura). KPIs de la semana y del año,
acceso a R1-R3 y el Excel consolidado."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import api
import graficos as g
import ui

st.title("Resultados del periodo")
c1, c2 = st.columns([1, 1], vertical_alignment="bottom")
semana = ui.elegir_semana(key="kpis_semana", donde=c1)
ui.boton_excel(semana, donde=c2)
k = ui.leer(lambda: api.get("/reportes/kpis", semana=semana))
roi, anio, sem = k["roi"], k["adopcion_anio"], k["adopcion_semana"]
lotes = k["produccion_por_lote"]

st.caption(f"Finca Portugal · {ui.rotulo_semana(semana)} · año {roi['anio']} hasta el "
           f"{ui.fecha_corta(ui.a_fecha(roi['hasta']))} · cifras en COP")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Margen de la semana", ui.pesos(k["margen_semana"]), border=True,
          help=f"Ingresos {ui.pesos(k['ingresos_semana'])} − gastos {ui.pesos(k['gastos_semana'])}")
m2.metric("Producción de la semana", ui.kg(sum(l["kg_cafe"] for l in lotes), 0) + " café", border=True,
          help=f"Café cereza recogido. Plátano: {ui.kg(sum(l['kg_platano'] for l in lotes), 0)} en "
               f"{ui.numero(sum(l['racimos'] for l in lotes))} racimos")
m3.metric("ROI simple del año", "—" if roi["roi"] is None else f"{ui.numero(100 * roi['roi'], 1)} %", border=True,
          help=f"Margen acumulado {ui.pesos(roi['margen_acumulado'])} / gasto acumulado "
               f"{ui.pesos(roi['gasto_acumulado'])}")
m4.metric("Adopción digital del año",
          "—" if anio["porcentaje"] is None else f"{ui.numero(anio['porcentaje'], 0)} %", border=True,
          help=f"Registros capturados el mismo día del evento: {ui.numero(anio['mismo_dia'])} de "
               f"{ui.numero(anio['registros'])}. Esta semana: "
               + ("sin registros" if sem["porcentaje"] is None else f"{ui.numero(sem['porcentaje'], 0)} %"))
st.caption("Adopción de la semana: "
           + ("sin registros" if sem["porcentaje"] is None else
              f"{ui.numero(sem['porcentaje'], 0)} % ({ui.numero(sem['mismo_dia'])} de {ui.numero(sem['registros'])} "
              "registros el mismo día)")
           + f" · Margen del año: {ui.pesos(roi['margen_acumulado'])}")

# ── producción por lote de la semana ──
st.subheader("Producción por lote en la semana")
con_produccion = [l for l in lotes if l["kg_cafe"] or l["kg_platano"]]
if not con_produccion:
    ui.sin_datos("Sin producción registrada en esta semana.")
else:
    c1, c2 = st.columns([3, 2])
    with c1:
        orden = sorted(con_produccion, key=lambda l: l["kg_cafe"] + l["kg_platano"])
        fig = go.Figure()
        fig.add_bar(y=[l["lote"] for l in orden], x=[l["kg_cafe"] for l in orden], orientation="h",
                    name="Café cereza (kg)", marker_color=g.SERIES[0], hovertemplate="%{x:,.0f} kg de café")
        fig.add_bar(y=[l["lote"] for l in orden], x=[l["kg_platano"] for l in orden], orientation="h",
                    name="Plátano (kg)", marker_color=g.SERIES[1], hovertemplate="%{x:,.0f} kg de plátano")
        fig.update_layout(barmode="stack", hovermode="y unified")
        fig.update_xaxes(showgrid=True, gridcolor=g.ARENA, title_text="kg en la semana")
        g.mostrar(g.tema(fig, alto=340), key="kpi_lotes")
    with c2:
        ui.tabla(pd.DataFrame([{"Lote": l["lote"], "Café (kg)": l["kg_cafe"], "Plátano (kg)": l["kg_platano"],
                                "Racimos": l["racimos"]} for l in con_produccion]),
                 kilos=["Café (kg)", "Plátano (kg)"], cifras=["Racimos"])

# ── acceso a los reportes ──
st.subheader("Reportes")
r1, r2, r3 = st.columns(3)
r1.page_link("pages/r1_produccion.py", label="Producción (R1)", icon=":material/coffee:")
r2.page_link("pages/r2_flujo.py", label="Flujo de caja (R2)", icon=":material/account_balance_wallet:")
r3.page_link("pages/r3_nomina.py", label="Nómina y labores (R3)", icon=":material/badge:")
st.caption("Fuente: registros de Agritics. Los datos del año 2026 son el año cafetero simulado del MVP (ejemplo).")
