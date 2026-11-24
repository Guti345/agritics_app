import re
import unicodedata
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile, status

from back.app.auth import ADMIN_O_MAYORDOMO
from back.app.reglas.errores import datos_invalidos
from back.app.reglas.fotos import FOTOS_DIR
from back.app.schemas import FotoSubidaResponse, ahora

router = APIRouter(prefix="/uploads", tags=["Fotos"])

MAX_BYTES = 10 * 1024 * 1024  # 10 MB
EXTENSIONES = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}


def _sanear(nombre: str) -> str:
    """'Recibo Coop #12 (ñ).JPG' -> 'Recibo_Coop_12_n.jpg' (sin tildes, espacios ni rutas)."""
    nombre = Path(nombre.replace("\\", "/")).name
    nombre = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    raiz, ext = Path(nombre).stem, Path(nombre).suffix.lower()
    raiz = re.sub(r"[^A-Za-z0-9_-]+", "_", raiz).strip("_")[:60] or "foto"
    return f"{raiz}{ext}"


def _es_imagen(contenido: bytes) -> bool:
    """Revisa la firma del archivo, no solo la extensión."""
    return (
        contenido.startswith(b"\xff\xd8\xff")                                  # JPG
        or contenido.startswith(b"\x89PNG\r\n\x1a\n")                          # PNG
        or (contenido[:4] == b"RIFF" and contenido[8:12] == b"WEBP")          # WEBP
        or (contenido[4:8] == b"ftyp" and contenido[8:12] in {b"heic", b"heix", b"mif1", b"msf1", b"hevc"})  # HEIC
    )


@router.post("/foto", response_model=FotoSubidaResponse, status_code=status.HTTP_201_CREATED,
             summary="Subir una foto (pluviómetro, recibo de la Cooperativa, comprobante)")
async def subir_foto(archivo: UploadFile = File(...), _: dict = Depends(ADMIN_O_MAYORDOMO)):
    """Guarda la foto en fotos/ con nombre único (fecha-hora + nombre original saneado) y
    devuelve su `ruta`, que luego va en foto_ruta o comprobante_ruta."""
    nombre = _sanear(archivo.filename or "")
    if Path(nombre).suffix not in EXTENSIONES:
        raise datos_invalidos("La foto debe ser una imagen JPG, PNG, WEBP o HEIC")
    contenido = await archivo.read(MAX_BYTES + 1)
    if not contenido:
        raise datos_invalidos("El archivo llegó vacío: vuelve a tomar la foto")
    if len(contenido) > MAX_BYTES:
        raise datos_invalidos("La foto pesa más de 10 MB: tómala con menos resolución")
    if not _es_imagen(contenido):
        raise datos_invalidos("El archivo no es una imagen válida: sube una foto JPG, PNG, WEBP o HEIC")

    FOTOS_DIR.mkdir(exist_ok=True)
    final = f"{ahora():%Y%m%d-%H%M%S-%f}_{nombre}"
    with open(FOTOS_DIR / final, "xb") as f:  # "x": nunca sobrescribe una foto existente
        f.write(contenido)
    return FotoSubidaResponse(ruta=f"fotos/{final}")
