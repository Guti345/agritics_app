"""R2 · Flujo de caja (solo lectura). El capital (aportes, retiros y ajustes) va SIEMPRE
aparte: nunca entra al margen."""

from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import api
import graficos as g
import ui

TIPOS = {"ingreso": "Ingreso", "egreso": "Egreso", "capital": "Capital"}

st.title("Flujo de caja")
hoy = ui.hoy()
f1, f2, _ = st.columns(3)
desde = f1.date_input("Desde", value=date(hoy.year, 1, 1), max_value=hoy, format="DD/MM/YYYY", key="r2_desde")
hasta = f2.date_input("Hasta", value=hoy, max_value=hoy, format="DD/MM/YYYY", key="r2_hasta")
if desde > hasta:
    st.error("La fecha «Desde» debe ser anterior a «Hasta»", icon=":material/error:")
    st.stop()
r2 = ui.leer(lambda: api.get("/reportes/r2-flujo-caja", desde=desde, hasta=hasta, detalle=True))
st.caption(f"Finca Portugal · del {ui.fecha_corta(desde)} al {ui.fecha_corta(hasta)} · cifras en COP")
for texto in r2["advertencias"]:
    st.warning(texto, icon=":material/warning:")

total = r2["total"]
m1, m2, m3, m4 = st.columns(4)
m1.metric("Saldo inicial", ui.pesos(r2["saldo_inicial"]), border=True)
ingresos_rango = total["ingresos"]["total"]
operativo = f"{ui.numero(100 * total['margen'] / ingresos_rango, 1)} %" if ingresos_rango else "—"   # margen / ingresos
m2.metric(f"Margen de la finca ({operativo} operativo)", ui.pesos(total["margen"]), border=True,
          help=f"Lo que deja la finca en el rango: ingresos − gastos ({ui.pesos(ingresos_rango)} − "
               f"{ui.pesos(total['gastos']['total'])}). Margen operativo = margen / ingresos. "
               "El capital no entra al margen.")
m3.metric("Capital neto (aparte)", ui.pesos(total["capital"]["neto"]), border=True,
          help=f"Aportes {ui.pesos(total['capital']['aportes'])}, retiros {ui.pesos(total['capital']['retiros'])}, "
               f"ajustes {ui.pesos(total['capital']['ajustes'])}")
m4.metric("Saldo final", ui.pesos(r2["saldo_final"]), border=True)

# ── (a) ingresos vs. gastos por semana, margen y capital aparte ──
st.subheader("Ingresos vs. gastos por semana")
semanas = r2["semanas"]
if semanas:
    x = [f"S{int(s['periodo'][6:])}" if "-W" in s["periodo"] else s["periodo"] for s in semanas]
    rotulos = [ui.rotulo_semana(s["periodo"]) if "-W" in s["periodo"] else s["periodo"] for s in semanas]
    fig = go.Figure()
    # Barras suavizadas (opacidad) para que resalten las líneas de margen y de capital.
    fig.add_bar(x=x, y=[s["ingresos"]["total"] for s in semanas], name="Ingresos", marker_color=g.SERIES[1],
                marker_opacity=0.35, customdata=rotulos, hovertemplate="Ingresos $%{y:,.0f}")
    fig.add_bar(x=x, y=[s["gastos"]["total"] for s in semanas], name="Gastos", marker_color=g.SERIES[2],
                marker_opacity=0.35, hovertemplate="Gastos $%{y:,.0f}")
    fig.add_scatter(x=x, y=[s["margen"] for s in semanas], name="Margen (ingresos − gastos)", mode="lines+markers",
                    line=dict(color=g.TINTA, width=2), marker=dict(size=8),
                    hovertemplate="Margen $%{y:,.0f}")
    fig.add_scatter(x=x, y=[s["capital"]["neto"] for s in semanas], name="Capital: aportes, retiros y ajustes (aparte)",
                    mode="lines+markers", line=dict(color=g.SERIES[3], width=2, dash="dash"),
                    marker=dict(size=8, symbol="diamond"), hovertemplate="Capital $%{y:,.0f}")
    fig.update_layout(barmode="group")
    fig.update_yaxes(tickformat="$,.0f")   # -$5.000.000 (signo antes del $)
    g.mostrar(g.tema(fig, alto=430, titulo_y="COP por semana"), key="r2_semanas")
    st.caption("El capital va en su propia línea: los aportes de la familia no son ingresos y nunca suman al margen.")

