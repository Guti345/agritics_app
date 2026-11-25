"""Mayordomo: programación de la finca, en una hoja con dos pestañas.

- «Cronograma de la finca» (histórico, zoom día / semana / mes): el componente compartido
  cronograma_view (el administrador ve el mismo en su entrada «Cronograma»).
- «Programar»: preasignar una labor (si el trabajador no está activo esa semana, queda
  activo), el calendario de asignaciones de esta semana a 4 adelante y quitar preasignaciones.

Sin estados duplicados: cada labor aparece una vez con su estado de mayor rango
(completada > abierta > planeada); ver campo.unificar.
"""

from datetime import date, timedelta
from html import escape

import streamlit as st

import api
import campo
import cronograma_view
import ui

hoy = ui.hoy()
st.title("Programación")
crono_tab, programar_tab = st.tabs([":material/view_week: Cronograma de la finca", ":material/event_available: Programar"],
                                   key="pg_tab", on_change="rerun")   # la pestaña se conserva al guardar

# ═══ PROGRAMAR ═════════════════════════════════════════════════════════════════
SEMANAS = [ui.semana_iso(hoy + timedelta(weeks=k)) for k in range(5)]     # esta semana y 4 adelante
LUNES = ui.dias_de(SEMANAS[0])[0]
if st.session_state.get("pg_semana") not in SEMANAS:
    st.session_state["pg_semana"] = SEMANAS[0]


def mover_carrusel(paso: int) -> None:
    i = SEMANAS.index(st.session_state["pg_semana"]) + paso
    st.session_state["pg_semana"] = SEMANAS[max(0, min(len(SEMANAS) - 1, i))]


def rotulo_corto(semana: str) -> str:
    k = SEMANAS.index(semana)
    return f"S{int(semana[6:])} · " + ("esta semana" if k == 0 else ui.rotulo_semana(semana).split(": ")[1])


def sin_id(lista: list[dict]) -> list[dict]:
    return [{"dia": x["dia"], "lote_id": x["lote_id"], "labor_id": x["labor_id"]} for x in lista]


