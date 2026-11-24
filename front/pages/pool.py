"""Pool de trabajadores de la semana en curso: quién está activo y quién no.

Solo los trabajadores activos en el pool de la semana aparecen en las listas de
captura y pueden recibir labores.
"""

from html import escape

import streamlit as st

import api
import ui

semana = ui.semana_iso()

st.title("Pool de trabajadores")
st.caption(f"{ui.rotulo_semana(semana)} · solo los activos aparecen al registrar labores")

trabajadores = ui.leer(lambda: api.get("/trabajadores"))
pool = {p["trabajador_id"]: p for p in ui.leer(lambda: api.get("/pool", semana=semana))}
activos = sum(1 for p in pool.values() if p["activo"])

m1, m2 = st.columns(2)
m1.metric("Activos esta semana", activos, border=True)
m2.metric("Trabajadores registrados", len(trabajadores), border=True)

f1, f2 = st.columns([2, 1], vertical_alignment="bottom")
buscar = f1.text_input("Buscar trabajador", placeholder="Parte del nombre", key="pool_buscar")
vista = f2.segmented_control("Mostrar", ["Todos", "Activos", "Fuera del pool"], default="Todos",
                             required=True, key="pool_vista")

avisos = st.container()   # el error de la API sale arriba de la lista, no en la columna del botón


def estado(t: dict) -> str:
    p = pool.get(t["id"])
    if p is None:
        return "fuera"
    return "activo" if p["activo"] else "desactivado"


ROTULO = {"activo": "Activo", "desactivado": "Desactivado esta semana", "fuera": "Fuera del pool"}

lista = [t for t in trabajadores
         if buscar.strip().lower() in t["nombre"].lower()
         and (vista == "Todos" or (vista == "Activos") == (estado(t) == "activo"))]
lista.sort(key=lambda t: (estado(t) != "activo", t["nombre"]))

if not lista:
    st.caption("Ningún trabajador coincide.")
for t in lista:
    e = estado(t)
    with st.container(border=True):
        nombre, rotulo, boton = st.columns([3, 2, 1.3], vertical_alignment="center")
        doc = f" · CC {escape(t['documento'])}" if t.get("documento") else ""
        nombre.html(f"<b>{escape(t['nombre'])}</b><small style='opacity:.75'>{doc}</small>")
        rotulo.html(f"<span class='ag-chip {'real completada' if e == 'activo' else 'plan'}' "
                    f"style='display:inline-block'>{ROTULO[e]}</span>")
        if e == "activo":
            if boton.button("Desactivar", key=f"des_{t['id']}", icon=":material/person_remove:", width="stretch"):
                ui.enviar(lambda: api.post("/pool/desactivar", {"trabajador_id": t["id"], "semana": semana}),
                          refrescar=True, donde=avisos,
                          exito=f"Registro guardado: {t['nombre']} salió del pool de la {ui.rotulo_semana(semana)}")
        elif boton.button("Activar", key=f"act_{t['id']}", type="primary", icon=":material/person_add:",
                          width="stretch"):
            ui.enviar(lambda: api.post("/pool/activar", {"trabajador_id": t["id"], "semana": semana}),
                      refrescar=True, donde=avisos,
                      exito=f"Registro guardado: {t['nombre']} quedó activo en la {ui.rotulo_semana(semana)}")
