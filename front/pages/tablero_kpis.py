"""Junta familiar: resultados del periodo (solo lectura).

Un solo filtro de periodo (semana, mes, año o rango de días) y uno de lote mueven toda la
hoja: KPIs, mapa del margen estimado por lote, tabla de producción e ingresos estimados.
ROI y adopción digital son del año vigente hasta el final del periodo (así los da la API).
Los valores por lote son ESTIMADOS: el café se vende por recibo a nivel finca, no por lote.
"""

from datetime import timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import api
import graficos as g
import mapa
import ui

ICONOS = ui.ASSETS / "iconos"
REPORTES = [
    ("r1", "pages/r1_produccion.py", "Producción (R1)",
     "Kg de café y plátano, rendimiento y ventas por lote y por día", "cafe.svg", ":material/coffee:"),
    ("r2", "pages/r2_flujo.py", "Flujo de caja (R2)",
     "Ingresos, gastos y margen de la finca en el tiempo", "caja.svg", ":material/account_balance_wallet:"),
    ("r3", "pages/r3_nomina.py", "Nómina y labores (R3)",
     "Qué se paga, a quién y por qué labores", "nomina.svg", ":material/badge:"),
]

st.title("Resultados del periodo")
f_periodo, f_lote = st.columns([4.6, 1.2], vertical_alignment="bottom")
desde, hasta, rotulo = ui.elegir_periodo("kpis", donde=f_periodo)
productivos = [l for l in ui.leer(lambda: api.lista("/lotes")) if set(l["cultivos"]) & {"cafe", "platano"}]
TODOS = "Todos los lotes"
lote = f_lote.selectbox("Lote", [TODOS, *sorted(l["nombre"] for l in productivos)], key="kpis_lote")
lote_id = next((l["id"] for l in productivos if l["nombre"] == lote), None)

k = ui.leer(lambda: api.get("/reportes/kpis", desde=desde, hasta=hasta, lote_id=lote_id))
roi, anio, periodo = k["roi"], k["adopcion_anio"], k["adopcion_semana"]     # adopcion_semana = la del periodo
lotes = k["produccion_por_lote"]

st.caption(f"Finca Portugal · {rotulo} · año {roi['anio']} hasta el {ui.fecha_corta(ui.a_fecha(roi['hasta']))}"
           + ("" if lote == TODOS else f" · producción del lote {lote}") + " · cifras en COP")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Margen del periodo", ui.pesos(k["margen_semana"]), border=True,
          help=f"Ingresos {ui.pesos(k['ingresos_semana'])} − gastos {ui.pesos(k['gastos_semana'])} de toda la finca")
m2.metric("Producción del periodo", ui.kg(sum(l["kg_cafe"] for l in lotes), 0), border=True,
          help=f"Café cereza recogido en el periodo. Plátano: {ui.kg(sum(l['kg_platano'] for l in lotes), 0)} en "
               f"{ui.numero(sum(l['racimos'] for l in lotes))} racimos")
m3.metric("ROI simple del año", "—" if roi["roi"] is None else f"{ui.numero(100 * roi['roi'], 1)} %", border=True,
          help=f"Margen acumulado {ui.pesos(roi['margen_acumulado'])} / gasto acumulado "
               f"{ui.pesos(roi['gasto_acumulado'])}")
m4.metric("Adopción digital del año",
          "—" if anio["porcentaje"] is None else f"{ui.numero(anio['porcentaje'], 0)} %", border=True,
          help=f"Registros capturados el mismo día del evento: {ui.numero(anio['mismo_dia'])} de "
               f"{ui.numero(anio['registros'])}.")
st.caption("Adopción del periodo: "
           + ("sin registros" if periodo["porcentaje"] is None else
              f"{ui.numero(periodo['porcentaje'], 0)} % ({ui.numero(periodo['mismo_dia'])} de "
              f"{ui.numero(periodo['registros'])} registros el mismo día)")
           + f" · Margen del año: {ui.pesos(roi['margen_acumulado'])}"
           + ("" if lote == TODOS else " · El margen es de toda la finca; el lote filtra la producción."))

