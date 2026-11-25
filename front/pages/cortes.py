"""Administrador: pagar nómina. SIEMPRE se ve lo que se va a pagar antes de pagar.

Por dentro, cada pago es un «corte» de la API (POST /cortes): cierra el periodo abierto de la
semana (del día siguiente al último pago, o el lunes, hasta `hasta`) y paga jornales
completados + contratos completados (pactado menos anticipos) + los anticipos nuevos que se
marquen aquí. Pago selectivo: solo a los trabajadores marcados (trabajador_ids); los demás
quedan pendientes y se pagan en un pago posterior. En pantalla nunca se dice «corte».
"""

from datetime import timedelta

import pandas as pd
import streamlit as st

import api
import ui


sin_corte = ui.sin_corte      # los textos de la API dicen «corte»; en pantalla se dice «pago»


st.title("Pagar nómina")
c1, _ = st.columns([1, 2])
semana = ui.elegir_semana(key="cortes_semana", donde=c1)
preview = ui.leer(lambda: api.get(f"/cortes/preview/{semana}"))
dias = ui.dias_de(semana)
periodo = preview["periodo_abierto"]
pagos = preview["cortes"]
# Sin periodo abierto: o la semana quedó pagada hasta el domingo, o ya se pagó hasta hoy y el
# periodo sigue mañana (la API no abre periodos con días futuros), o la semana no ha empezado.
siguiente = (ui.a_fecha(pagos[-1]["hasta"]) + timedelta(days=1)) if pagos else dias[0]
if periodo is not None:
    estado_periodo = f"{ui.dia_corto(ui.a_fecha(periodo['desde']))} – {ui.dia_corto(ui.a_fecha(periodo['hasta']))}"
elif siguiente > dias[-1]:
    estado_periodo = "Semana pagada completa"
else:
    estado_periodo = f"Sigue el {ui.dia_corto(siguiente)}"

# ── periodo abierto ──
st.caption(f"Finca Portugal · {ui.rotulo_semana(semana)} · cifras en COP")
p1, p2, p3 = st.columns(3)
with p1:
    ui.cifra_grande("Periodo por pagar", estado_periodo)
with p2:
    ui.cifra_grande("Nómina pendiente", ui.pesos(preview["total_periodo_abierto"]), "labores completadas sin pagar")
with p3:
    ui.cifra_grande("Pagos hechos en la semana", str(len(pagos)), f"{len(preview['pool_activo'])} trabajadores en el pool")

# ── pagos ya hechos ──
st.subheader("Pagos ya hechos")
if pagos:
    ui.tabla(pd.DataFrame([{
        "Pago n.º": c["corte"],
        "Desde": ui.dia_corto(ui.a_fecha(c["desde"])),
        "Hasta": ui.dia_corto(ui.a_fecha(c["hasta"])),
        "Pagado por": c["cerrada_por"],
        "Fecha": ui.fecha_hora(c["fecha"]),
        "Labores": c["total_labores"],
        "Anticipos": c["total_anticipos"],
        "Total pagado": c["total"],
    } for c in pagos]), dinero=["Labores", "Anticipos", "Total pagado"])
else:
    ui.sin_datos("Todavía no hay pagos de nómina en esta semana.")

# ── nómina pendiente, con la selección de a quién pagar ──
st.subheader("Nómina pendiente: a quién se le paga")
filas = preview["nomina_periodo_abierto"]
clave_sel = f"pagar_sel_{semana}_{periodo['desde'] if periodo else 'sin'}_{len(pagos)}"   # nueva tras cada pago
seleccion = []
if filas:
    editor = st.data_editor(
        pd.DataFrame([{
            "Pagar": True, "Trabajador": f["nombre"], "Jornales": ui.numero(f["jornal"]["jornales"], 1).removesuffix(",0"),
            "A jornal": ui.pesos(f["jornal"]["valor"]), "Contratos (pactado)": ui.pesos(f["contrato"]["pactado"]),
            "Anticipos descontados": ui.pesos(f["contrato"]["anticipos_descontados"]),
            "A contrato": ui.pesos(f["contrato"]["valor"]), "Total": ui.pesos(f["total"]),
        } for f in filas]),
        hide_index=True, key=clave_sel, disabled=[c for c in ("Trabajador", "Jornales", "A jornal", "Contratos (pactado)",
                                                               "Anticipos descontados", "A contrato", "Total")],
        column_config={"Pagar": st.column_config.CheckboxColumn("Pagar", help="Desmarca a quien no se le paga ahora"),
                       **{c: st.column_config.TextColumn(c, alignment="right")
                          for c in ("Jornales", "A jornal", "Contratos (pactado)", "Anticipos descontados", "A contrato",
                                    "Total")}})
    seleccion = [f for f, marcado in zip(filas, editor["Pagar"]) if marcado]
    pendientes = [f for f in filas if f not in seleccion]
    st.markdown(f"**A pagar: {ui.pesos(sum(f['total'] for f in seleccion))} a {len(seleccion)} "
                f"{'trabajador' if len(seleccion) == 1 else 'trabajadores'}**"
                + (f" · quedan pendientes {len(pendientes)} por {ui.pesos(sum(f['total'] for f in pendientes))}"
                   if pendientes else ""))
    st.caption("Todos vienen marcados. Desmarca a quien no se le paga ahora: sus labores siguen pendientes y se "
               "pagan en un pago posterior.")
