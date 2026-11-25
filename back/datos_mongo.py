"""Agritics · limpieza total + seed de un año cafetero (5 de enero - sábado 14 de noviembre de 2026)
y la coyuntura de la semana de la sustentación (16 de noviembre - 6 de diciembre). UNA corrida deja
TODO listo: no hay otro script de datos.

Uso (desde la raíz del repo):
    python back/datos_mongo.py              DRY-RUN: muestra qué borraría y qué cargaría. No toca nada.
    python back/datos_mongo.py --confirmar  Limpia (delete_many, sin drop) y carga todo.

Fase 1 · LIMPIEZA: corre back/init_db.py (idempotente), borra TODOS los documentos de TODAS
las colecciones (la lista sale de back/init_db.py) con delete_many({}) -validadores e
índices quedan intactos- y borra las fotos de prueba de fotos/ (conserva .gitkeep y los
placeholders del seed).
Fase 2 · SEED: inserta directo a Mongo, pero cada documento se arma con su DTO de
back/app/schemas/ (mismas validaciones que la API) y respeta las reglas de back/app/reglas/
(pool, regla estrella, stock, periodos cerrados, cortes y anticipos). random.seed fijo e ids
deterministas: --confirmar deja siempre el mismo mundo (la limpieza de la fase 1 borra cualquier
prueba anterior, así que correrlo dos veces deja lo mismo).
Coyuntura (misma corrida, a continuación del año; ver Mundo.coyuntura): solo labores, pool, el
corte de la W47 y un aporte de capital.
  - W47 (16-22/11): pool, labores completadas lunes a sábado y su corte del sábado 21/11 a las
    6:30 p. m. Como en la API, ese corte paga TODO lo completado sin corte hasta el 21/11: también
    las 38 labores de la W46 que el año deja pendientes a propósito.
  - W48 (23-29/11, la actual; hoy miércoles 25): pool; lunes y martes completadas SIN corte (las
    paga el administrador desde la app, en «Pagar nómina»); miércoles a viernes, planeadas
    (preasignación del pool).
  - W49 (30/11-6/12): pool activado el 25/11 y preasignación de lunes a sábado (programación futura).
  - Sin ventas, compras ni lluvias nuevas. Única excepción de caja: un aporte de capital el lunes
    16/11, redondo, para que la caja nunca quede negativa día a día desde el 16/11, aun restando lo
    que se pagará de la W48. Las labores de la coyuntura no consumen insumos y la recolección de
    plátano va sin cosecha ni venta registradas (solo la labor y sus kg).

═══════════════════════════════════════════════════════════════════════════════════════════
SUPUESTOS (cifra clave -> origen). "Dueño" = definido por la finca en el prompt del seed;
"Supuesto" = valor razonable elegido para simular, ajustable en las constantes de abajo.
═══════════════════════════════════════════════════════════════════════════════════════════
Calendario
  - Datos del lunes 5 ene (ISO 2026-W02) al sábado 14 nov 2026 (W46). W01 (29 dic-4 ene) sin datos.
  - Campo: lunes a sábado; domingo descanso (solo lecturas de lluvia).            [Dueño]
  - W02-W45 cortadas; W46 sin corte propio, con 3 labores sin completar (sus completadas las
    paga el corte de la W47 de la coyuntura).                                     [Dueño]
Lotes (área, variedad)                                                          [Dueño]
  - Portugal 2,40 ha Castillo | Oriente 1,60 Colombia | Villa Aurora 2,80 Castillo
  - Centro 0,60 Colombia | Madroño 1,55 Cenicafé | Minitas 2,50 Castillo | La Casa 2,40 Colombia
  - Baltimore 6,50 ha (Plátano Hartón) | Bosque Natural 4,65 ha (no_productivo)
  - Café: 13,85 ha en 7 lotes.
  - Polígonos (solo para el mapa) desde back/datos_finca.geojson (Google Earth Engine). El área
    oficial es la del catálogo: Bosque Natural lleva el polígono derivado (perímetro menos los
    lotes, ~6,65 ha con caminos y casa) como aproximación visual, pero sigue con 4,65 ha.
Tarifas de nómina                                                               [Dueño]
  - Jornal $80.000-$130.000 según la labor (guadaña $125.000); ver TARIFA_JORNAL.
  - Jornales por labor: 1 (70 %), 0,5 (22 %), 1,5 (5 %), 2 (3 %).                  [Supuesto]
  - Recolección de café a contrato ~$2.000/kg de cereza (promedio del administrador).
  - Recolección de plátano a contrato $100/kg.                                    [Supuesto]
  - Contratos "por labor completada": $/ha según labor (PRECIO_HA), p. ej. guadaña $260.000/ha. [Supuesto]
Productividad
  - Recolección: 40-160 kg de cereza por trabajador-día (3-12 kg/h).              [Dueño]
  - Rendimientos por jornal (ha/jornal): guadaña 0,5; plateo 0,35; fertilización 1,0... [Supuesto]
Estacionalidad del café (factor 0-1 por mes)                                    [Dueño]
  - Mitaca fuerte abr-may; cosecha principal oct-dic; valle jun-ago; ene y sep moderados.
  - Sin recolección en 6 semanas (W07, W28, W29, W31, W32, W34): café en 39 de 45 semanas.
Conversión y ventas de café
  - Cereza -> pergamino mojado x0,44; mojado -> pergamino seco equivalente x0,50
    (cereza:pergamino seco ~4,5:1).                                                 [Supuesto]
  - Pasilla: 0,8 % de la cereza, vendida en seco a ~$5.000/kg.                    [Supuesto]
  - Venta a la Cooperativa cada 1-3 semanas (2 por semana en pico), 2-8 sacos de ~62 kg. [Dueño]
  - Factor de rendimiento 100-105 (kg de pergamino seco por saco de 70 kg de excelso). [Dueño]
  - Precio por carga (125 kg pergamino seco eq.) $1.400.000-$1.900.000 según el mes (PRECIO_CARGA). [Dueño]
  - Descuentos del recibo: contribución cafetera 3 %, retención 0,5 %, broca >5 %: 0,6 % por punto. [Supuesto]
  - Broca 3-22 % (más alta en el valle).                                          [Dueño]
Plátano                                                                         [Dueño]
  - Cosecha y venta el mismo día, 1-2 veces por semana: 300-1.200 kg, 25-100 racimos, 70-85 % primera.
  - Precio $1.000-$1.200/kg primera, $700-$850/kg segunda; comprador mayorista de la plaza (simulado).
Lluvia                                                                          [Dueño]
  - Lectura 6 a.m. todos los días (algunos días otra ~5 p.m.); ~2.150 mm en el periodo
    (régimen anual 2.000-2.500 mm), lluvioso abr-may y oct-nov, seco ene-feb y jul-ago.
Insumos (precio 2026 / stock de arranque / umbral)                              [Dueño]
  - Urea 50 kg $210.000 (18/5) | 17-6-18-3 50 kg $240.000 (12/4) | Cal dolomita $85.000 (8/3)
  - Glifosato 20 L $380.000 (6/2) | Insecticida $150.000/L (5/2) | Fungicida cobre $95.000/kg (10/3)
  - Sacos costales x100 $220.000 (4/2) | Guadua/puntillas $3.500/und (300/100) | Lubricante oruga $60.000 (3/1)
  - El stock de arranque es el inventario al 5 de enero (comprado en 2025).       [Supuesto]
  - Cada compra cubre ~6 semanas de consumo; el fertilizante del ciclo se compra en 2 partes
    (60 % dos semanas antes del ciclo, 40 % a mitad del ciclo).                    [Supuesto]
  - Dosis: fertilización 3 bultos/ha por ciclo (ciclos mar-abr y sep-oct); encalado 4 bultos/ha
    en feb en 3 lotes; insecticida 1,2 L/ha; fungicida 2 kg/ha; glifosato 0,15 garrafa/ha. [Supuesto]
Gastos y caja
  - Servicios: energía $180.000-$300.000 + agua $70.000-$150.000 al mes.            [Dueño]
  - Fletes: a la Cooperativa por venta ($60.000-$140.000); a la plaza en ~40 % de ventas de plátano. [Supuesto]
  - Casa recreativa: 2-4 gastos al mes ($80.000-$650.000); otros 1-2 al mes + predial en marzo. [Supuesto]
  - La nómina NO va como gasto: se calcula de labor_diaria.                       [Dueño]
  - Aportes de capital de la familia cuando la caja baja de $5.000.000: 1-3 al mes de $1-4 millones. [Dueño]
  - Caja nunca negativa: si la caja de algún día quedaría negativa, los socios aportan ESA semana el
    faltante redondeado hacia arriba a $500.000 (se suma al aporte de la semana si ya hay). [Dueño]
  - Retiros ocasionales (máx. 3 en el año) cuando la caja pasa de $9.000.000.     [Supuesto]
Cortes de nómina (modelo B6/B7)                                                 [Dueño]
  - Corte normal: sábado 6:30 p.m., desde el lunes hasta el sábado.
  - ~1 de cada 3-4 semanas (55 % en pico, 20 % fuera de pico): corte a mitad de semana (miércoles 6 p.m., hasta el
    martes) con 1-2 ANTICIPOS sobre contratos de 2 días abiertos (miércoles-jueves), y el corte
    del sábado paga lo pactado menos lo adelantado.
Captura
  - registrado_por: labores/lluvia/cosechas "mayordomo"; ventas/compras/gastos/caja/cortes "jaime". [Dueño]
  - ~85 % capturado el mismo día; el resto al día siguiente temprano (nunca después de un corte). [Dueño]
Usuarios: jaime (administrador), mayordomo, junta, antonio (superusuario); clave CLAVE_USUARIOS. [Dueño]
"""

import asyncio
import json
import math
import random
import struct
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

# Con `python back/datos_mongo.py`, Python solo ve la carpeta back/; se agrega la
# raíz del repo para poder importar el paquete `back`.
_RAIZ = str(Path(__file__).resolve().parents[1])
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from bson import ObjectId  # noqa: E402
from pymongo.errors import BulkWriteError  # noqa: E402

from back.app import database as db  # noqa: E402
from back.app.auth import hashear_clave  # noqa: E402
from back.app.reglas.fotos import FOTOS_DIR  # noqa: E402
from back.app.reglas.semana import semana_iso  # noqa: E402
from back.app.schemas import (  # noqa: E402
    BOGOTA,
    CompraInsumoCreate,
    CosechaPlatanoCreate,
    GastoCreate,
    InsumoCreate,
    LaborCreate,
    LaborDiariaCreate,
    LluviaCreate,
    LoteCreate,
    MovimientoCajaCreate,
    PoolSemanaCreate,
    TrabajadorCreate,
    UnidadCreate,
    UsuarioCreate,
    VentaCafeCreate,
    VentaPlatanoCreate,
)
from back.init_db import COLECCIONES, init_db  # noqa: E402

