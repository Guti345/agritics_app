"""Mayordomo: administración de trabajadores. Dos pestañas: crear trabajador (con la opción
de activarlo en el pool de la semana en el mismo envío) y el pool de la semana."""

import streamlit as st

import campo

st.title("Administración de trabajadores")
crear_tab, pool_tab = st.tabs([":material/person_add: Crear trabajador", ":material/groups: Pool de trabajadores"],
                              key="trab_tab", on_change="rerun")

with crear_tab:
    formulario, _ = st.columns([3, 2])
    with formulario:
        campo.form_trabajador()

with pool_tab:
    campo.pool_trabajadores()
