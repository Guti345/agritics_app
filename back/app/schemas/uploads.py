"""DTO de la subida de fotos (lluvia, recibos de café, comprobantes de compra)."""

from pydantic import BaseModel


class FotoSubidaResponse(BaseModel):
    """Ruta relativa al repo ("fotos/<archivo>") que luego va en foto_ruta / comprobante_ruta."""
    ruta: str
