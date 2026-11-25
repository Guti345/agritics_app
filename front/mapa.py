"""Mapa de la finca, reutilizable (inicio del mayordomo; después junta y administrador).

    import mapa
    mapa.mapa_finca(semana="2026-W46", key="inicio_mapa")

- Lotes: GET /lotes (cada uno con su `poligono` GeoJSON, Polygon o MultiPolygon). El
  perímetro de la finca NO es un lote: se lee de back/datos_finca.geojson
  (feature con properties.tipo == "perimetro") y va solo como línea gruesa.
- Mapa base OpenStreetMap (con carreteras, sin satélite y sin token): go.Scattermap con
  map_style="open-street-map". (Plotly 7 retiró Scattermapbox; Scattermap es su reemplazo
  directo, con MapLibre.)
- Un trazo relleno por lote (fill="toself"); los huecos del polígono (Bosque Natural rodea
  a otros lotes) se cosen al borde exterior para que el relleno no se monte encima de ellos.
- Rótulo de cada lote en un punto interior (no solo en la ventanita del mouse). Ese punto
  también es un botón: al tocarlo se elige el lote. Además hay un selector encima del mapa.
- Al lado: lo que se hace en el lote elegido en la semana (planeadas y reales, sin estados
  duplicados) y los kilos recogidos, si hubo.
"""

import json
import math
from html import escape
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import api
import campo
import ui

GEOJSON = Path(__file__).resolve().parents[1] / "back" / "datos_finca.geojson"

TINTA, HOJA, BROTE, MARFIL, ARENA = "#004846", "#009C48", "#00C94B", "#FFF4E8", "#EBE2DD"
CULTIVO = {  # color de relleno, opacidad, nombre en la leyenda
    "cafe": (HOJA, 0.55, "Café"),
    "platano": (BROTE, 0.6, "Plátano"),
    "bosque": (TINTA, 0.38, "Bosque"),
}
NOMBRE_CULTIVO = {"cafe": "Café", "platano": "Plátano", "bosque": "Bosque"}


# ── geometría ──────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def perimetro() -> list | None:
    """Anillo exterior del perímetro de la finca, o None si el archivo no está."""
    try:
        datos = json.loads(GEOJSON.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    for f in datos.get("features", []):
        if f.get("properties", {}).get("tipo") == "perimetro":
            g = f["geometry"]
            return g["coordinates"][0] if g["type"] == "Polygon" else max(
                (p[0] for p in g["coordinates"]), key=lambda r: abs(_area(r)))
    return None


def piezas(geometria: dict) -> list[list]:
    """Polígonos de la geometría: [[exterior, *huecos], ...]."""
    return [geometria["coordinates"]] if geometria["type"] == "Polygon" else geometria["coordinates"]


def _area(anillo: list) -> float:
    return sum(x1 * y2 - x2 * y1 for (x1, y1, *_), (x2, y2, *_) in zip(anillo, anillo[1:])) / 2


def _coser(poligono: list) -> list:
    """Un solo anillo con los huecos cosidos al exterior por el par de vértices más cercano
    (un 'ojo de cerradura'): así fill="toself" deja los huecos vacíos."""
    anillo = [tuple(p[:2]) for p in poligono[0]]
    for hueco in poligono[1:]:
        h = [tuple(p[:2]) for p in hueco[:-1]]
        i, j = min(((i, j) for i in range(len(anillo)) for j in range(len(h))),
                   key=lambda ij: (anillo[ij[0]][0] - h[ij[1]][0]) ** 2 + (anillo[ij[0]][1] - h[ij[1]][1]) ** 2)
        anillo = anillo[:i + 1] + h[j:] + h[:j + 1] + anillo[i:]
    return anillo


def _dentro(x: float, y: float, anillo: list) -> bool:
    adentro = False
    for (x1, y1, *_), (x2, y2, *_) in zip(anillo, anillo[1:]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            adentro = not adentro
    return adentro


def _distancia_borde(x: float, y: float, anillos: list) -> float:
    mejor = math.inf
    for anillo in anillos:
        for (x1, y1, *_), (x2, y2, *_) in zip(anillo, anillo[1:]):
            dx, dy = x2 - x1, y2 - y1
            t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy or 1)))
            mejor = min(mejor, math.hypot(x - x1 - t * dx, y - y1 - t * dy))
    return mejor


