"""Mayordomo: captura rápida del día. Tres accesos: labor, lluvia y cosecha de plátano.

La recolección es una labor más. Una labor se abre (POST /labores-diarias) y se completa
después con los valores reales (POST /labores-diarias/{id}/completar). Si se registra al
final del día ya terminada, la pantalla hace las dos llamadas seguidas: la API no deja
abrir una labor ya completada.
"""

from datetime import datetime, time

import streamlit as st

import api
import campo
import ui

UNIDAD = {"kg": "kg", "hectareas": "ha", "jornales": "jornales", "racimos": "racimos", "ninguna": None}
METAS = {"kilos": "Por kilos", "horas": "Por horas", "completada": "Labor completada"}
TARIFA = {"jornal": "Tarifa ($ por jornal)", "kilos": "Tarifa ($ por kilo)",
          "horas": "Tarifa ($ por hora)", "completada": "Tarifa ($ por la labor)"}


def rotulo_avance(labor: dict) -> str | None:
    """Etiqueta del avance real según la unidad de la labor (None = la labor no mide avance)."""
    unidad = UNIDAD.get(labor["unidad_avance"])
    if unidad is None:
        return None
    if unidad == "kg" and "cafe" in labor["cultivos"]:
        return "Kilos de café cereza recogidos"
    return f"Avance real ({unidad})"


st.title("Registro diario")
labor_tab, lluvia_tab, platano_tab = st.tabs(
    [":material/agriculture: Registrar labor", ":material/rainy: Registrar lluvia",
     ":material/nutrition: Guardar cosecha de plátano"],
    key="captura_acceso", on_change="rerun",   # al guardar se queda en la misma pestaña
)

