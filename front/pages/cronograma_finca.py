"""Administrador: cronograma de la finca. El mismo componente que el mayordomo ve en
Programación (zoom día / semana / mes, sin estados duplicados, resumen de la API y filtro
por lote)."""

import streamlit as st

import cronograma_view

st.title("Cronograma de la finca")
cronograma_view.cronograma_finca(clave="adm_cr")
