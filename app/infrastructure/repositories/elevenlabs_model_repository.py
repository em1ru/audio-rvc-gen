"""
Repositório de modelos de voz ElevenLabs — carrega vozes a partir da configuração.

Exporta:
    - ElevenLabsModelRepository (class): Implementação de IModelRepository para ElevenLabs.

Dependências:
    - config.yaml: seção elevenlabs.voices com nome e voice_id de cada voz.

Utilizado por:
    - app.infrastructure.factory.PipelineFactory

Falhas de Domínio:
    - Levanta ModelNotFoundError se a lista de vozes estiver vazia ou nenhuma voz
      corresponder ao filtro ativo.
"""

import logging
from typing import List, Optional

from app.core.entities.voice_model import VoiceModel
from app.core.exceptions.pipeline_exceptions import ModelNotFoundError
from app.core.interfaces.model_repository_interface import IModelRepository


_log = logging.getLogger(__name__)


class ElevenLabsModelRepository(IModelRepository):
    """
    Fornece os modelos de voz ElevenLabs configurados para uso no pipeline.

    As vozes são lidas da configuração (config.yaml) em vez do sistema de arquivos,
    pois modelos ElevenLabs são identificados por voice_id na API, não por arquivos locais.

    Atributos:
        _voices (List[dict]): Lista de dicionários com 'name' e 'voice_id' de cada voz.

    Métodos Públicos:
        find_all: Retorna todos os modelos configurados, opcionalmente filtrados por nome.

    Utilizado por:
        - app.infrastructure.factory.PipelineFactory (instanciação)
        - app.core.use_cases.run_pipeline_use_case.RunPipelineUseCase (via injeção)

    Falhas de Domínio:
        - Levanta ModelNotFoundError se nenhuma voz estiver configurada ou disponível.
    """

    def __init__(self, voices: List[dict]) -> None:
        self._voices = voices

    def find_all(self, name_filter: Optional[List[str]] = None) -> List[VoiceModel]:
        """
        Retorna todos os modelos de voz ElevenLabs configurados.

        Args:
            name_filter (Optional[List[str]]): Nomes das vozes a incluir;
                None retorna todas as vozes configuradas.

        Returns:
            List[VoiceModel]: Lista de modelos com voice_id preenchido, ordenados por nome.

        Raises:
            ModelNotFoundError: Se nenhuma voz estiver configurada ou restar após filtro.
        """
        if not self._voices:
            raise ModelNotFoundError(
                "Nenhuma voz ElevenLabs configurada. "
                "Adicione entradas em elevenlabs.voices no config.yaml."
            )

        models = [
            VoiceModel(
                name=v["name"],
                pth_path="",
                index_path="",
                voice_id=v["voice_id"],
            )
            for v in self._voices
            if "name" in v and "voice_id" in v
        ]

        if name_filter:
            models = [m for m in models if m.name in name_filter]

        if not models:
            raise ModelNotFoundError(
                f"Nenhuma voz ElevenLabs encontrada para o filtro: {name_filter}. "
                "Verifique os nomes em elevenlabs.voices no config.yaml."
            )

        models.sort(key=lambda m: m.name)
        _log.info(f"{len(models)} voz(es) ElevenLabs carregada(s).")
        return models
