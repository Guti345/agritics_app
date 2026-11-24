"""Fotos: viven en la carpeta fotos/ de la raíz del repo; los documentos guardan la ruta."""

from pathlib import Path

from back.app.reglas.errores import datos_invalidos

RAIZ = Path(__file__).resolve().parents[3]  # back/app/reglas/ -> raíz del repo
FOTOS_DIR = RAIZ / "fotos"


def exigir_foto(ruta: str) -> None:
    """La ruta debe ser una foto ya subida con POST /uploads/foto ("fotos/<archivo>")."""
    nombre = ruta.removeprefix("fotos/")
    archivo = (FOTOS_DIR / nombre).resolve()
    if not ruta.startswith("fotos/") or "/" in nombre or "\\" in nombre or archivo.parent != FOTOS_DIR.resolve():
        raise datos_invalidos(f"La ruta de la foto '{ruta}' no es válida: usa la que devuelve /uploads/foto")
    if not archivo.is_file():
        raise datos_invalidos(f"La foto '{ruta}' no está en el servidor: súbela primero con /uploads/foto")
