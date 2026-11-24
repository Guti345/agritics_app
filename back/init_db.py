"""Crea las colecciones de Agritics con sus validadores $jsonSchema e índices.

Uso:    python -m back.init_db
Desde código (datos_mongo.py):   from back.init_db import init_db;  await init_db()

IDEMPOTENTE: si una colección ya existe, se deja como está (no se recrea, no se
cambia su validador, no falla). Los índices sí se aseguran en todas: crear un
índice que ya existe igual no hace nada.

Los validadores son la SEGUNDA línea de defensa. La primera es la API (schemas +
back/app/reglas), que falla antes con mensajes en español claros. Si Mongo rechaza
un documento, falta una regla en la API.

Convenciones del esquema:
- Todo campo listado es obligatorio salvo los marcados como opcionales.
- Fechas: tipo BSON date (en Python, datetime; un `date` se guarda como
  datetime a medianoche).
- Referencias: ObjectId. Valores pactados (tarifa, forma_pago) van copiados.
- No se usa additionalProperties: false, para poder agregar campos sin
  migrar (por ejemplo, marcas de corrección).
- En $jsonSchema de Mongo, exclusiveMinimum es booleano:
  {"minimum": 0, "exclusiveMinimum": True} significa "> 0".
"""

import asyncio

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import CollectionInvalid, OperationFailure

from back.app import database as db

# --- Piezas de esquema -------------------------------------------------------

FECHA = {"bsonType": "date"}
OID = {"bsonType": "objectId"}
BOOL = {"bsonType": "bool"}
TEXTO = {"bsonType": "string", "minLength": 1}  # texto no vacío
TEXTO_LIBRE = {"bsonType": "string"}            # puede ir vacío
ENTERO = {"bsonType": ["int", "long"]}


def num(minimo=None, *, exclusivo=False, maximo=None, multiplo=None) -> dict:
    s: dict = {"bsonType": "number"}
    if minimo is not None:
        s["minimum"] = minimo
        if exclusivo:
            s["exclusiveMinimum"] = True
    if maximo is not None:
        s["maximum"] = maximo
    if multiplo is not None:
        s["multipleOf"] = multiplo
    return s


POSITIVO = num(0, exclusivo=True)   # > 0
NO_NEGATIVO = num(0)                # >= 0
ENTERO_POSITIVO = {**ENTERO, "minimum": 1}
PORCENTAJE = num(0, maximo=100)


def enum(*valores) -> dict:
    return {"enum": list(valores)}


def arreglo(items: dict, *, min_items: int = 0, unicos: bool = False) -> dict:
    s = {"bsonType": "array", "items": items, "minItems": min_items}
    if unicos:
        s["uniqueItems"] = True
    return s


def objeto(propiedades: dict, requeridos: list[str] | None = None, **extra) -> dict:
    s = {"bsonType": "object", "properties": propiedades, **extra}
    if requeridos:
        s["required"] = requeridos
    return s


def documento(propiedades: dict, *, opcionales: tuple[str, ...] = (), **extra) -> dict:
    """Esquema de un documento: todo lo listado es obligatorio salvo `opcionales`."""
    requeridos = [k for k in propiedades if k not in opcionales]
    return objeto(propiedades, requeridos, **extra)


CULTIVOS = arreglo(enum("cafe", "platano"), min_items=1, unicos=True)
CALIDAD_PLATANO = enum("primera", "segunda")
TIPO_META = enum("kilos", "horas", "completada")
AUDIT_CAPTURA = {"registrado_por": TEXTO, "fecha_captura": FECHA}

GEOJSON = objeto(
    {
        "type": enum("Polygon", "MultiPolygon"),
        "coordinates": {"bsonType": "array"},
    },
    ["type", "coordinates"],
)

# Único solo entre textos no vacíos: permite varios documentos sin el campo,
# con null o con "". (Un índice sparse NO sirve: "" y null sí entran al índice
# y chocarían entre ellos.)
SOLO_TEXTO_NO_VACIO = lambda campo: {campo: {"$type": "string", "$gt": ""}}  # noqa: E731

# --- Esquemas por colección -------------------------------------------------
# Cada entrada: nombre -> (validador o None, [(llaves, opciones_de_índice), ...])

COLECCIONES: dict[str, tuple[dict | None, list[tuple[list, dict]]]] = {}

