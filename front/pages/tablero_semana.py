"""Administrador: la semana en finca. Métricas de la semana y alertas (cuadres, insumos)."""

from datetime import timedelta

import pandas as pd
import streamlit as st

import api
import ui

st.title("La semana en finca")
c1, _ = st.columns([1, 2])
semana = ui.elegir_semana(key="tablero_semana", donde=c1)
dias = ui.dias_de(semana)
lunes, hasta = dias[0], min(dias[-1], ui.hoy())      # semana en curso: del lunes a hoy
en_curso = semana == ui.semana_iso()

alertas = ui.leer(lambda: api.get("/reportes/alertas", semana=semana))
crono = ui.leer(lambda: api.get("/reportes/cronograma", semana=semana))
pool = ui.leer(lambda: api.get("/pool", semana=semana, activo=True))
lluvia = ui.leer(lambda: api.get("/lluvia", desde=lunes, hasta=hasta)) if hasta >= lunes else []
cosechas = ui.leer(lambda: api.get("/cosechas-platano", desde=lunes, hasta=hasta)) if hasta >= lunes else []
ventas_platano = ui.leer(lambda: api.get("/ventas-platano", desde=lunes, hasta=hasta)) if hasta >= lunes else []
cuadres = alertas["cuadres"]

st.caption(f"Finca Portugal · {ui.rotulo_semana(semana)}"
           + (f" · del lunes a hoy ({ui.dia_corto(hasta)})" if en_curso else ""))

# ── producción y clima ──
st.subheader("Producción y lluvia")
m = st.columns(5)
mm = sum(x["mm"] for x in lluvia)
m[0].metric("Lluvia acumulada", f"{ui.numero(mm, 1).removesuffix(',0')} mm" if lluvia else "Sin registro",
            help=f"{len(lluvia)} lecturas del pluviómetro", border=True)
m[1].metric("Café cereza recogido", ui.kg(cuadres["kg_cereza_recogidos"], 0), border=True,
            help="Avance en kg de las labores de café completadas en la semana")
m[2].metric("Café vendido", ui.kg(cuadres["kg_cafe_vendidos"], 0), border=True,
            help=f"Kilos netos de los recibos de la semana; equivalen a "
                 f"{ui.kg(cuadres['kg_pergamino_equivalente_vendidos'])} de pergamino")
m[3].metric("Plátano cosechado", ui.kg(sum(c["kg"] for c in cosechas), 0), border=True,
            help=f"{sum(c['racimos'] for c in cosechas)} racimos")
m[4].metric("Plátano vendido", ui.kg(sum(v["kg"] for v in ventas_platano), 0), border=True)

# ── labores y gente ──
st.subheader("Labores y trabajadores")
pct = crono["cumplimiento_pct"]
k = st.columns(4)
k[0].metric("Labores planeadas", crono["planeadas"], border=True, help="Preasignaciones del pool")
k[1].metric("Labores registradas", crono["reales"], border=True)
k[2].metric("Cumplimiento", "Sin planeadas" if pct is None else f"{ui.numero(pct, 0)} %", border=True,
            help=f"{crono['planeadas_cumplidas']} de {crono['planeadas']} planeadas se registraron")
k[3].metric("Trabajadores activos", len(pool), border=True)

# ── alertas ──
st.subheader("Alertas")
if not alertas["alertas"] and not alertas["insumos_bajo_umbral"]:
    st.success("Sin alertas esta semana.", icon=":material/check_circle:")
for texto in alertas["alertas"]:            # tal cual las da la API («corte» se lee «pago»)
    st.warning(ui.sin_corte(texto), icon=":material/warning:")
if alertas["insumos_bajo_umbral"]:
    st.markdown("**Revisar existencias**")
    cant = lambda v: ui.numero(v, 2).removesuffix(",00").removesuffix("0") if v % 1 else ui.numero(v)  # noqa: E731
    st.dataframe(pd.DataFrame([{
        "Insumo": i["nombre"], "Quedan": f"{cant(i['stock_actual'])} {i['unidad']}",
        "Umbral": f"{cant(i['umbral_alerta'])} {i['unidad']}", "Faltante": f"{cant(i['faltante'])} {i['unidad']}",
    } for i in alertas["insumos_bajo_umbral"]]), hide_index=True,
        column_config={c: st.column_config.TextColumn(c, alignment="right") for c in ("Quedan", "Umbral", "Faltante")})

st.markdown("**Cuadres de la semana**")
q1, q2, q3 = st.columns(3)
q1.metric("Jornales registrados / en nómina",
          f"{ui.numero(cuadres['jornales_registrados'], 1).removesuffix(',0')} / "
          f"{ui.numero(cuadres['jornales_en_nomina'], 1).removesuffix(',0')}", border=True,
          help="Jornales de labores a jornal de la semana vs. los ya pagados o listos para el próximo pago")
q2.metric("Kg cereza recogidos / vendidos",
          f"{ui.numero(cuadres['kg_cereza_recogidos'])} / {ui.numero(cuadres['kg_cafe_vendidos'])}", border=True,
          help="Recogido en labores vs. kilos netos de los recibos de la Cooperativa")
rel = cuadres["relacion_cereza_pergamino"]
q3.metric("Relación cereza / pergamino", "Sin ventas" if rel is None else ui.numero(rel, 2), border=True,
          help="Kg de cereza recogidos por cada kg de pergamino equivalente vendido")
st.caption(f"Fuente: registros de la {ui.rotulo_semana(semana)} al {ui.fecha_corta(hasta if hasta >= lunes else lunes - timedelta(days=1))}.")