def punto_rotulo(geometria: dict) -> tuple[float, float]:
    """Punto bien adentro de la pieza más grande (lejos de bordes y fuera de los huecos):
    el centroide de un lote cóncavo o con huecos puede caer afuera."""
    poligono = max(piezas(geometria), key=lambda p: abs(_area(p[0])))
    xs, ys = [p[0] for p in poligono[0]], [p[1] for p in poligono[0]]
    mejor, punto, n = -1.0, (sum(xs) / len(xs), sum(ys) / len(ys)), 36
    for a in range(1, n):
        for b in range(1, n):
            x = min(xs) + (max(xs) - min(xs)) * a / n
            y = min(ys) + (max(ys) - min(ys)) * b / n
            if _dentro(x, y, poligono[0]) and not any(_dentro(x, y, h) for h in poligono[1:]):
                d = _distancia_borde(x, y, poligono)
                if d > mejor:
                    mejor, punto = d, (x, y)
    return punto


def encuadre(lons: list[float], lats: list[float], ancho: int, alto: int) -> tuple[dict, float]:
    """Centro y zoom para que todo quepa (proyección web Mercator, teselas de 512 px en MapLibre)."""
    centro = {"lon": (min(lons) + max(lons)) / 2, "lat": (min(lats) + max(lats)) / 2}
    estirar = 1 / math.cos(math.radians(centro["lat"]))
    zx = math.log2(ancho * 360 / (512 * (max(lons) - min(lons))))
    zy = math.log2(alto * 360 / (512 * (max(lats) - min(lats)) * estirar))
    return centro, round(min(zx, zy) - 0.25, 2)


def _rgba(color: str, opacidad: float) -> str:
    return f"rgba({int(color[1:3], 16)},{int(color[3:5], 16)},{int(color[5:7], 16)},{opacidad})"


# ── figura ─────────────────────────────────────────────────────────────────────

def _cultivo(lote: dict) -> str:
    return next((c for c in ("cafe", "platano", "bosque") if c in lote["cultivos"]), "cafe")


def figura(lotes: list[dict], elegido: str | None, alto: int = 520) -> go.Figure:
    """Mapa con el perímetro, los lotes rellenos y sus rótulos. `elegido`: id del lote resaltado.
    El último trazo son los rótulos (puntos que se pueden tocar), en el orden de `lotes`."""
    fig = go.Figure()
    en_leyenda = set()
    for l in sorted(lotes, key=lambda l: _cultivo(l) != "bosque"):        # el bosque abajo de todo
        c = _cultivo(l)
        color, opacidad, nombre = CULTIVO[c]
        resaltado = l["id"] == elegido
        lon, lat = [], []
        for poligono in piezas(l["poligono"]):
            anillo = _coser(poligono)
            lon += [p[0] for p in anillo] + [None]
            lat += [p[1] for p in anillo] + [None]
        fig.add_trace(go.Scattermap(
            lon=lon[:-1], lat=lat[:-1], mode="lines", fill="toself", name=nombre, legendgroup=c,
            showlegend=c not in en_leyenda, fillcolor=_rgba(color, min(opacidad + (0.3 if resaltado else 0), 0.92)),
            line=dict(color=TINTA if resaltado else (MARFIL if c != "bosque" else _rgba(TINTA, 0)),
                      width=4 if resaltado else (1.5 if c != "bosque" else 0)),
            hoverinfo="skip"))
        en_leyenda.add(c)

    borde = perimetro()
    if borde:
        fig.add_trace(go.Scattermap(lon=[p[0] for p in borde], lat=[p[1] for p in borde], mode="lines",
                                    line=dict(color=TINTA, width=4), name="Perímetro de la finca", hoverinfo="skip"))

    puntos = [punto_rotulo(l["poligono"]) for l in lotes]
    texto_hover = [f"<b>{escape(l['nombre'])}</b><br>{NOMBRE_CULTIVO[_cultivo(l)]}"
                   + (f" · {escape(l['variedad'])}" if l.get("variedad") else "")
                   + f"<br>{ui.numero(l['area_ha'], 2)} ha (catálogo)<br><i>Toca para ver la semana</i>"
                   for l in lotes]
    fig.add_trace(go.Scattermap(       # anillo oscuro bajo cada rótulo
        lon=[p[0] for p in puntos], lat=[p[1] for p in puntos], mode="markers", hoverinfo="skip", showlegend=False,
        marker=dict(size=[17 if l["id"] == elegido else 13 for l in lotes], color=TINTA)))
    fig.add_trace(go.Scattermap(
        lon=[p[0] for p in puntos], lat=[p[1] for p in puntos], mode="markers+text", showlegend=False,
        text=[l["nombre"] for l in lotes], textposition="top center", customdata=[l["id"] for l in lotes],
        textfont=dict(size=13, color=TINTA, family="Open Sans Bold"),
        marker=dict(size=[11 if l["id"] == elegido else 8 for l in lotes],
                    color=[BROTE if l["id"] == elegido else MARFIL for l in lotes]),
        hovertext=texto_hover, hovertemplate="%{hovertext}<extra></extra>"))

    todos = borde or [p for l in lotes for pz in piezas(l["poligono"]) for p in pz[0]]
    centro, zoom = encuadre([p[0] for p in todos], [p[1] for p in todos], ancho=760, alto=alto)
    fig.update_layout(
        map=dict(style="open-street-map", center=centro, zoom=zoom),
        height=alto, margin=dict(l=0, r=0, t=0, b=0), separators=",.", paper_bgcolor=MARFIL,
        font=dict(family="Montserrat, Arial, sans-serif", color=TINTA),
        hoverlabel=dict(bgcolor="#FFFFFF", font=dict(family="Montserrat, Arial, sans-serif", color=TINTA)),
        legend=dict(x=0.01, y=0.02, yanchor="bottom", bgcolor=_rgba("#FFFFFF", 0.88), bordercolor=ARENA, borderwidth=1,
                    font=dict(size=12)),
        clickmode="event+select", dragmode="pan",
    )
    return fig