# ---------- Catálogos ----------

COLECCIONES[db.LOTES] = (
    {"$jsonSchema": documento(
        {
            "nombre": TEXTO,
            "cultivos": CULTIVOS,
            "variedad": TEXTO_LIBRE,
            "area_ha": POSITIVO,
            "poligono": GEOJSON,
            "estado": enum("activo", "no_activo", "no_productivo"),
        },
        opcionales=("poligono",),
    )},
    [([("nombre", ASCENDING)], {"unique": True})],
)

COLECCIONES[db.LABORES] = (
    {"$jsonSchema": documento(
        {
            "nombre": TEXTO,
            "cultivos": CULTIVOS,
            "unidad_avance": enum("kg", "hectareas", "jornales", "racimos", "ninguna"),
            "admite_contrato": BOOL,
            "tipo_meta": TIPO_META,
            "activa": BOOL,
        },
        opcionales=("tipo_meta",),
    )},
    [([("nombre", ASCENDING)], {"unique": True})],
)

COLECCIONES[db.TRABAJADORES] = (
    {"$jsonSchema": documento(
        {
            "nombre": TEXTO,
            "documento": TEXTO_LIBRE,
            "telefono": TEXTO_LIBRE,
        },
        opcionales=("documento", "telefono"),
        # El tipo (recurrente/esporádico/de una vez) y el rendimiento se CALCULAN,
        # nunca se guardan.
        **{"not": {"anyOf": [{"required": ["tipo"]}, {"required": ["rendimiento"]}]}},
    )},
    [(
        [("documento", ASCENDING)],
        {"unique": True, "name": "documento_unico_no_vacio",
         "partialFilterExpression": SOLO_TEXTO_NO_VACIO("documento")},
    )],
)

COLECCIONES[db.INSUMOS] = (
    {"$jsonSchema": documento({
        "nombre": TEXTO,
        "unidad": TEXTO,
        "stock_actual": NO_NEGATIVO,
        "umbral_alerta": NO_NEGATIVO,
    })},
    [([("nombre", ASCENDING)], {"unique": True})],
)

COLECCIONES[db.UNIDADES] = (
    # equivalencias es informativo, p. ej. {"arroba": 12.5, "carga": 125, "bulto": 62.5} (kg)
    {"$jsonSchema": documento({
        "nombre": TEXTO,
        "equivalencias": objeto({}, additionalProperties=NO_NEGATIVO),
    })},
    [([("nombre", ASCENDING)], {"unique": True})],
)

COLECCIONES[db.USUARIOS] = (
    {"$jsonSchema": documento({
        "nombre": TEXTO,
        "usuario": TEXTO,
        "clave": TEXTO,  # hash de la clave, nunca la clave en claro
        "rol": enum("administrador", "mayordomo", "junta", "superusuario"),
        "activo": BOOL,
    })},
    [([("usuario", ASCENDING)], {"unique": True})],
)

# ---------- Operación ----------

COLECCIONES[db.LABOR_DIARIA] = (
    {"$jsonSchema": documento(
        {
            "fecha": FECHA,
            "trabajador_id": OID,
            "lote_id": OID,
            "labor_id": OID,
            # Copias congeladas de lo pactado (no referencias):
            "forma_pago": enum("jornal", "contrato"),
            "tarifa": POSITIVO,
            "tipo_meta": TIPO_META,
            "jornales": num(0, exclusivo=True, multiplo=0.5),
            "avance": NO_NEGATIVO,
            "completada": BOOL,
            "insumo_consumido": objeto(
                {"insumo_id": OID, "cantidad": POSITIVO}, ["insumo_id", "cantidad"]
            ),
            **AUDIT_CAPTURA,
            "fecha_cierre": {"bsonType": ["date", "null"]},
        },
        opcionales=("tipo_meta", "insumo_consumido", "fecha_cierre"),
        # A contrato, tipo_meta es obligatorio.
        anyOf=[
            {"properties": {"forma_pago": enum("jornal")}},
            {"properties": {"forma_pago": enum("contrato")}, "required": ["tipo_meta"]},
        ],
    )},
    [
        ([("fecha", DESCENDING)], {}),
        ([("trabajador_id", ASCENDING), ("fecha", DESCENDING)], {}),
        ([("lote_id", ASCENDING), ("fecha", DESCENDING)], {}),
    ],
)

