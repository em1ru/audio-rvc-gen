"""
Interface do repositório de manifesto do golden dataset.

Exporta:
    - IManifestRepository (ABC): Contrato para leitura e escrita do manifesto CSV.

Utilizado por:
    - app.core.use_cases.run_pipeline_use_case (consumidor)
    - app.infrastructure.repositories.manifest_repository (implementação)
"""

from abc import ABC, abstractmethod
from typing import List

from app.core.entities.manifest_entry import ManifestEntry


class IManifestRepository(ABC):
    """
    Contrato para persistência incremental do manifesto do golden dataset.

    O manifesto é um CSV com uma linha por áudio (real ou fake), acumulado
    ao longo de múltiplas execuções do pipeline.

    Métodos Públicos:
        load: Carrega as entradas existentes do manifesto.
        save: Persiste a lista completa de entradas, sobrescrevendo o arquivo.

    Utilizado por:
        - app.core.use_cases.run_pipeline_use_case.RunPipelineUseCase
    """

    @abstractmethod
    def load(self) -> List[ManifestEntry]:
        """
        Carrega as entradas existentes do manifesto.

        Returns:
            List[ManifestEntry]: Entradas previamente salvas; lista vazia se não existir.
        """

    @abstractmethod
    def save(self, entries: List[ManifestEntry]) -> None:
        """
        Persiste a lista completa de entradas no manifesto CSV.

        Sobrescreve o arquivo existente. Para acumulação incremental,
        o consumidor deve carregar, mesclar e então salvar.

        Args:
            entries (List[ManifestEntry]): Lista completa de entradas a persistir.
        """
