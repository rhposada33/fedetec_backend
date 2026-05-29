from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class EntradaRankingTecnico:
    tecnico_id: UUID
    region: str
    calificacion_promedio: float | None
    servicios_completados: int
    servicios_aceptados: int
    servicios_rechazados: int


def calcular_tasa_aceptacion(servicios_aceptados: int, servicios_rechazados: int) -> float:
    total_decisiones = servicios_aceptados + servicios_rechazados
    if total_decisiones <= 0:
        return 0
    return servicios_aceptados / total_decisiones


def calcular_porcentaje_cumplimiento(
    servicios_completados: int, servicios_aceptados: int
) -> int:
    if servicios_aceptados <= 0:
        return 0
    return round((servicios_completados / servicios_aceptados) * 100)


def calcular_puntos_ranking(entrada: EntradaRankingTecnico) -> int:
    calificacion = entrada.calificacion_promedio or 0
    tasa_aceptacion = calcular_tasa_aceptacion(
        entrada.servicios_aceptados, entrada.servicios_rechazados
    )
    cumplimiento = calcular_porcentaje_cumplimiento(
        entrada.servicios_completados, entrada.servicios_aceptados
    )
    return round(
        (entrada.servicios_completados * 10)
        + (calificacion * 100)
        + (tasa_aceptacion * 200)
        + cumplimiento
    )


def ordenar_ranking(
    entradas: list[EntradaRankingTecnico],
) -> list[tuple[EntradaRankingTecnico, int]]:
    return sorted(
        [(entrada, calcular_puntos_ranking(entrada)) for entrada in entradas],
        key=lambda item: (
            item[1],
            item[0].servicios_completados,
            item[0].calificacion_promedio or 0,
        ),
        reverse=True,
    )