COLECCIONES[db.POOL_SEMANA] = (
    {"$jsonSchema": documento(
        {
            "trabajador_id": OID,
            "semana": {"bsonType": "string", "pattern": r"^\d{4}-W(0[1-9]|[1-4]\d|5[0-3])$"},
            "activo": BOOL,
            "preasignacion": arreglo(objeto(
                {"dia": FECHA, "lote_id": OID, "labor_id": OID},
                ["dia", "lote_id", "labor_id"],
            )),
            "fecha_activacion": FECHA,
        },
        opcionales=("preasignacion",),
    )},
    [
        ([("trabajador_id", ASCENDING), ("semana", ASCENDING)], {"unique": True}),
        ([("semana", ASCENDING)], {}),
    ],
)

COLECCIONES[db.COSECHA_PLATANO] = (
    {"$jsonSchema": documento({
        "fecha": FECHA,
        "lote_id": OID,
        "kg": POSITIVO,
        "racimos": ENTERO_POSITIVO,
        "calidad": CALIDAD_PLATANO,
        **AUDIT_CAPTURA,
    })},
    [([("fecha", DESCENDING)], {}), ([("lote_id", ASCENDING), ("fecha", DESCENDING)], {})],
)

COLECCIONES[db.VENTA_PLATANO] = (
    {"$jsonSchema": documento(
        {
            "fecha": FECHA,
            "comprador": TEXTO,
            "kg": POSITIVO,
            "racimos": ENTERO_POSITIVO,
            "calidad": CALIDAD_PLATANO,
            "precio_kg": POSITIVO,
            "valor_total": NO_NEGATIVO,
            "cosecha_id": OID,
            **AUDIT_CAPTURA,
        },
        opcionales=("cosecha_id",),
    )},
    [([("fecha", DESCENDING)], {})],
)

COLECCIONES[db.VENTA_CAFE] = (
    {
        # Recibo de la Cooperativa, un solo documento con todo embebido.
        "$jsonSchema": documento(
            {
                "fecha": FECHA,
                "almacen": TEXTO,
                "tipo_producto": enum("mojado", "pasilla", "pergamino"),
                "sacos": {**ENTERO, "minimum": 0},
                "kg_brutos": POSITIVO,
                "destare": NO_NEGATIVO,
                "kg_netos": POSITIVO,
                "kg_pergamino_equivalente": NO_NEGATIVO,
                "analisis_calidad": objeto(
                    {"almendra_sana": PORCENTAJE, "pasilla": PORCENTAJE, "broca": PORCENTAJE},
                    ["almendra_sana", "pasilla", "broca"],
                ),
                "factor_rendimiento": POSITIVO,
                "precio_base": POSITIVO,
                "descuentos": arreglo(objeto(
                    {"concepto": TEXTO, "valor": NO_NEGATIVO}, ["concepto", "valor"]
                )),
                "valor_total": NO_NEGATIVO,
                "numero_pedido": TEXTO_LIBRE,
                "id_comprobante": TEXTO_LIBRE,
                "foto_ruta": TEXTO,
                **AUDIT_CAPTURA,
            },
            opcionales=("id_comprobante",),
        ),
        # Aritmética del recibo: kg_netos = kg_brutos - destare (tolerancia de redondeo).
        "$expr": {"$lte": [
            {"$abs": {"$subtract": ["$kg_netos", {"$subtract": ["$kg_brutos", "$destare"]}]}},
            0.01,
        ]},
    },
    [
        (
            [("id_comprobante", ASCENDING)],
            {"unique": True, "name": "id_comprobante_unico_no_vacio",
             "partialFilterExpression": SOLO_TEXTO_NO_VACIO("id_comprobante")},
        ),
        ([("fecha", DESCENDING)], {}),
    ],
)

COLECCIONES[db.COMPRA_INSUMO] = (
    {"$jsonSchema": documento(
        {
            "fecha": FECHA,
            "insumo_id": OID,
            "cantidad": POSITIVO,
            "valor": POSITIVO,
            "comprobante_ruta": TEXTO,
            **AUDIT_CAPTURA,
        },
        opcionales=("comprobante_ruta",),
    )},
    [([("fecha", DESCENDING)], {}), ([("insumo_id", ASCENDING), ("fecha", DESCENDING)], {})],
)

