"""
DTO de resposta do pipeline para o controlador.

Exporta:
    - PipelineResultDTO (dataclass): Resultado consolidado da execução do pipeline.

Utilizado por:
    - app.presentation.controllers.pipeline_controller
"""

from dataclasses import dataclass
from typing import List

from app.core.entities.conversion_result import ConversionResult


@dataclass
class PipelineResultDTO:
    """
    Resultado consolidado da execução completa do pipeline.

    Atributos:
        results (List[ConversionResult]): Resultado individual por modelo de voz.
        total_success (int): Total de conversões bem-sucedidas em todos os modelos.
        total_errors (int): Total de conversões com erro em todos os modelos.
        total_elapsed_seconds (float): Tempo de parede total da execução do pipeline.

    Utilizado por:
        - app.presentation.controllers.pipeline_controller.PipelineController
    """

    results: List[ConversionResult]
    total_success: int
    total_errors: int
    total_elapsed_seconds: float
