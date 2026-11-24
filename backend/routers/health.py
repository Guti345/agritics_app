from fastapi import APIRouter

router = APIRouter(tags=["Sistema"])


@router.get("/health", summary="Verifica que la API está arriba")
async def health() -> dict:
    return {"status": "ok", "app": "Agritics"}
