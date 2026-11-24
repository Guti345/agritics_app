from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from back.app.auth import ADMIN, requiere_rol
from back.app.database import get_db
from back.app.reglas.cortes import crear_corte, preview
from back.app.schemas import CorteCreate, CortePreviewResponse, CorteResponse
from back.app.utils import semana_de_query

router = APIRouter(prefix="/cortes", tags=["Cortes de nómina"])

SOLO_ADMINISTRADOR = requiere_rol("administrador")


@router.get("/preview/{semana}", response_model=CortePreviewResponse, summary="Resumen ANTES de cortar")
async def ver_preview(semana: str, db: AsyncIOMotorDatabase = Depends(get_db), _: dict = Depends(ADMIN)):
    """Periodo abierto y lo que se pagaría si se corta hoy; labores abiertas (las de jornal
    NO se pagan en el corte); contratos abiertos con su saldo adelantable; cortes ya
    hechos con sus totales; pool activo; ventas y gastos de la semana; cuadres y alertas."""
    return CortePreviewResponse.model_validate(await preview(db, semana_de_query(semana)))


@router.post("", response_model=CorteResponse, status_code=status.HTTP_201_CREATED,
             summary="Hacer un corte de nómina (solo administrador)")
async def cortar(
    datos: CorteCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    yo: dict = Depends(SOLO_ADMINISTRADOR),
):
    """Cierra el periodo desde el día siguiente al último corte de la semana (o el lunes)
    hasta `hasta` (por defecto hoy). Paga: jornal completadas sin corte + contrato
    completadas sin corte (pactado - anticipos) + anticipos nuevos sobre contratos
    abiertos. La nómina no se guarda: va en la respuesta y es recalculable."""
    return CorteResponse.model_validate(await crear_corte(db, datos, yo))