# ═══════════════════════════ Parámetros ═══════════════════════════

SEMILLA = 2026
CLAVE_USUARIOS = "agritics2026"          # la misma para los 4 usuarios del MVP (se entrega por fuera)
INICIO = date(2026, 1, 5)                # lunes, ISO 2026-W02
FIN = date(2026, 11, 14)                 # sábado de la W46
SEMANA_ABIERTA = "2026-W46"

# Coyuntura de la sustentación (Mundo.coyuntura): del lunes 16/11 al sábado 5/12.
INICIO_DEMO = date(2026, 11, 16)         # lunes de la W47
HOY_DEMO = date(2026, 11, 25)            # miércoles de la W48: el día de la sustentación
FIN_DEMO = date(2026, 12, 6)             # domingo de la W49
W47, W48, W49 = 47, 48, 49
DIAS_PLATANO_DEMO = (1, 4)               # martes y viernes, como el seed en cosecha
NOTA_APORTE_DEMO = "Aporte de la familia para la nómina de noviembre"
P_CAPTURA_TARDE = 0.175                  # de lunes a viernes -> ~85 % del total el mismo día

FOTO_RECIBO = "fotos/placeholder_recibo.jpg"
FOTO_PLUVIOMETRO = "fotos/placeholder_pluviometro.jpg"
FOTO_COMPROBANTE = "fotos/placeholder_comprobante.jpg"
PLACEHOLDERS = {FOTO_RECIBO: 232, FOTO_PLUVIOMETRO: 150, FOTO_COMPROBANTE: 200}  # nivel de gris

# Polígonos de los lotes (properties.id del GeoJSON -> lote). El perímetro de la finca
# (properties.tipo == "perimetro") no es un lote: no va a la base, el frontend lo lee del archivo.
GEOJSON_FINCA = Path(__file__).resolve().parent / "datos_finca.geojson"
POLIGONO_DE = {
    "portugal_lote": "Portugal", "oriente_lote": "Oriente", "centro_lote": "Centro",
    "villa_aurora_lote": "Villa Aurora", "madrono_lote": "Madroño", "minitas_lote": "Minitas",
    "la_casa_lote": "La Casa", "baltimore": "Baltimore", "bosque_natural": "Bosque Natural",
}

LOTES = [  # nombre, área, cultivos, variedad, estado
    ("Portugal", 2.40, ["cafe"], "Castillo", "activo"),
    ("Oriente", 1.60, ["cafe"], "Colombia", "activo"),
    ("Villa Aurora", 2.80, ["cafe"], "Castillo", "activo"),
    ("Centro", 0.60, ["cafe"], "Colombia", "activo"),
    ("Madroño", 1.55, ["cafe"], "Cenicafé", "activo"),
    ("Minitas", 2.50, ["cafe"], "Castillo", "activo"),
    ("La Casa", 2.40, ["cafe"], "Colombia", "activo"),
    ("Baltimore", 6.50, ["platano"], "Plátano Hartón", "activo"),
    ("Bosque Natural", 4.65, ["bosque"], "Guadua y bosque natural", "no_productivo"),   # nunca recibe labores
]

LABORES = [  # nombre, cultivos, unidad_avance, admite_contrato, tipo_meta
    ("Recolección café", ["cafe"], "kg", True, "kilos"),
    ("Recolección plátano", ["platano"], "kg", True, "kilos"),
    ("Guadaña", ["cafe", "platano"], "hectareas", True, "completada"),
    ("Plateo", ["cafe"], "hectareas", True, "completada"),
    ("Desbejuque", ["cafe"], "hectareas", True, "completada"),
    ("Control de malezas", ["cafe", "platano"], "hectareas", True, "completada"),
    ("Fumigación", ["cafe", "platano"], "hectareas", True, "completada"),
    ("Fertilización", ["cafe", "platano"], "hectareas", True, "completada"),
    ("Siembra", ["cafe", "platano"], "jornales", True, "completada"),
    ("Drenajes", ["cafe", "platano"], "jornales", True, "completada"),
    ("Mantenimiento de caminos", ["cafe", "platano"], "jornales", True, "completada"),
    ("Chapia", ["cafe", "platano"], "hectareas", True, "completada"),
    ("Manejo de beneficio", ["cafe"], "jornales", True, "completada"),
    ("Transporte interno", ["cafe", "platano"], "jornales", False, None),
]
TARIFA_JORNAL = {
    "Recolección café": 95000, "Recolección plátano": 90000, "Guadaña": 125000, "Plateo": 95000,
    "Desbejuque": 95000, "Control de malezas": 105000, "Fumigación": 110000, "Fertilización": 100000,
    "Siembra": 100000, "Drenajes": 110000, "Mantenimiento de caminos": 100000, "Chapia": 90000,
    "Manejo de beneficio": 90000, "Transporte interno": 85000,
}
HA_POR_JORNAL = {"Guadaña": 0.5, "Plateo": 0.35, "Desbejuque": 0.4, "Control de malezas": 0.6,
                 "Fumigación": 0.8, "Fertilización": 1.0, "Chapia": 0.5}
PRECIO_HA = {"Guadaña": 260000, "Plateo": 280000, "Desbejuque": 240000, "Control de malezas": 200000,
             "Fumigación": 150000, "Fertilización": 130000, "Chapia": 220000}
TARIFA_KG_CAFE = 2000
DOSIS_FERTILIZANTE = 3        # bultos/ha por ciclo
CEREZA_A_MOJADO = 0.44        # kg de pergamino mojado por kg de cereza
MOJADO_A_SECO = 0.50          # kg de pergamino seco por kg de mojado  (cereza:seco ~4,5:1)
UMBRAL_APORTE = 5_000_000
TARIFA_KG_PLATANO = 100

INSUMOS = [  # nombre, unidad, precio, stock de arranque, umbral
    ("Urea 50 kg", "bulto", 210000, 18, 5),
    ("Fertilizante 17-6-18-3 50 kg", "bulto", 240000, 12, 4),
    ("Cal dolomita", "bulto", 85000, 8, 3),
    ("Glifosato 20 L", "garrafa", 380000, 6, 2),
    ("Insecticida", "litro", 150000, 5, 2),
    ("Fungicida cobre", "kg", 95000, 10, 3),
    ("Sacos costales x100", "paquete", 220000, 4, 2),
    ("Guadua y puntillas", "unidad", 3500, 300, 100),
    ("Lubricante oruga", "unidad", 60000, 3, 1),
]
UNIDADES = [("kg", {"arroba": 12.5, "carga": 125, "bulto": 62.5}), ("racimos", {}), ("jornales", {}), ("hectareas", {})]

TRABAJADORES = [  # nombre, documento, tipo de participación
    ("Orlando Castro", "10234567", "recurrente"), ("Libardo Henao", None, "recurrente"),
    ("Marleny Cardona", "24876123", "recurrente"), ("José Arley Gómez", None, "recurrente"),
    ("Luz Dary Ospina", "30345998", "recurrente"), ("Wilson Restrepo", None, "recurrente"),
    ("Hernán Giraldo", "75081234", "esporadico"), ("Gloria Patricia Valencia", None, "esporadico"),
    ("Fabio Nelson Arango", None, "esporadico"), ("Yeison Marín", None, "esporadico"),
    ("Arnulfo Zuluaga", "4567891", "esporadico"), ("Duván Loaiza", None, "de_una_vez"),
    ("Jhon Fredy Salazar", None, "de_una_vez"), ("Ángela María Rendón", None, "de_una_vez"),
    ("Cristian Camilo Ocampo", None, "de_una_vez"),
]
SEMANA_UNICA = {"Duván Loaiza": 17, "Jhon Fredy Salazar": 19, "Ángela María Rendón": 42, "Cristian Camilo Ocampo": 44}
USUARIOS = [("Jaime", "jaime", "administrador"), ("Mayordomo", "mayordomo", "mayordomo"),
            ("Junta familiar", "junta", "junta"), ("Antonio", "antonio", "superusuario")]

COSECHA_MES = {1: 0.45, 2: 0.2, 3: 0.3, 4: 0.9, 5: 0.95, 6: 0.3, 7: 0.08, 8: 0.08, 9: 0.4, 10: 0.85, 11: 1.0}
SEMANAS_SIN_CAFE = {7, 28, 29, 31, 32, 34}
LLUVIA_MES = {1: 120, 2: 130, 3: 210, 4: 310, 5: 300, 6: 170, 7: 110, 8: 120, 9: 190, 10: 320, 11: 170}
P_LLUEVE_MES = {1: .35, 2: .35, 3: .5, 4: .7, 5: .7, 6: .5, 7: .35, 8: .35, 9: .5, 10: .7, 11: .65}
PRECIO_CARGA = {1: 1850000, 2: 1880000, 3: 1800000, 4: 1700000, 5: 1650000, 6: 1600000,
                7: 1550000, 8: 1550000, 9: 1650000, 10: 1750000, 11: 1800000}
CICLOS_FERTILIZACION = [(10, 16), (36, 42)]   # semanas ISO
# Compras de fertilizante del ciclo, repartidas (semana: (ciclo, fracción de la necesidad)): antes y durante.
PRECOMPRAS_FERTILIZANTE = {8: (0, 0.6), 12: (0, 0.4), 34: (1, 0.6), 38: (1, 0.4)}
SEMANAS_ENCALADO = (6, 8)
COMPRADOR_PLATANO = "Distribuidora La Plaza (mayorista)"
OTRO_COMPRADOR = "Frutas y Verduras El Galpón"

# ═══════════════════════════ Utilidades ═══════════════════════════

_BASE_ID = int(datetime(2026, 1, 5, tzinfo=timezone.utc).timestamp())


def en(dia: date, h: int, m: int = 0) -> datetime:
    return datetime.combine(dia, time(h, m), tzinfo=BOGOTA)