# ── mapa coloreado por un valor (p. ej. margen estimado por lote) ──────────────

ESCALA = [(0.0, ARENA), (0.5, HOJA), (1.0, TINTA)]    # bajo -> alto (paleta Agritics)


def _color_en(t: float) -> str:
    """Color de la ESCALA en t (0-1), interpolado en RGB."""
    for (t0, c0), (t1, c1) in zip(ESCALA, ESCALA[1:]):
        if t <= t1:
            f = (t - t0) / (t1 - t0) if t1 > t0 else 0
            rgb = [round(int(c0[i:i + 2], 16) + f * (int(c1[i:i + 2], 16) - int(c0[i:i + 2], 16))) for i in (1, 3, 5)]
            return "#" + "".join(f"{v:02X}" for v in rgb)
    return ESCALA[-1][1]


def figura_por_valor(lotes: list[dict], valores: dict[str, float], titulo: str, detalle: dict[str, str] | None = None,
                     alto: int = 480) -> go.Figure:
    """Mapa con cada lote relleno según su valor (escala #EBE2DD bajo -> #009C48 -> #004846 alto),
    el perímetro y rótulos visibles con nombre y valor. `valores`: {lote_id: valor}; los lotes
    sin valor (p. ej. el bosque) van en gris claro. `detalle`: texto extra para la ventanita."""
    con_valor = [v for v in valores.values() if v is not None]
    bajo, alto_v = (min(con_valor), max(con_valor)) if con_valor else (0, 0)
    t_de = lambda v: 0.5 if alto_v == bajo else (v - bajo) / (alto_v - bajo)  # noqa: E731
    fig = go.Figure()
    for l in sorted(lotes, key=lambda l: l["id"] in valores):                  # los grises abajo
        lon, lat = [], []
        for poligono in piezas(l["poligono"]):
            anillo = _coser(poligono)
            lon += [p[0] for p in anillo] + [None]
            lat += [p[1] for p in anillo] + [None]
        v = valores.get(l["id"])
        relleno = _rgba(_color_en(t_de(v)), 0.85) if v is not None else _rgba(ARENA, 0.45)
        fig.add_trace(go.Scattermap(lon=lon[:-1], lat=lat[:-1], mode="lines", fill="toself", fillcolor=relleno,
                                    line=dict(color=MARFIL, width=1.5), hoverinfo="skip", showlegend=False))
    borde = perimetro()
    if borde:
        fig.add_trace(go.Scattermap(lon=[p[0] for p in borde], lat=[p[1] for p in borde], mode="lines",
                                    line=dict(color=TINTA, width=4), hoverinfo="skip", showlegend=False))

    # Rótulos: nombre y valor en cada lote. Texto claro sobre los rellenos oscuros y oscuro sobre
    # los claros (Scattermap no deja un color de texto por punto: van en dos trazos).
    puntos = {l["id"]: punto_rotulo(l["poligono"]) for l in lotes}
    for oscuro in (False, True):
        grupo = [l for l in lotes if (valores.get(l["id"]) is not None and t_de(valores[l["id"]]) > 0.55) == oscuro]
        if not grupo:
            continue
        fig.add_trace(go.Scattermap(
            lon=[puntos[l["id"]][0] for l in grupo], lat=[puntos[l["id"]][1] for l in grupo], mode="text",
            text=[f"{l['nombre']}<br>{ui.pesos(valores[l['id']]) if valores.get(l['id']) is not None else '—'}"
                  for l in grupo],
            textfont=dict(size=12, color=MARFIL if oscuro else TINTA, family="Open Sans Bold"),
            hovertext=[f"<b>{escape(l['nombre'])}</b><br>{titulo}: "
                       + (ui.pesos(valores[l['id']]) if valores.get(l["id"]) is not None else "sin valor")
                       + ((detalle or {}).get(l["id"], "")) for l in grupo],
            hovertemplate="%{hovertext}<extra></extra>", showlegend=False))
    if con_valor:                                                             # barra de color
        fig.add_trace(go.Scattermap(
            lon=[puntos[next(iter(valores))][0]] * 2, lat=[puntos[next(iter(valores))][1]] * 2, mode="markers",
            marker=dict(size=0.1, color=[bajo, alto_v], cmin=bajo, cmax=alto_v, showscale=True,
                        colorscale=[[t, c] for t, c in ESCALA],
                        colorbar=dict(title=dict(text=titulo, side="top"), tickformat="$,.0f", thickness=10,
                                      orientation="h", x=0.02, xanchor="left", y=0.98, yanchor="top", len=0.62,
                                      bgcolor=_rgba("#FFFFFF", 0.88), outlinewidth=0, nticks=5,
                                      tickfont=dict(size=11))),
            hoverinfo="skip", showlegend=False))

    todos = borde or [p for l in lotes for pz in piezas(l["poligono"]) for p in pz[0]]
    centro, zoom = encuadre([p[0] for p in todos], [p[1] for p in todos], ancho=560, alto=alto)
    fig.update_layout(
        map=dict(style="open-street-map", center=centro, zoom=zoom),
        height=alto, margin=dict(l=0, r=0, t=0, b=0), separators=",.", paper_bgcolor=MARFIL,
        font=dict(family="Montserrat, Arial, sans-serif", color=TINTA),
        hoverlabel=dict(bgcolor="#FFFFFF", font=dict(family="Montserrat, Arial, sans-serif", color=TINTA)),
        dragmode="pan",
    )
    return fig


