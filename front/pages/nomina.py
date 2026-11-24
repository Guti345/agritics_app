"""Administrador: nómina de la semana por trabajador (R3). La nómina no se guarda: la API
la calcula de las labores registradas."""

import pandas as pd
import streamlit as st

import api
import ui

st.title("Nómina de la semana")
c1, _ = st.columns([1, 2])
semana = ui.elegir_semana(key="nomina_semana", donde=c1)
r3 = ui.leer(lambda: api.get("/reportes/r3-nomina", semana=semana))

st.caption(f"Finca Portugal · {ui.rotulo_semana(semana)} · cifras en COP")
t1, t2, t3 = st.columns(3)
t1.metric("Total a pagar", ui.pesos(r3["total_a_pagar"]), border=True,
          help="Labores completadas, descontando los anticipos")
t2.metric("Anticipos recibidos", ui.pesos(r3["total_anticipos_recibidos"]), border=True)
t3.metric("Nómina causada", ui.pesos(r3["total_nomina_causada"]), border=True,
          help="Lo que cuesta la semana: entra al flujo de caja")

filas = r3["trabajadores"]
if not filas:
    ui.sin_datos("Sin labores registradas en esta semana.")
    st.stop()

df = pd.DataFrame([{
    "Trabajador": t["nombre"],
    "Tipo": t["tipo"].capitalize(),
    "Jornales": t["jornales"],
    "A pagar": t["total_a_pagar"],
    "Pagado en cortes": t["pagado_en_cortes"],
    "Pendiente por pagar": t["pendiente_por_pagar"],
    "Estimado abiertas": t["estimado_abiertas"],
    "Anticipos recibidos": t["total_anticipos_recibidos"],
    "Kg recolectados": t["kg_recolectados"],
    "Costo por kg": t["costo_por_kg"],
} for t in filas])
ui.tabla(df, dinero=["A pagar", "Pagado en cortes", "Pendiente por pagar", "Estimado abiertas",
                     "Anticipos recibidos", "Costo por kg"],
         kilos=["Kg recolectados"], cifras=["Jornales"])
st.caption(f"Tipo de trabajador: {r3['criterio_tipo']}. «Estimado abiertas» no entra al pago hasta completarlas.")

# ── detalle por trabajador ──
st.subheader("Labores de un trabajador")
quien = st.selectbox("Trabajador", [t["nombre"] for t in filas], index=None, placeholder="Elige el trabajador",
                     key="nomina_trabajador")
if quien:
    t = next(x for x in filas if x["nombre"] == quien)
    ui.tabla(pd.DataFrame([{
        "Día": ui.dia_corto(ui.a_fecha(l["fecha"])),
        "Lote": l["lote"],
        "Labor": l["labor"],
        "Forma de pago": l["forma_pago"],
        "Jornales": l["jornales"],
        "Tarifa": l["tarifa"],
        "Pactado": l["valor_pactado"],
        "Anticipos": l["anticipos"],
        "A pagar": l["a_pagar"],
        "Estado": l["estado"],
    } for l in t["labores"]]), dinero=["Tarifa", "Pactado", "Anticipos", "A pagar"], cifras=["Jornales"])
