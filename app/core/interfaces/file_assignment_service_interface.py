"""
Interface do serviço de atribuição de arquivos de áudio aos modelos de voz.

Exporta:
    - IFileAssignmentService (ABC): Contrato para distribuição de áudios entre modelos.

Utilizado por:
    - app.core.use_cases.run_pipeline_use_case (consumidor)
    - app.infrastructure.services.file_assignment_service (implementação)
"""

from abc import ABC, abstractmethod
from typing import Dict, List

from app.core.entities.voice_model import VoiceModel
from app.core.enums.assignment_strategy import AssignmentStrategy


class IFileAssignmentService(ABC):
    """
    Contrato para distribuição dos arquivos de áudio entre os modelos de voz.

    Métodos Públicos:
        assign: Mapeia cada modelo para sua lista de arquivos de entrada.

    Utilizado por:
        - app.core.use_cases.run_pipeline_use_case.RunPipelineUseCase
    """

    @abstractmethod
    def assign(
        self,
        source_paths: List[str],
        models: List[VoiceModel],
        strategy: AssignmentStrategy,
    ) -> Dict[str, List[str]]:
        """
        Distribui os arquivos de áudio entre os modelos conforme a estratégia escolhida.

        Args:
            source_paths (List[str]): Caminhos absolutos dos áudios reais de entrada.
            models (List[VoiceModel]): Modelos de voz disponíveis para conversão.
            strategy (AssignmentStrategy): Estratégia de atribuição (stratified ou cross).

        Returns:
            Dict[str, List[str]]: Mapeamento nome_do_modelo → lista de caminhos de entrada.

        Raises:
            ValueError: Se a estratégia fornecida não for reconhecida.
        """