def utc_dia(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def lunes_de(semana_num: int) -> date:
    return date.fromisocalendar(2026, semana_num, 1)


def redondo(v: float, paso: float) -> float:
    return round(round(v / paso) * paso, 2)


def jpeg_gris(ancho: int, alto: int, nivel: int) -> bytes:
    """JPEG baseline en escala de grises de un solo tono (placeholder), sin dependencias.
    Bloques 8x8 con solo coeficiente DC: tablas de Huffman mínimas (DC: categoría 0 y la del
    primer bloque; AC: solo EOB)."""
    dc = (nivel - 128) * 8                                  # DCT de un bloque uniforme, Q=1
    cat = dc.bit_length() if dc > 0 else (0 if dc == 0 else (-dc).bit_length())
    simbolos_dc = sorted({0, cat})

    def seg(marca: int, datos: bytes) -> bytes:
        return struct.pack(">HH", marca, len(datos) + 2) + datos

    def dht(clase: int, simbolos: list[int], largo: int) -> bytes:
        cuenta = [0] * 16
        cuenta[largo - 1] = len(simbolos)
        return bytes([clase << 4]) + bytes(cuenta) + bytes(simbolos)

    bits = []
    bloques = (ancho // 8) * (alto // 8)
    codigo_dc = {s: format(i, "02b") for i, s in enumerate(simbolos_dc)}
    for i in range(bloques):
        if i == 0 and cat:
            v = dc if dc > 0 else dc + (1 << cat) - 1
            bits.append(codigo_dc[cat] + format(v, f"0{cat}b"))
        else:
            bits.append(codigo_dc[0])
        bits.append("0")                                    # AC: EOB
    flujo = "".join(bits)
    flujo += "1" * (-len(flujo) % 8)
    datos = bytearray()
    for i in range(0, len(flujo), 8):
        b = int(flujo[i:i + 8], 2)
        datos.append(b)
        if b == 0xFF:
            datos.append(0x00)
    return (b"\xff\xd8"
            + seg(0xFFE0, b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00")
            + seg(0xFFDB, b"\x00" + bytes([1] * 64))
            + seg(0xFFC0, struct.pack(">BHHB", 8, alto, ancho, 1) + b"\x01\x11\x00")
            + seg(0xFFC4, dht(0, simbolos_dc, 2) + dht(1, [0], 1))
            + seg(0xFFDA, b"\x01\x01\x00\x00\x3f\x00")
            + bytes(datos) + b"\xff\xd9")


def poligonos_lotes() -> dict[str, dict]:
    """Geometría GeoJSON de cada lote del seed, leída de back/datos_finca.geojson."""
    datos = json.loads(GEOJSON_FINCA.read_text(encoding="utf-8"))
    poligonos = {POLIGONO_DE[f["properties"]["id"]]: f["geometry"] for f in datos["features"]
                 if f["properties"]["tipo"] == "lote"}
    faltan = {nombre for nombre, *_ in LOTES} - poligonos.keys()
    if faltan:
        raise SystemExit(f"{GEOJSON_FINCA.name}: faltan polígonos para {sorted(faltan)}")
    return poligonos


# ═══════════════════════════ Generador ═══════════════════════════

class Mundo:
    """Arma el año completo en memoria (sin tocar la base)."""

    def __init__(self):
        self.r = random.Random(SEMILLA)
        self._n = 0
        self.docs: dict[str, list[dict]] = {c: [] for c in COLECCIONES}
        self.saldo = 0.0
        self.aportes_mes: dict[tuple, int] = {}
        self.compras_mes: dict[tuple, int] = {}
        self.retiros = 0
        self.ajustes = 0
        self.inv_mojado = 0.0
        self.inv_pasilla = 0.0
        self.semanas_desde_venta = 0
        self.recibo = 0
        self.consumo: dict[str, float] = {}
        self.anticipos = 0
        self.cola_ferti: dict = {}

    # ── ids y captura ──
    def oid(self) -> ObjectId:
        self._n += 1
        return ObjectId(f"{_BASE_ID:08x}{self._n:016x}")

    def tarde(self, dia: date) -> bool:
        if dia >= lunes_de(W48):        # la semana de la sustentación: nada «al día siguiente» en el futuro
            return False
        return dia.weekday() <= 4 and self.r.random() < P_CAPTURA_TARDE

    def captura(self, dia: date, h: int, m: int, puede_tarde: bool = True, quien_madruga: bool = False) -> datetime:
        """Momento de registro: el mismo día a la hora dada o, a veces (lun-vie), al día siguiente
        temprano -siempre antes de cualquier corte y de las labores del día siguiente-."""
        if puede_tarde and self.tarde(dia):
            return en(dia + timedelta(days=1), 6, self.r.randint(0, 25)) if quien_madruga else \
                en(dia + timedelta(days=1), 7, self.r.randint(0, 50))
        return en(dia, h, m) + timedelta(minutes=self.r.randint(0, 25))

    def agregar(self, coleccion: str, doc: dict, **servidor) -> dict:
        doc = {"_id": self.oid(), **doc, **servidor}
        self.docs[coleccion].append(doc)
        return doc

    # ── catálogos ──
    def catalogos(self):
        alta = en(INICIO, 6, 0)
        cat = {"registrado_por": "jaime", "fecha_captura": alta}
        self.lotes = {}
        poligonos = poligonos_lotes()
        for nombre, area, cultivos, variedad, estado in LOTES:
            d = self.agregar(db.LOTES, LoteCreate(nombre=nombre, area_ha=area, cultivos=cultivos, variedad=variedad,
                                                  estado=estado, poligono=poligonos[nombre]).a_mongo(), **cat)
            self.lotes[nombre] = d
        self.lotes_cafe = [l for l in self.lotes.values() if "cafe" in l["cultivos"] and l["estado"] == "activo"]
        self.lote_platano = self.lotes["Baltimore"]
        self.labores = {}
        for nombre, cultivos, unidad, contrato, meta in LABORES:
            self.labores[nombre] = self.agregar(db.LABORES, LaborCreate(
                nombre=nombre, cultivos=cultivos, unidad_avance=unidad, admite_contrato=contrato,
                tipo_meta=meta).a_mongo(), **cat)
        for nombre, eq in UNIDADES:
            self.agregar(db.UNIDADES, UnidadCreate(nombre=nombre, equivalencias=eq).a_mongo(), **cat)
        self.insumos, self.stock, self.precio = {}, {}, {}
        for nombre, unidad, precio, stock, umbral in INSUMOS:
            self.insumos[nombre] = self.agregar(db.INSUMOS, InsumoCreate(
                nombre=nombre, unidad=unidad, stock_actual=stock, umbral_alerta=umbral).a_mongo(), **cat)
            self.stock[nombre], self.precio[nombre] = float(stock), precio
            self.consumo[nombre] = 0.0
        self.trabajadores = []
        for i, (nombre, documento, tipo) in enumerate(TRABAJADORES):
            d = self.agregar(db.TRABAJADORES, TrabajadorCreate(
                nombre=nombre, documento=documento, telefono=f"310{self.r.randint(1000000, 9999999)}").a_mongo(), **cat)
            d["_tipo"] = tipo
            self.trabajadores.append(d)
        for nombre, usuario, rol in USUARIOS:
            u = UsuarioCreate(nombre=nombre, usuario=usuario, clave=CLAVE_USUARIOS, rol=rol)
            self.agregar(db.USUARIOS, {**u.a_mongo(), "clave": hashear_clave(CLAVE_USUARIOS)},
                         registrado_por="antonio", fecha_captura=alta)

    # ── participación de trabajadores ──
    def plan_participacion(self):
        self.semanas = list(range(INICIO.isocalendar()[1], 47))
        self.pool_de: dict[int, list] = {s: [] for s in self.semanas}
        recurrentes = [t for t in self.trabajadores if t["_tipo"] == "recurrente"]
        esporadicos = [t for t in self.trabajadores if t["_tipo"] == "esporadico"]
        ausencias = {t["_id"]: set(self.r.sample(self.semanas[:-1], 4)) for t in recurrentes}
        for s in self.semanas:
            f = self.factor(s)
            activos = [t for t in recurrentes if s not in ausencias[t["_id"]]]
            # esporádicos: una de cada 2-4 semanas (más en cosecha); el pool solo se completa hasta 6
            esp = [t for t in esporadicos if self.r.random() < 0.22 + 0.22 * f]
            unica = [t for t in self.trabajadores if SEMANA_UNICA.get(t["nombre"]) == s]
            activos += esp + unica
            faltan = [t for t in esporadicos if t not in activos]
            self.r.shuffle(faltan)
            while len(activos) < 6 and faltan:
                activos.append(faltan.pop())
            while len(activos) > 11:
                quitables = [t for t in activos if t["_tipo"] == "esporadico"]
                activos.remove(quitables[-1])
            self.pool_de[s] = activos

    def factor(self, semana: int) -> float:
        if semana in SEMANAS_SIN_CAFE:
            return 0.0
        return COSECHA_MES[lunes_de(semana).month]

    # ── caja ──
    def mover_caja(self, dia: date, tipo: str, valor: float, nota: str, momento: datetime):
        doc = MovimientoCajaCreate(fecha=dia, tipo=tipo, valor=valor, nota=nota).a_mongo()
        self.agregar(db.MOVIMIENTO_CAJA, doc, registrado_por="jaime", fecha_captura=momento)
        self.saldo += -valor if tipo == "retiro" else valor

    def revisar_aporte(self, dia: date):
        mes = (dia.year, dia.month)
        if self.saldo < UMBRAL_APORTE and self.aportes_mes.get(mes, 0) < 3:
            valor = max(1_000_000, min(4_000_000, redondo(UMBRAL_APORTE + 1_000_000 - self.saldo + self.r.uniform(0, 1_000_000), 100_000)))
            self.mover_caja(dia, "aporte_capital", valor, "Aporte de capital de la familia", en(dia, 7, self.r.randint(0, 40)))
            self.aportes_mes[mes] = self.aportes_mes.get(mes, 0) + 1

    def gasto(self, dia: date, categoria: str, valor: float, descripcion: str, h: int = 10):
        doc = GastoCreate(fecha=dia, categoria=categoria, valor=redondo(valor, 100), descripcion=descripcion).a_mongo()
        self.agregar(db.GASTO, doc, registrado_por="jaime", fecha_captura=self.captura(dia, h, self.r.randint(0, 30)))
        self.saldo -= doc["valor"]

    def compra(self, dia: date, insumo: str, cantidad: float, momento: datetime | None = None):
        cantidad = round(cantidad, 2)
        valor = redondo(cantidad * self.precio[insumo] * self.r.uniform(0.97, 1.03), 100)
        doc = CompraInsumoCreate(fecha=dia, insumo_id=str(self.insumos[insumo]["_id"]), cantidad=cantidad,
                                 valor=valor, comprobante_ruta=FOTO_COMPROBANTE).a_mongo()
        self.agregar(db.COMPRA_INSUMO, doc, registrado_por="jaime",
                     fecha_captura=momento or self.captura(dia, 9, self.r.randint(0, 50)))
        self.stock[insumo] += cantidad
        self.saldo -= valor
        mes = (dia.year, dia.month)
        self.compras_mes[mes] = self.compras_mes.get(mes, 0) + 1

    # ── plan de labores de una semana ──
    def elegir_labor(self, semana: int, f: float) -> str:
        mes = lunes_de(semana).month
        en_ciclo = any(a <= semana <= b for a, b in CICLOS_FERTILIZACION)
        encalado = SEMANAS_ENCALADO[0] <= semana <= SEMANAS_ENCALADO[1]
        lluvioso = mes in (4, 5, 10, 11)
        pesos = {
            "Guadaña": 1.0, "Plateo": 1.5 if mes in (2, 3, 8, 9) else 0.8, "Desbejuque": 0.4,
            "Control de malezas": 0.9, "Fumigación": 0.9 if f >= 0.4 else 0.6,
            "Fertilización": 3.0 if (en_ciclo and self.cola_ferti) else (1.0 if (encalado and self.cola_ferti) else 0.0),
            "Siembra": 0.7 if lluvioso else 0.05, "Drenajes": 0.5 if lluvioso else 0.15,
            "Mantenimiento de caminos": 0.4, "Chapia": 0.6, "Manejo de beneficio": 1.6 * f,
            "Transporte interno": 1.0 * f,
        }
        nombres = list(pesos)
        return self.r.choices(nombres, weights=[pesos[n] for n in nombres])[0]

    def preparar_ciclo(self, semana: int):
        """Al arrancar un ciclo de fertilización (o el encalado), cada lote queda pendiente por su área."""
        inicios = [a for a, _ in CICLOS_FERTILIZACION]
        if semana in inicios:
            self.cola_ferti = {l["nombre"]: l["area_ha"] for l in self.lotes_cafe + [self.lote_platano]}
            self.tipo_ciclo = "17-6-18-3" if semana == inicios[0] else "urea"
        elif semana == SEMANAS_ENCALADO[0]:
            self.cola_ferti = {"Minitas": 2.5, "Villa Aurora": 2.8, "Oriente": 1.6}
            self.tipo_ciclo = "cal"
        elif semana in (b + 1 for _, b in CICLOS_FERTILIZACION) or semana == SEMANAS_ENCALADO[1] + 1:
            self.cola_ferti = {}

    def necesidad_ciclo(self, ciclo: int) -> dict[str, float]:
        """Bultos de cada fertilizante para un ciclo completo (café + bloque de plátano, que va con urea)."""
        cafe = sum(l["area_ha"] for l in self.lotes_cafe)
        urea_cafe = 0.35 if ciclo == 0 else 0.65          # ciclo 1: 17-6-18-3 domina; ciclo 2: urea
        return {"Urea 50 kg": cafe * DOSIS_FERTILIZANTE * urea_cafe + self.lote_platano["area_ha"] * DOSIS_FERTILIZANTE,
                "Fertilizante 17-6-18-3 50 kg": cafe * DOSIS_FERTILIZANTE * (1 - urea_cafe)}

    def lote_para(self, labor: str, area_max: float | None = None) -> dict:
        cultivos = self.labores[labor]["cultivos"]
        candidatos = list(self.lotes_cafe)
        if "platano" in cultivos and self.r.random() < 0.15:
            return self.lote_platano
        return self.r.choices(candidatos, weights=[l["area_ha"] for l in candidatos])[0]

    def labor_campo(self, dia: date, trabajador: dict, labor: str, contrato: bool = False, jornales: float | None = None) -> dict:
        """Una labor que NO es recolección: jornales, avance acotado al área, insumo y tarifa."""
        unidad = self.labores[labor]["unidad_avance"]
        if jornales is None:
            jornales = self.r.choices([1, 0.5, 1.5, 2], weights=[70, 22, 5, 3])[0]
        insumo = None
        if labor == "Fertilización" and self.cola_ferti:
            nombre_lote = self.r.choice(list(self.cola_ferti))
            lote = self.lotes[nombre_lote]
            avance = min(redondo(HA_POR_JORNAL[labor] * jornales * self.r.uniform(0.8, 1.2), 0.05), self.cola_ferti[nombre_lote])
            self.cola_ferti[nombre_lote] = round(self.cola_ferti[nombre_lote] - avance, 2)
            if self.cola_ferti[nombre_lote] <= 0.01:
                del self.cola_ferti[nombre_lote]
            if self.tipo_ciclo == "cal":
                insumo = ("Cal dolomita", max(0.5, redondo(avance * 4, 0.5)))  # encalado: 4 bultos/ha
            else:
                urea = lote is self.lote_platano or (self.tipo_ciclo == "urea") == (self.r.random() < 0.65)
                insumo = ("Urea 50 kg" if urea else "Fertilizante 17-6-18-3 50 kg", max(0.5, redondo(avance * DOSIS_FERTILIZANTE, 0.5)))
        else:
            if labor == "Fertilización":       # sin ciclo pendiente: abonamiento puntual del plátano
                lote = self.lote_platano
            else:
                lote = self.lote_para(labor)
            if unidad == "hectareas":
                avance = min(redondo(HA_POR_JORNAL[labor] * jornales * self.r.uniform(0.8, 1.2), 0.05), lote["area_ha"])
            else:
                avance = jornales
            if labor == "Fertilización":
                insumo = ("Urea 50 kg", max(0.5, redondo(avance * DOSIS_FERTILIZANTE, 0.5)))
            elif labor == "Fumigación":
                insumo = ("Insecticida", max(0.2, round(avance * 1.2, 1))) if self.r.random() < 0.55 else \
                    ("Fungicida cobre", max(0.2, round(avance * 2, 1)))
            elif labor == "Control de malezas":
                insumo = ("Glifosato 20 L", max(0.05, round(avance * 0.15, 2)))
            elif labor in ("Drenajes", "Mantenimiento de caminos") and self.r.random() < 0.6:
                insumo = ("Guadua y puntillas", float(self.r.randint(8, 30)))
            elif labor == "Manejo de beneficio" and self.r.random() < 0.5:
                insumo = ("Sacos costales x100", round(self.r.uniform(0.1, 0.3), 2))
            elif labor == "Transporte interno" and self.r.random() < 0.3:
                insumo = ("Lubricante oruga", round(self.r.uniform(0.1, 0.2), 2))
        if contrato and self.labores[labor]["admite_contrato"]:
            tarifa = redondo(avance * PRECIO_HA[labor], 1000) if unidad == "hectareas" else redondo(jornales * 115000, 1000)
            pago = {"forma_pago": "contrato", "tipo_meta": "completada", "tarifa": max(tarifa, 50000)}
        else:
            pago = {"forma_pago": "jornal", "tarifa": TARIFA_JORNAL[labor]}
        return {"dia": dia, "t": trabajador, "lote": lote, "labor": labor, "jornales": jornales, "avance": avance,
                "insumo": insumo, **pago}

    def plan_semana(self, semana: int, pool: list) -> tuple[list, list]:
        """Labores de lunes a sábado (y los contratos de 2 días con anticipo, si toca)."""
        f = self.factor(semana)
        lunes = lunes_de(semana)
        plan, contratos = [], []
        ocupado: dict[date, set] = {lunes + timedelta(days=i): set() for i in range(6)}
        anticipos = semana != int(SEMANA_ABIERTA[-2:]) and self.r.random() < (0.55 if f >= 0.8 else 0.2)
        if anticipos:
            candidatos = [t for t in pool if t["_tipo"] != "de_una_vez"]
            for t in self.r.sample(candidatos, self.r.choice([1, 1, 2])):
                miercoles = lunes + timedelta(days=2)
                c = self.labor_campo(miercoles, t, self.r.choice(["Guadaña", "Chapia", "Plateo", "Desbejuque"]),
                                     contrato=True, jornales=2)
                c["dos_dias"] = True
                contratos.append(c)
                ocupado[miercoles].add(t["_id"])
                ocupado[miercoles + timedelta(days=1)].add(t["_id"])
        for i in range(6):
            dia = lunes + timedelta(days=i)
            disponibles = [t for t in pool if t["_id"] not in ocupado[dia]
                           and (SEMANA_UNICA.get(t["nombre"]) != semana or i >= 2 or t["_tipo"] != "de_una_vez")]
            self.r.shuffle(disponibles)
            total = max(3, min(7, round(3 + 4 * f + self.r.uniform(-0.7, 0.7))))
            total = min(total, len(disponibles))
            recolectores = 0 if f == 0 else max(0, min(total - 1, round(f * 3.6 + self.r.uniform(-0.6, 0.6))))
            platano_hoy = i in self.dias_platano.get(semana, ())
            for j in range(total):
                t = disponibles[j]
                if j < recolectores:
                    kg = max(40, min(160, round(self.r.gauss(55 + 95 * f, 16))))
                    plan.append({"dia": dia, "t": t, "lote": self.r.choices(self.lotes_cafe, weights=[l["area_ha"] for l in self.lotes_cafe])[0],
                                 "labor": "Recolección café", "jornales": 1, "avance": float(kg), "insumo": None,
                                 "forma_pago": "contrato", "tipo_meta": "kilos",
                                 "tarifa": float(self.r.choice([1900, 2000, 2000, 2000, 2100]))})
                elif platano_hoy and j == recolectores:
                    plan.append({"dia": dia, "t": t, "lote": self.lote_platano, "labor": "Recolección plátano",
                                 "jornales": 1, "avance": 0.0, "insumo": None, "forma_pago": "contrato",
                                 "tipo_meta": "kilos", "tarifa": float(TARIFA_KG_PLATANO), "platano": True})
                else:
                    contrato = self.r.random() < 0.08
                    plan.append(self.labor_campo(dia, t, self.elegir_labor(semana, f), contrato=contrato))
        return plan, contratos

    # ── la semana completa ──
    def semana(self, s: int):
        lunes = lunes_de(s)
        etiqueta = f"2026-W{s:02d}"
        f = self.factor(s)
        self.preparar_ciclo(s)
        pool = self.pool_de[s]
        # Pool: activación el lunes temprano (los "de una vez" entran el miércoles).
        for t in pool:
            entra = lunes + timedelta(days=2) if t["_tipo"] == "de_una_vez" else lunes
            momento = en(entra, 6, self.r.randint(0, 20))
            doc = PoolSemanaCreate(trabajador_id=str(t["_id"]), semana=etiqueta, activo=True).a_mongo()
            t["_pool_doc"] = self.agregar(db.POOL_SEMANA, doc, fecha_activacion=momento,
                                          registrado_por="mayordomo", fecha_captura=momento)
        plan, contratos = self.plan_semana(s, pool)
        abierta = etiqueta == SEMANA_ABIERTA
        if abierta:   # 3 labores quedan abiertas para la demo: un contrato del viernes y dos jornales del sábado
            plan, contratos = self.dejar_abiertas(lunes, plan, pool)

        # Compras del lunes para cubrir los insumos de la semana (nunca stock negativo).
        necesidad: dict[str, float] = {}
        for p in sorted(plan + contratos, key=lambda x: x["dia"]):
            if p["insumo"]:
                necesidad[p["insumo"][0]] = necesidad.get(p["insumo"][0], 0) + p["insumo"][1]
        for insumo, cant in necesidad.items():
            umbral = next(x[4] for x in INSUMOS if x[0] == insumo)
            tarde_en_el_anio = lunes >= date(2026, 10, 19) and insumo in ("Sacos costales x100", "Lubricante oruga")
            fertilizante = insumo in ("Urea 50 kg", "Fertilizante 17-6-18-3 50 kg", "Cal dolomita")
            piso = 0 if (tarde_en_el_anio or fertilizante) else umbral   # el fertilizante del ciclo ya se compró planeado
            if self.stock[insumo] - cant < piso:
                colchon = 0.0 if tarde_en_el_anio else (umbral if fertilizante else umbral + 5 * cant)
                objetivo = cant - self.stock[insumo] + colchon
                paso = 1 if insumo not in ("Glifosato 20 L", "Insecticida", "Fungicida cobre", "Sacos costales x100",
                                            "Lubricante oruga", "Guadua y puntillas") else 0.5
                if insumo == "Guadua y puntillas":
                    paso = 50
                self.compra(lunes, insumo, max(paso, math.ceil(objetivo / paso) * paso), en(lunes, 6, 5))

        if s in PRECOMPRAS_FERTILIZANTE:
            ciclo, fraccion = PRECOMPRAS_FERTILIZANTE[s]
            primera = fraccion == max(fr for c, fr in PRECOMPRAS_FERTILIZANTE.values() if c == ciclo)
            for insumo, total in self.necesidad_ciclo(ciclo).items():
                umbral = next(x[4] for x in INSUMOS if x[0] == insumo)
                cantidad = total * fraccion - (max(0.0, self.stock[insumo] - umbral) if primera else 0.0)
                if cantidad >= 1:
                    self.compra(lunes, insumo, float(math.ceil(cantidad)), en(lunes, 6, 5))
        lluvias = self.lluvia_semana(lunes)
        dias_venta = self.dias_venta_cafe(s, f)
        for i in range(7):
            dia = lunes + timedelta(days=i)
            if dia > FIN:
                break
            if i in (0, 3):
                self.revisar_aporte(dia)
            for momento, mm in lluvias.get(dia, []):
                self.lectura(dia, momento, mm)
            if i == 6:
                continue
            if i in self.dias_platano.get(s, ()):   # primero la cosecha: fija el avance (kg) de sus recolectores
                self.platano(dia, s, [x for x in plan if x["dia"] == dia and x.get("platano")])
            for p in [x for x in plan + contratos if x["dia"] == dia]:
                self.emitir_labor(p, s)
            if i in dias_venta:
                self.venta_cafe(dia, f)
            self.gastos_del_dia(dia)
            if i == 5 and self.saldo > 9_000_000 and self.retiros < 3 and self.r.random() < 0.35:
                self.mover_caja(dia, "retiro", redondo(self.r.uniform(1_000_000, 2_500_000), 100_000),
                                "Retiro para gastos de la familia", en(dia, 16, self.r.randint(0, 30)))
                self.retiros += 1
            if i == 4 and self.ajustes < 2 and self.r.random() < 0.03:
                self.mover_caja(dia, "ajuste", float(self.r.choice([-1, 1]) * redondo(self.r.uniform(5000, 60000), 500)),
                                "Diferencia de arqueo", en(dia, 17, 0))
                self.ajustes += 1
        if not abierta:
            self.cortes(s, etiqueta, lunes, plan, contratos)
        else:
            self.preasignar(lunes, etiqueta, pool, plan)

    def dejar_abiertas(self, lunes: date, plan: list, pool: list) -> tuple[list, list]:
        viernes, sabado = lunes + timedelta(days=4), lunes + timedelta(days=5)
        recurrentes = [t for t in pool if t["_tipo"] == "recurrente"]
        elegidos = recurrentes[:3]
        ids = {t["_id"] for t in elegidos}
        quedan = [p for p in plan if not (p["t"]["_id"] in ids and p["dia"] >= viernes)]
        contrato = self.labor_campo(viernes, elegidos[0], "Guadaña", contrato=True, jornales=2)
        contrato.update(abierta=True)
        abiertas = [contrato]
        for t, labor in zip(elegidos[1:], ["Plateo", "Control de malezas"]):
            p = self.labor_campo(sabado, t, labor, contrato=False, jornales=1)
            p.update(abierta=True)
            abiertas.append(p)
        return quedan + abiertas, []

    def emitir_labor(self, p: dict, s: int):
        dia, t = p["dia"], p["t"]
        if p.get("dos_dias"):
            abre = en(dia, 6, self.r.randint(30, 59))
            cierra = en(dia + timedelta(days=1), 15, self.r.randint(0, 50))
        elif p.get("abierta"):
            abre, cierra = en(dia, 6, self.r.randint(35, 59)), None
        elif self.tarde(dia):
            abre = en(dia + timedelta(days=1), 6, self.r.randint(0, 20))
            cierra = abre + timedelta(minutes=self.r.randint(2, 8))
        else:
            abre = en(dia, 6, self.r.randint(30, 59)) + timedelta(minutes=self.r.randint(0, 50))
            cierra = en(dia, 12 if dia.weekday() == 5 else 15, self.r.randint(0, 59)) - timedelta(
                hours=self.r.randint(0, 1 if dia.weekday() == 5 else 3))
        insumo = None
        if p["insumo"]:
            nombre, cant = p["insumo"]
            if self.stock[nombre] < cant:
                cant = round(self.stock[nombre], 2)
            if cant > 0:
                insumo = {"insumo_id": str(self.insumos[nombre]["_id"]), "cantidad": cant}
                self.stock[nombre] = round(self.stock[nombre] - cant, 4)
                self.consumo[nombre] += cant
        campos = dict(fecha=dia, trabajador_id=str(t["_id"]), lote_id=str(p["lote"]["_id"]),
                      labor_id=str(self.labores[p["labor"]]["_id"]), forma_pago=p["forma_pago"], tarifa=p["tarifa"],
                      tipo_meta=p.get("tipo_meta"), jornales=p["jornales"], avance=p["avance"], insumo_consumido=insumo)
        doc = LaborDiariaCreate(**campos).a_mongo()
        doc = self.agregar(db.LABOR_DIARIA, doc, completada=cierra is not None, fecha_cierre=cierra,
                           registrado_por="mayordomo", fecha_captura=abre)
        p["doc"] = doc
        if cierra is not None:
            self.saldo -= self.pactado(doc)
            if p["labor"] == "Recolección café":
                self.inv_mojado += doc["avance"] * CEREZA_A_MOJADO
                self.inv_pasilla += doc["avance"] * 0.008

    @staticmethod
    def pactado(doc: dict) -> float:
        if doc["forma_pago"] == "jornal":
            return doc["jornales"] * doc["tarifa"]
        if doc.get("tipo_meta") == "completada":
            return doc["tarifa"]
        return doc["avance"] * doc["tarifa"]

    # ── lluvia ──
    def lluvia_semana(self, lunes: date) -> dict:
        lecturas = {}
        for i in range(7):
            dia = lunes + timedelta(days=i)
            if dia > FIN:
                break
            mes = dia.month
            if self.r.random() < P_LLUEVE_MES[mes]:
                tormenta = self.r.random() < 0.12
                media = LLUVIA_MES[mes] / (30 * P_LLUEVE_MES[mes])
                mm = self.r.uniform(20, 60) if tormenta else min(self.r.expovariate(1 / (media * 0.8)), 45)
            else:
                mm = 0.0
            mm = round(mm, 1)
            if mm >= 8 and self.r.random() < 0.25:     # aguacero de la tarde: segunda lectura
                tarde = round(mm * self.r.uniform(0.3, 0.6), 1)
                lecturas[dia] = [(en(dia, 6, 0), round(mm - tarde, 1)), (en(dia, 17, 0), tarde)]
            else:
                lecturas[dia] = [(en(dia, 6, 0), mm)]
        return lecturas

    def lectura(self, dia: date, momento: datetime, mm: float):
        doc = LluviaCreate(fecha_hora=momento, mm=mm, foto_ruta=FOTO_PLUVIOMETRO, leida_por="Mayordomo").a_mongo()
        domingo = dia.weekday() == 6
        if (dia.weekday() <= 4 or domingo) and self.r.random() < P_CAPTURA_TARDE:
            captura = en(dia + timedelta(days=1), 6, self.r.randint(0, 25))
        else:
            captura = momento + timedelta(minutes=self.r.randint(4, 35))
        self.agregar(db.LLUVIA, doc, registrado_por="mayordomo", fecha_captura=captura)

    # ── plátano ──
    def plan_platano(self):
        self.dias_platano = {}
        for s in self.semanas:
            self.dias_platano[s] = (1, 4) if self.r.random() < 0.5 else (self.r.choice([1, 4]),)

    def platano(self, dia: date, s: int, labores_platano: list):
        mes = dia.month
        kg_total = round(self.r.uniform(300, 1200) * (1.1 if mes in (4, 5, 10, 11) else 0.95), 1)
        kg_total = max(300.0, min(1200.0, kg_total))
        racimos = max(25, min(100, round(kg_total / self.r.uniform(11.5, 13.5))))
        p1 = self.r.uniform(0.70, 0.85)
        partes = [("primera", round(kg_total * p1, 1), max(1, round(racimos * p1))),
                  ("segunda", None, None)]
        partes[1] = ("segunda", round(kg_total - partes[0][1], 1), max(1, racimos - partes[0][2]))
        comprador = COMPRADOR_PLATANO if self.r.random() < 0.9 else OTRO_COMPRADOR
        for calidad, kg, rac in partes:
            cos = CosechaPlatanoCreate(fecha=dia, lote_id=str(self.lote_platano["_id"]), kg=kg, racimos=rac,
                                       calidad=calidad).a_mongo()
            cos = self.agregar(db.COSECHA_PLATANO, cos, registrado_por="mayordomo",
                               fecha_captura=self.captura(dia, 12, self.r.randint(0, 40)))
            precio = float(self.r.randint(1000, 1200) if calidad == "primera" else self.r.randint(700, 850))
            venta = VentaPlatanoCreate(fecha=dia, comprador=comprador, kg=kg, racimos=rac, calidad=calidad,
                                       precio_kg=precio, valor_total=round(kg * precio), cosecha_id=str(cos["_id"])).a_mongo()
            self.agregar(db.VENTA_PLATANO, venta, registrado_por="jaime",
                         fecha_captura=self.captura(dia, 14, self.r.randint(0, 50)))
            self.saldo += venta["valor_total"]
        # el avance (kg) de la recolección del día es lo cosechado, repartido entre los recolectores
        for lp in labores_platano:
            lp["avance"] = round(kg_total / max(1, len(labores_platano)), 1)
        if self.r.random() < 0.4:
            self.gasto(dia, "transporte", self.r.uniform(50000, 90000), "Flete de plátano a la plaza", h=15)

    # ── café ──
    def dias_venta_cafe(self, s: int, f: float) -> tuple:
        self.semanas_desde_venta += 1
        if f >= 0.8:
            self.semanas_desde_venta = 0
            return (1, 4)
        intervalo = 1 if f >= 0.4 else (2 if f >= 0.2 else 3)
        if self.semanas_desde_venta >= intervalo:
            self.semanas_desde_venta = 0
            return (3,)
        return ()

    def venta_cafe(self, dia: date, f: float):
        if self.inv_pasilla >= 80 and self.r.random() < 0.5:
            self.recibo_cafe(dia, "pasilla", round(self.inv_pasilla, 1), f)
            self.inv_pasilla = 0
        if self.inv_mojado < 120:
            return
        seco = f < 0.8 and self.r.random() < 0.25
        saco = 62.5 if seco else 62.0
        disponible = self.inv_mojado * (MOJADO_A_SECO if seco else 1)
        kg = min(disponible, 8 * saco * self.r.uniform(0.93, 0.99))
        self.inv_mojado -= kg / (MOJADO_A_SECO if seco else 1)
        self.recibo_cafe(dia, "pergamino" if seco else "mojado", round(kg, 1), f)

    def recibo_cafe(self, dia: date, tipo: str, kg_netos: float, f: float):
        self.recibo += 1
        saco = {"mojado": 62.0, "pergamino": 62.5, "pasilla": 40.0}[tipo]
        sacos = max(2, min(8, math.ceil(kg_netos / saco)))
        destare = round(sacos * 0.6, 1)
        kg_brutos = round(kg_netos + destare, 1)
        broca = round(self.r.uniform(3, 9) if f >= 0.6 else self.r.uniform(8, 22), 1)
        pasilla = round(self.r.uniform(2, 6), 1)
        almendra = round(100 - broca - pasilla - self.r.uniform(2, 6), 1)
        if tipo == "pasilla":
            eq = kg_netos
            factor = round(self.r.uniform(140, 155), 1)
            precio = redondo(self.r.uniform(600_000, 700_000), 1000)
        else:
            eq = round(kg_netos * (MOJADO_A_SECO if tipo == "mojado" else 1.0), 2)
            factor = round(max(100, min(105, 100 + (broca - 3) / 19 * 5 + self.r.uniform(-0.6, 0.6))), 1)
            precio = redondo(PRECIO_CARGA[dia.month] * self.r.uniform(0.98, 1.02), 1000)
        bruto = eq / 125 * precio
        descuentos = [{"concepto": "Contribución cafetera", "valor": round(bruto * 0.03)},
                      {"concepto": "Retención en la fuente", "valor": round(bruto * 0.005)}]
        if broca > 5 and tipo != "pasilla":
            descuentos.append({"concepto": "Descuento por broca", "valor": round(bruto * (broca - 5) * 0.006)})
        valor = round(bruto - sum(d["valor"] for d in descuentos))
        doc = VentaCafeCreate(
            fecha=dia, almacen="Cooperativa · punto de compra Neira", tipo_producto=tipo, sacos=sacos,
            kg_brutos=kg_brutos, destare=destare, kg_netos=kg_netos, kg_pergamino_equivalente=eq,
            analisis_calidad={"almendra_sana": almendra, "pasilla": pasilla, "broca": broca},
            factor_rendimiento=factor, precio_base=precio, descuentos=descuentos, valor_total=valor,
            numero_pedido=f"P-26-{self.recibo:04d}", id_comprobante=f"REC-2026-{self.recibo:04d}",
            foto_ruta=FOTO_RECIBO).a_mongo()
        self.agregar(db.VENTA_CAFE, doc, registrado_por="jaime", fecha_captura=self.captura(dia, 15, self.r.randint(0, 40)))
        self.saldo += valor
        self.gasto(dia, "transporte", self.r.uniform(60000, 140000), f"Flete a la Cooperativa ({sacos} sacos)", h=16)

    # ── gastos recurrentes ──
    def gastos_del_dia(self, dia: date):
        if dia.weekday() == 6:
            return
        mes = (dia.year, dia.month)
        if not hasattr(self, "_agenda") or self._agenda[0] != mes:
            dias_mes = [d for d in (date(dia.year, dia.month, k) for k in range(1, 29)) if d.weekday() <= 5]
            casa = self.r.sample(dias_mes, self.r.randint(2, 4))
            otros = self.r.sample(dias_mes, self.r.randint(1, 2))
            self._agenda = (mes, {"casa": casa, "otros": otros, "energia": False, "agua": False, "relleno": False})
        ag = self._agenda[1]
        if dia.day >= 12 and not ag["energia"]:
            self.gasto(dia, "servicios", self.r.uniform(180000, 300000), "Energía eléctrica")
            ag["energia"] = True
        if dia.day >= 18 and not ag["agua"]:
            self.gasto(dia, "servicios", self.r.uniform(70000, 150000), "Acueducto veredal")
            ag["agua"] = True
        if dia in ag["casa"]:
            desc = self.r.choice(["Arreglo de la cubierta de la casa recreativa", "Pintura y mantenimiento de la casa",
                                  "Aseo y jardinería de la casa", "Reparación de plomería en la casa",
                                  "Mantenimiento de la piscina", "Compra de menaje para la casa"])
            self.gasto(dia, "casa", self.r.uniform(80000, 650000), desc)
        if dia in ag["otros"]:
            desc = self.r.choice(["Herramientas (machetes, limas)", "Papelería y planillas", "Recarga de celular del mayordomo",
                                  "Repuestos de la guadañadora", "Asesoría técnica del comité", "Botas y elementos de protección"])
            self.gasto(dia, "otros", self.r.uniform(40000, 300000), desc)
        if dia.month == 3 and dia.day == 16:
            self.gasto(dia, "otros", 1_250_000, "Impuesto predial 2026")
        # relleno de compras: al menos 2 al mes
        if dia.day >= (9 if dia.month == FIN.month else 21) and not ag["relleno"] and dia.weekday() <= 4:
            ag["relleno"] = True
            while self.compras_mes.get(mes, 0) < 2:
                insumo = self.r.choice(["Guadua y puntillas", "Fungicida cobre", "Insecticida"])
                cant = {"Guadua y puntillas": 50, "Fungicida cobre": 2, "Insecticida": 1}[insumo]
                self.compra(dia, insumo, cant)

    # ── cortes ──
    def cortes(self, s: int, etiqueta: str, lunes: date, plan: list, contratos: list):
        martes, miercoles, sabado = lunes + timedelta(days=1), lunes + timedelta(days=2), lunes + timedelta(days=5)
        labores = [p["doc"] for p in plan + contratos]
        numero = 0
        if contratos:
            numero += 1
            momento = en(miercoles, 18, 0)
            pagadas = [d for d in labores if d["completada"] and "corte" not in d and d["fecha"] <= utc_dia(martes)
                       and d["fecha_cierre"] <= momento]
            anticipos = []
            for c in contratos:
                d = c["doc"]
                valor = min(redondo(self.pactado(d) * self.r.uniform(0.35, 0.6), 10000), self.pactado(d))
                anticipos.append({"labor_diaria_id": d["_id"], "trabajador_id": d["trabajador_id"], "valor": float(valor)})
                d.setdefault("anticipos", []).append({"corte": numero, "semana": etiqueta, "valor": float(valor), "fecha": momento})
                self.anticipos += 1
            self.agregar(db.CIERRES, {"semana": etiqueta, "corte": numero, "desde": utc_dia(lunes), "hasta": utc_dia(martes),
                                      "cerrada_por": "jaime", "fecha": momento, "anticipos": anticipos})
            for d in pagadas:
                d["corte"], d["corte_semana"] = numero, etiqueta
        numero += 1
        momento = en(sabado, 18, 30)
        desde = miercoles if contratos else lunes
        for d in labores:
            if d["completada"] and "corte" not in d and d["fecha"] <= utc_dia(sabado):
                assert d["fecha_cierre"] <= momento, "labor completada después del corte"
                d["corte"], d["corte_semana"] = numero, etiqueta
        self.agregar(db.CIERRES, {"semana": etiqueta, "corte": numero, "desde": utc_dia(desde), "hasta": utc_dia(sabado),
                                  "cerrada_por": "jaime", "fecha": momento, "anticipos": []})

    def preasignar(self, lunes: date, etiqueta: str, pool: list, plan: list):
        """Semana abierta: preasignación (planeado) para el cronograma de los recurrentes."""
        for t in pool:
            if t["_tipo"] != "recurrente":
                continue
            propias = [p for p in plan if p["t"]["_id"] == t["_id"]]
            pre = [{"dia": p["dia"], "lote_id": str(p["lote"]["_id"]), "labor_id": str(self.labores[p["labor"]]["_id"])}
                   for p in propias if self.r.random() < 0.8]
            libre = [lunes + timedelta(days=i) for i in range(6) if all(p["dia"] != lunes + timedelta(days=i) for p in propias)]
            if libre:
                pre.append({"dia": libre[0], "lote_id": str(self.lotes_cafe[0]["_id"]), "labor_id": str(self.labores["Plateo"]["_id"])})
            doc = PoolSemanaCreate(trabajador_id=str(t["_id"]), semana=etiqueta, activo=True, preasignacion=pre).a_mongo()
            t["_pool_doc"]["preasignacion"] = doc["preasignacion"]

    # ── caja nunca negativa ──
    def garantizar_caja(self):
        """Cuando se sabe lo que hay que pagar en la semana y la caja no alcanza, los socios aportan
        ESA semana. Se recorren las semanas en orden con la caja calculada como la API (flujo_diario);
        si algún día cerraría en negativo, el faltante (redondeado hacia arriba a $500.000) se suma al
        aporte que ya haya esa semana antes de ese día, o se registra un aporte nuevo ese día.
        Los aportes nunca entran al margen."""
        neto = flujo_diario(self.docs)
        saldo, lunes, self.aportes_extra = 0.0, INICIO, 0
        while lunes <= FIN:
            dias = [lunes + timedelta(days=i) for i in range(7) if lunes + timedelta(days=i) <= FIN]
            while True:
                s, primero, deficit = saldo, None, 0.0
                for d in dias:
                    s += neto.get(d, 0.0)
                    if s < 0 and primero is None:
                        primero, deficit = d, -s
                if primero is None:
                    break
                valor = float(math.ceil(deficit / 500_000) * 500_000)
                existente = next((mv for mv in self.docs[db.MOVIMIENTO_CAJA] if mv["tipo"] == "aporte_capital"
                                  and dias[0] <= mv["fecha"].date() <= primero), None)
                if existente is not None:
                    existente["valor"] += valor
                    neto[existente["fecha"].date()] = neto.get(existente["fecha"].date(), 0.0) + valor
                else:
                    doc = MovimientoCajaCreate(fecha=primero, tipo="aporte_capital", valor=valor,
                                               nota="Aporte de los socios para cubrir los pagos de la semana").a_mongo()
                    self.agregar(db.MOVIMIENTO_CAJA, doc, registrado_por="jaime", fecha_captura=en(primero, 7, 0))
                    neto[primero] = neto.get(primero, 0.0) + valor
                self.aportes_extra += 1
            saldo = s
            lunes += timedelta(days=7)

    # ── coyuntura de la sustentación (W47-W49) ──
    def pool_coyuntura(self) -> list[dict]:
        """Los recurrentes y 2-3 esporádicos (los "de una vez" ya pasaron por la finca)."""
        recurrentes = [t for t in self.trabajadores if t["_tipo"] == "recurrente"]
        esporadicos = [t for t in self.trabajadores if t["_tipo"] == "esporadico"]
        return recurrentes + self.r.sample(esporadicos, self.r.choice([2, 3, 3]))

    def activar_pool(self, s: int, pool: list, momento: datetime) -> None:
        for t in pool:
            doc = PoolSemanaCreate(trabajador_id=str(t["_id"]), semana=f"2026-W{s:02d}", activo=True).a_mongo()
            t["_pool_doc"] = self.agregar(db.POOL_SEMANA, doc, fecha_activacion=momento,
                                          registrado_por="mayordomo", fecha_captura=momento)

    def plan_dias(self, s: int, pool: list, dias: range) -> list[dict]:
        """Las mismas reglas de plan_semana, sin contratos con anticipo y sin consumo de insumos."""
        f, lunes, plan = self.factor(s), lunes_de(s), []
        for i in dias:
            dia = lunes + timedelta(days=i)
            disponibles = list(pool)
            self.r.shuffle(disponibles)
            total = min(len(disponibles), max(3, min(7, round(3 + 4 * f + self.r.uniform(-0.7, 0.7)))))
            recolectores = 0 if f == 0 else max(0, min(total - 1, round(f * 3.6 + self.r.uniform(-0.6, 0.6))))
            for j, t in enumerate(disponibles[:total]):
                if j < recolectores:
                    kg = max(40, min(160, round(self.r.gauss(55 + 95 * f, 16))))
                    plan.append({"dia": dia, "t": t, "lote": self.r.choices(self.lotes_cafe, weights=[l["area_ha"] for l in self.lotes_cafe])[0],
                                 "labor": "Recolección café", "jornales": 1, "avance": float(kg), "insumo": None,
                                 "forma_pago": "contrato", "tipo_meta": "kilos",
                                 "tarifa": float(self.r.choice([1900, 2000, 2000, 2000, 2100]))})
                elif i in DIAS_PLATANO_DEMO and j == recolectores:
                    plan.append({"dia": dia, "t": t, "lote": self.lote_platano, "labor": "Recolección plátano",
                                 "jornales": 1, "avance": float(round(self.r.uniform(280, 650))), "insumo": None,
                                 "forma_pago": "contrato", "tipo_meta": "kilos", "tarifa": float(TARIFA_KG_PLATANO)})
                else:
                    p = self.labor_campo(dia, t, self.elegir_labor(s, f), contrato=self.r.random() < 0.08)
                    p["insumo"] = None                    # sin compras en la coyuntura: no se gasta inventario
                    plan.append(p)
        return plan

    def preasignacion(self, plan: list, t: dict, prob: float = 1.0) -> list[dict]:
        return [{"dia": p["dia"], "lote_id": str(p["lote"]["_id"]), "labor_id": str(self.labores[p["labor"]]["_id"])}
                for p in plan if p["t"]["_id"] == t["_id"] and self.r.random() < prob]

    def guardar_preasignacion(self, s: int, t: dict, pre: list[dict]) -> None:
        doc = PoolSemanaCreate(trabajador_id=str(t["_id"]), semana=f"2026-W{s:02d}", activo=True,
                               preasignacion=pre).a_mongo()
        t["_pool_doc"]["preasignacion"] = doc["preasignacion"]

    def coyuntura_w47(self):
        lunes, sabado = lunes_de(W47), lunes_de(W47) + timedelta(days=5)
        pool = self.pool_coyuntura()
        self.activar_pool(W47, pool, en(lunes, 6, self.r.randint(0, 20)))
        plan = self.plan_dias(W47, pool, range(6))
        for p in plan:
            self.emitir_labor(p, W47)
        for t in pool:                                    # lo planeado el lunes: casi todo se cumplió
            self.guardar_preasignacion(W47, t, self.preasignacion(plan, t, 0.8 if t["_tipo"] == "recurrente" else 0.5))
        # Corte normal del sábado: como en la API, paga TODO lo completado sin corte hasta ese día
        # (también lo que la W46 dejó pendiente).
        momento = en(sabado, 18, 30)
        for d in self.docs[db.LABOR_DIARIA]:
            if d["completada"] and "corte" not in d and d["fecha"] <= utc_dia(sabado):
                assert d["fecha_cierre"] <= momento, "labor completada después del corte"
                d["corte"], d["corte_semana"] = 1, f"2026-W{W47}"
        self.agregar(db.CIERRES, {"semana": f"2026-W{W47}", "corte": 1, "desde": utc_dia(lunes), "hasta": utc_dia(sabado),
                                  "cerrada_por": "jaime", "fecha": momento, "anticipos": []})

    def coyuntura_w48(self):
        pool = self.pool_coyuntura()
        self.activar_pool(W48, pool, en(lunes_de(W48), 6, self.r.randint(0, 20)))
        hechas = self.plan_dias(W48, pool, range(2))          # lunes y martes: completadas, sin corte
        for p in hechas:
            self.emitir_labor(p, W48)
        planeadas = self.plan_dias(W48, pool, range(2, 5))    # miércoles a viernes: planeadas
        for t in pool:
            pre = self.preasignacion(hechas, t, 0.8 if t["_tipo"] == "recurrente" else 0.5) + self.preasignacion(planeadas, t)
            self.guardar_preasignacion(W48, t, pre)

    def coyuntura_w49(self):
        pool = self.pool_coyuntura()
        self.activar_pool(W49, pool, en(HOY_DEMO, 7, self.r.randint(5, 40)))   # programada el día de la sustentación
        planeadas = self.plan_dias(W49, pool, range(6))
        for t in pool:
            self.guardar_preasignacion(W49, t, self.preasignacion(planeadas, t))

    def aporte_coyuntura(self):
        """Un aporte redondo el lunes 16/11 para que la caja nunca quede negativa día a día del 16/11 al
        6/12, aun restando lo que se pagará de la W48 (la nómina ya resta como causada en la fecha de
        cada labor: restarla otra vez deja un colchón)."""
        neto = flujo_diario(self.docs)
        saldo = sum(v for d, v in neto.items() if d < INICIO_DEMO)
        minimo = saldo
        dia = INICIO_DEMO
        while dia <= FIN_DEMO:
            saldo += neto.get(dia, 0.0)
            minimo = min(minimo, saldo)
            dia += timedelta(days=1)
        por_pagar = sum(self.pactado(d) for d in self.docs[db.LABOR_DIARIA] if d["completada"] and "corte" not in d)
        faltante = max(0.0, por_pagar - minimo)
        valor = float(math.ceil((faltante + 500_000) / 500_000) * 500_000)     # + margen, redondo a $500.000
        self.mover_caja(INICIO_DEMO, "aporte_capital", valor, NOTA_APORTE_DEMO, en(INICIO_DEMO, 7, 0))
        self.coyuntura_caja = {"minimo_sin_aporte": minimo, "por_pagar_w48": por_pagar, "aporte": valor}

    def coyuntura(self):
        """W47-W49, a continuación del año, con el mismo generador (mismo azar, mismas reglas)."""
        self.coyuntura_w47()
        self.coyuntura_w48()
        self.coyuntura_w49()
        self.aporte_coyuntura()

    # ── todo el año ──
    def generar(self):
        self.catalogos()
        self.plan_participacion()
        self.plan_platano()
        for s in self.semanas:
            self.semana(s)
        self.garantizar_caja()
        for nombre, d in self.insumos.items():      # stock final = arranque + compras - consumos
            d["stock_actual"] = round(self.stock[nombre], 2)
        self.coyuntura()                            # W47-W49: la semana de la sustentación
        for t in self.trabajadores:
            t.pop("_tipo", None)
            t.pop("_pool_doc", None)
        return self


# ═══════════════════════════ Fases ═══════════════════════════

def fotos_de_prueba() -> list[Path]:
    conservar = {".gitkeep"} | {Path(p).name for p in PLACEHOLDERS}
    return sorted(p for p in FOTOS_DIR.iterdir() if p.is_file() and p.name not in conservar) if FOTOS_DIR.exists() else []


def flujo_diario(docs: dict) -> dict[date, float]:
    """Movimiento neto de caja por día, con las reglas de la API (reglas/caja.py y reglas/nomina.py):
    ventas +, gastos y compras -, nómina causada en la fecha de cada labor completada (y los anticipos
    de contratos abiertos en su día), aportes y ajustes con su signo, retiros -."""
    neto: dict[date, float] = {}

    def sumar(dia: date, valor: float):
        neto[dia] = neto.get(dia, 0.0) + valor
    for v in docs[db.VENTA_CAFE] + docs[db.VENTA_PLATANO]:
        sumar(v["fecha"].date(), v["valor_total"])
    for g in docs[db.GASTO] + docs[db.COMPRA_INSUMO]:
        sumar(g["fecha"].date(), -g["valor"])
    for l in docs[db.LABOR_DIARIA]:
        if l["completada"]:
            sumar(l["fecha"].date(), -Mundo.pactado(l))
        else:
            for a in l.get("anticipos", []):
                sumar(a["fecha"].astimezone(BOGOTA).date(), -a["valor"])
    for mv in docs[db.MOVIMIENTO_CAJA]:
        sumar(mv["fecha"].date(), -mv["valor"] if mv["tipo"] == "retiro" else mv["valor"])
    return neto


def resumen_previsto(m: Mundo) -> dict:
    d = m.docs
    nomina = sum(Mundo.pactado(x) for x in d[db.LABOR_DIARIA] if x["completada"])
    ingresos = sum(v["valor_total"] for v in d[db.VENTA_CAFE] + d[db.VENTA_PLATANO])
    gastos = sum(g["valor"] for g in d[db.GASTO]) + sum(c["valor"] for c in d[db.COMPRA_INSUMO]) + nomina
    saldo, minimo = 0.0, (None, float("inf"))
    for dia, valor in sorted(flujo_diario(d).items()):
        saldo += valor
        if saldo < minimo[1]:
            minimo = (dia, saldo)
    return {"nomina": nomina, "ingresos": ingresos, "gastos": gastos, "margen": ingresos - gastos, "saldo": saldo,
            "saldo_minimo": minimo}


async def limpiar(base) -> None:
    print("FASE 1 · LIMPIEZA")
    r = await init_db(base)
    print(f"  init_db: {sum(1 for v in r.values() if v == 'creada')} creada(s), {len(r)} colecciones aseguradas")
    for c in COLECCIONES:
        borrados = (await base[c].delete_many({})).deleted_count
        print(f"  {c:<16} {borrados:>6} documento(s) borrado(s)")
    for p in fotos_de_prueba():
        p.unlink()
        print(f"  foto de prueba borrada: fotos/{p.name}")
    FOTOS_DIR.mkdir(exist_ok=True)
    for ruta, nivel in PLACEHOLDERS.items():
        (FOTOS_DIR / Path(ruta).name).write_bytes(jpeg_gris(160, 120, nivel))
    print(f"  placeholders: {', '.join(PLACEHOLDERS)}")


async def sembrar(base, m: Mundo) -> None:
    print("FASE 2 · SEED")
    for c in COLECCIONES:
        docs = m.docs[c]
        if not docs:
            continue
        try:
            await base[c].insert_many(docs, ordered=True)
        except BulkWriteError as e:
            err = e.details["writeErrors"][0]
            print(f"  ERROR insertando en {c}: {err.get('errmsg')}\n  detalle: {err.get('errInfo')}")
            raise SystemExit(1)
        print(f"  {c:<16} {len(docs):>6} documento(s)")


async def resumen_final(base) -> None:
    from back.app.reglas.caja import calcular_saldo
    from back.app.reglas.cortes import preview, recalcular_corte
    from back.app.reglas.nomina import nomina
    from back.app.reglas.reportes import adopcion_digital, ids_recoleccion_cafe, r2_flujo_caja

    print("\nRESUMEN (calculado con las mismas reglas de la API)")
    for c in COLECCIONES:
        print(f"  {c:<16} {await base[c].count_documents({}):>6}")
    cierres = await base[db.CIERRES].find().sort([("semana", 1), ("corte", 1)]).to_list(None)
    con_anticipo = [c for c in cierres if c["anticipos"]]
    n_anticipos = sum(len(c["anticipos"]) for c in cierres)
    pagado = 0.0
    for c in cierres:
        pagado += (await recalcular_corte(base, c))["total"]
    semanas_cortadas = sorted({c["semana"] for c in cierres})
    filas = await nomina(base, date(2026, 1, 1), HOY_DEMO)
    recol = await ids_recoleccion_cafe(base)
    kg_cafe = sum([l["avance"] async for l in base[db.LABOR_DIARIA].find({"completada": True, "labor_id": {"$in": recol}})])
    kg_platano = sum([c["kg"] async for c in base[db.COSECHA_PLATANO].find()])
    flujo = await r2_flujo_caja(base, date(2026, 1, 1), HOY_DEMO, detalle=False)
    saldo = await calcular_saldo(base, None, HOY_DEMO)
    adop = await adopcion_digital(base, date(2026, 1, 1), HOY_DEMO)
    abiertas = await base[db.LABOR_DIARIA].count_documents({"completada": False})
    sin_corte = await base[db.LABOR_DIARIA].count_documents({"completada": True, "corte": {"$exists": False}})
    pesos = lambda v: f"${v:,.0f}".replace(",", ".")  # noqa: E731
    print(f"  cortes: {len(cierres)} en {len(semanas_cortadas)} semanas ({semanas_cortadas[0]}..{semanas_cortadas[-1]}); "
          f"{len(con_anticipo)} cortes con anticipos, {n_anticipos} anticipos en el año")
    print(f"  {abiertas} labores abiertas (de la {SEMANA_ABIERTA}); {sin_corte} completadas por pagar (lunes y martes de la W48)")
    print(f"  nómina causada del año: {pesos(sum(t['total'] for t in filas))} | pagada en cortes: {pesos(pagado)}")
    print(f"  kg de café cereza: {kg_cafe:,.0f} | kg de plátano: {kg_platano:,.0f}".replace(",", "."))
    t = flujo["total"]
    print(f"  ingresos {pesos(t['ingresos']['total'])} - gastos {pesos(t['gastos']['total'])} = MARGEN DEL AÑO {pesos(t['margen'])}")
    print(f"  capital: aportes {pesos(t['capital']['aportes'])}, retiros {pesos(t['capital']['retiros'])}, ajustes {pesos(t['capital']['ajustes'])}")
    print(f"  saldo de caja al {HOY_DEMO}: {pesos(saldo['saldo'])}")
    detalle = (await r2_flujo_caja(base, date(2026, 1, 1), HOY_DEMO, detalle=True))["detalle"]
    cierre_dia = {}
    for linea in detalle:                         # saldo de la última línea de cada día
        cierre_dia[linea["fecha"]] = linea["saldo"]
    dia_min = min(cierre_dia, key=cierre_dia.get)
    print(f"  saldo mínimo de caja en el año (cierre del día, R2): {pesos(cierre_dia[dia_min])} el {dia_min}")
    coy = min((s, d) for d, s in cierre_dia.items() if d >= INICIO_DEMO)
    pr = await preview(base, f"2026-W{W48}")
    print(f"  coyuntura: saldo mínimo desde el {INICIO_DEMO:%d/%m} {pesos(coy[0])} el {coy[1]}; por pagar de la W48 "
          f"(preview) {pesos(pr['total_periodo_abierto'])} -> queda {pesos(coy[0] - pr['total_periodo_abierto'])}")
    print(f"  adopción digital del año: {adop['porcentaje']:.1f} % ({adop['mismo_dia']}/{adop['registros']})")
    bajos = [i["nombre"] async for i in base[db.INSUMOS].find({"$expr": {"$lte": ["$stock_actual", "$umbral_alerta"]}})]
    print(f"  insumos bajo el umbral: {bajos or 'ninguno'}")


async def main() -> None:
    confirmar = "--confirmar" in sys.argv
    mundo = Mundo().generar()       # en memoria; valida cada documento con su DTO
    base = db.get_db()
    try:
        existentes = set(await base.list_collection_names())
        print(f"Base '{db.MONGO_DB}' · {'EJECUCIÓN (--confirmar)' if confirmar else 'DRY-RUN (no se toca nada)'}")
        print(f"\nBorraría (delete_many, sin drop) · {len(COLECCIONES)} colecciones de back/init_db.py:")
        for c in COLECCIONES:
            n = await base[c].count_documents({}) if c in existentes else 0
            print(f"  {c:<16} {n:>6}")
        fotos = fotos_de_prueba()
        print(f"  fotos de prueba: {len(fotos)} {[f.name for f in fotos]}")
        print(f"\nCargaría (año {INICIO} a {FIN} + coyuntura W47-W49, del {INICIO_DEMO} al {FIN_DEMO}):")
        for c in COLECCIONES:
            print(f"  {c:<16} {len(mundo.docs[c]):>6}")
        prev = resumen_previsto(mundo)
        pesos = lambda v: f"${v:,.0f}".replace(",", ".")  # noqa: E731
        print(f"  previsto: nómina {pesos(prev['nomina'])} | ingresos {pesos(prev['ingresos'])} | gastos {pesos(prev['gastos'])} "
              f"| margen {pesos(prev['margen'])} | saldo {pesos(prev['saldo'])}")
        print(f"  saldo mínimo de caja previsto: {pesos(prev['saldo_minimo'][1])} ({prev['saldo_minimo'][0]}) "
              f"| aportes agregados o aumentados para que la caja no quede negativa: {mundo.aportes_extra}")
        print(f"  anticipos: {mundo.anticipos} | compras por mes: {dict(sorted((f'{k[1]:02d}', v) for k, v in mundo.compras_mes.items()))}")
        aportes = {}
        for mv in mundo.docs[db.MOVIMIENTO_CAJA]:
            if mv["tipo"] == "aporte_capital":
                aportes[f"{mv['fecha'].month:02d}"] = aportes.get(f"{mv['fecha'].month:02d}", 0) + 1
        print(f"  aportes por mes: {dict(sorted(aportes.items()))}")
        print("  coyuntura:")
        d = mundo.docs
        for s, rotulo in ((W47, "lunes a sábado completadas + corte del sábado 21/11 (paga también lo pendiente de la W46)"),
                          (W48, "lunes y martes completadas sin corte; miércoles a viernes planeadas"),
                          (W49, "planeadas de lunes a sábado (pool activado el 25/11)")):
            etiqueta = f"2026-W{s:02d}"
            pool = [x for x in d[db.POOL_SEMANA] if x["semana"] == etiqueta]
            labores = sum(1 for x in d[db.LABOR_DIARIA] if semana_iso(x["fecha"].date()) == etiqueta)
            print(f"    {etiqueta}: pool {len(pool)} | labores {labores} | preasignaciones "
                  f"{sum(len(x.get('preasignacion', [])) for x in pool)} · {rotulo}")
        caja = mundo.coyuntura_caja
        print(f"    aporte de capital del {INICIO_DEMO:%d/%m}: {pesos(caja['aporte'])} (sin él, la caja bajaría a "
              f"{pesos(caja['minimo_sin_aporte'])}; por pagar de la W48: {pesos(caja['por_pagar_w48'])})")
        if not confirmar:
            print("\nDRY-RUN: no se borró ni se cargó nada. Para ejecutar: python back/datos_mongo.py --confirmar")
            return
        print()
        await limpiar(base)
        await sembrar(base, mundo)
        await resumen_final(base)
    finally:
        db.close_client()


if __name__ == "__main__":
    asyncio.run(main())
