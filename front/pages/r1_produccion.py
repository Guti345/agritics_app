"""R1 · Producción de café y plátano (solo lectura)."""

from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import api
import graficos as g
import ui

st.title("Producción")
hoy = ui.hoy()
f1, f2, f3 = st.columns(3)
desde = f1.date_input("Desde", value=date(hoy.year, 1, 1), max_value=hoy, format="DD/MM/YYYY", key="r1_desde")
hasta = f2.date_input("Hasta", value=hoy, max_value=hoy, format="DD/MM/YYYY", key="r1_hasta")
lotes = [l for l in ui.leer(lambda: api.lista("/lotes")) if set(l["cultivos"]) & {"cafe", "platano"}]
TODOS = "Todos los lotes"
lote = f3.selectbox("Lote", [TODOS, *[l["nombre"] for l in lotes]], key="r1_lote")
lote_id = next((l["id"] for l in lotes if l["nombre"] == lote), None)
if desde > hasta:
    st.error("La fecha «Desde» debe ser anterior a «Hasta»", icon=":material/error:")
    st.stop()

r1 = ui.leer(lambda: api.get("/reportes/r1-produccion", desde=desde, hasta=hasta, lote_id=lote_id))
COLOR_LOTE = g.colores(l["nombre"] for l in lotes if "cafe" in l["cultivos"])   # fijo, no depende del filtro
st.caption(f"Finca Portugal · del {ui.fecha_corta(desde)} al {ui.fecha_corta(hasta)}"
           + ("" if lote == TODOS else f" · lote {lote}"))

cafe_tab, platano_tab = st.tabs([":material/coffee: Café", ":material/nutrition: Plátano"], key="r1_tab")