def lotes_con_poligono() -> list[dict]:
    return sorted((l for l in ui.leer(lambda: api.lista("/lotes")) if l.get("poligono")), key=lambda l: l["nombre"])


# ── resumen del lote ───────────────────────────────────────────────────────────

def resumen_lote(lote: dict, semana: str) -> None:
    """Lo que se hace en el lote en la semana: planeadas y reales (una ficha por labor, con su
    estado de mayor rango) y, si hubo recolección, los kilos."""
    dias = ui.dias_de(semana)
    st.markdown(f"#### {lote['nombre']}")
    st.caption(f"{NOMBRE_CULTIVO[_cultivo(lote)]}" + (f" · {lote['variedad']}" if lote.get("variedad") else "")
               + f" · {ui.numero(lote['area_ha'], 2)} ha · {ui.rotulo_semana(semana)}")

    crono = campo.cronograma(semana)
    por_dia = [(ui.a_fecha(d["fecha"]), fichas) for d in crono["dias"] for l in d["lotes"]
               if l["lote_id"] == lote["id"] for fichas in [campo.unificar(l)] if fichas]

    kilos = []
    if set(lote["cultivos"]) & {"cafe", "platano"}:
        r1 = ui.leer(lambda: api.get("/reportes/r1-produccion", desde=dias[0], hasta=dias[-1], lote_id=lote["id"]))
        cafe = sum(p["kg"] for p in r1["por_lote"] if p["lote_id"] == lote["id"])
        platano = [p for p in r1["platano"] if p["lote_id"] == lote["id"]]
        if cafe:
            kilos.append(("Café cereza recogido", ui.kg(cafe, 0), None))
        if platano:
            kilos.append(("Plátano cosechado", ui.kg(sum(p["kg"] for p in platano), 0),
                          f"{ui.numero(sum(p['racimos'] for p in platano))} racimos"))

    if not por_dia and not kilos:
        st.info("Sin trabajo registrado esta semana.", icon=":material/event_busy:")
        return
    for rotulo, valor, nota in kilos:
        ui.cifra_grande(f"{rotulo} esta semana", valor, nota or "")
    if por_dia:
        n = sum(len(f) for _, f in por_dia)
        st.caption(f"{n} {'labor' if n == 1 else 'labores'} en la semana")
        st.html(campo.LEYENDA + "".join(
            f"<div class='ag-lote'>{ui.dia_corto(dia)}</div>"
            + "".join(campo.ficha(f"{f['trabajador']} · {f['labor']}", f) for f in fichas)
            for dia, fichas in por_dia))


