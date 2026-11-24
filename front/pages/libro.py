"""Administrador: libro de la finca. Ventas de café y plátano, compras de insumos y gastos,
cada uno con su formulario corto y los registros de la semana elegida."""

from datetime import timedelta

import pandas as pd
import streamlit as st

import api
import ui

PRODUCTOS = {"pergamino": "Pergamino", "mojado": "Mojado", "pasilla": "Pasilla"}
CATEGORIAS = {"insumos": "Insumos", "servicios": "Servicios", "transporte": "Transporte", "casa": "Casa",
              "otros": "Otros", "nomina": "Nómina (pagos por fuera de la semanal)"}


def faltante(*pares) -> str | None:
    """Primer mensaje cuyo campo falta (para no mandar a la API campos vacíos)."""
    return next((m for falta, m in pares if falta), None)


st.title("Ventas, compras y gastos")
c1, _ = st.columns([1, 2])
semana = ui.elegir_semana("Semana del libro", key="libro_semana", donde=c1)
dias = ui.dias_de(semana)
rango = {"desde": dias[0], "hasta": dias[-1]}

cafe_tab, platano_tab, compra_tab, gasto_tab = st.tabs(
    [":material/coffee: Venta de café", ":material/nutrition: Venta de plátano",
     ":material/inventory_2: Compra de insumos", ":material/receipt_long: Gastos"], key="libro_tab")

