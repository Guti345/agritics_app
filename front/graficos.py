"""Tema de Plotly para Agritics y colores por entidad.

Paleta categórica: abre con el verde hoja de la marca y sigue con tonos validados con el
validador de la guía de visualización (orden que pasa las pruebas de daltonismo entre
series vecinas sobre superficie blanca). Amarillo y rosado quedan bajo 3:1 de contraste:
por eso cada gráfico lleva leyenda y su tabla al lado.

Reglas: el color sigue a la entidad (un lote siempre tiene el mismo color, aunque se
filtre); los textos van en tinta de la marca, nunca del color de la serie; separadores
colombianos (coma decimal, punto de miles).
"""

from datetime import date

import plotly.graph_objects as go
import streamlit as st

TINTA = "#004846"          # verde oscuro: textos, ejes y línea principal
ARENA = "#EBE2DD"          # cuadrícula y divisiones
PAPEL = "#FFFFFF"          # superficie lisa para gráficas (guía, sección 6)
SERIES = ["#009C48", "#2a78d6", "#eb6834", "#6250d6", "#e87ba4", "#eda100", "#e34948"]

PRODUCTOS = {"mojado": "Mojado", "pasilla": "Pasilla", "pergamino": "Pergamino"}
COLOR_PRODUCTO = {"pergamino": SERIES[0], "mojado": SERIES[1], "pasilla": SERIES[2]}
SIMBOLO_PRODUCTO = {"pergamino": "circle", "mojado": "square", "pasilla": "diamond"}


def colores(nombres) -> dict[str, str]:
    """Color fijo por entidad (orden alfabético del catálogo completo, no del filtro)."""
    return {n: SERIES[i % len(SERIES)] for i, n in enumerate(sorted(set(nombres)))}


def tema(fig: go.Figure, alto: int = 380, titulo_y: str | None = None) -> go.Figure:
    fig.update_layout(
        height=alto, paper_bgcolor=PAPEL, plot_bgcolor=PAPEL, separators=",.",
        font=dict(family="Montserrat, Arial, sans-serif", size=13, color=TINTA),
        margin=dict(l=10, r=10, t=30, b=10), hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title_text=""),
        bargap=0.15, hoverlabel=dict(font_family="Montserrat, Arial, sans-serif"),
    )
    fig.update_xaxes(showgrid=False, linecolor=ARENA, tickcolor=ARENA)
    fig.update_yaxes(gridcolor=ARENA, zerolinecolor=ARENA)
    if titulo_y is not None:              # sin título: se respeta el que ya traiga el gráfico
        fig.update_yaxes(title_text=titulo_y)
    return fig


MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def eje_meses(fig: go.Figure, desde: date, hasta: date) -> go.Figure:
    """Eje de fechas con los meses en español (Plotly solo trae inglés sin su paquete de idioma)."""
    marcas, d = [], date(desde.year, desde.month, 1)
    while d <= hasta:
        marcas.append(d)
        d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    fig.update_xaxes(tickvals=marcas, ticktext=[f"{MESES[m.month - 1]}" + (f" {m.year}" if m.month == 1 else "")
                                                for m in marcas],
                     hoverformat="%d/%m/%Y")   # sin nombres de mes en inglés en la ventana flotante
    return fig


def mostrar(fig: go.Figure, key: str | None = None) -> None:
    st.plotly_chart(fig, width="stretch", key=key,
                    config={"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]})
