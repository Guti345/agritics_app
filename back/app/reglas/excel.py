"""Excel consolidado semanal (openpyxl), estilo la hoja "Ingresos vs Egresos" de la finca.

Se arma en memoria y se devuelve para descargar: no se guarda en disco ni en la base.
Hojas:
  1. "Ingresos vs Egresos": una fila por semana ISO del año hasta la semana pedida.
  2. "Detalle <semana>":    movimientos día a día de esa semana con el saldo de caja.
  3. "Nómina <semana>":     por trabajador (reporte R3).
Las celdas llevan valores (no fórmulas): el archivo muestra los números aunque se abra
en un programa que no recalcula.
"""

from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from back.app.schemas import ahora

VERDE, MARFIL = "004846", "FFF4E8"   # paleta de la marca Agritics
PESOS = '"$"#,##0;[Red]-"$"#,##0'
NUMERO = "#,##0.0"
_borde = Border(bottom=Side(style="thin", color="BBBBBB"))

COLUMNAS_SEMANAS = [
    ("Semana", None, 11), ("Desde", "fecha", 11), ("Hasta", "fecha", 11),
    ("Café", PESOS, 14), ("Plátano", PESOS, 13), ("Total ingresos", PESOS, 15),
    ("Nómina", PESOS, 13), ("Nómina (registrada como gasto)", PESOS, 15), ("Insumos", PESOS, 13),
    ("Servicios", PESOS, 13), ("Transporte", PESOS, 13), ("Casa", PESOS, 12), ("Otros", PESOS, 12),
    ("Total egresos", PESOS, 15), ("Margen", PESOS, 15),
    ("Aportes de capital", PESOS, 15), ("Retiros", PESOS, 13), ("Ajustes", PESOS, 12),
    ("Préstamos recibidos", PESOS, 15), ("Abonos a deuda", PESOS, 14), ("Pago de intereses", PESOS, 14),
    ("Flujo neto", PESOS, 15),
]

# Movimientos de caja (capital y deuda): nombre legible en la hoja de detalle.
MOVIMIENTOS = {"aporte_capital": "Aporte de capital", "retiro": "Retiro", "ajuste": "Ajuste",
               "prestamo_recibido": "Préstamo recibido", "abono_deuda": "Abono a deuda",
               "pago_intereses": "Pago de intereses"}


def _fila_semana(p: dict) -> list:
    i, g, c = p["ingresos"], p["gastos"], p["capital"]
    return [p["periodo"], p["desde"], p["hasta"], i["cafe"], i["platano"], i["total"],
            g["nomina"], g["nomina_registrada_como_gasto"], g["insumos"], g["servicios"], g["transporte"],
            g["casa"], g["otros"], g["total"], p["margen"], c["aportes"], c["retiros"], c["ajustes"],
            c.get("prestamos", 0), c.get("abonos_deuda", 0), c.get("intereses", 0), p["flujo_neto"]]


def _hoja(ws, titulo: str, subtitulo: str, columnas: list, filas: list[list], total: list | None = None) -> None:
    ws["A1"] = titulo
    ws["A1"].font = Font(bold=True, size=14, color=VERDE)
    ws["A2"] = subtitulo
    ws["A2"].font = Font(italic=True, size=9, color="666666")
    encabezado = 4
    for j, (nombre, _, ancho) in enumerate(columnas, start=1):
        celda = ws.cell(row=encabezado, column=j, value=nombre)
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor=VERDE)
        celda.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.column_dimensions[get_column_letter(j)].width = ancho
    ws.row_dimensions[encabezado].height = 32
    for i, fila in enumerate(filas + ([total] if total else []), start=encabezado + 1):
        es_total = total is not None and i == encabezado + len(filas) + 1
        for j, valor in enumerate(fila, start=1):
            celda = ws.cell(row=i, column=j, value=valor)
            formato = columnas[j - 1][1]
            if formato == "fecha":
                celda.number_format = "yyyy-mm-dd"
            elif formato:
                celda.number_format = formato
            celda.border = _borde
            if es_total:
                celda.font = Font(bold=True, color=VERDE)
                celda.fill = PatternFill("solid", fgColor="E2ECEB")
            elif (i - encabezado) % 2 == 0:
                celda.fill = PatternFill("solid", fgColor=MARFIL)
    ws.freeze_panes = ws.cell(row=encabezado + 1, column=2)


