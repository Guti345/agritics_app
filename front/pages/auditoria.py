"""Superusuario: auditoría global de correcciones (más recientes primero). Los filtros de
fecha, registro y usuario se aplican aquí sobre lo ya cargado."""

from datetime import timedelta

import pandas as pd
import streamlit as st

import api
import ui

COLECCIONES = {"labor_diaria": "Labor diaria", "lotes": "Lotes", "labores": "Labores",
               "trabajadores": "Trabajadores", "insumos": "Insumos", "unidades": "Unidades",
               "venta_cafe": "Venta de café", "venta_platano": "Venta de plátano", "compra_insumo": "Compra de insumos",
               "gasto": "Gastos", "movimiento_caja": "Caja", "cosecha_platano": "Cosecha de plátano",
               "lluvia": "Lluvia", "pool_semana": "Pool", "usuarios": "Usuarios", "cierres": "Cortes"}


def texto(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return ui.numero(v, 2).removesuffix(",00")
    return str(v)


st.title("Auditoría")
registros = ui.leer(lambda: api.get("/auditoria", limite=1000))
if not registros:
    ui.sin_datos("Sin correcciones registradas.")
    st.stop()

df = pd.DataFrame(registros)
df["momento"] = df["fecha"].map(ui.fecha_hora)
df["dia"] = df["fecha"].map(ui.dia_bogota)

f1, f2, f3 = st.columns(3)
minimo, maximo = df["dia"].min(), df["dia"].max()
rango = f1.date_input("Fechas", value=(max(minimo, maximo - timedelta(days=30)), maximo), min_value=minimo,
                      max_value=maximo, format="DD/MM/YYYY", key="au_rango")
colecciones = f2.multiselect("Registro", sorted(df["coleccion"].unique()), format_func=lambda c: COLECCIONES.get(c, c),
                             key="au_coleccion", placeholder="Todos")
usuarios = f3.multiselect("Usuario", sorted(df["usuario"].unique()), key="au_usuario", placeholder="Todos")

vista = df
if isinstance(rango, tuple) and len(rango) == 2:
    vista = vista[(vista["dia"] >= rango[0]) & (vista["dia"] <= rango[1])]
if colecciones:
    vista = vista[vista["coleccion"].isin(colecciones)]
if usuarios:
    vista = vista[vista["usuario"].isin(usuarios)]

st.dataframe(pd.DataFrame({
    "Fecha": vista["momento"], "Usuario": vista["usuario"],
    "Registro": vista["coleccion"].map(lambda c: COLECCIONES.get(c, c)), "Campo": vista["campo"],
    "Antes": vista["valor_anterior"].map(texto), "Después": vista["valor_nuevo"].map(texto),
    "Id del registro": vista["documento_id"],
}), hide_index=True)
st.caption(f"{len(vista)} de {len(df)} correcciones cargadas (las últimas 1.000), más recientes primero.")
