"""
Entidade que representa o resultado agregado de uma sessão de conversão de voz.

Exporta:
    - ConversionResult (dataclass): Métricas de sucesso, erro e tempo de um modelo.

Utilizado por:
    - app.core.use_cases.run_pipeline_use_case
    - app.core.interfaces.voice_converter_interface
    - app.presentation.dtos.pipeline_result_dto
    - app.infrastructure.providers.rvc_provider
"""

from dataclasses import dataclass


@dataclass
class ConversionResult:
    """
    Resultado agregado de uma sessão de conversão para um único modelo de voz.

    Atributos:
        model_name (str): Nome do modelo de voz processado.
        success_count (int): Número de arquivos convertidos com sucesso.
        error_count (int): Número de arquivos que falharam na conversão.
        elapsed_seconds (float): Tempo total de processamento em segundos.

    Utilizado por:
        - app.core.use_cases.run_pipeline_use_case.RunPipelineUseCase
        - app.presentation.controllers.pipeline_controller.PipelineController
    """

    model_name: str
    success_count: int
    error_count: int
    elapsed_seconds: float
