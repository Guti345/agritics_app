"""Agritics: entrada de la app (streamlit run front/app.py).

Sin iniciar sesión no se ve nada: la única página que existe es el acceso. Al entrar,
cada rol recibe SOLO sus pantallas (st.navigation) y cae en su pantalla inicial.
"""

import streamlit as st
from PIL import Image

import api
import ui

st.set_page_config(page_title="Agritics", page_icon=Image.open(ui.ICONO_APP), layout="wide")
ui.estilos()

# Pantallas por rol; la primera es la inicial. Las rutas son relativas a este archivo.
# Un rol puede tener secciones ({sección: [pantallas]}) o una lista simple.
# Campo del administrador. «Programación» es la misma página del mayordomo (Cronograma y Programar).
CAMPO = [
    ("pages/captura.py", "Captura rápida", ":material/edit_note:"),
    ("pages/pool.py", "Pool de trabajadores", ":material/groups:"),
    ("pages/programacion.py", "Programación", ":material/event_note:"),
]
# Mayordomo: inicio con tarjetas y mapa, y sus tres vistas.
MAYORDOMO = [
    ("pages/inicio.py", "Inicio", ":material/home:"),
    ("pages/captura.py", "Registro", ":material/edit_note:"),
    ("pages/programacion.py", "Programación", ":material/event_note:"),
    ("pages/trabajadores.py", "Trabajadores", ":material/groups:"),
]
REPORTES = [
    ("pages/r1_produccion.py", "Producción (R1)", ":material/coffee:"),
    ("pages/r2_flujo.py", "Flujo de caja (R2)", ":material/account_balance_wallet:"),
    ("pages/r3_nomina.py", "Nómina y labores (R3)", ":material/badge:"),
]
PANTALLAS = {
    "mayordomo": MAYORDOMO,                    # sin reportes
    "administrador": {
        "La semana": [
            ("pages/tablero_semana.py", "Tablero de la semana", ":material/calendar_view_week:"),
            ("pages/cortes.py", "Cortes de nómina", ":material/content_cut:"),
        ],
        "Libro contable": [
            ("pages/libro.py", "Ventas, compras y gastos", ":material/receipt_long:"),
            ("pages/caja.py", "Caja", ":material/wallet:"),
        ],
        # El administrador también puede escribir lo de campo (la API lo deja: ADMIN_O_MAYORDOMO).
        "Campo": CAMPO,
        "Reportes": [
            *REPORTES,
            ("pages/tablero_kpis.py", "Resultados de la junta", ":material/monitoring:"),
        ],
        "Administración": [
            ("pages/catalogos.py", "Catálogos", ":material/list_alt:"),
            ("pages/trazabilidad.py", "Trazabilidad y Excel", ":material/history:"),
        ],
    },
    # Junta: todo solo lectura (estas pantallas no tienen formularios).
    "junta": [
        ("pages/tablero_kpis.py", "Resultados del periodo", ":material/monitoring:"),
        *REPORTES,
    ],
    "superusuario": [
        ("pages/usuarios.py", "Usuarios", ":material/group:"),
        ("pages/auditoria.py", "Auditoría", ":material/history:"),
    ],
}


def paginas(pantallas):
    """st.Page de cada pantalla (la primera de todas es la inicial), en lista o por secciones."""
    primera = True

    def pagina(ruta, titulo, icono):
        nonlocal primera
        p = st.Page(ruta, title=titulo, icon=icono, default=primera)
        primera = False
        return p
    if isinstance(pantallas, dict):
        return {seccion: [pagina(*x) for x in lista] for seccion, lista in pantallas.items()}
    return [pagina(*x) for x in pantallas]


def acceso() -> None:
    """Pantalla de acceso: marca, eslogan, campos e ilustración; Soagro al pie."""
    st.image(str(ui.LOGO), width=210)
    st.subheader("Los datos de tu finca, aliados para crecer")

    campos, ilustracion = st.columns([2, 3], gap="large")
    with campos:
        with st.form("acceso", border=True):        # clear_on_submit=False: lo digitado se queda
            usuario = st.text_input("Usuario", key="acceso_usuario", autocomplete="username")
            clave = st.text_input("Clave", type="password", key="acceso_clave",
                                  autocomplete="current-password")
            entrar = st.form_submit_button("Ingresar", type="primary", width="stretch")
        if entrar:
            if not usuario.strip() or not clave:
                st.error("Escribe tu usuario y tu clave", icon=":material/error:")
            else:
                try:
                    st.session_state["usuario"] = api.login(usuario.strip(), clave)
                except api.ErrorApi as e:
                    st.error(e.detalle, icon=":material/error:")
                else:
                    st.rerun()
    with ilustracion:
        st.image(str(ui.ASSETS / "fondos" / "portada_cafetal.webp"), width="stretch")

    st.write("")
    pie, _ = st.columns([1, 5])
    pie.caption("Una herramienta de")
    pie.image(str(ui.ASSETS / "soagro" / "logo_original_oscuro.png"), width=110)


def cerrar_sesion() -> None:
    st.session_state.clear()
    api.refrescar_listas()


usuario = st.session_state.get("usuario")

if usuario is None:
    st.navigation([st.Page(acceso, title="Acceso", url_path="acceso")], position="hidden").run()
    st.stop()

if usuario["rol"] not in PANTALLAS:
    cerrar_sesion()
    st.error(f"El rol «{usuario['rol']}» no tiene pantallas asignadas. Inicia sesión de nuevo.")
    st.stop()

pagina = st.navigation(paginas(PANTALLAS[usuario["rol"]]), position="sidebar", expanded=True)  # sin «ver más»

with st.sidebar:
    st.button("Cerrar sesión", icon=":material/logout:", on_click=cerrar_sesion, width="stretch")

ui.encabezado(usuario)
ui.aviso_guardado()
pagina.run()
