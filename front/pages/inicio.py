"""Mayordomo: pantalla inicial. Tarjetas grandes de acceso a sus vistas (Registro,
Programación, Trabajadores) y, debajo, el mapa de la finca con lo de la semana por lote."""

import streamlit as st

import mapa
import ui

ICONOS = ui.ASSETS / "iconos"
CALENDARIO = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><g fill='none' stroke='#004846' "
              "stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'><rect x='3' y='5' width='18' "
              "height='16' rx='2'/><path d='M3 10h18M8 3v4m8-4v4m-9 7h2m3 0h2m-7 4h2'/></g></svg>")

TARJETAS = [
    ("registro", "pages/captura.py", "Registro", "Labores del día, lluvia y cosecha de plátano",
     (ICONOS / "labores.svg").read_text(encoding="utf-8"), ":material/edit_note:"),
    ("programacion", "pages/programacion.py", "Programación", "Cronograma de la finca y labores por programar",
     CALENDARIO, ":material/event_note:"),
    ("trabajadores", "pages/trabajadores.py", "Trabajadores", "Crear trabajadores y el pool de la semana",
     (ICONOS / "nomina.svg").read_text(encoding="utf-8"), ":material/groups:"),
]


st.title(f"Hola, {st.session_state['usuario']['nombre']}")
for col, (clave, ruta, titulo, texto, icono, simbolo) in zip(st.columns(3), TARJETAS):
    with col:
        ui.tarjeta(clave, ruta, titulo, texto, icono, simbolo)

# ── mapa de la finca ──
st.write("")
titulo, selector = st.columns([3, 2], vertical_alignment="bottom")
titulo.subheader("Mapa de la finca")
semana = ui.elegir_semana("Semana", key="inicio_semana", donde=selector)
mapa.mapa_finca(semana, key="inicio_mapa")
