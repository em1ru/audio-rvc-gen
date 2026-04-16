"""
Provedor de conversão de voz via API ElevenLabs speech-to-speech.

Exporta:
    - ElevenLabsProvider (class): Implementação de IVoiceConverter usando a API ElevenLabs.

Dependências externas:
    - elevenlabs: SDK oficial da ElevenLabs (pip install elevenlabs).
    - ELEVENLABS_API_KEY: Variável de ambiente com a chave de API.
    - tqdm: Barra de progresso no terminal.

Utilizado por:
    - app.infrastructure.factory.PipelineFactory

Falhas de Domínio:
    - Levanta ElevenLabsError se a chave de API estiver ausente ou inválida.
    - Erros individuais de conversão são logados em 'conversion_errors' sem interromper o lote.
"""

import logging
import os
import time
import wave
from typing import List, Optional

import tqdm

from app.core.entities.audio_file import AudioFile
from app.core.entities.conversion_params import ConversionParams
from app.core.entities.conversion_result import ConversionResult
from app.core.entities.elevenlabs_params import ElevenLabsParams
from app.core.entities.voice_model import VoiceModel
from app.core.exceptions.pipeline_exceptions import ElevenLabsError
from app.core.interfaces.voice_converter_interface import IVoiceConverter


_log = logging.getLogger(__name__)

# Logger dedicado para erros de conversão por arquivo, em formato estruturado.
# Saída: conversion_errors.log — configurado em AppModule._setup_logging.
_error_log = logging.getLogger("conversion_errors")

# Taxa de amostragem (Hz) do formato pcm_16000 retornado pela API ElevenLabs.
# Impacto: Deve corresponder ao output_format usado; alterar requer atualizar ambos.
_PCM_SAMPLE_RATE = 16000

# Largura de amostra em bytes para PCM 16-bit.
# Impacto: Define a resolução do áudio; 2 bytes = 16-bit é o padrão do golden dataset.
_PCM_SAMPLE_WIDTH = 2

# Número de canais do áudio PCM retornado pela API ElevenLabs.
# Impacto: ElevenLabs pcm_16000 retorna sempre mono; alterar quebra a escrita do WAV.
_PCM_CHANNELS = 1


class ElevenLabsProvider(IVoiceConverter):
    """
    Integra a API ElevenLabs para execução de conversão de voz speech-to-speech em lote.

    O cliente ElevenLabs é instanciado uma única vez no construtor e reutilizado
    em todas as chamadas de convert_batch, evitando overhead de autenticação por arquivo.

    Atributos:
        _api_key (str): Chave de API ElevenLabs lida do ambiente ou da config.
        _client: Instância do cliente ElevenLabs (inicializada no construtor).

    Métodos Públicos:
        convert_batch: Converte uma lista de arquivos para uma voz-alvo via STS.

    Utilizado por:
        - app.infrastructure.factory.PipelineFactory

    Falhas de Domínio:
        - Levanta ElevenLabsError se a API key estiver ausente.
    """

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ElevenLabsError(
                "Chave de API ElevenLabs ausente. "
                "Defina a variável de ambiente ELEVENLABS_API_KEY antes de executar."
            )
        self._api_key = api_key
        from elevenlabs import ElevenLabs
        self._client = ElevenLabs(api_key=api_key)

    def convert_batch(
        self,
        model: VoiceModel,
        files: List[AudioFile],
        params: ConversionParams,
    ) -> ConversionResult:
        """
        Converte um lote de arquivos de áudio para a voz do modelo fornecido via STS.

        Args:
            model (VoiceModel): Modelo de voz de destino com voice_id ElevenLabs preenchido.
            files (List[AudioFile]): Arquivos de áudio pendentes a converter.
            params (ConversionParams): Deve ser ElevenLabsParams com model_id e output_format.

        Returns:
            ConversionResult: Resultado com contagem de sucessos, erros e tempo total.

        Raises:
            ElevenLabsError: Se a chave de API estiver ausente ou o modelo inválido.
        """
        if not isinstance(params, ElevenLabsParams):
            raise ElevenLabsError(
                f"ElevenLabsProvider requer ElevenLabsParams, recebeu {type(params).__name__}."
            )

        _log.info(
            f"Iniciando ElevenLabs STS para '{model.name}' "
            f"(voice_id: {model.voice_id}, model: {params.model_id})"
        )

        converted_files: List[AudioFile] = []
        errors = 0
        t_start = time.time()

        with tqdm.tqdm(
            total=len(files),
            desc=f"  {model.name}",
            unit="arq",
            ncols=80,
        ) as progress:
            for audio_file in files:
                error_message = self._convert_single(model, audio_file, params)
                if error_message:
                    errors += 1
                    _error_log.error(
                        f"{model.name}|{audio_file.filename}|{error_message}"
                    )
                else:
                    converted_files.append(audio_file)
                progress.update(1)

        elapsed = time.time() - t_start
        return ConversionResult(
            model_name=model.name,
            success_count=len(converted_files),
            error_count=errors,
            elapsed_seconds=elapsed,
            converted_files=converted_files,
        )

    def _convert_single(
        self,
        model: VoiceModel,
        audio_file: AudioFile,
        params: ElevenLabsParams,
    ) -> Optional[str]:
        """
        Executa a conversão de um único arquivo via ElevenLabs speech-to-speech.

        Args:
            model (VoiceModel): Modelo de voz de destino com voice_id preenchido.
            audio_file (AudioFile): Par de caminhos de entrada e saída.
            params (ElevenLabsParams): Parâmetros da API ElevenLabs.

        Returns:
            str: Mensagem de erro descritiva se a conversão falhou.
            None: Se a conversão foi bem-sucedida.
        """
        try:
            os.makedirs(os.path.dirname(audio_file.target_path), exist_ok=True)

            with open(audio_file.source_path, "rb") as audio_in:
                audio_stream = self._client.speech_to_speech.convert(
                    voice_id=model.voice_id,
                    audio=audio_in,
                    model_id=params.model_id,
                    output_format=params.output_format,
                )

            pcm_bytes = b"".join(audio_stream)

            if not pcm_bytes:
                return "API ElevenLabs retornou resposta vazia."

            self._save_pcm_as_wav(pcm_bytes, audio_file.target_path)

            if not os.path.isfile(audio_file.target_path):
                return "Arquivo de saída não criado após escrita do WAV."

            _log.debug(f"Convertido via ElevenLabs: {audio_file.filename}")
            return None

        except Exception as exc:
            self._cleanup_partial_output(audio_file.target_path)
            return str(exc)

    def _save_pcm_as_wav(self, pcm_bytes: bytes, output_path: str) -> None:
        """
        Empacota bytes PCM brutos em um arquivo WAV válido.

        Args:
            pcm_bytes (bytes): Dados PCM 16-bit mono a 16 kHz retornados pela API.
            output_path (str): Caminho absoluto do arquivo WAV a criar.
        """
        with wave.open(output_path, "wb") as wav_file:
            wav_file.setnchannels(_PCM_CHANNELS)
            wav_file.setsampwidth(_PCM_SAMPLE_WIDTH)
            wav_file.setframerate(_PCM_SAMPLE_RATE)
            wav_file.writeframes(pcm_bytes)

    def _cleanup_partial_output(self, target_path: str) -> None:
        """
        Remove arquivo de saída parcialmente escrito após falha de conversão.

        Args:
            target_path (str): Caminho do arquivo de saída a remover.
        """
        if os.path.isfile(target_path):
            try:
                os.remove(target_path)
            except OSError:
                _log.warning(f"Não foi possível remover arquivo parcial: {target_path}")
