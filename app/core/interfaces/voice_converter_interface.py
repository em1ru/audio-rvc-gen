"""
Interface do conversor de voz via engine RVC.

Exporta:
    - IVoiceConverter (ABC): Contrato para execução de conversão de voz em lote.

Utilizado por:
    - app.core.use_cases.run_pipeline_use_case (consumidor)
    - app.infrastructure.providers.rvc_provider (implementação)
"""

from abc import ABC, abstractmethod
from typing import List

from app.core.entities.audio_file import AudioFile
from app.core.entities.conversion_result import ConversionResult
from app.core.entities.rvc_params import RvcParams
from app.core.entities.voice_model import VoiceModel


class IVoiceConverter(ABC):
    """
    Contrato para execução de conversão de voz em lote via engine RVC.

    Métodos Públicos:
        convert_batch: Converte uma lista de arquivos para uma voz-alvo.

    Utilizado por:
        - app.core.use_cases.run_pipeline_use_case.RunPipelineUseCase

    Falhas de Domínio:
        - Implementações devem levantar RvcEngineError se o engine não inicializar.
        - Erros por arquivo devem ser logados individualmente sem interromper o lote.
    """

    @abstractmethod
    def convert_batch(
        self,
        model: VoiceModel,
        files: List[AudioFile],
        params: RvcParams,
    ) -> ConversionResult:
        """
        Converte um lote de arquivos de áudio para a voz do modelo fornecido.

        Args:
            model (VoiceModel): Modelo de voz de destino (pesos .pth + índice .index).
            files (List[AudioFile]): Arquivos de áudio a converter.
            params (RvcParams): Parâmetros de inferência RVC (F0, index_rate, pitch...).

        Returns:
            ConversionResult: Resultado com contagem de sucessos, erros e tempo total.

        Raises:
            RvcEngineError: Se o engine RVC não puder ser inicializado.
        """