# ═══ REGISTRAR LABOR ═══════════════════════════════════════════════════════════
with labor_tab:
    lotes = ui.leer(lambda: api.lista("/lotes", estado="activo"))
    labores = [l for l in ui.leer(lambda: api.lista("/labores")) if l["activa"]]
    insumos = ui.leer(lambda: api.lista("/insumos"))

    # El catálogo de labores (las 14 estables de la finca) lo maneja solo el administrador,
    # en Catálogos. El mayordomo crea trabajadores en su pantalla «Trabajadores»; el
    # administrador conserva aquí el atajo.
    if not ui.puede("mayordomo"):
        nuevo_trab, _ = st.columns(2)
        with nuevo_trab.expander("+ Crear trabajador"):
            campo.form_trabajador()

    # Sin st.form: los campos dependen unos de otros (labor -> forma de pago -> meta).
    # Lo digitado vive en st.session_state (key=...) y solo se limpia al guardar.
    c1, c2 = st.columns(2)
    fecha = c1.date_input("Fecha", value=ui.hoy(), max_value=ui.hoy(), format="DD/MM/YYYY", key="lab_fecha")
    pool = ui.leer(lambda: api.opciones_trabajadores(ui.semana_iso(fecha)))
    trabajador = c2.selectbox("Trabajador", list(pool), index=None, key="lab_trabajador",
                              placeholder="Elige del pool de la semana")
    if not pool:
        donde = "Trabajadores › Pool de trabajadores" if ui.puede("mayordomo") else "Pool de trabajadores"
        st.warning(f"No hay trabajadores activos en la {ui.rotulo_semana(ui.semana_iso(fecha))}: "
                   f"actívalos en {donde}.", icon=":material/group_off:")

    lote_nombre = c1.selectbox("Lote", [l["nombre"] for l in lotes], index=None, key="lab_lote",
                               placeholder="Elige el lote")
    lote = next((l for l in lotes if l["nombre"] == lote_nombre), None)
    del_lote = [l for l in labores if lote is None or set(l["cultivos"]) & set(lote["cultivos"])]
    labor_nombre = c2.selectbox("Labor", [l["nombre"] for l in del_lote], index=None, key="lab_labor",
                                placeholder="Elige la labor")
    labor = next((l for l in del_lote if l["nombre"] == labor_nombre), None)

    formas = ["jornal", "contrato"] if labor and labor["admite_contrato"] else ["jornal"]
    forma = c1.segmented_control("Forma de pago", formas, default="jornal", required=True,
                                 format_func=str.capitalize, key=f"lab_forma_{len(formas)}")
    meta = None
    if forma == "contrato":
        meta = c2.segmented_control("Tipo de meta", list(METAS), format_func=METAS.get, required=True,
                                    default=labor.get("tipo_meta") or "completada", key="lab_meta")
    tarifa = c1.number_input(TARIFA[meta or "jornal"], min_value=0, step=1000, value=None,
                             placeholder="$", key="lab_tarifa")
    jornales = c2.number_input("Jornales", min_value=0.5, step=0.5, value=1.0, format="%.1f", key="lab_jornales")

    terminada = st.toggle("Terminó hoy: registrar el avance real y dejarla completada", key="lab_terminada")
    avance = 0.0
    if terminada and labor and rotulo_avance(labor):
        avance = st.number_input(rotulo_avance(labor), min_value=0.0, step=1.0, value=None,
                                 placeholder="Escribe el avance", key="lab_avance")

    insumo = None
    if st.toggle("Usó insumo", key="lab_usa_insumo"):
        i1, i2 = st.columns(2)
        insumo_nombre = i1.selectbox("Insumo", [i["nombre"] for i in insumos], index=None, key="lab_insumo",
                                     placeholder="Elige el insumo")
        insumo = next((i for i in insumos if i["nombre"] == insumo_nombre), None)
        cantidad = i2.number_input(f"Cantidad ({insumo['unidad']})" if insumo else "Cantidad",
                                   min_value=0.0, step=0.5, value=None, key="lab_cantidad")
        if insumo:
            st.caption(f"Quedan {ui.numero(insumo['stock_actual'], 1).removesuffix(',0')} {insumo['unidad']} en bodega.")

    if trabajador and lote and labor:
        estado = "completada" if terminada else "abierta"
        st.caption(f"Se registra: **{trabajador}** · {labor['nombre']} · {lote['nombre']} · "
                   f"{ui.dia_corto(fecha)} · {ui.jornales(jornales)} · {forma} · queda {estado}")

    if st.button("Registrar labor", type="primary", icon=":material/save:"):
        faltante = next((m for falta, m in [
            (not trabajador, "Elige el trabajador"), (not lote, "Elige el lote"), (not labor, "Elige la labor"),
            (tarifa is None, "Escribe la tarifa"),
            (terminada and avance is None, "Escribe el avance real (por ejemplo, cuántos kilos recogió)"),
            (insumo is None and st.session_state.get("lab_usa_insumo"), "Elige el insumo que usó"),
            (insumo is not None and not st.session_state.get("lab_cantidad"), "Escribe cuánto insumo usó"),
        ] if falta), None)
        if faltante:
            st.error(faltante, icon=":material/error:")
        else:
            datos = {"fecha": fecha, "trabajador_id": pool[trabajador], "lote_id": lote["id"],
                     "labor_id": labor["id"], "forma_pago": forma, "tarifa": tarifa, "tipo_meta": meta,
                     "jornales": jornales,
                     "insumo_consumido": {"insumo_id": insumo["id"], "cantidad": st.session_state["lab_cantidad"]}
                     if insumo else None}

            def registrar_labor():
                creada = api.post("/labores-diarias", datos)
                if terminada:
                    try:
                        api.post(f"/labores-diarias/{creada['id']}/completar",
                                 {"avance": avance or 0, "jornales": jornales})
                    except api.ErrorApi as e:
                        raise api.ErrorApi(e.estado, f"La labor quedó registrada pero abierta: {e.detalle}. "
                                                     "Complétala en «Labores abiertas».") from None
                return creada

            # Lote, labor, tarifa y fecha se quedan: así se registra seguido a la cuadrilla.
            ui.enviar(registrar_labor,
                      limpiar=["lab_trabajador", "lab_avance", "lab_terminada", "lab_usa_insumo",
                               "lab_insumo", "lab_cantidad"],
                      exito=f"Registro guardado: {labor['nombre']} de {trabajador} "
                            f"{'completada' if terminada else 'abierta'}",
                      refrescar=bool(insumo))

    # ── labores abiertas: se completan con los valores reales ──
    st.subheader("Labores abiertas")
    abiertas = ui.leer(lambda: api.get("/labores-diarias", completada=False))
    if not abiertas:
        st.caption("No hay labores abiertas.")
    nombres_t = ui.leer(lambda: api.por_id("/trabajadores"))
    todos_lotes, todas_labores = ui.leer(lambda: api.por_id("/lotes")), ui.leer(lambda: api.por_id("/labores"))
    for a in abiertas:
        lb = todas_labores.get(a["labor_id"], {"nombre": "?", "unidad_avance": "ninguna", "cultivos": []})
        titulo = (f"{nombres_t.get(a['trabajador_id'], {}).get('nombre', '?')} · {lb['nombre']} · "
                  f"{todos_lotes.get(a['lote_id'], {}).get('nombre', '?')} · "
                  f"{ui.dia_corto(datetime.fromisoformat(a['fecha']).date())}")
        with st.expander(titulo, icon=":material/pending_actions:"):
            with st.form(f"completar_{a['id']}", border=False):
                f1, f2 = st.columns(2)
                rotulo = rotulo_avance(lb)
                av = f1.number_input(rotulo, min_value=0.0, step=1.0, value=None, key=f"ca_av_{a['id']}",
                                     placeholder="Escribe el avance") if rotulo else 0.0
                jr = f2.number_input("Jornales reales", min_value=0.5, step=0.5, value=float(a["jornales"]),
                                     format="%.1f", key=f"ca_jr_{a['id']}")
                if st.form_submit_button("Completar labor", type="primary"):
                    if av is None:
                        st.error("Escribe el avance real (por ejemplo, cuántos kilos recogió)", icon=":material/error:")
                    else:
                        ui.enviar(lambda: api.post(f"/labores-diarias/{a['id']}/completar",
                                                   {"avance": av, "jornales": jr}),
                                  limpiar=[f"ca_av_{a['id']}", f"ca_jr_{a['id']}"],
                                  exito=f"Registro guardado: {titulo} completada")

