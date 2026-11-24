"""DTOs del pool de la semana."""

from datetime import date

from pydantic import BaseModel, Field, model_validator

from .campos import FechaHoraOut, FechaOut, OidIn, OidOut, SemanaISO
from .base import Entrada, Salida


class Preasignacion(Entrada):
    dia: date
    lote_id: OidIn
    labor_id: OidIn


class PoolSemanaCreate(Entrada):
    trabajador_id: OidIn
    semana: SemanaISO
    activo: bool = True
    preasignacion: list[Preasignacion] = Field(default_factory=list)

    @model_validator(mode="after")
    def _dias_de_la_semana(self):
        anio, num = int(self.semana[:4]), int(self.semana[6:])
        for p in self.preasignacion:
            a, s, _ = p.dia.isocalendar()
            if (a, s) != (anio, num):
                raise ValueError(f"El día {p.dia:%Y-%m-%d} no es de la semana {self.semana}")
        return self


class PreasignacionResponse(BaseModel):
    dia: FechaOut
    lote_id: OidOut
    labor_id: OidOut


class PoolSemanaResponse(Salida):
    trabajador_id: OidOut
    semana: str
    activo: bool
    preasignacion: list[PreasignacionResponse] = Field(default_factory=list)
    fecha_activacion: FechaHoraOut