# ═══ VENTA DE CAFÉ (recibo de la Cooperativa) ══════════════════════════════════
with cafe_tab:
    st.caption("Todos los campos del recibo de la Cooperativa. La foto del recibo es obligatoria.")
    a, b, c = st.columns(3)
    fecha = a.date_input("Fecha", value=ui.hoy(), max_value=ui.hoy(), format="DD/MM/YYYY", key="vc_fecha")
    almacen = b.text_input("Almacén", key="vc_almacen", placeholder="Almacén de la Cooperativa")
    producto = c.segmented_control("Producto", list(PRODUCTOS), format_func=PRODUCTOS.get, default="pergamino",
                                   required=True, key="vc_producto")
    a, b, c, d = st.columns(4)
    sacos = a.number_input("Sacos", min_value=0, step=1, value=None, key="vc_sacos")
    brutos = b.number_input("Kg brutos", min_value=0.0, step=0.1, value=None, key="vc_brutos")
    destare = c.number_input("Destare (kg)", min_value=0.0, step=0.1, value=None, placeholder="0", key="vc_destare")
    netos = round((brutos or 0) - (destare or 0), 2)
    d.metric("Kg netos (brutos − destare)", ui.kg(netos, 2) if brutos else "—")
    a, b, c, d = st.columns(4)
    pergamino = a.number_input("Kg pergamino equivalente", min_value=0.0, step=0.1, value=None, key="vc_pergamino")
    sana = b.number_input("Almendra sana (%)", min_value=0.0, max_value=100.0, step=0.1, value=None, key="vc_sana")
    pasilla = c.number_input("Pasilla (%)", min_value=0.0, max_value=100.0, step=0.1, value=None, key="vc_pasilla")
    broca = d.number_input("Broca (%)", min_value=0.0, max_value=100.0, step=0.1, value=None, key="vc_broca")
    a, b, c = st.columns(3)
    factor = a.number_input("Factor de rendimiento", min_value=0.0, step=0.1, value=None, key="vc_factor",
                            help="Kg de pergamino seco por saco de 70 kg de café. NO es porcentaje: "
                                 "en los recibos suele estar entre 88 y ~110.")
    precio = b.number_input("Precio base ($)", min_value=0, step=1000, value=None, key="vc_precio")
    valor_total = c.number_input("Valor total del recibo ($)", min_value=0, step=1000, value=None, key="vc_total")
    st.markdown("**Descuentos del recibo** (agrega una fila por concepto)")
    descuentos = st.data_editor(pd.DataFrame({"Concepto": pd.Series(dtype="str"), "Valor": pd.Series(dtype="float")}),
                                num_rows="dynamic", hide_index=True,
                                key=f"vc_descuentos_{st.session_state.get('vc_n', 0)}",  # nuevo tras guardar
                                column_config={"Valor": st.column_config.NumberColumn("Valor ($)", min_value=0,
                                                                                      step=100, format="%d")})
    lista_desc = [{"concepto": str(f["Concepto"]).strip(), "valor": float(f["Valor"])}
                  for _, f in descuentos.iterrows() if pd.notna(f["Concepto"]) and str(f["Concepto"]).strip()
                  and pd.notna(f["Valor"])]
    if lista_desc:
        st.caption(f"Descuentos: {ui.pesos(sum(x['valor'] for x in lista_desc))}")
    a, b = st.columns(2)
    pedido = a.text_input("Número de pedido (opcional)", key="vc_pedido")
    comprobante = b.text_input("Id del comprobante (opcional)", key="vc_comprobante")
    ruta = ui.foto("vc", "Foto del recibo de la Cooperativa")

    if st.button("Registrar venta de café", type="primary", icon=":material/save:", disabled=ruta is None,
                 help=None if ruta else "Adjunta la foto del recibo para poder guardar"):
        falta = faltante((not almacen.strip(), "Escribe el almacén del recibo"), (sacos is None, "Escribe los sacos"),
                         (not brutos, "Escribe los kilos brutos"),
                         (pergamino is None, "Escribe los kilos de pergamino equivalente"),
                         (None in (sana, pasilla, broca), "Completa el análisis de calidad: almendra sana, pasilla y broca"),
                         (factor is None, "Escribe el factor de rendimiento"), (not precio, "Escribe el precio base"),
                         (valor_total is None, "Escribe el valor total del recibo"))
        if falta:
            st.error(falta, icon=":material/error:")
        else:
            datos = {"fecha": fecha, "almacen": almacen, "tipo_producto": producto, "sacos": sacos,
                     "kg_brutos": brutos, "destare": destare or 0, "kg_netos": netos,
                     "kg_pergamino_equivalente": pergamino,
                     "analisis_calidad": {"almendra_sana": sana, "pasilla": pasilla, "broca": broca},
                     "factor_rendimiento": factor, "precio_base": precio, "descuentos": lista_desc,
                     "valor_total": valor_total, "numero_pedido": pedido.strip(),
                     "id_comprobante": comprobante.strip() or None, "foto_ruta": ruta}

            def vender_cafe():
                r = api.post("/ventas-cafe", datos)
                ui.foto_nueva("vc")
                return r
            ui.enviar(vender_cafe, exito=f"Registro guardado: venta de café por {ui.pesos(valor_total)}",
                      limpiar=["vc_almacen", "vc_sacos", "vc_brutos", "vc_destare", "vc_pergamino", "vc_sana",
                               "vc_pasilla", "vc_broca", "vc_factor", "vc_precio", "vc_total",
                               "vc_pedido", "vc_comprobante"])

    st.subheader("Recibos de la semana")
    ventas = ui.leer(lambda: api.get("/ventas-cafe", **rango))
    if ventas:
        ui.tabla(pd.DataFrame([{
            "Fecha": ui.dia_corto(ui.a_fecha(v["fecha"])), "Almacén": v["almacen"],
            "Producto": PRODUCTOS[v["tipo_producto"]], "Sacos": v["sacos"], "Kg netos": v["kg_netos"],
            "Pergamino eq.": v["kg_pergamino_equivalente"], "Factor": v["factor_rendimiento"],
            "Valor total": v["valor_total"]} for v in ventas]),
            dinero=["Valor total"], kilos=["Kg netos", "Pergamino eq."], cifras=["Factor"])
        st.caption(f"Total de la semana: {ui.pesos(sum(v['valor_total'] for v in ventas))}")
    else:
        ui.sin_datos("Sin recibos de café en esta semana.")