else:
    pendientes = []
    ui.sin_datos("No hay labores completadas por pagar.")

# ── labores abiertas (su estimado NO entra al pago) ──
st.subheader("Labores abiertas")
if preview["labores_abiertas"]:
    if preview["advertencia_abiertas"]:
        st.warning(sin_corte(preview["advertencia_abiertas"]), icon=":material/warning:")
    ui.tabla(pd.DataFrame([{
        "Día": ui.dia_corto(ui.a_fecha(l["fecha"])),
        "Trabajador": l["trabajador"],
        "Labor": l["labor"],
        "Lote": l["lote"],
        "Forma de pago": l["forma_pago"],
        "Jornales": l["jornales"],
        "Estimado": l["estimado"],
        "Anticipos": l["anticipos"],
    } for l in preview["labores_abiertas"]]), dinero=["Estimado", "Anticipos"], cifras=["Jornales"])
else:
    ui.sin_datos("No hay labores abiertas en la semana.")

# ── anticipos opcionales sobre contratos abiertos ──
st.subheader("Anticipos en este pago (opcional)")
anticipos, errores = [], []
if not preview["contratos_abiertos"]:
    ui.sin_datos("No hay contratos abiertos a los que se les pueda adelantar.")
for c in preview["contratos_abiertos"]:
    with st.container(border=True):
        a1, a2, a3 = st.columns([3, 1, 1.5], vertical_alignment="center")
        a1.markdown(f"**{c['trabajador']}** · {c['labor']} · desde {ui.dia_corto(ui.a_fecha(c['fecha']))}  \n"
                    f"Pactado {ui.pesos(c['pactado'])} · ya adelantado {ui.pesos(c['anticipos'])} · "
                    f"**se puede adelantar hasta {ui.pesos(c['saldo_adelantable'])}**")
        marcar = a2.checkbox("Adelantar", key=f"ant_si_{c['id']}", disabled=c["saldo_adelantable"] <= 0)
        valor = a3.number_input("Valor del anticipo", min_value=0, step=10000, value=None, placeholder="$",
                                key=f"ant_valor_{c['id']}", disabled=not marcar)
        if marcar:
            if not valor:
                errores.append(f"Escribe el valor del anticipo de {c['trabajador']}")
            elif valor > c["saldo_adelantable"]:
                errores.append(f"El anticipo de {c['trabajador']} ({ui.pesos(valor)}) supera lo que se puede "
                               f"adelantar ({ui.pesos(c['saldo_adelantable'])})")
            else:
                anticipos.append({"labor_diaria_id": c["id"], "valor": valor, "trabajador": c["trabajador"]})
for e in errores:
    st.error(e, icon=":material/error:")

# ── pagar ──
st.subheader("Pagar nómina")
if periodo is None:
    if siguiente > dias[-1]:
        st.info("La nómina de esta semana ya quedó pagada completa." + (
            " Las labores que siguen pendientes se pagan en el pago de una semana siguiente." if filas else ""),
            icon=":material/task_alt:")
    elif pagos:
        st.info(f"Ya se pagó hasta el {ui.dia_corto(siguiente - timedelta(days=1))}. El próximo pago se puede hacer "
                f"desde el {ui.dia_corto(siguiente)}" + (" e incluye a los que quedaron pendientes." if filas else "."),
                icon=":material/schedule:")
    else:
        st.info("La semana todavía no empieza: no hay días por pagar.", icon=":material/schedule:")
