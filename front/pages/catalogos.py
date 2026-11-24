"""Administrador: catálogos de la finca (lotes, labores, trabajadores e insumos).

Se corrigen directo en la tabla (PATCH /{id}: solo los campos que cambiaron; la API deja
cada corrección en auditoría) y se crean con un formulario corto (POST). El catálogo de
labores lo maneja SOLO el administrador: aquí es donde se crean labores nuevas.
"""

import math

import pandas as pd
import streamlit as st

import api
import ui

CULTIVOS = {"cafe": "Café", "platano": "Plátano", "bosque": "Bosque"}
ESTADOS = {"activo": "Activo", "no_activo": "No activo", "no_productivo": "No productivo"}
UNIDADES = {"kg": "kg", "hectareas": "hectáreas", "jornales": "jornales", "racimos": "racimos",
            "ninguna": "sin avance"}
METAS = {"kilos": "Por kilos", "horas": "Por horas", "completada": "Labor completada"}


def limpio(v):
    """Valor de una celda del editor a JSON: sin NaN ni tipos de numpy, listas como list."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    if hasattr(v, "tolist") and not isinstance(v, str):
        return v.tolist()
    if isinstance(v, tuple):
        return list(v)
    return v


def tabla_editable(clave: str, ruta: str, registros: list[dict], columnas: dict, solo_lectura=(),
                   vacio_es_nulo=()) -> None:
    """Tabla del catálogo con corrección en línea. `columnas`: {campo: column_config}."""
    if not registros:
        ui.sin_datos()
        return
    original = pd.DataFrame([{"id": r["id"], **{c: r.get(c) for c in columnas}} for r in registros]).set_index("id")
    editado = st.data_editor(original, column_config=columnas, disabled=list(solo_lectura), hide_index=True,
                             key=f"editor_{clave}", num_rows="fixed")
    cambios = []
    for id_ in original.index:
        diff = {}
        for c in columnas:
            if c in solo_lectura:
                continue
            antes, ahora = limpio(original.at[id_, c]), limpio(editado.at[id_, c])
            if isinstance(ahora, str):
                ahora = ahora.strip()
            if c in vacio_es_nulo and ahora == "":
                ahora = None
            if antes != ahora:
                diff[c] = ahora
        if diff:
            cambios.append((id_, original.at[id_, "nombre"], diff))
    if cambios:
        st.caption(f"{len(cambios)} registro(s) con correcciones sin guardar: "
                   + ", ".join(n for _, n, _ in cambios))

    def guardar():
        hechos = 0
        for id_, nombre, diff in cambios:
            try:
                api.patch(f"{ruta}/{id_}", diff)
            except api.ErrorApi as e:
                previas = f" (las {hechos} correcciones anteriores sí quedaron guardadas)" if hechos else ""
                raise api.ErrorApi(e.estado, f"{nombre}: {e.detalle}{previas}") from None
            hechos += 1

    if st.button("Guardar correcciones", key=f"guardar_{clave}", type="primary", icon=":material/save:",
                 disabled=not cambios):
        ui.enviar(guardar, limpiar=[f"editor_{clave}"], refrescar=True,
                  exito=f"Registro guardado: {len(cambios)} corrección(es); quedan en auditoría")


Col = st.column_config
COL_CULTIVOS = Col.MultiselectColumn("Cultivos", options=list(CULTIVOS), format_func=CULTIVOS.get, required=True)

st.title("Catálogos")
st.caption("Corrige directo en la tabla y pulsa «Guardar correcciones»: cada cambio queda en auditoría.")
lotes_tab, labores_tab, trab_tab, insumos_tab = st.tabs(
    [":material/landscape: Lotes", ":material/agriculture: Labores", ":material/groups: Trabajadores",
     ":material/inventory_2: Insumos"], key="catalogo_tab")

with lotes_tab:
    tabla_editable("lotes", "/lotes", ui.leer(lambda: api.get("/lotes")), {
        "nombre": Col.TextColumn("Nombre", required=True),
        "cultivos": COL_CULTIVOS,
        "variedad": Col.TextColumn("Variedad"),
        "area_ha": Col.NumberColumn("Área (ha)", min_value=0.01, step=0.01, format="localized", required=True),
        "estado": Col.SelectboxColumn("Estado", options=list(ESTADOS), format_func=ESTADOS.get, required=True),
    })
    with st.expander("+ Crear lote"):
        with st.form("nuevo_lote", border=False):
            a, b = st.columns(2)
            nombre = a.text_input("Nombre", key="lo_nombre")
            cultivos = b.multiselect("Cultivos", list(CULTIVOS), format_func=CULTIVOS.get, key="lo_cultivos")
            variedad = a.text_input("Variedad", key="lo_variedad")
            area = b.number_input("Área (ha)", min_value=0.0, step=0.1, value=None, key="lo_area")
            if st.form_submit_button("Crear lote", type="primary"):
                ui.enviar(lambda: api.post("/lotes", {"nombre": nombre, "cultivos": cultivos,
                                                      "variedad": variedad.strip(), "area_ha": area}),
                          limpiar=["lo_nombre", "lo_cultivos", "lo_variedad", "lo_area"], refrescar=True,
                          exito=f"Registro guardado: lote {nombre.strip()}")

with labores_tab:
    st.caption("Las labores estables de la finca. Solo el administrador crea o corrige labores.")
    tabla_editable("labores", "/labores", ui.leer(lambda: api.get("/labores")), {
        "nombre": Col.TextColumn("Nombre", required=True),
        "cultivos": COL_CULTIVOS,
        "unidad_avance": Col.SelectboxColumn("Unidad de avance", options=list(UNIDADES), format_func=UNIDADES.get,
                                             required=True),
        "admite_contrato": Col.CheckboxColumn("Admite contrato"),
        "tipo_meta": Col.SelectboxColumn("Meta del contrato", options=list(METAS), format_func=METAS.get),
        "activa": Col.CheckboxColumn("Activa"),
    })
    with st.expander("+ Crear labor"):
        with st.form("nueva_labor", border=False):
            a, b = st.columns(2)
            nombre_l = a.text_input("Nombre", key="la_nombre")
            cultivos_l = b.multiselect("Cultivos", list(CULTIVOS), format_func=CULTIVOS.get, key="la_cultivos")
            unidad = a.selectbox("Unidad de avance", list(UNIDADES), format_func=UNIDADES.get, key="la_unidad")
            meta = b.selectbox("Meta si es por contrato", [None, *METAS], format_func=lambda m: METAS.get(m, "—"),
                               key="la_meta")
            admite = st.checkbox("Admite contrato", key="la_admite")
            if st.form_submit_button("Crear labor", type="primary"):
                ui.enviar(lambda: api.post("/labores", {"nombre": nombre_l, "cultivos": cultivos_l,
                                                        "unidad_avance": unidad, "admite_contrato": admite,
                                                        "tipo_meta": meta}),
                          limpiar=["la_nombre", "la_cultivos", "la_admite"], refrescar=True,
                          exito=f"Registro guardado: labor {nombre_l.strip()}")

with trab_tab:
    tabla_editable("trabajadores", "/trabajadores", ui.leer(lambda: api.get("/trabajadores")), {
        "nombre": Col.TextColumn("Nombre", required=True),
        "documento": Col.TextColumn("Documento"),
        "telefono": Col.TextColumn("Teléfono"),
    }, vacio_es_nulo=("documento", "telefono"))
    with st.expander("+ Crear trabajador"):
        with st.form("nuevo_trabajador_cat", border=False):
            a, b, c = st.columns(3)
            nombre_t = a.text_input("Nombre", key="tr_nombre")
            documento = b.text_input("Documento (opcional)", key="tr_documento")
            telefono = c.text_input("Teléfono (opcional)", key="tr_telefono")
            if st.form_submit_button("Crear trabajador", type="primary"):
                ui.enviar(lambda: api.post("/trabajadores", {"nombre": nombre_t, "documento": documento.strip() or None,
                                                             "telefono": telefono.strip() or None}),
                          limpiar=["tr_nombre", "tr_documento", "tr_telefono"], refrescar=True,
                          exito=f"Registro guardado: trabajador {nombre_t.strip()} (actívalo en el pool de la semana)")

with insumos_tab:
    st.caption("El stock no se corrige a mano: sube con las compras y baja con el consumo en las labores.")
    tabla_editable("insumos", "/insumos", ui.leer(lambda: api.get("/insumos")), {
        "nombre": Col.TextColumn("Nombre", required=True),
        "unidad": Col.TextColumn("Unidad", required=True),
        "stock_actual": Col.NumberColumn("Stock actual", format="localized"),
        "umbral_alerta": Col.NumberColumn("Umbral de alerta", min_value=0, format="localized"),
    }, solo_lectura=("stock_actual",))
    with st.expander("+ Crear insumo"):
        with st.form("nuevo_insumo", border=False):
            a, b = st.columns(2)
            nombre_i = a.text_input("Nombre", key="in_nombre")
            unidad_i = b.text_input("Unidad", key="in_unidad", placeholder="bulto, litro, kg...")
            stock = a.number_input("Stock inicial", min_value=0.0, step=1.0, value=0.0, key="in_stock")
            umbral = b.number_input("Umbral de alerta", min_value=0.0, step=1.0, value=0.0, key="in_umbral")
            if st.form_submit_button("Crear insumo", type="primary"):
                ui.enviar(lambda: api.post("/insumos", {"nombre": nombre_i, "unidad": unidad_i,
                                                        "stock_actual": stock, "umbral_alerta": umbral}),
                          limpiar=["in_nombre", "in_unidad"], refrescar=True,
                          exito=f"Registro guardado: insumo {nombre_i.strip()}")
