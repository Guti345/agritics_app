"""Carga de datos simulados (un año cafetero: enero - semana 46 de 2026).

Uso (desde la raíz del repo):  python back/datos_mongo.py
                         o:  python -m back.datos_mongo

Primero corre back.init_db (idempotente) para asegurar las colecciones con sus
validadores e índices; después carga los datos (pendiente de implementar).
"""

import asyncio
import sys
from pathlib import Path

# Con `python back/datos_mongo.py`, Python solo ve la carpeta back/; se agrega la
# raíz del repo para poder importar el paquete `back`.
_RAIZ = str(Path(__file__).resolve().parents[1])
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from back.app import database as db  # noqa: E402
from back.init_db import init_db  # noqa: E402


async def main() -> None:
    resultado = await init_db()
    creadas = [n for n, e in resultado.items() if e == "creada"]
    print(f"Colecciones listas en '{db.MONGO_DB}' ({len(creadas)} nueva(s)).")
    print("Carga de datos simulados: pendiente.")
    db.close_client()


if __name__ == "__main__":
    asyncio.run(main())
