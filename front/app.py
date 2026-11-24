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
PANTALLAS = {
    "mayordomo": [
        ("pages/captura.py", "Captura rápida", ":material/edit_note:"),
    ],
    "administrador": [
        ("pages/tablero_semana.py", "Tablero de la semana", ":material/calendar_view_week:"),
    ],
    "junta": [
        ("pages/tablero_kpis.py", "Tablero de KPIs", ":material/monitoring:"),
    ],
    "superusuario": [
        ("pages/usuarios.py", "Usuarios", ":material/group:"),
    ],
}


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

pagina = st.navigation(
    [st.Page(ruta, title=titulo, icon=icono, default=(i == 0))
     for i, (ruta, titulo, icono) in enumerate(PANTALLAS[usuario["rol"]])],
    position="sidebar",
)

with st.sidebar:
    st.button("Cerrar sesión", icon=":material/logout:", on_click=cerrar_sesion, width="stretch")

ui.encabezado(usuario)
ui.aviso_guardado()
pagina.run()