# ═══ CAFÉ ══════════════════════════════════════════════════════════════════════
with cafe_tab:
    finca = r1["finca"]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Café cereza recogido", ui.kg(finca["kg"], 0), border=True, help="En el rango elegido")
    m2.metric("Rendimiento (kg/ha)", ui.numero(finca["kg_ha"], 0), border=True,
              help=f"Sobre {ui.numero(finca['area_ha'], 2)} ha de café")
    # Estático: del 1 de enero a hoy, sin importar las fechas del filtro (la API lo acumula
    # hasta «Hasta»; por eso va en una lectura aparte, con el mismo lote).
    anio = ui.leer(lambda: api.get("/reportes/r1-produccion", desde=date(hoy.year, 1, 1), hasta=hoy, lote_id=lote_id))
    m3.metric("Acumulado del año vigente", ui.kg(anio["finca"]["kg_acumulado_anio"], 0), border=True,
              help="Del 1 de enero a hoy; NO cambia con el filtro de fechas")
    m4.metric("Recibos de venta", len(r1["ventas_por_recibo"]), border=True)

    # ── kg de cereza por día, por lote ──
    st.subheader("Café cereza recogido por día")
    dias = pd.DataFrame(r1["cafe_por_dia"])
    if dias.empty:
        ui.sin_datos("Sin recolección de café en el rango.")
    else:
        dias["fecha"] = pd.to_datetime(dias["fecha"])
        fig = go.Figure()
        for nombre in sorted(dias["lote"].unique()):   # una línea por lote, sin apilar
            d = dias[dias["lote"] == nombre]
            fig.add_scatter(x=d["fecha"], y=d["kg"], name=nombre, mode="lines+markers",
                            line=dict(color=COLOR_LOTE.get(nombre, g.TINTA), width=2), marker=dict(size=6),
                            hovertemplate="%{y:,.0f} kg")
        g.mostrar(g.eje_meses(g.tema(fig, titulo_y="kg de cereza"), desde, hasta), key="r1_dia")

    # ── ventas por semana (barras) + factor de cada recibo (línea, eje derecho) ──
    st.subheader("Ventas de café por semana y factor de rendimiento por recibo")
    semanas = pd.DataFrame(r1["ventas_cafe_por_semana"])
    recibos = pd.DataFrame(r1["ventas_por_recibo"])
    if semanas.empty:
        ui.sin_datos("Sin ventas de café en el rango.")
    else:
        semanas["x"] = semanas["semana"].map(lambda s: ui.dias_de(s)[3])   # centro de la semana (jueves)
        semanas["rotulo"] = semanas["semana"].map(ui.rotulo_semana)
        fig = go.Figure()
        for producto in ("pergamino", "mojado", "pasilla"):
            fig.add_bar(x=semanas["x"], y=semanas[f"kg_{producto}"], name=f"kg {g.PRODUCTOS[producto].lower()}",
                        marker_color=g.COLOR_PRODUCTO[producto], width=6 * 86_400_000, customdata=semanas["rotulo"],
                        hovertemplate="%{customdata}: %{y:,.1f} kg", legendgroup=producto)
        recibos["fecha"] = pd.to_datetime(recibos["fecha"])
        for producto in ("pergamino", "mojado", "pasilla"):
            r = recibos[recibos["tipo_producto"] == producto].sort_values("fecha")
            if r.empty:
                continue
            fig.add_scatter(x=r["fecha"], y=r["factor_rendimiento"], yaxis="y2", mode="lines+markers",
                            name=f"Factor {g.PRODUCTOS[producto].lower()} (cada recibo)", legendgroup=producto,
                            line=dict(color=g.TINTA if producto == "pergamino" else g.COLOR_PRODUCTO[producto],
                                      width=2, dash="solid" if producto != "pasilla" else "dot"),
                            marker=dict(size=9, symbol=g.SIMBOLO_PRODUCTO[producto], line=dict(color="#FFFFFF", width=2)),
                            hovertemplate="Factor %{y:,.1f}")
        factores = recibos["factor_rendimiento"]
        fig.update_layout(
            barmode="stack", hovermode="closest",
            yaxis=dict(title_text="kg vendidos por semana"),
            yaxis2=dict(title_text="Factor de rendimiento (cada recibo)", overlaying="y", side="right",
                        showgrid=False, dtick=10, tickformat=".0f",
                        range=[max(60, 10 * (factores.min() // 10) - 10), min(160, 10 * (factores.max() // 10) + 10)]),
        )
        g.tema(fig, alto=420)
        fig.update_layout(yaxis_title_text="kg vendidos por semana",
                          yaxis2_title_text="Factor de rendimiento (cada recibo)")
        g.mostrar(g.eje_meses(fig, desde, hasta), key="r1_ventas")
    st.caption("El pergamino equivalente usa el factor de rendimiento de cada recibo. El factor NO es un "
               "porcentaje: son kg de café pergamino seco por saco de 70 kg; puede haber varios recibos por semana.")

    with st.expander("Ver los recibos (tabla)"):
        if not recibos.empty:
            ui.tabla(pd.DataFrame({
                "Fecha": recibos["fecha"].dt.date.map(ui.fecha_corta),
                "Producto": recibos["tipo_producto"].map(g.PRODUCTOS),
                "Kg netos": recibos["kg_netos"], "Pergamino equivalente": recibos["kg_pergamino_equivalente"],
                "Factor": recibos["factor_rendimiento"], "Valor": recibos["valor_total"],
            }), dinero=["Valor"], kilos=["Kg netos", "Pergamino equivalente"], cifras=["Factor"])
        else:
            ui.sin_datos("Sin recibos de venta de café en el rango.")

    # ── por lote ──
    st.subheader("Producción por lote")
    por_lote = r1["por_lote"]
    if por_lote:
        tabla = pd.DataFrame([{
            "Lote": p["lote"], "Área (ha)": p["area_ha"], "Kg en el rango": p["kg"], "Kg/ha en el rango": p["kg_ha"],
            "Kg del año": p["kg_acumulado_anio"], "Kg/ha del año": p["kg_ha_acumulado_anio"]} for p in por_lote]
            + [{"Lote": "Finca", "Área (ha)": finca["area_ha"], "Kg en el rango": finca["kg"],
                "Kg/ha en el rango": finca["kg_ha"], "Kg del año": finca["kg_acumulado_anio"],
                "Kg/ha del año": finca["kg_ha_acumulado_anio"]}])
        c1, c2 = st.columns([3, 2])
        with c1:
            ui.tabla(tabla, kilos=["Kg en el rango", "Kg del año"], cifras=["Área (ha)", "Kg/ha en el rango", "Kg/ha del año"])
        with c2:
            orden = sorted(por_lote, key=lambda p: p["kg_ha_acumulado_anio"])
            mejor = orden[-1]["lote"]               # el de mayor kg/ha del año, destacado
            fig = go.Figure(go.Bar(
                y=[p["lote"] for p in orden], x=[p["kg_ha_acumulado_anio"] for p in orden], orientation="h",
                marker_color=[g.TINTA if p["lote"] == mejor else "rgba(0,201,75,0.45)" for p in orden],
                text=[ui.numero(p["kg_ha_acumulado_anio"]) for p in orden], textposition="outside",
                hovertemplate="%{y}: %{x:,.0f} kg/ha<extra></extra>"))
            fig.update_layout(showlegend=False, hovermode="closest")
            g.mostrar(g.tema(fig, alto=320, titulo_y=None).update_xaxes(title_text="kg/ha de cereza en el año",
                                                                        showgrid=True, gridcolor=g.ARENA),
                      key="r1_lotes")
    else:
        ui.sin_datos("Sin lotes de café para mostrar con este filtro.")

# ═══ PLÁTANO ═══════════════════════════════════════════════════════════════════
with platano_tab:
    plat = pd.DataFrame(r1["platano"])
    cosechas = pd.DataFrame(ui.leer(lambda: api.get("/cosechas-platano", desde=desde, hasta=hasta, lote_id=lote_id)))
    if plat.empty:
        ui.sin_datos("Sin cosechas de plátano en el rango.")
    else:
        por_semana = plat.groupby("semana", as_index=False)[["kg", "racimos", "cosechas"]].sum().sort_values("semana")
        por_semana["rotulo"] = por_semana["semana"].map(lambda s: f"S{int(s[6:])}")
        kg_primera = cosechas.loc[cosechas["calidad"] == "primera", "kg"].sum() if not cosechas.empty else 0
        kg_total = cosechas["kg"].sum() if not cosechas.empty else 0
        m1, m2, m3 = st.columns(3)
        m1.metric("Plátano cosechado", ui.kg(plat["kg"].sum(), 0), border=True)
        m2.metric("Racimos", ui.numero(plat["racimos"].sum()), border=True,
                  help=f"{ui.numero(plat['kg'].sum() / plat['racimos'].sum(), 1)} kg por racimo en promedio")
        m3.metric("Primera calidad", f"{ui.numero(100 * kg_primera / kg_total, 0)} %" if kg_total else "—",
                  border=True, help="Porcentaje de los kilos cosechados")

        # dos medidas de distinta escala: dos gráficos, no doble eje
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Kilos por semana**")
            fig = go.Figure(go.Scatter(x=por_semana["rotulo"], y=por_semana["kg"], mode="lines+markers",
                                       line=dict(color=g.SERIES[0], width=2, dash="dash"),
                                       marker=dict(symbol="diamond", size=9), name="kg",
                                       hovertemplate="%{y:,.0f} kg<extra></extra>"))
            g.mostrar(g.tema(fig, alto=300, titulo_y="kg").update_layout(showlegend=False), key="r1_plat_kg")
        with c2:
            st.markdown("**Racimos por semana**")
            fig = go.Figure(go.Scatter(x=por_semana["rotulo"], y=por_semana["racimos"], mode="lines+markers",
                                       line=dict(color=g.SERIES[1], width=2, dash="dash"),
                                       marker=dict(symbol="diamond", size=9), name="racimos",
                                       hovertemplate="%{y:,.0f} racimos<extra></extra>"))
            g.mostrar(g.tema(fig, alto=300, titulo_y="racimos").update_layout(showlegend=False), key="r1_plat_rac")

        if not cosechas.empty:
            st.markdown("**Primera vs. segunda calidad por semana (kg)**")
            cosechas["semana"] = cosechas["fecha"].map(lambda f: ui.semana_iso(ui.a_fecha(f)))
            cal = cosechas.pivot_table(index="semana", columns="calidad", values="kg", aggfunc="sum", fill_value=0)
            fig = go.Figure()
            for calidad, color in (("primera", g.SERIES[0]), ("segunda", g.SERIES[1])):
                if calidad in cal:
                    pct = 100 * cal[calidad] / cal.sum(axis=1)
                    fig.add_bar(x=[f"S{int(s[6:])}" for s in cal.index], y=cal[calidad], name=calidad.capitalize(),
                                marker_color=color, customdata=pct,
                                hovertemplate="%{y:,.0f} kg (%{customdata:.0f} %)")
            fig.update_layout(barmode="stack")
            g.mostrar(g.tema(fig, alto=320, titulo_y="kg"), key="r1_plat_cal")

        with st.expander("Ver el plátano por semana (tabla)"):
            ui.tabla(pd.DataFrame({"Semana": por_semana["semana"].map(ui.rotulo_semana), "Kg": por_semana["kg"],
                                   "Racimos": por_semana["racimos"], "Cosechas": por_semana["cosechas"]}),
                     kilos=["Kg"], cifras=["Racimos", "Cosechas"])
