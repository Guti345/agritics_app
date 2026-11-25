"""Administrador: caja. Saldo con su detalle por componente, movimientos de caja (capital y
deuda: aportes, retiros, ajustes, préstamos recibidos, abonos a deuda y pago de intereses; entran
o salen de caja pero NUNCA son ingreso ni gasto operacional) y el formulario para registrarlos."""

import pandas as pd
import streamlit as st

import api
import ui

TIPOS = ui.MOVIMIENTOS_CAJA      # los 6 tipos de la API; los que salen restan (ui.SALEN_DE_CAJA)
CATEGORIAS = {"nomina": "Nómina", "insumos": "Insumos", "servicios": "Servicios", "transporte": "Transporte",
              "casa": "Casa", "otros": "Otros"}

st.title("Caja")
saldo = ui.leer(lambda: api.get("/caja/saldo"))

s1, s2 = st.columns([1, 2])
with s1:
    ui.cifra_grande("Saldo de caja", ui.pesos(saldo["saldo"]),
                    f"al {ui.fecha_corta(ui.a_fecha(saldo['hasta']))}"
                    + (f", desde el {ui.fecha_corta(ui.a_fecha(saldo['desde']))}" if saldo["desde"] else ""))
with s2:
    componentes = [
        ("Ventas de café", "ventas_cafe", 1), ("Ventas de plátano", "ventas_platano", 1),
        ("Gastos", "gastos", -1), ("Compras de insumos", "compras_insumos", -1),
        ("Nómina causada", "nomina_causada", -1),
    ]
    filas = [{"Componente": n, "Registros": saldo[c]["registros"], "Efecto en caja": signo * saldo[c]["valor"]}
             for n, c, signo in componentes]
    por_tipo = saldo["movimientos_por_tipo"]
    neto_mov = sum(ui.efecto_en_caja(t, v) for t, v in por_tipo.items())
    filas.append({"Componente": "Capital y deuda (aparte del margen)",
                  "Registros": saldo["movimientos_caja"]["registros"], "Efecto en caja": neto_mov})
    ui.tabla(pd.DataFrame(filas), dinero=["Efecto en caja"], cifras=["Registros"])
for texto in saldo["advertencias"]:
    st.warning(texto, icon=":material/warning:")

d1, d2 = st.columns(2)
with d1:
    st.markdown("**Gastos por categoría**")
    if saldo["gastos_por_categoria"]:
        ui.tabla(pd.DataFrame([{"Categoría": CATEGORIAS.get(k, k), "Valor": v}
                               for k, v in saldo["gastos_por_categoria"].items()]), dinero=["Valor"])
with d2:
    st.markdown("**Movimientos por tipo**")
    if por_tipo:
        ui.tabla(pd.DataFrame([{"Tipo": TIPOS.get(k, k), "Entra o sale": "Sale" if ui.efecto_en_caja(k, v) < 0 else "Entra",
                                "Efecto en caja": ui.efecto_en_caja(k, v)}
                               for k, v in sorted(por_tipo.items(), key=lambda x: list(TIPOS).index(x[0]) if x[0] in TIPOS else 99)]),
                 dinero=["Efecto en caja"])

# ── registrar movimiento ──
st.subheader("Registrar movimiento de caja")
st.caption("Estos movimientos entran o salen de caja pero NUNCA son ingreso ni gasto operacional de la finca: no "
           "mueven el margen. Entran: aporte de capital y préstamo recibido; salen: retiro, abono a deuda y pago de "
           "intereses. El valor va siempre en positivo (el tipo dice si entra o sale); solo un ajuste puede ser "
           "negativo. En la nota va el detalle: a quién se le debe, qué préstamo, qué cuota.")
with st.form("movimiento_caja", border=False):
    a, b, c = st.columns(3)
    fecha = a.date_input("Fecha", value=ui.hoy(), max_value=ui.hoy(), format="DD/MM/YYYY", key="mc_fecha")
    tipo = b.selectbox("Tipo", list(TIPOS), format_func=TIPOS.get, key="mc_tipo")
    valor = c.number_input("Valor ($)", step=10000, value=None, key="mc_valor")
    nota = st.text_input("Nota (detalle del movimiento)", key="mc_nota",
                         placeholder="Por ejemplo: crédito Banco Agrario n.º 123, o aporte de la familia para la nómina")
    if st.form_submit_button("Registrar movimiento", type="primary", icon=":material/save:"):
        if valor is None:
            st.error("Escribe el valor del movimiento", icon=":material/error:")
        else:
            ui.enviar(lambda: api.post("/caja/movimientos", {"fecha": fecha, "tipo": tipo, "valor": valor,
                                                             "nota": nota.strip()}),
                      limpiar=["mc_valor", "mc_nota"],
                      exito=f"Registro guardado: {TIPOS[tipo].lower()} por {ui.pesos(valor)}")

# ── movimientos ──
st.subheader("Movimientos de caja")
movimientos = ui.leer(lambda: api.get("/caja/movimientos"))
if movimientos:
    ui.tabla(pd.DataFrame([{
        "Fecha": ui.fecha_corta(ui.a_fecha(m["fecha"])), "Tipo": TIPOS.get(m["tipo"], m["tipo"]),
        "Valor": ui.efecto_en_caja(m["tipo"], m["valor"]), "Nota": m["nota"],
        "Registrado por": m.get("registrado_por", "")} for m in movimientos]), dinero=["Valor"])
else:
    ui.sin_datos("Sin movimientos de caja.")