# ── mapa del margen estimado (izquierda) · producción e ingresos por lote (derecha) ──
izq, der = st.columns([1.15, 1], gap="medium")
with izq:
    st.subheader("Margen estimado por lote")
    poligonos = mapa.lotes_con_poligono()
    if poligonos:
        valores = {l["lote_id"]: l["margen_estimado"] for l in lotes if l["lote"] != "Bosque Natural"}
        detalle = {l["lote_id"]: f"<br>Ingreso estimado {ui.pesos(l['ingreso_estimado'])}"
                                 f"<br>Costo de labores {ui.pesos(l['costo_labores'])}" for l in lotes}
        g.mostrar(mapa.figura_por_valor(poligonos, valores, "Margen estimado", detalle), key="kpis_mapa")
    else:
        ui.sin_datos("Los lotes todavía no tienen su polígono.")
    st.caption("Margen estimado = ingreso estimado − costo de las labores completadas del lote. El café se vende "
               "por recibo para toda la finca: su venta del periodo se reparte por los kg de cereza de cada lote.")

with der:
    st.subheader("Producción por lote")
    con_produccion = [l for l in lotes if l["kg_cafe"] or l["kg_platano"]]
    if not con_produccion:
        ui.sin_datos("Sin producción registrada en el periodo.")
    else:
        ui.tabla(pd.DataFrame([{"Lote": l["lote"], "Café (kg)": l["kg_cafe"], "Plátano (kg)": l["kg_platano"],
                                "Racimos": l["racimos"]} for l in con_produccion]),
                 kilos=["Café (kg)", "Plátano (kg)"], cifras=["Racimos"], width="stretch")

    st.subheader("Ingresos estimados por lote")
    con_ingreso = [l for l in lotes if l["ingreso_estimado"]]
    if not con_ingreso:
        ui.sin_datos("Sin ventas en el periodo.")
    else:
        # La API da el ingreso estimado total del lote; se separa por cultivo según lo que produjo
        # (en la finca cada lote es de un solo cultivo; si un lote tuviera los dos, va por kg).
        def partes(l):
            kg_total = l["kg_cafe"] + l["kg_platano"]
            cafe = l["ingreso_estimado"] * (l["kg_cafe"] / kg_total if kg_total else 0)
            return cafe, l["ingreso_estimado"] - cafe
        orden = sorted(con_ingreso, key=lambda l: l["ingreso_estimado"])
        fig = go.Figure()
        fig.add_bar(y=[l["lote"] for l in orden], x=[partes(l)[0] for l in orden], orientation="h",
                    name="Café", marker_color=g.SERIES[0], hovertemplate="Café $%{x:,.0f}")
        fig.add_bar(y=[l["lote"] for l in orden], x=[partes(l)[1] for l in orden], orientation="h",
                    name="Plátano", marker_color=g.SERIES[1], hovertemplate="Plátano $%{x:,.0f}")
        fig.update_layout(barmode="stack", hovermode="y unified")
        fig.update_xaxes(showgrid=True, gridcolor=g.ARENA, tickformat="$,.0f", title_text="Ingreso estimado (COP)")
        g.mostrar(g.tema(fig, alto=60 + 34 * len(orden)), key="kpi_ingresos")

# ── Excel consolidado (por semana) ──
st.subheader("Excel consolidado")
e1, e2, _ = st.columns([1.3, 1, 1.7], vertical_alignment="bottom")
if st.session_state.get("kpis_modo") == "Semana":
    semana_excel = st.session_state["kpis_semana"]
    e1.caption(f"Semana del Excel: {ui.rotulo_semana(semana_excel)}")
else:   # arranca en la semana del último día del periodo
    semana_excel = e1.selectbox("Semana del Excel", [ui.semana_iso(hasta - timedelta(weeks=i)) for i in range(53)],
                                format_func=ui.rotulo_semana, key=f"kpis_semana_excel_{hasta}")
ui.boton_excel(semana_excel, donde=e2)
st.caption("El Excel consolida todo el año hasta la semana elegida, con el detalle diario y la nómina de esa semana.")

# ── acceso a los reportes ──
st.subheader("Reportes")
for col, (clave, ruta, titulo, texto, icono, simbolo) in zip(st.columns(3), REPORTES):
    with col:
        ui.tarjeta(clave, ruta, titulo, texto, (ICONOS / icono).read_text(encoding="utf-8"), simbolo,
                   enlace=f"Abrir {titulo.split(' (')[0].lower()}")
st.caption("Fuente: registros de Agritics. Los datos del año 2026 son el año cafetero simulado del MVP (ejemplo).")
