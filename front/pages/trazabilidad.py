"""Administrador: trazabilidad (auditoría de correcciones) y Excel consolidado de la semana."""

import pandas as pd
import streamlit as st

import api
import ui

COLECCIONES = {None: "Todas", "labor_diaria": "Labor diaria", "lotes": "Lotes", "labores": "Labores",
               "trabajadores": "Trabajadores", "insumos": "Insumos", "venta_cafe": "Venta de café",
               "venta_platano": "Venta de plátano", "compra_insumo": "Compra de insumos", "gasto": "Gastos",
               "movimiento_caja": "Caja", "cosecha_platano": "Cosecha de plátano", "lluvia": "Lluvia",
               "pool_semana": "Pool", "usuarios": "Usuarios"}

st.title("Trazabilidad y Excel")

# ── Excel consolidado ──
st.subheader("Excel consolidado")
e1, e2 = st.columns([1, 1], vertical_alignment="bottom")
semana = ui.elegir_semana(key="excel_semana", donde=e1)


ui.boton_excel(semana, donde=e2)
st.caption("Ingresos vs. egresos por semana del año hasta la semana elegida, con el detalle diario y la nómina de esa semana.")

# ── auditoría ──
st.subheader("Auditoría de correcciones")
f1, f2, f3 = st.columns(3)
coleccion = f1.selectbox("Registro", list(COLECCIONES), format_func=COLECCIONES.get, key="aud_coleccion")
usuario = f2.text_input("Usuario", key="aud_usuario", placeholder="Todos")
limite = f3.selectbox("Mostrar", [100, 300, 1000], format_func=lambda n: f"Últimas {n}", key="aud_limite")
filas = ui.leer(lambda: api.get("/auditoria", coleccion=coleccion, usuario=usuario.strip() or None, limite=limite))


def texto(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return ui.numero(v, 2).removesuffix(",00")
    return str(v)


if filas:
    st.dataframe(pd.DataFrame([{
        "Fecha": ui.fecha_hora(f["fecha"]), "Usuario": f["usuario"],
        "Registro": COLECCIONES.get(f["coleccion"], f["coleccion"]), "Campo": f["campo"],
        "Antes": texto(f["valor_anterior"]), "Después": texto(f["valor_nuevo"]), "Id": f["documento_id"],
    } for f in filas]), hide_index=True)
    st.caption(f"{len(filas)} correcciones, más recientes primero.")
else:
    ui.sin_datos("Sin correcciones registradas con esos filtros.")
