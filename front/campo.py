"""Piezas de campo que comparten varias pantallas: crear trabajador, el pool de la semana
y las fichas del cronograma SIN estados duplicados.

Regla de las fichas: cada labor (trabajador + labor, en un lote y un día) se muestra UNA
sola vez, con el estado de mayor rango: completada > abierta > planeada. Una planeada que
ya se cumplió (hay una labor real que coincide) deja de aparecer como planeada.
"""

from datetime import date
from html import escape

import streamlit as st

import api
import ui

RANGO = {"planeada": 0, "abierta": 1, "completada": 2}

LEYENDA = ("<div class='ag-leyenda'>"
           "<span class='ag-chip plan'>Planeada</span>"
           "<span class='ag-chip real abierta'>Abierta</span>"
           "<span class='ag-chip real completada'>Completada</span></div>")


# ── fichas del cronograma ──────────────────────────────────────────────────────

def unificar(lote: dict) -> list[dict]:
    """Planeadas y reales de un lote en un día (un elemento de crono['dias'][i]['lotes'])
    -> una ficha por (trabajador, labor) con el estado de mayor rango."""
    fichas: dict[tuple, dict] = {}
    for p in lote["planeadas"]:
        fichas.setdefault((p["trabajador_id"], p["labor_id"]), {
            "trabajador_id": p["trabajador_id"], "trabajador": p["trabajador"], "labor_id": p["labor_id"],
            "labor": p["labor"], "estado": "planeada", "jornales": 0.0, "forma_pago": None, "planeada": True})
    for r in lote["reales"]:
        estado = "completada" if r["completada"] else "abierta"
        f = fichas.get((r["trabajador_id"], r["labor_id"]))
        if f is None:
            fichas[(r["trabajador_id"], r["labor_id"])] = {
                "trabajador_id": r["trabajador_id"], "trabajador": r["trabajador"], "labor_id": r["labor_id"],
                "labor": r["labor"], "estado": estado, "jornales": r["jornales"], "forma_pago": r["forma_pago"],
                "planeada": r["planeada"]}
            continue
        f["jornales"] += r["jornales"]
        f["forma_pago"] = f["forma_pago"] or r["forma_pago"]
        if RANGO[estado] > RANGO[f["estado"]]:
            f["estado"] = estado
    return sorted(fichas.values(), key=lambda f: (-RANGO[f["estado"]], f["trabajador"], f["labor"]))


def lotes_del_dia(dia: dict, lote: str | None = None) -> list[tuple[str, list[dict]]]:
    """[(nombre del lote, fichas)] de un día del cronograma, opcionalmente de un solo lote."""
    return [(l["lote"], unificar(l)) for l in dia["lotes"] if lote is None or l["lote"] == lote]


def ficha(texto: str, f: dict, detalle: bool = True) -> str:
    """Ficha HTML: completada (verde oscuro), abierta (borde vivo) o planeada (blanca, borde punteado)."""
    if f["estado"] == "planeada":
        return f"<span class='ag-chip plan'>{escape(texto)}<small>planeada</small></span>"
    extra = ""
    if detalle:
        extra = " · " + ui.jornales(f["jornales"])
        if f["forma_pago"] == "contrato":
            extra += " · contrato"
        if not f["planeada"]:
            extra += " · sin plan"
    return f"<span class='ag-chip real {f['estado']}'>{escape(texto)}<small>{f['estado']}{escape(extra)}</small></span>"


def cronograma(semana: str) -> dict:
    """GET /reportes/cronograma de una semana (sin caché: lo registrado se ve ya)."""
    return ui.leer(lambda: api.get("/reportes/cronograma", semana=semana))


# ── trabajadores ───────────────────────────────────────────────────────────────

def form_trabajador() -> None:
    """Crear trabajador (nombre, documento, teléfono) y, si se marca, activarlo en el pool
    de la semana en curso en el mismo envío."""
    with st.form("nuevo_trabajador", border=False):
        nombre = st.text_input("Nombre", key="nt_nombre")
        documento = st.text_input("Documento (opcional)", key="nt_documento")
        telefono = st.text_input("Teléfono (opcional)", key="nt_telefono")
        activar = st.checkbox(f"Activarlo en el pool de esta semana ({ui.semana_en_curso()})", value=True,
                              key="nt_activar")
        if st.form_submit_button("Crear trabajador", type="primary", icon=":material/person_add:"):
            def crear_trabajador():
                """Devuelve el aviso. Si el trabajador se crea pero no se activa, el formulario se
                limpia igual (repetir el envío lo crearía dos veces) y el aviso lo dice."""
                t = api.post("/trabajadores", {"nombre": nombre, "documento": documento.strip() or None,
                                               "telefono": telefono.strip() or None})
                if not activar:
                    return f"Trabajador creado: {nombre.strip()}"
                try:
                    api.post("/pool/activar", {"trabajador_id": t["id"], "semana": ui.semana_iso()})
                except api.ErrorApi as e:
                    return (f"Trabajador creado: {nombre.strip()}, pero no quedó activo en el pool: {e.detalle}. "
                            "Actívalo en «Pool de trabajadores».")
                return f"Trabajador creado: {nombre.strip()} · activo en la {ui.semana_en_curso()}"
            ui.enviar(crear_trabajador, limpiar=["nt_nombre", "nt_documento", "nt_telefono"],
                      exito=lambda aviso: aviso, refrescar=True)


ROTULO_POOL = {"activo": "Activo", "desactivado": "Desactivado esta semana", "fuera": "Fuera del pool"}


def pool_trabajadores() -> None:
    """Pool de trabajadores de la semana en curso: quién está activo y quién no. Solo los
    activos aparecen en las listas de captura y pueden recibir labores."""
    semana = ui.semana_iso()
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
                        f"style='display:inline-block'>{ROTULO_POOL[e]}</span>")
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


def jueves(dia: date) -> date:
    """Jueves de la semana ISO del día: define a qué mes pertenece la semana (norma ISO)."""
    return date.fromisocalendar(*dia.isocalendar()[:2], 4)
