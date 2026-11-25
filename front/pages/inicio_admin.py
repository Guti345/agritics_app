"""Administrador: pantalla inicial. Una tarjeta por cada sección de su menú (en el mismo orden
del menú lateral), con una línea de lo que encuentra ahí y el botón a su primera pantalla."""

import streamlit as st

import ui

ICONOS = ui.ASSETS / "iconos"
CALENDARIO = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><g fill='none' stroke='#004846' "
              "stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'><rect x='3' y='5' width='18' "
              "height='16' rx='2'/><path d='M3 10h18M8 3v4m8-4v4m-9 7h2m3 0h2m-7 4h2'/></g></svg>")
ENGRANAJE = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><g fill='none' stroke='#004846' "
             "stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'><circle cx='12' cy='12' r='3'/>"
             "<path d='M12 2v3m0 14v3M2 12h3m14 0h3M4.9 4.9 7 7m10 10 2.1 2.1M4.9 19.1 7 17M17 7l2.1-2.1'/></g></svg>")


def svg(nombre: str) -> str:
    return (ICONOS / nombre).read_text(encoding="utf-8")


SECCIONES = [  # clave, primera pantalla de la sección, título, qué encuentra, ícono, símbolo
    ("semana", "pages/tablero_semana.py", "La semana",
     "Cómo va la semana en la finca y el pago de la nómina", CALENDARIO, ":material/calendar_view_week:"),
    ("libro", "pages/libro.py", "Libro contable",
     "Ventas de café y plátano, compras, gastos y la caja", svg("caja.svg"), ":material/receipt_long:"),
    ("campo", "pages/captura.py", "Campo",
     "Registro diario, trabajadores y programación de labores", svg("labores.svg"), ":material/agriculture:"),
    ("reportes", "pages/r1_produccion.py", "Reportes",
     "Producción, flujo de caja, nómina y resultados de la junta", svg("reporte.svg"), ":material/monitoring:"),
    ("administracion", "pages/catalogos.py", "Administración",
     "Catálogos de la finca, trazabilidad y Excel", ENGRANAJE, ":material/settings:"),
]

st.title(f"Hola, {st.session_state['usuario']['nombre']}")
st.caption("Tu menú tiene cinco secciones. Entra a cada una desde aquí o desde el menú de la izquierda.")
filas = [SECCIONES[:3], SECCIONES[3:]]
for fila in filas:
    for col, (clave, ruta, titulo, texto, icono, simbolo) in zip(st.columns(3), fila):
        with col:
            ui.tarjeta(f"adm_{clave}", ruta, titulo, texto, icono, simbolo, enlace=f"Ir a {titulo.lower()}")