def vista_programar() -> None:
    trabajadores = {t["nombre"]: t["id"] for t in ui.leer(lambda: api.lista("/trabajadores"))}
    opciones_lotes, opciones_labores = api.opciones_lotes(), api.opciones_labores()
    nombre_lote = {v: k for k, v in opciones_lotes.items()}
    nombre_labor = {v: k for k, v in opciones_labores.items()}
    pools = {s: ui.leer(lambda s=s: api.get("/pool", semana=s)) for s in SEMANAS}

    # ── preasignar ──
    st.subheader("Programar una labor")
    with st.form("pg_form"):
        c1, c2 = st.columns(2)
        trabajador = c1.selectbox("Trabajador", list(trabajadores), index=None, placeholder="Elige el trabajador",
                                  key="pg_trabajador")
        dia = c2.date_input("Día", value=hoy, min_value=LUNES, max_value=LUNES + timedelta(days=34),
                            format="DD/MM/YYYY", key="pg_dia")
        lote_p = c1.selectbox("Lote", list(opciones_lotes), index=None, placeholder="Elige el lote", key="pg_lote")
        labor_p = c2.selectbox("Labor", list(opciones_labores), index=None, placeholder="Elige la labor",
                               key="pg_labor")
        programar = st.form_submit_button("Programar labor", type="primary", icon=":material/event_available:")
    st.caption("Puedes programar desde esta semana hasta 4 semanas adelante. Si el trabajador no está activo "
               "esa semana, queda activo en el pool al guardar.")
    if programar:
        faltante = next((m for falta, m in [(trabajador is None, "Elige el trabajador"), (lote_p is None, "Elige el lote"),
                                            (labor_p is None, "Elige la labor")] if falta), None)
        if faltante:
            st.error(faltante, icon=":material/error:")
        else:
            semana = ui.semana_iso(dia)
            tid = trabajadores[trabajador]
            # Lectura fresca del pool de esa semana (la API reemplaza la lista entera en el PATCH).
            fila = next((p for p in ui.leer(lambda: api.get("/pool", semana=semana)) if p["trabajador_id"] == tid), None)
            nueva = {"dia": dia.isoformat(), "lote_id": opciones_lotes[lote_p], "labor_id": opciones_labores[labor_p]}
            activo = fila is not None and fila["activo"]
            if activo and nueva in sin_id(fila["preasignacion"]):
                st.warning(f"{trabajador} ya tiene {labor_p} en {lote_p} el {ui.dia_corto(dia)}.", icon=":material/info:")
            else:
                def preasignar():
                    if activo:
                        api.patch(f"/pool/{fila['id']}", {"preasignacion": sin_id(fila["preasignacion"]) + [nueva]})
                    else:
                        api.post("/pool/activar", {"trabajador_id": tid, "semana": semana, "preasignacion": [nueva]})
                    st.session_state["pg_semana"] = semana          # el carrusel va a esa semana
                ui.enviar(preasignar, limpiar=["pg_lote", "pg_labor"], refrescar=True,
                          exito=f"Registro guardado: {labor_p} en {lote_p} para {trabajador} el {ui.dia_corto(dia)}"
                                + ("" if activo else f" · {trabajador} quedó activo en la {ui.rotulo_semana(semana)}"))

    # ── calendario de asignaciones (carrusel) ──
    st.subheader("Calendario de asignaciones")
    i = SEMANAS.index(st.session_state["pg_semana"])
    izq, centro, der = st.columns([0.6, 8, 0.6], vertical_alignment="center")
    izq.button("", icon=":material/chevron_left:", key="pg_atras", on_click=mover_carrusel, args=(-1,),
               disabled=i == 0, help="Semana anterior")
    centro.segmented_control("Semana", SEMANAS, format_func=rotulo_corto, key="pg_semana", required=True,
                             label_visibility="collapsed")
    der.button("", icon=":material/chevron_right:", key="pg_adelante", on_click=mover_carrusel, args=(1,),
               disabled=i == len(SEMANAS) - 1, help="Semana siguiente")
    semana_c = st.session_state["pg_semana"]
    crono_c = campo.cronograma(semana_c)
    activos = [p for p in pools[semana_c] if p["activo"]]

    celdas: dict[tuple[str, str], list[str]] = {}
    nombres = {p["trabajador_id"]: p["trabajador_nombre"] for p in activos}
    for d in crono_c["dias"]:
        for nombre, fichas in campo.lotes_del_dia(d):
            for f in fichas:
                nombres.setdefault(f["trabajador_id"], f["trabajador"])
                celdas.setdefault((f["trabajador_id"], str(d["fecha"])), []).append(
                    campo.ficha(f"{f['labor']} · {nombre}", f, detalle=False))
    st.caption(f"{ui.rotulo_semana(semana_c)} · {len(activos)} trabajadores activos en el pool")
    if not nombres:
        st.info(f"Nadie está activo en la {ui.rotulo_semana(semana_c)} todavía: al programarle una labor a "
                "alguien, queda activo.", icon=":material/group_off:")
    else:
        dias_c = ui.dias_de(semana_c)
        clase = lambda d: " class='hoy'" if d == hoy else ""  # noqa: E731
        cabeza = "".join(f"<th{clase(d)}>{ui.dia_corto(d)}</th>" for d in dias_c)
        filas = "".join(
            f"<tr><td class='nombre'>{escape(nombre)}</td>"
            + "".join(f"<td{clase(d)}>{''.join(celdas.get((tid, d.isoformat()), []))}</td>" for d in dias_c) + "</tr>"
            for tid, nombre in sorted(nombres.items(), key=lambda x: x[1]))
        st.html(campo.LEYENDA + f"<div class='ag-scroll'><table class='ag-cal'><thead><tr><th>Trabajador</th>{cabeza}"
                f"</tr></thead><tbody>{filas}</tbody></table></div>")

    # ── quitar preasignación: grande y a la vista ──
    with st.container(border=True, key="pg_quitar"):
        st.subheader(":material/event_busy: Quitar preasignación")
        avisos = st.container()
        cumplidas = {(f["trabajador_id"], str(d["fecha"]), l["lote_id"], f["labor_id"])
                     for d in campo.cronograma(SEMANAS[0])["dias"] for l in d["lotes"]
                     for f in campo.unificar(l) if f["estado"] != "planeada" and f["planeada"]}
        quitables = sorted(
            ((p, x) for s in SEMANAS for p in pools[s] if p["activo"] for x in p["preasignacion"]
             if (p["trabajador_id"], x["dia"], x["lote_id"], x["labor_id"]) not in cumplidas),
            key=lambda par: (par[1]["dia"], par[0]["trabajador_nombre"]))

        def rotulo(par) -> str:
            p, x = par
            return (f"{ui.dia_corto(date.fromisoformat(x['dia']))} · {p['trabajador_nombre']} · "
                    f"{nombre_labor.get(x['labor_id'], '?')} · {nombre_lote.get(x['lote_id'], '?')}")

        if not quitables:
            st.caption("No hay preasignaciones pendientes entre esta semana y 4 semanas adelante. "
                       "(Las que ya se cumplieron no se quitan: son historia de la finca.)")
        else:
            elegida = st.selectbox("Preasignación", quitables, format_func=rotulo, index=None,
                                   placeholder="Elige cuál quitar", key="pg_quitar_elegida")
            st.caption("Solo salen las pendientes; las que ya se cumplieron quedan en el cronograma.")
            b1, b2 = st.columns(2)
            if b1.button("Quitar preasignación", type="primary", icon=":material/event_busy:", width="stretch",
                         disabled=elegida is None, key="pg_quitar_una"):
                p, x = elegida
                resto = [y for y in sin_id(p["preasignacion"]) if y != sin_id([x])[0]]
                ui.enviar(lambda: api.patch(f"/pool/{p['id']}", {"preasignacion": resto}),
                          limpiar=["pg_quitar_elegida"], refrescar=True, donde=avisos,
                          exito=f"Registro guardado: se quitó {rotulo(elegida)}")
            semana_e = ui.semana_iso(date.fromisoformat(elegida[1]["dia"])) if elegida else None
            if b2.button(f"Quitar todas las pendientes de {elegida[0]['trabajador_nombre']} en la semana "
                         f"{int(semana_e[6:])}" if elegida else "Quitar todas las de ese trabajador en la semana",
                         icon=":material/event_busy:", width="stretch", disabled=elegida is None,
                         key="pg_quitar_todas"):
                p = elegida[0]
                # Se conservan solo las ya cumplidas (lista vacía si no hay ninguna).
                resto = [y for y in sin_id(p["preasignacion"])
                         if (p["trabajador_id"], y["dia"], y["lote_id"], y["labor_id"]) in cumplidas]
                ui.enviar(lambda: api.patch(f"/pool/{p['id']}", {"preasignacion": resto}),
                          limpiar=["pg_quitar_elegida"], refrescar=True, donde=avisos,
                          exito=f"Registro guardado: se quitaron las preasignaciones pendientes de "
                                f"{p['trabajador_nombre']} en la {ui.rotulo_semana(semana_e)}")


# Solo se dibuja (y se le pide a la API) la pestaña abierta.
with crono_tab:
    if crono_tab.open:
        cronograma_view.cronograma_finca(clave="cr")
with programar_tab:
    if programar_tab.open:
        vista_programar()
