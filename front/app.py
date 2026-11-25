"""Agritics: entrada de la app (streamlit run front/app.py).

Sin iniciar sesión no se ve nada: la única página que existe es el acceso. Al entrar,
cada rol recibe SOLO sus pantallas (st.navigation) y cae en su pantalla inicial.
"""

from pathlib import Path

import streamlit as st
from PIL import Image

import api
import ui

st.set_page_config(page_title="Agritics", page_icon=Image.open(ui.ICONO_APP), layout="wide")
ui.estilos()

# Pantallas por rol; la primera es la inicial. Las rutas son relativas a este archivo.
# Un rol puede tener secciones ({sección: [pantallas]}) o una lista simple.
# Campo del administrador: las mismas pantallas del mayordomo, con los mismos títulos.
CAMPO = [
    ("pages/captura.py", "Registro", ":material/edit_note:"),
    ("pages/trabajadores.py", "Trabajadores", ":material/groups:"),
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
ADMINISTRADOR = {
    "": [("pages/inicio_admin.py", "Inicio", ":material/home:")],   # su pantalla inicial, sin título de sección
    "La semana": [
        ("pages/tablero_semana.py", "Tablero de la semana", ":material/calendar_view_week:"),
        ("pages/cortes.py", "Pagar nómina", ":material/payments:"),
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
}
PANTALLAS = {
    "mayordomo": MAYORDOMO,                    # sin reportes
    "administrador": ADMINISTRADOR,
    # Junta: todo solo lectura (estas pantallas no tienen formularios).
    "junta": [
        ("pages/tablero_kpis.py", "Resultados del periodo", ":material/monitoring:"),
        *REPORTES,
    ],
    # Superusuario: lo de la junta (cae en Resultados del periodo), los catálogos y lo del sistema.
    "superusuario": {
        "Reportes": [
            ("pages/tablero_kpis.py", "Resultados del periodo", ":material/monitoring:"),
            *REPORTES,
        ],
        "Administración": [
            ("pages/catalogos.py", "Catálogos", ":material/list_alt:"),
        ],
        "Sistema": [
            ("pages/usuarios.py", "Usuarios", ":material/group:"),
            ("pages/auditoria.py", "Auditoría", ":material/history:"),
        ],
    },
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


IMAGEN_LOGIN = ui.ASSETS / "fondos" / "login_cafetal.jpg"          # ruta oficial: front/assets/fondos/
IMAGEN_LOGIN_RESPALDO = ui.ASSETS / "fondos" / "portada_cafetal.webp"


def imagen_login() -> Path:
    """La ilustración del login (front/assets/fondos/login_cafetal.jpg); si no está, la de siempre."""
    return IMAGEN_LOGIN if IMAGEN_LOGIN.exists() else IMAGEN_LOGIN_RESPALDO


def acceso() -> None:
    """Pantalla de acceso: marca, eslogan, campos y Soagro al pie a la izquierda; la ilustración
    llena toda la columna derecha, de borde a borde y a toda la altura de la ventana."""
    st.html(CSS_LOGIN)
    campos, ilustracion = st.columns([2, 3], gap="large")
    with campos.container(key="login_campos"):
        st.image(str(ui.LOGO), width=210)
        st.subheader("Los datos de tu finca, aliados para crecer")
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
        st.write("")
        st.caption("Una herramienta de")
        st.image(str(ui.SOAGRO), width=150)                    # logo de Soagro sin fondo
    with ilustracion.container(key="login_imagen"):
        st.image(str(imagen_login()), width="stretch")


# Solo en el acceso: sin el encabezado de Streamlit y sin márgenes arriba, a la derecha ni abajo,
# para que la ilustración toque esos tres bordes de la ventana (recorta sin deformar: object-fit
# cover). El formulario conserva su margen superior normal.
CSS_LOGIN = """
<style>
[data-testid="stHeader"] {display: none;}
[data-testid="stMain"], [data-testid="stAppViewContainer"] {padding-top: 0 !important;}
[data-testid="stMainBlockContainer"] {padding-top: 0; padding-right: 0; padding-bottom: 0; max-width: 100%;}
.st-key-login_campos {padding-top: 1.5rem;}
.st-key-login_imagen, .st-key-login_imagen [data-testid="stImage"],
.st-key-login_imagen [data-testid="stImageContainer"] {width: 100%; max-width: none;}
.st-key-login_imagen img {display: block; width: 100% !important; max-width: none !important;
  height: 100vh; object-fit: cover; object-position: center;
  border-radius: 0 !important; box-shadow: none !important; border: none !important;}
.st-key-login_imagen [data-testid="stElementToolbar"], .st-key-login_imagen button {display: none !important;}
</style>
"""


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

# Barra lateral: la marca arriba (st.logo, nativo), el menú del rol en medio, cerrar sesión y,
# pegado al fondo, «Una herramienta de» + Soagro.
st.logo(str(ui.LOGO), size="large", icon_image=str(ui.ICONO_APP))
with st.sidebar:
    st.button("Cerrar sesión", icon=":material/logout:", on_click=cerrar_sesion, width="stretch")
    with st.container(key="sidebar_pie"):
        st.caption("Una herramienta de")
        st.image(str(ui.SOAGRO), width=120)

ui.encabezado(usuario)
ui.aviso_guardado()
pagina.run()
