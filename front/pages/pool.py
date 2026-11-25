"""Pool de trabajadores de la semana en curso: quién está activo y quién no.

Solo los trabajadores activos en el pool de la semana aparecen en las listas de
captura y pueden recibir labores. (El mayordomo lo ve dentro de «Trabajadores».)
"""

import streamlit as st

import campo

st.title("Pool de trabajadores")
campo.pool_trabajadores()