_CATEGORIAS_GASTO = ("nomina", "insumos", "servicios", "transporte", "casa", "otros")
COLECCIONES[db.GASTO] = (
    {"$jsonSchema": documento(
        {
            "fecha": FECHA,
            "categoria": enum(*_CATEGORIAS_GASTO),
            "descripcion": TEXTO_LIBRE,
            "valor": POSITIVO,
            **AUDIT_CAPTURA,
        },
        opcionales=("descripcion",),
        # Si la categoría es "otros", la descripción es obligatoria y no vacía.
        anyOf=[
            {"properties": {"categoria": enum(*[c for c in _CATEGORIAS_GASTO if c != "otros"])}},
            {"required": ["descripcion"], "properties": {"descripcion": TEXTO}},
        ],
    )},
    [([("fecha", DESCENDING)], {}), ([("categoria", ASCENDING), ("fecha", DESCENDING)], {})],
)

COLECCIONES[db.MOVIMIENTO_CAJA] = (
    # Aportes de capital, retiros y ajustes: alimentan el flujo de caja, NUNCA el margen.
    {"$jsonSchema": documento({
        "fecha": FECHA,
        "tipo": enum("aporte_capital", "retiro", "ajuste"),
        "valor": num(),
        "nota": TEXTO_LIBRE,
        **AUDIT_CAPTURA,
    })},
    [([("fecha", DESCENDING)], {})],
)

COLECCIONES[db.LLUVIA] = (
    # 1 o 2 lecturas por día; los mm del día son la suma.
    {"$jsonSchema": documento({
        "fecha_hora": FECHA,  # hora real de la lectura
        "mm": num(0, maximo=500),
        "foto_ruta": TEXTO,
        "leida_por": TEXTO,
        "fecha_captura": FECHA,
    })},
    [([("fecha_hora", ASCENDING)], {"unique": True})],
)

# ---------- Auditoría (sin validador estricto) ----------
# Campos: fecha, usuario, coleccion, documento_id, campo, valor_anterior, valor_nuevo.
COLECCIONES[db.AUDITORIA] = (
    None,
    [
        ([("coleccion", ASCENDING), ("documento_id", ASCENDING), ("fecha", DESCENDING)], {}),
        ([("fecha", DESCENDING)], {}),
    ],
)

assert set(COLECCIONES) == set(db.COLECCIONES), "init_db y db.COLECCIONES no coinciden"


# --- Ejecución ---------------------------------------------------------------

async def init_db(base: AsyncIOMotorDatabase | None = None) -> dict[str, str]:
    """Crea lo que falte. Devuelve {colección: "creada" | "ya existía"}."""
    base = base if base is not None else db.get_db()
    existentes = set(await base.list_collection_names())
    resultado: dict[str, str] = {}

    for nombre, (validador, indices) in COLECCIONES.items():
        if nombre in existentes:
            resultado[nombre] = "ya existía"
        else:
            opciones = {"validator": validador} if validador else {}
            try:
                await base.create_collection(nombre, **opciones)
                resultado[nombre] = "creada"
            except CollectionInvalid:  # la creó otro proceso entre medio
                resultado[nombre] = "ya existía"

        for llaves, opciones_indice in indices:
            try:
                await base[nombre].create_index(llaves, **opciones_indice)
            except OperationFailure as e:
                # Existe un índice con el mismo nombre/llaves pero otras opciones: se deja.
                print(f"  aviso: índice {llaves} de '{nombre}' no se cambió ({e.code}: {e.details.get('errmsg') if e.details else e})")

    return resultado


async def _main() -> None:
    resultado = await init_db()
    base = db.get_db()
    print(f"Base '{db.MONGO_DB}':")
    for nombre, estado in resultado.items():
        info = await (await base.list_collections(filter={"name": nombre})).to_list(1)
        con_validador = "con validador" if info and info[0].get("options", {}).get("validator") else "sin validador"
        n_indices = len(await base[nombre].index_information()) - 1  # sin contar _id
        print(f"  {nombre:<16} {estado:<11} {con_validador:<14} {n_indices} índice(s)")
    creadas = sum(1 for e in resultado.values() if e == "creada")
    print(f"{creadas} creada(s), {len(resultado) - creadas} ya existía(n). Total: {len(resultado)}.")
    db.close_client()


if __name__ == "__main__":
    asyncio.run(_main())
