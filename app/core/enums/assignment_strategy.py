"""
Enumeração das estratégias de atribuição de arquivos a modelos de voz.

Exporta:
    - AssignmentStrategy (enum): Define como os áudios reais são distribuídos entre os modelos.

Utilizado por:
    - app.core.use_cases.run_pipeline_use_case
    - app.presentation.dtos.pipeline_request_dto
    - app.infrastructure.services.file_assignment_service
"""

from enum import Enum


class AssignmentStrategy(str, Enum):
    """
    Estratégia de distribuição dos arquivos de áudio entre os modelos de voz.

    Atributos:
        STRATIFIED (str): Divide os arquivos por round-robin entre os modelos,
            garantindo total_fake ≈ total_real e diversidade de locutores por modelo.
        CROSS (str): Cada arquivo é convertido por todos os modelos
            (N_arquivos × N_modelos conversões — alto custo computacional).

    Utilizado por:
        - app.infrastructure.services.file_assignment_service.FileAssignmentService
    """

    STRATIFIED = "stratified"
    CROSS = "cross"
