"""Errores de negocio en español claro (regla transversal del proyecto).

Ninguna validación de negocio llega a Mongo como error interno. Las reglas se
validan antes, aquí en la API, y fallan con uno de estos helpers:

    201  al crear (se pone en el decorador del endpoint: status_code=201)
    404  no_encontrado("No existe el lote 'La Cañada'")
    409  conflicto("No hay stock suficiente de urea: quedan 40 kg")
    422  datos_invalidos("La lluvia no puede pasar de 500 mm en un día")

El texto debe entenderlo un mayordomo de finca: qué pasó y, si se puede, el dato
concreto (cuánto queda, qué semana, qué trabajador).
"""

from fastapi import HTTPException, status


def no_encontrado(mensaje: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=mensaje)


def conflicto(mensaje: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=mensaje)


def datos_invalidos(mensaje: str) -> HTTPException:
    return HTTPException(status_code=422, detail=mensaje)
