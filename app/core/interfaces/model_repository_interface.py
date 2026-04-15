"""
Interface do repositório de modelos de voz.

Exporta:
    - IModelRepository (ABC): Contrato para descoberta de modelos no sistema de arquivos.

Utilizado por:
    - app.core.use_cases.run_pipeline_use_case (consumidor)
    - app.infrastructure.repositories.model_repository (implementação)
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from app.core.entities.voice_model import VoiceModel


class IModelRepository(ABC):
    """
    Contrato para descoberta e acesso aos modelos de voz disponíveis.

    Métodos Públicos:
        find_all: Retorna todos os modelos válidos descobertos no diretório.

    Utilizado por:
        - app.core.use_cases.run_pipeline_use_case.RunPipelineUseCase

    Falhas de Domínio:
        - Implementações devem levantar ModelNotFoundError se o diretório não existir.
    """

    @abstractmethod
    def find_all(self, name_filter: Optional[List[str]] = None) -> List[VoiceModel]:
        """
        Retorna todos os modelos de voz válidos (com .pth e .index).

        Args:
            name_filter (Optional[List[str]]): Nomes de modelos permitidos.
                Se None ou lista vazia, retorna todos os modelos descobertos.

        Returns:
            List[VoiceModel]: Lista de modelos válidos, ordenados pelo nome.

        Raises:
            ModelNotFoundError: Se o diretório de modelos não existir.
        """
