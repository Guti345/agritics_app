"""Superusuario: usuarios de la app. Crear, activar o inactivar y cambiar la clave.
La API nunca devuelve la clave."""

from html import escape

import streamlit as st

import api
import ui

ROLES = {"administrador": "Administrador", "mayordomo": "Mayordomo", "junta": "Junta familiar",
         "superusuario": "Superusuario"}

st.title("Usuarios")
usuarios = ui.leer(lambda: api.get("/usuarios"))
yo = st.session_state["usuario"]["usuario"]
avisos = st.container()   # errores de los botones de cada fila, arriba de la lista

st.caption(f"{sum(u['activo'] for u in usuarios)} activos de {len(usuarios)}. Un usuario inactivo no puede entrar.")
for u in usuarios:
    with st.container(border=True):
        a, b, c, d = st.columns([2.5, 1.5, 1.5, 1.3], vertical_alignment="center")
        a.html(f"<b>{escape(u['nombre'])}</b><br><small style='opacity:.75'>usuario: {escape(u['usuario'])}"
               f"{' (tú)' if u['usuario'] == yo else ''}</small>")
        b.write(ROLES.get(u["rol"], u["rol"]))
        c.html(f"<span class='ag-chip {'real completada' if u['activo'] else 'plan'}' style='display:inline-block'>"
               f"{'Activo' if u['activo'] else 'Inactivo'}</span>")
        if u["activo"]:
            if d.button("Inactivar", key=f"inact_{u['id']}", icon=":material/person_off:", width="stretch"):
                ui.enviar(lambda: api.patch(f"/usuarios/{u['id']}", {"activo": False}), donde=avisos,
                          exito=f"Registro guardado: {u['usuario']} quedó inactivo")
        elif d.button("Activar", key=f"act_{u['id']}", type="primary", icon=":material/person_check:", width="stretch"):
            ui.enviar(lambda: api.patch(f"/usuarios/{u['id']}", {"activo": True}), donde=avisos,
                      exito=f"Registro guardado: {u['usuario']} quedó activo")

c1, c2 = st.columns(2)
with c1:
    st.subheader("Crear usuario")
    with st.form("nuevo_usuario"):
        nombre = st.text_input("Nombre", key="us_nombre")
        usuario = st.text_input("Usuario (sin espacios)", key="us_usuario", help="Se guarda en minúsculas")
        clave = st.text_input("Clave (mínimo 6 caracteres)", type="password", key="us_clave",
                              autocomplete="new-password")
        rol = st.selectbox("Rol", list(ROLES), format_func=ROLES.get, key="us_rol")
        activo = st.checkbox("Activo", value=True, key="us_activo")
        if st.form_submit_button("Crear usuario", type="primary", icon=":material/person_add:"):
            ui.enviar(lambda: api.post("/usuarios", {"nombre": nombre, "usuario": usuario, "clave": clave,
                                                     "rol": rol, "activo": activo}),
                      limpiar=["us_nombre", "us_usuario", "us_clave"],
                      exito=f"Registro guardado: usuario {usuario.strip().lower()} creado")
with c2:
    st.subheader("Cambiar clave")
    with st.form("cambiar_clave"):
        cual = st.selectbox("Usuario", usuarios, index=None, key="cc_usuario", placeholder="Elige el usuario",
                            format_func=lambda u: f"{u['nombre']} ({u['usuario']})")
        nueva = st.text_input("Clave nueva (mínimo 6 caracteres)", type="password", key="cc_clave",
                              autocomplete="new-password")
        if st.form_submit_button("Cambiar clave", type="primary", icon=":material/key:"):
            if cual is None:
                st.error("Elige el usuario", icon=":material/error:")
            else:
                ui.enviar(lambda: api.patch(f"/usuarios/{cual['id']}", {"clave": nueva}),
                          limpiar=["cc_usuario", "cc_clave"],
                          exito=f"Registro guardado: clave de {cual['usuario']} cambiada")
