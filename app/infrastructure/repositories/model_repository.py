"""
Repositório de modelos de voz — descobre modelos válidos no sistema de arquivos.

Exporta:
    - ModelRepository (class): Implementação de IModelRepository via varredura de diretório.

Dependências externas:
    - Sistema de arquivos: diretório models/ com subpastas contendo .pth e .index.

Utilizado por:
    - app.infrastructure.factory.PipelineFactory
    - app.core.use_cases.run_pipeline_use_case.RunPipelineUseCase (via interface)

Falhas de Domínio:
    - Levanta ModelNotFoundError se o diretório de modelos não existir.
"""

import logging
import os
from typing import List, Optional

from app.core.entities.voice_model import VoiceModel
from app.core.exceptions.pipeline_exceptions import ModelNotFoundError
from app.core.interfaces.model_repository_interface import IModelRepository
from app.infrastructure.mappers.model_mapper import ModelMapper


_log = logging.getLogger(__name__)


class ModelRepository(IModelRepository):
    """
    Descobre e carrega modelos de voz RVC a partir do sistema de arquivos.

    Atributos:
        _models_dir (str): Diretório raiz onde as subpastas de modelos estão armazenadas.

    Métodos Públicos:
        find_all: Retorna todos os modelos válidos, com filtro opcional por nome.

    Utilizado por:
        - app.infrastructure.factory.PipelineFactory (instanciação)
        - app.core.use_cases.run_pipeline_use_case.RunPipelineUseCase (via injeção)

    Falhas de Domínio:
        - Levanta ModelNotFoundError se o diretório de modelos não existir.
    """

    def __init__(self, models_dir: str) -> None:
        self._models_dir = models_dir

    def find_all(self, name_filter: Optional[List[str]] = None) -> List[VoiceModel]:
        """
        Varre o diretório de modelos e retorna os válidos (com .pth e .index).

        Args:
            name_filter (Optional[List[str]]): Nomes de modelos permitidos.
                Se None ou lista vazia, retorna todos os descobertos.

        Returns:
            List[VoiceModel]: Modelos válidos, ordenados pelo nome da pasta.

        Raises:
            ModelNotFoundError: Se o diretório de modelos não existir.
        """
        if not os.path.isdir(self._models_dir):
            raise ModelNotFoundError(
                f"Diretório de modelos não encontrado: {self._models_dir}"
            )

        models: List[VoiceModel] = []

        for entry in sorted(os.listdir(self._models_dir)):
            model_dir = os.path.join(self._models_dir, entry)

            if not os.path.isdir(model_dir):
                continue
            if name_filter and entry not in name_filter:
                continue

            model = ModelMapper.from_directory(model_dir, entry)
            if model is None:
                _log.warning(f"Modelo '{entry}' ignorado: .pth ou .index ausente.")
                continue

            models.append(model)
            _log.debug(f"Modelo descoberto: {entry}")

        return models