def consolidado_xlsx(semana: str, flujo_anio: dict, flujo_semana: dict, nomina_semana: dict) -> bytes:
    wb = Workbook()
    generado = f"Generado por Agritics el {ahora():%Y-%m-%d %H:%M} (hora de Colombia). Valores en pesos colombianos."

    ws = wb.active
    ws.title = "Ingresos vs Egresos"
    filas = [_fila_semana(p) for p in flujo_anio["semanas"]]
    total = _fila_semana({**flujo_anio["total"], "periodo": "TOTAL"})
    _hoja(ws, f"Finca Portugal · Ingresos vs Egresos {flujo_anio['hasta'].year} (hasta {semana})",
          generado + " Capital y deuda (aportes, retiros, ajustes, préstamos, abonos e intereses) van aparte, "
          "cada uno en su columna: no entran al margen.", COLUMNAS_SEMANAS, filas, total)

    ws = wb.create_sheet(f"Detalle {semana}")
    columnas = [("Fecha", "fecha", 11), ("Tipo", None, 10), ("Categoría", None, 26), ("Descripción", None, 40),
                ("Valor", PESOS, 15), ("Saldo de caja", PESOS, 16)]
    filas = [[flujo_semana["desde"], "", "", "Saldo inicial", None, flujo_semana["saldo_inicial"]]]
    filas += [[l["fecha"], l["tipo"], MOVIMIENTOS.get(l["categoria"], l["categoria"]) if l["tipo"] == "capital" else l["categoria"],
               l["descripcion"], l["valor"], l["saldo"]] for l in flujo_semana["detalle"]]
    _hoja(ws, f"Movimientos de caja día a día · {semana} ({flujo_semana['desde']:%Y-%m-%d} a {flujo_semana['hasta']:%Y-%m-%d})",
          generado, columnas, filas,
          [flujo_semana["hasta"], "", "", "Saldo final", flujo_semana["saldo_final"] - flujo_semana["saldo_inicial"],
           flujo_semana["saldo_final"]])

    ws = wb.create_sheet(f"Nómina {semana}")
    columnas = [("Trabajador", None, 24), ("Tipo", None, 12), ("Labores", None, 9), ("Jornales", NUMERO, 10),
                ("A pagar (neto de anticipos)", PESOS, 16), ("Pagado en cortes", PESOS, 15), ("Pendiente", PESOS, 13),
                ("Anticipos recibidos", PESOS, 15), ("Kg recolectados", NUMERO, 12), ("Costo por kg", PESOS, 12),
                ("Nómina causada", PESOS, 15)]
    filas = [[t["nombre"], t["tipo"], len(t["labores"]), t["jornales"], t["total_a_pagar"], t["pagado_en_cortes"],
              t["pendiente_por_pagar"], t["total_anticipos_recibidos"], t["kg_recolectados"], t["costo_por_kg"],
              t["nomina_causada"]] for t in nomina_semana["trabajadores"]]
    tr = nomina_semana["trabajadores"]
    total = ["TOTAL", "", sum(len(t["labores"]) for t in tr), sum(t["jornales"] for t in tr), nomina_semana["total_a_pagar"],
             sum(t["pagado_en_cortes"] for t in tr), sum(t["pendiente_por_pagar"] for t in tr),
             nomina_semana["total_anticipos_recibidos"], sum(t["kg_recolectados"] for t in tr), None,
             nomina_semana["total_nomina_causada"]]
    _hoja(ws, f"Nómina por trabajador · {semana}", generado + " " + nomina_semana["criterio_tipo"] + ".", columnas, filas, total)

    salida = BytesIO()
    wb.save(salida)
    return salida.getvalue()