# ═══ REGISTRAR LLUVIA ══════════════════════════════════════════════════════════
with lluvia_tab:
    # La foto se sube a la API apenas se elige (una sola vez por archivo) y su ruta se guarda
    # en la sesión: si el registro falla, no se vuelve a subir al reintentar.
    st.session_state.setdefault("llu_n", 0)
    archivo = st.file_uploader("Foto del pluviómetro", type=["jpg", "jpeg", "png", "webp", "heic", "heif"],
                               key=f"llu_archivo_{st.session_state['llu_n']}")
    subida = st.session_state.get("llu_foto")
    if archivo is None:
        st.session_state.pop("llu_foto", None)
        subida = None
    elif subida is None or subida["archivo"] != archivo.file_id:
        try:
            r = api.post("/uploads/foto", archivos={"archivo": (archivo.name, archivo.getvalue(), archivo.type)})
            subida = st.session_state["llu_foto"] = {"archivo": archivo.file_id, "ruta": r["ruta"]}
        except api.ErrorApi as e:
            st.session_state.pop("llu_foto", None)
            subida = None
            st.error(e.detalle, icon=":material/error:")
    if subida:
        if archivo.type in ("image/jpeg", "image/png", "image/webp"):   # HEIC no se puede previsualizar
            st.image(archivo, width=220, caption="Foto adjunta")
        else:
            st.caption(f":material/check_circle: Foto adjunta: {archivo.name}")

    l1, l2, l3 = st.columns(3)
    ahora = datetime.now(ui.BOGOTA)
    dia_l = l1.date_input("Fecha", value=ahora.date(), max_value=ahora.date(), format="DD/MM/YYYY", key="llu_fecha")
    hora_l = l2.time_input("Hora", value=time(ahora.hour, ahora.minute), step=60, key="llu_hora")
    mm = l3.number_input("Lluvia (mm)", min_value=0.0, max_value=500.0, step=0.5, value=None,
                         placeholder="mm del pluviómetro", key="llu_mm")
    st.caption(f"Leída por {st.session_state['usuario']['nombre']}. Escribe 0 solo si mediste y no llovió.")

    if st.button("Registrar lluvia", type="primary", icon=":material/save:", disabled=subida is None,
                 help=None if subida else "Adjunta la foto del pluviómetro para poder guardar"):
        if mm is None:
            st.error("Escribe cuántos milímetros marcó el pluviómetro", icon=":material/error:")
        else:
            datos_l = {"fecha_hora": datetime.combine(dia_l, hora_l), "mm": mm, "foto_ruta": subida["ruta"],
                       "leida_por": st.session_state["usuario"]["nombre"]}

            def registrar_lluvia():
                r = api.post("/lluvia", datos_l)
                st.session_state["llu_n"] += 1   # uploader nuevo y vacío
                return r
            ui.enviar(registrar_lluvia, limpiar=["llu_foto", "llu_mm", "llu_hora", "llu_fecha"],
                      exito=f"Registro guardado: {ui.numero(mm, 1).removesuffix(',0')} mm de lluvia")
    if subida is None:
        st.caption(":material/photo_camera: Adjunta la foto del pluviómetro para habilitar «Registrar lluvia».")

# ═══ COSECHA DE PLÁTANO ════════════════════════════════════════════════════════
with platano_tab:
    lotes_platano = ui.leer(lambda: api.opciones_lotes("platano"))
    with st.form("cosecha_platano", border=False):
        p1, p2 = st.columns(2)
        dia_p = p1.date_input("Fecha", value=ui.hoy(), max_value=ui.hoy(), format="DD/MM/YYYY", key="cp_fecha")
        lote_p = p2.selectbox("Lote", list(lotes_platano), index=None, placeholder="Elige el lote", key="cp_lote")
        kg = p1.number_input("Kilos", min_value=0.0, step=1.0, value=None, placeholder="kg", key="cp_kg")
        racimos = p2.number_input("Racimos", min_value=0, step=1, value=None, placeholder="racimos", key="cp_racimos")
        calidad = st.radio("Calidad", ["primera", "segunda"], format_func=str.capitalize, horizontal=True,
                           key="cp_calidad")
        if st.form_submit_button("Guardar cosecha", type="primary", icon=":material/save:"):
            faltante = next((m for falta, m in [(lote_p is None, "Elige el lote"),
                                                (kg is None, "Escribe cuántos kilos cosechaste"),
                                                (racimos is None, "Escribe cuántos racimos cosechaste")] if falta), None)
            if faltante:
                st.error(faltante, icon=":material/error:")
            else:
                ui.enviar(lambda: api.post("/cosechas-platano", {"fecha": dia_p, "lote_id": lotes_platano[lote_p],
                                                                 "kg": kg, "racimos": racimos, "calidad": calidad}),
                          limpiar=["cp_kg", "cp_racimos"],
                          exito=f"Registro guardado: {ui.kg(kg)} de plátano de {lote_p}")
