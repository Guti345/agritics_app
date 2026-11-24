"""Administrador: cortes de nómina. SIEMPRE se ve el preview antes de cortar.

Un corte cierra el periodo abierto de la semana (del día siguiente al último corte, o el
lunes, hasta `hasta`) y paga: jornales completados + contratos completados (pactado menos
anticipos) + los anticipos nuevos sobre contratos abiertos que se marquen aquí. Los cortes
se apilan dentro de la semana y el periodo abierto se corre al día siguiente.
"""

from datetime import timedelta

import pandas as pd
import streamlit as st

import api
import ui

st.title("Cortes de nómina")
c1, _ = st.columns([1, 2])
semana = ui.elegir_semana(key="cortes_semana", donde=c1)
preview = ui.leer(lambda: api.get(f"/cortes/preview/{semana}"))
dias = ui.dias_de(semana)
periodo = preview["periodo_abierto"]
# Sin periodo abierto: o la semana quedó cortada hasta el domingo, o ya se cortó hasta hoy y el
# periodo sigue mañana (la API no abre periodos con días futuros), o la semana no ha empezado.
siguiente = (ui.a_fecha(preview["cortes"][-1]["hasta"]) + timedelta(days=1)) if preview["cortes"] else dias[0]
if periodo is not None:
    estado_periodo = f"{ui.dia_corto(ui.a_fecha(periodo['desde']))} – {ui.dia_corto(ui.a_fecha(periodo['hasta']))}"
elif siguiente > dias[-1]:
    estado_periodo = "Semana cortada completa"
else:
    estado_periodo = f"Sigue el {ui.dia_corto(siguiente)}"

# ── periodo abierto ──
st.caption(f"Finca Portugal · {ui.rotulo_semana(semana)} · cifras en COP")
p1, p2, p3 = st.columns(3)
with p1:
    ui.cifra_grande("Periodo abierto", estado_periodo)
with p2:
    ui.cifra_grande("Nómina del periodo abierto", ui.pesos(preview["total_periodo_abierto"]),
                    "labores completadas sin corte")
with p3:
    ui.cifra_grande("Cortes hechos en la semana", str(len(preview["cortes"])),
                    f"{len(preview['pool_activo'])} trabajadores en el pool")

# ── cortes ya hechos (apilados) ──
st.subheader("Cortes ya hechos")
if preview["cortes"]:
    ui.tabla(pd.DataFrame([{
        "Corte": c["corte"],
        "Desde": ui.dia_corto(ui.a_fecha(c["desde"])),
        "Hasta": ui.dia_corto(ui.a_fecha(c["hasta"])),
        "Cerrado por": c["cerrada_por"],
        "Fecha": ui.fecha_hora(c["fecha"]),
        "Labores": c["total_labores"],
        "Anticipos": c["total_anticipos"],
        "Total pagado": c["total"],
    } for c in preview["cortes"]]), dinero=["Labores", "Anticipos", "Total pagado"])
else:
    ui.sin_datos("Todavía no hay cortes en esta semana.")

# ── nómina del periodo abierto ──
st.subheader("Nómina del periodo abierto")
if preview["nomina_periodo_abierto"]:
    ui.tabla(pd.DataFrame([{
        "Trabajador": f["nombre"],
        "Jornales": f["jornal"]["jornales"],
        "A jornal": f["jornal"]["valor"],
        "Contratos (pactado)": f["contrato"]["pactado"],
        "Anticipos descontados": f["contrato"]["anticipos_descontados"],
        "A contrato": f["contrato"]["valor"],
        "Anticipos": f["anticipos"]["valor"],
        "Total": f["total"],
    } for f in preview["nomina_periodo_abierto"]]),
        dinero=["A jornal", "Contratos (pactado)", "Anticipos descontados", "A contrato", "Anticipos", "Total"],
        cifras=["Jornales"])
    st.markdown(f"**Total del periodo abierto: {ui.pesos(preview['total_periodo_abierto'])}**")
else:
    ui.sin_datos("No hay labores completadas por pagar en el periodo abierto.")

# ── labores abiertas (su estimado NO entra al pago) ──
st.subheader("Labores abiertas")
if preview["labores_abiertas"]:
    if preview["advertencia_abiertas"]:
        st.warning(preview["advertencia_abiertas"], icon=":material/warning:")
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
st.subheader("Anticipos en este corte (opcional)")
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

# ── hacer corte ──
st.subheader("Hacer corte")
if periodo is None:
    if siguiente > dias[-1]:
        st.info("Esta semana ya quedó cortada completa.", icon=":material/task_alt:")
    elif preview["cortes"]:
        st.info(f"Ya se cortó hasta el {ui.dia_corto(siguiente - timedelta(days=1))}. El periodo abierto sigue "
                f"el {ui.dia_corto(siguiente)}: desde ese día se podrá hacer el siguiente corte.",
                icon=":material/schedule:")
    else:
        st.info("La semana todavía no empieza: no hay días para cortar.", icon=":material/schedule:")
else:
    desde = ui.a_fecha(periodo["desde"])
    tope = min(dias[-1], ui.hoy())               # por defecto hoy, o el domingo si la semana ya pasó
    if tope < desde:
        st.info("El periodo abierto empieza después de hoy: todavía no hay días para cortar.",
                icon=":material/schedule:")
    else:
        hasta = st.date_input("Cortar hasta", value=tope, min_value=desde, max_value=tope,
                              format="DD/MM/YYYY", key=f"corte_hasta_{semana}")
        total_anticipos = sum(a["valor"] for a in anticipos)
        st.warning(
            f"Vas a cerrar el periodo del {ui.dia_corto(desde)} al {ui.dia_corto(hasta)}. Se pagan las labores "
            f"completadas de esos días (el preview suma {ui.pesos(preview['total_periodo_abierto'])} para todo el "
            f"periodo abierto) más {len(anticipos)} anticipos por {ui.pesos(total_anticipos)}. Un corte no se "
            "deshace: después, solo el administrador puede registrar o corregir en esos días.",
            icon=":material/warning:")
        confirmo = st.checkbox("Revisé el preview y quiero hacer el corte", key=f"corte_confirmo_{semana}")
        if st.button("Hacer corte", type="primary", icon=":material/content_cut:",
                     disabled=not confirmo or bool(errores)):
            def cortar():
                return api.post("/cortes", {"semana": semana, "hasta": hasta,
                                            "anticipos": [{"labor_diaria_id": a["labor_diaria_id"], "valor": a["valor"]}
                                                          for a in anticipos]})
            limpiar = [f"corte_confirmo_{semana}", f"corte_hasta_{semana}"] + \
                      [f"ant_{k}_{c['id']}" for c in preview["contratos_abiertos"] for k in ("si", "valor")]
            ui.enviar(cortar, limpiar=limpiar, refrescar=True,
                      exito=f"Corte guardado: del {ui.dia_corto(desde)} al {ui.dia_corto(hasta)}"
                            + (f", con {len(anticipos)} anticipos por {ui.pesos(total_anticipos)}" if anticipos else ""))

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
        st.warning(texto, icon=":material/warning:")