# ═══ VENTA DE PLÁTANO ══════════════════════════════════════════════════════════
with platano_tab:
    a, b = st.columns(2)
    fecha_p = a.date_input("Fecha", value=ui.hoy(), max_value=ui.hoy(), format="DD/MM/YYYY", key="vp_fecha")
    comprador = b.text_input("Comprador", key="vp_comprador")
    a, b, c = st.columns(3)
    kg_p = a.number_input("Kilos", min_value=0.0, step=1.0, value=None, key="vp_kg")
    racimos = b.number_input("Racimos", min_value=0, step=1, value=None, key="vp_racimos")
    calidad = c.radio("Calidad", ["primera", "segunda"], format_func=str.capitalize, horizontal=True,
                      key="vp_calidad")
    a, b = st.columns(2)
    precio_kg = a.number_input("Precio por kilo ($)", min_value=0, step=50, value=None, key="vp_precio")
    total_p = round((kg_p or 0) * (precio_kg or 0))
    b.metric("Valor total (kilos × precio)", ui.pesos(total_p) if kg_p and precio_kg else "—")
    cosechas = ui.leer(lambda: api.get("/cosechas-platano", desde=ui.hoy() - timedelta(days=30), hasta=ui.hoy()))
    lotes = ui.leer(lambda: api.por_id("/lotes"))
    cosecha = st.selectbox(
        "Cosecha que se vende (opcional)", cosechas, index=None, key="vp_cosecha", placeholder="Sin cosecha asociada",
        format_func=lambda x: f"{ui.dia_corto(ui.a_fecha(x['fecha']))} · "
                              f"{lotes.get(x['lote_id'], {}).get('nombre', '?')} · {ui.kg(x['kg'])} · {x['calidad']}")
    if st.button("Registrar venta de plátano", type="primary", icon=":material/save:"):
        falta = faltante((not comprador.strip(), "Escribe el comprador"), (not kg_p, "Escribe cuántos kilos vendiste"),
                         (not racimos, "Escribe cuántos racimos vendiste"), (not precio_kg, "Escribe el precio por kilo"))
        if falta:
            st.error(falta, icon=":material/error:")
        else:
            ui.enviar(lambda: api.post("/ventas-platano", {
                "fecha": fecha_p, "comprador": comprador, "kg": kg_p, "racimos": racimos, "calidad": calidad,
                "precio_kg": precio_kg, "valor_total": total_p, "cosecha_id": cosecha["id"] if cosecha else None}),
                limpiar=["vp_comprador", "vp_kg", "vp_racimos", "vp_precio", "vp_cosecha"],
                exito=f"Registro guardado: venta de plátano por {ui.pesos(total_p)}")

    st.subheader("Ventas de la semana")
    ventas_p = ui.leer(lambda: api.get("/ventas-platano", **rango))
    if ventas_p:
        ui.tabla(pd.DataFrame([{
            "Fecha": ui.dia_corto(ui.a_fecha(v["fecha"])), "Comprador": v["comprador"], "Kg": v["kg"],
            "Racimos": v["racimos"], "Calidad": v["calidad"].capitalize(), "Precio por kg": v["precio_kg"],
            "Valor total": v["valor_total"]} for v in ventas_p]),
            dinero=["Precio por kg", "Valor total"], kilos=["Kg"])
        st.caption(f"Total de la semana: {ui.pesos(sum(v['valor_total'] for v in ventas_p))}")
    else:
        ui.sin_datos("Sin ventas de plátano en esta semana.")