def resumen_finca(lotes: list[dict], semana: str) -> None:
    """Sin lote elegido: cuántas labores y kilos tuvo cada lote en la semana."""
    dias = ui.dias_de(semana)
    crono = campo.cronograma(semana)
    r1 = ui.leer(lambda: api.get("/reportes/r1-produccion", desde=dias[0], hasta=dias[-1]))
    labores = {}
    for d in crono["dias"]:
        for l in d["lotes"]:
            labores[l["lote_id"]] = labores.get(l["lote_id"], 0) + len(campo.unificar(l))
    kilos = {p["lote_id"]: p["kg"] for p in r1["por_lote"]}
    for p in r1["platano"]:
        kilos[p["lote_id"]] = kilos.get(p["lote_id"], 0) + p["kg"]
    st.markdown("#### La finca esta semana")
    st.caption(f"{ui.rotulo_semana(semana)} · toca un rótulo del mapa o elige un lote para ver el detalle")
    ui.tabla(pd.DataFrame([{"Lote": l["nombre"], "Labores": labores.get(l["id"], 0), "Kg recogidos": kilos.get(l["id"], 0)}
                           for l in sorted(lotes, key=lambda l: (-labores.get(l["id"], 0), l["nombre"]))]),
             kilos=["Kg recogidos"], cifras=["Labores"], width="stretch")


# ── componente ─────────────────────────────────────────────────────────────────

def mapa_finca(semana: str, key: str = "mapa", alto: int = 520) -> None:
    """Mapa de la finca con el resumen de la semana `semana` ('2026-W46') por lote."""
    lotes = sorted((l for l in ui.leer(lambda: api.lista("/lotes")) if l.get("poligono")), key=lambda l: l["nombre"])
    if not lotes:
        ui.sin_datos("Los lotes todavía no tienen su polígono: el mapa aparece cuando se carguen.")
        return
    por_nombre = {l["nombre"]: l for l in lotes}
    clave_lote, clave_grafico, clave_clic = f"{key}_lote", f"{key}_grafico", f"{key}_clic"

    # Un toque en un rótulo del mapa elige ese lote (solo si es un toque nuevo: si no, el
    # selector manda). Se aplica antes de dibujar el selector.
    puntos = ((st.session_state.get(clave_grafico) or {}).get("selection") or {}).get("points") or []
    if puntos:
        tocado = puntos[0].get("customdata")
        tocado = tocado[0] if isinstance(tocado, list) else tocado
        firma = json.dumps(puntos[0], sort_keys=True, default=str)
        if firma != st.session_state.get(clave_clic):
            st.session_state[clave_clic] = firma
            nombre = next((l["nombre"] for l in lotes if l["id"] == tocado), None)
            if nombre:
                st.session_state[clave_lote] = nombre

    izq, der = st.columns([3, 2], gap="medium")
    elegido = por_nombre.get(der.selectbox("Lote", list(por_nombre), index=None, key=clave_lote,
                                           placeholder="Toca un rótulo del mapa o elígelo aquí"))
    with izq:
        st.plotly_chart(figura(lotes, elegido["id"] if elegido else None, alto), key=clave_grafico,
                        on_select="rerun", selection_mode="points", width="stretch",
                        config={"displaylogo": False, "scrollZoom": True,
                                "modeBarButtonsToRemove": ["lasso2d", "select2d"]})
        if "Bosque Natural" in por_nombre:
            st.caption("Bosque Natural: polígono aproximado (el perímetro menos los lotes; incluye caminos y la "
                       f"casa). Su área oficial es la del catálogo: {ui.numero(por_nombre['Bosque Natural']['area_ha'], 2)} ha.")
    with der:
        if elegido:
            resumen_lote(elegido, semana)
        else:
            resumen_finca(lotes, semana)