# ── (b) flujo en formato largo ──
st.subheader("Flujo de caja detallado")
b1, b2 = st.columns([2, 1], vertical_alignment="bottom")
vista = b1.segmented_control("Ver por", ["Día", "Semana", "Mes"], default="Semana", required=True, key="r2_vista")
b2.metric("Saldo de caja al cierre", ui.pesos(r2["saldo_final"]), border=True)

if vista == "Día":
    detalle = r2["detalle"]
    if not detalle:
        ui.sin_datos()
    else:
        filas = [{"Fecha": ui.fecha_corta(ui.a_fecha(l["fecha"])), "Tipo": TIPOS.get(l["tipo"], l["tipo"]),
                  "Categoría": l["categoria"].replace("_", " ").capitalize(), "Descripción": l["descripcion"],
                  "Valor": l["valor"], "Saldo": l["saldo"]} for l in detalle]
        ingresos = sum(l["valor"] for l in detalle if l["tipo"] == "ingreso")
        egresos = sum(l["valor"] for l in detalle if l["tipo"] == "egreso")
        capital = sum(l["valor"] for l in detalle if l["tipo"] == "capital")
        filas += [{"Fecha": "TOTAL", "Tipo": "Ingresos", "Categoría": "", "Descripción": "", "Valor": ingresos, "Saldo": None},
                  {"Fecha": "TOTAL", "Tipo": "Egresos", "Categoría": "", "Descripción": "", "Valor": egresos, "Saldo": None},
                  {"Fecha": "TOTAL", "Tipo": "Margen", "Categoría": "", "Descripción": "ingresos − egresos",
                   "Valor": ingresos + egresos, "Saldo": None},
                  {"Fecha": "TOTAL", "Tipo": "Capital", "Categoría": "", "Descripción": "aparte del margen",
                   "Valor": capital, "Saldo": r2["saldo_final"]}]
        ui.tabla(pd.DataFrame(filas), dinero=["Valor", "Saldo"], height=520)
        st.caption(f"{len(detalle)} movimientos. Cada línea muestra el saldo de caja después de ese movimiento.")
else:
    periodos = r2["semanas"] if vista == "Semana" else r2["meses"]
    saldo = r2["saldo_inicial"]
    filas = []
    for p in periodos + [total]:
        es_total = p is total
        if not es_total:
            saldo += p["flujo_neto"]
        etiqueta = "TOTAL" if es_total else (ui.rotulo_semana(p["periodo"]) if vista == "Semana" else
                                             f"{g.MESES[ui.a_fecha(p['desde']).month - 1]} {ui.a_fecha(p['desde']).year}")
        gastos = p["gastos"]
        filas.append({
            "Periodo": etiqueta, "Café": p["ingresos"]["cafe"], "Plátano": p["ingresos"]["platano"],
            "Ingresos": p["ingresos"]["total"], "Nómina": gastos["nomina"], "Insumos": gastos["insumos"],
            "Servicios": gastos["servicios"], "Transporte": gastos["transporte"], "Casa": gastos["casa"],
            "Otros": gastos["otros"], "Nómina por fuera": gastos["nomina_registrada_como_gasto"],
            "Gastos": gastos["total"],
            "Margen": p["margen"], "Capital (aparte)": p["capital"]["neto"], "Flujo neto": p["flujo_neto"],
            "Saldo": r2["saldo_final"] if es_total else saldo,
        })
    if not any(f["Nómina por fuera"] for f in filas):      # columna solo si hubo pagos de nómina como gasto
        for f in filas:
            del f["Nómina por fuera"]
    columnas = [c for c in filas[0] if c != "Periodo"]
    ui.tabla(pd.DataFrame(filas), dinero=columnas, height=520)
    st.caption("Saldo = saldo inicial + flujo neto acumulado (margen + capital).")