else:
    desde = ui.a_fecha(periodo["desde"])
    tope = min(dias[-1], ui.hoy())               # por defecto hoy, o el domingo si la semana ya pasó
    if tope < desde:
        st.info("El periodo por pagar empieza después de hoy: todavía no hay días por pagar.",
                icon=":material/schedule:")
    else:
        hasta = st.date_input("Pagar hasta", value=tope, min_value=desde, max_value=tope,
                              format="DD/MM/YYYY", key=f"corte_hasta_{semana}")
        total_anticipos = sum(a["valor"] for a in anticipos)
        total_sel = sum(f["total"] for f in seleccion)
        st.warning(
            f"Vas a pagar la nómina del {ui.dia_corto(desde)} al {ui.dia_corto(hasta)}: {ui.pesos(total_sel)} a "
            f"{len(seleccion)} {'trabajador' if len(seleccion) == 1 else 'trabajadores'}"
            + (f" (quedan {len(pendientes)} pendientes)" if pendientes else "")
            + (f" más {len(anticipos)} anticipos por {ui.pesos(total_anticipos)}" if anticipos else "")
            + ". Esos días quedan cerrados para todos: el pago no se deshace y, después, solo el administrador puede "
              "registrar o corregir en ellos. Los que no se paguen ahora se pagan en el próximo pago.",
            icon=":material/warning:")
        confirmo = st.checkbox("Revisé la nómina y quiero pagarla", key=f"corte_confirmo_{semana}")
        nada = not seleccion and not anticipos
        if nada and filas:
            st.caption("Marca al menos un trabajador (o un anticipo) para poder pagar.")
        if st.button("Pagar nómina", type="primary", icon=":material/payments:",
                     disabled=not confirmo or bool(errores) or nada):
            def pagar():
                datos = {"semana": semana, "hasta": hasta,
                         "anticipos": [{"labor_diaria_id": a["labor_diaria_id"], "valor": a["valor"]} for a in anticipos]}
                if pendientes:          # pago selectivo: solo los marcados (y a quien se le adelanta)
                    ids = [f["trabajador_id"] for f in seleccion]
                    for a in anticipos:
                        tid = api.get(f"/labores-diarias/{a['labor_diaria_id']}")["trabajador_id"]
                        if tid not in ids:
                            ids.append(tid)
                    datos["trabajador_ids"] = ids
                try:
                    return api.post("/cortes", datos)
                except api.ErrorApi as e:
                    raise api.ErrorApi(e.estado, sin_corte(e.detalle)) from None

            def aviso(r: dict) -> str:
                pagados = len(r["nomina"])
                texto = (f"Nómina pagada del {ui.dia_corto(desde)} al {ui.dia_corto(hasta)}: {ui.pesos(r['total'])} a "
                         f"{pagados} {'trabajador' if pagados == 1 else 'trabajadores'}")
                if r["total_anticipos"]:
                    texto += f" (incluye {ui.pesos(r['total_anticipos'])} en anticipos)"
                if pendientes:
                    texto += (f". Quedan pendientes {len(pendientes)} "
                              f"{'trabajador' if len(pendientes) == 1 else 'trabajadores'} por "
                              f"{ui.pesos(sum(f['total'] for f in pendientes))}: se pagan en el próximo pago")
                return texto + "."
            limpiar = [f"corte_confirmo_{semana}", f"corte_hasta_{semana}"] + \
                      [f"ant_{k}_{c['id']}" for c in preview["contratos_abiertos"] for k in ("si", "valor")]
            ui.enviar(pagar, limpiar=limpiar, refrescar=True, exito=aviso)

# ── la semana ──
with st.expander("La semana: pool, ventas, gastos, cuadres y alertas"):
    s1, s2, s3 = st.columns(3)
    vc, vp, g = preview["ventas_cafe"], preview["ventas_platano"], preview["gastos"]
    s1.metric("Ventas de café", ui.pesos(vc["valor"]), help=f"{vc['registros']} recibos · {ui.kg(vc['kg'] or 0)}",
              border=True)
    s2.metric("Ventas de plátano", ui.pesos(vp["valor"]), help=f"{vp['registros']} ventas · {ui.kg(vp['kg'] or 0)}",
              border=True)
    s3.metric("Gastos", ui.pesos(g["valor"]), help=f"{g['registros']} registros", border=True)
    q = preview["cuadres"]
    st.markdown(
        f"**Cuadres:** jornales registrados {ui.numero(q['jornales_registrados'], 1).removesuffix(',0')} · "
        f"en nómina {ui.numero(q['jornales_en_nomina'], 1).removesuffix(',0')} · cereza recogida "
        f"{ui.kg(q['kg_cereza_recogidos'])} · café vendido {ui.kg(q['kg_cafe_vendidos'])} · relación "
        f"cereza/pergamino {'—' if q['relacion_cereza_pergamino'] is None else ui.numero(q['relacion_cereza_pergamino'], 2)}")
    st.markdown("**Pool activo:** " + (", ".join(t["nombre"] for t in preview["pool_activo"]) or "nadie"))
    for texto in preview["alertas"]:
        st.warning(sin_corte(texto), icon=":material/warning:")
