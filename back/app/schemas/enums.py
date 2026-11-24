"""Enums del dominio; mismos valores que los validadores $jsonSchema de init_db.py."""

from enum import StrEnum


class FormaPago(StrEnum):
    jornal = "jornal"
    contrato = "contrato"


class Calidad(StrEnum):
    primera = "primera"
    segunda = "segunda"


class EstadoLote(StrEnum):
    activo = "activo"
    no_activo = "no_activo"
    no_productivo = "no_productivo"


class CategoriaGasto(StrEnum):
    nomina = "nomina"
    insumos = "insumos"
    servicios = "servicios"
    transporte = "transporte"
    casa = "casa"
    otros = "otros"


class TipoMovimientoCaja(StrEnum):
    aporte_capital = "aporte_capital"
    retiro = "retiro"
    ajuste = "ajuste"


class UnidadAvance(StrEnum):
    kg = "kg"
    hectareas = "hectareas"
    jornales = "jornales"
    racimos = "racimos"
    ninguna = "ninguna"


class TipoMeta(StrEnum):
    kilos = "kilos"
    horas = "horas"
    completada = "completada"


class Rol(StrEnum):
    administrador = "administrador"
    mayordomo = "mayordomo"
    junta = "junta"
    superusuario = "superusuario"


class TipoProductoCafe(StrEnum):
    mojado = "mojado"
    pasilla = "pasilla"
    pergamino = "pergamino"


class Cultivo(StrEnum):
    cafe = "cafe"
    platano = "platano"
