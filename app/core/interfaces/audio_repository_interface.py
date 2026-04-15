"""
Interface do repositório de arquivos de áudio.

Exporta:
    - IAudioRepository (ABC): Contrato para acesso e gerenciamento de WAVs do pipeline.

Utilizado por:
    - app.core.use_cases.run_pipeline_use_case (consumidor)
    - app.infrastructure.repositories.audio_repository (implementação)
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from app.core.entities.audio_file import AudioFile


class IAudioRepository(ABC):
    """
    Contrato para leitura dos áudios reais e controle de arquivos pendentes por modelo.

    Métodos Públicos:
        find_all_real: Lista todos os WAVs reais disponíveis.
        find_pending: Filtra arquivos ainda não convertidos para um modelo específico.

    Utilizado por:
        - app.core.use_cases.run_pipeline_use_case.RunPipelineUseCase

    Falhas de Domínio:
        - Implementações devem levantar AudioInputError se o diretório real estiver vazio.
    """

    @abstractmethod
    def find_all_real(self) -> List[str]:
        """
        Retorna os caminhos absolutos ordenados de todos os WAVs no diretório real.

        Returns:
            List[str]: Caminhos dos arquivos de entrada, ordenados alfabeticamente.

        Raises:
            AudioInputError: Se o diretório não existir ou não contiver arquivos WAV.
        """

    @abstractmethod
    def find_pending(
        self,
        source_paths: List[str],
        model_name: str,
        limit: Optional[int] = None,
    ) -> List[AudioFile]:
        """
        Filtra os arquivos ainda não convertidos para um dado modelo de voz.

        Args:
            source_paths (List[str]): Caminhos dos arquivos de entrada candidatos.
            model_name (str): Nome do modelo de voz (define o subdiretório de saída).
            limit (Optional[int]): Número máximo de arquivos a retornar;
                None retorna todos os pendentes.

        Returns:
            List[AudioFile]: Arquivos pendentes com caminhos de entrada e saída resolvidos.
        """