# ═══ COMPRA DE INSUMOS ═════════════════════════════════════════════════════════
with compra_tab:
    insumos = ui.leer(lambda: api.lista("/insumos"))
    st.caption("La compra suma sola al stock del insumo. La foto del comprobante es obligatoria.")
    a, b = st.columns(2)
    fecha_c = a.date_input("Fecha", value=ui.hoy(), max_value=ui.hoy(), format="DD/MM/YYYY", key="ci_fecha")
    insumo = b.selectbox("Insumo", insumos, index=None, key="ci_insumo", placeholder="Elige el insumo",
                         format_func=lambda i: f"{i['nombre']} ({i['unidad']})")
    a, b = st.columns(2)
    cantidad = a.number_input(f"Cantidad ({insumo['unidad']})" if insumo else "Cantidad", min_value=0.0, step=1.0,
                              value=None, key="ci_cantidad")
    valor_c = b.number_input("Valor pagado ($)", min_value=0, step=1000, value=None, key="ci_valor")
    if insumo:
        st.caption(f"Hay {ui.numero(insumo['stock_actual'], 1).removesuffix(',0')} {insumo['unidad']} en bodega.")
    ruta_c = ui.foto("ci", "Foto del comprobante de la compra")
    if st.button("Registrar compra", type="primary", icon=":material/save:", disabled=ruta_c is None,
                 help=None if ruta_c else "Adjunta la foto del comprobante para poder guardar"):
        falta = faltante((insumo is None, "Elige el insumo"), (not cantidad, "Escribe la cantidad comprada"),
                         (not valor_c, "Escribe cuánto pagaste"))
        if falta:
            st.error(falta, icon=":material/error:")
        else:
            def comprar():
                r = api.post("/compras-insumos", {"fecha": fecha_c, "insumo_id": insumo["id"], "cantidad": cantidad,
                                                  "valor": valor_c, "comprobante_ruta": ruta_c})
                ui.foto_nueva("ci")
                return r
            ui.enviar(comprar, limpiar=["ci_insumo", "ci_cantidad", "ci_valor"], refrescar=True,
                      exito=f"Registro guardado: compra de {insumo['nombre']} por {ui.pesos(valor_c)}")

    st.subheader("Compras de la semana")
    compras = ui.leer(lambda: api.get("/compras-insumos", **rango))
    if compras:
        por_id = {i["id"]: i for i in insumos}
        ui.tabla(pd.DataFrame([{
            "Fecha": ui.dia_corto(ui.a_fecha(x["fecha"])),
            "Insumo": por_id.get(x["insumo_id"], {}).get("nombre", "?"),
            "Cantidad": f"{ui.numero(x['cantidad'], 1).removesuffix(',0')} {por_id.get(x['insumo_id'], {}).get('unidad', '')}",
            "Valor": x["valor"]} for x in compras]), dinero=["Valor"])
        st.caption(f"Total de la semana: {ui.pesos(sum(x['valor'] for x in compras))}")
    else:
        ui.sin_datos("Sin compras de insumos en esta semana.")

# ═══ GASTOS ════════════════════════════════════════════════════════════════════
with gasto_tab:
    st.caption("La nómina semanal NO se registra aquí: se calcula de las labores. La categoría «Nómina» es solo "
               "para pagos por fuera de la semanal.")
    with st.form("gasto", border=False):
        a, b, c = st.columns(3)
        fecha_g = a.date_input("Fecha", value=ui.hoy(), max_value=ui.hoy(), format="DD/MM/YYYY", key="g_fecha")
        categoria = b.selectbox("Categoría", list(CATEGORIAS), format_func=CATEGORIAS.get, key="g_categoria")
        valor_g = c.number_input("Valor ($)", min_value=0, step=1000, value=None, key="g_valor")
        descripcion = st.text_input("Descripción (obligatoria en «Otros»)", key="g_descripcion")
        if st.form_submit_button("Registrar gasto", type="primary", icon=":material/save:"):
            if not valor_g:
                st.error("Escribe el valor del gasto", icon=":material/error:")
            else:
                ui.enviar(lambda: api.post("/gastos", {"fecha": fecha_g, "categoria": categoria,
                                                       "descripcion": descripcion.strip() or None, "valor": valor_g}),
                          limpiar=["g_valor", "g_descripcion"],
                          exito=f"Registro guardado: gasto de {ui.pesos(valor_g)} en {CATEGORIAS[categoria].lower()}")

    st.subheader("Gastos de la semana")
    gastos = ui.leer(lambda: api.get("/gastos", **rango))
    if gastos:
        ui.tabla(pd.DataFrame([{
            "Fecha": ui.dia_corto(ui.a_fecha(g["fecha"])), "Categoría": CATEGORIAS[g["categoria"]].split(" (")[0],
            "Descripción": g["descripcion"] or "", "Valor": g["valor"]} for g in gastos]), dinero=["Valor"])
        st.caption(f"Total de la semana: {ui.pesos(sum(g['valor'] for g in gastos))}")
    else:
        ui.sin_datos("Sin gastos en esta semana.")
