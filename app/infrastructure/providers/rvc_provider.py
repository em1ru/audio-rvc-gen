"""
Provedor de conversão de voz via engine Applio RVC v2.

Exporta:
    - RvcProvider (class): Implementação de IVoiceConverter usando o VoiceConverter do Applio.

Dependências externas:
    - rvc_engine/: Submódulo Applio com rvc.infer.infer.VoiceConverter.
    - tqdm: Barra de progresso no terminal.

Utilizado por:
    - app.infrastructure.factory.PipelineFactory

Falhas de Domínio:
    - Levanta RvcEngineError se o diretório do engine não existir ao tentar converter.
    - Erros individuais de conversão são logados em 'conversion_errors' sem interromper o lote.
"""

import logging
import os
import sys
import time
from typing import List, Optional

import tqdm

from app.core.entities.audio_file import AudioFile
from app.core.entities.conversion_result import ConversionResult
from app.core.entities.rvc_params import RvcParams
from app.core.entities.voice_model import VoiceModel
from app.core.exceptions.pipeline_exceptions import RvcEngineError
from app.core.interfaces.voice_converter_interface import IVoiceConverter


_log = logging.getLogger(__name__)

# Logger dedicado para erros de conversão por arquivo, em formato estruturado.
# Saída: conversion_errors.log — configurado em AppModule._setup_logging.
_error_log = logging.getLogger("conversion_errors")


class RvcProvider(IVoiceConverter):
    """
    Integra o engine Applio RVC v2 para execução de conversão de voz em lote.

    O engine é carregado de forma lazy: o diretório é validado e adicionado ao
    PYTHONPATH somente na primeira chamada a convert_batch, permitindo que
    operações como --list-models funcionem sem o engine instalado.

    Atributos:
        _engine_dir (str): Caminho do submódulo rvc_engine adicionado ao PYTHONPATH.
        _is_ready (bool): Flag de inicialização lazy do engine.

    Métodos Públicos:
        convert_batch: Converte uma lista de arquivos para uma voz-alvo.

    Utilizado por:
        - app.infrastructure.factory.PipelineFactory

    Falhas de Domínio:
        - Levanta RvcEngineError se o diretório do engine não existir.
    """

    def __init__(self, engine_dir: str) -> None:
        self._engine_dir = engine_dir
        self._is_ready: bool = False

    def convert_batch(
        self,
        model: VoiceModel,
        files: List[AudioFile],
        params: RvcParams,
    ) -> ConversionResult:
        """
        Converte um lote de arquivos de áudio para a voz do modelo fornecido.

        Args:
            model (VoiceModel): Modelo de voz de destino (pesos .pth + índice FAISS .index).
            files (List[AudioFile]): Arquivos de áudio pendentes a converter.
            params (RvcParams): Parâmetros de inferência RVC (F0, index_rate, pitch...).

        Returns:
            ConversionResult: Resultado com contagem de sucessos, erros e tempo total.

        Raises:
            RvcEngineError: Se o diretório do engine RVC não existir.
        """
        self._ensure_engine_ready()

        from rvc.infer.infer import VoiceConverter  # importação após setup do PYTHONPATH

        _log.info(
            f"Carregando VoiceConverter para '{model.name}' "
            f"(F0: {params.f0_method.value}, "
            f"index_rate: {params.index_rate}, "
            f"protect: {params.protect})"
        )

        voice_converter = VoiceConverter()
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
                error_message = self._convert_single(
                    voice_converter, model, audio_file, params
                )
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
        voice_converter: object,
        model: VoiceModel,
        audio_file: AudioFile,
        params: RvcParams,
    ) -> Optional[str]:
        """
        Executa a conversão de um único arquivo de áudio via VoiceConverter.

        Args:
            voice_converter: Instância do VoiceConverter do Applio já carregada.
            model (VoiceModel): Modelo de voz de destino.
            audio_file (AudioFile): Par de caminhos de entrada e saída.
            params (RvcParams): Parâmetros de inferência RVC.

        Returns:
            str: Mensagem de erro descritiva se a conversão falhou.
            None: Se a conversão foi bem-sucedida.
        """
        try:
            voice_converter.convert_audio(
                audio_input_path=audio_file.source_path,
                audio_output_path=audio_file.target_path,
                model_path=model.pth_path,
                index_path=model.index_path,
                pitch=params.pitch,
                f0_method=params.f0_method.value,
                index_rate=params.index_rate,
                volume_envelope=params.volume_envelope,
                protect=params.protect,
                hop_length=params.hop_length,
                split_audio=False,
                f0_autotune=False,
                clean_audio=False,
                export_format=params.export_format,
                resample_sr=0,
                sid=0,
            )

            if not os.path.isfile(audio_file.target_path):
                return "Arquivo de saída não criado pelo engine RVC."

            _log.debug(f"Convertido: {audio_file.filename}")
            return None

        except Exception as exc:
            self._cleanup_partial_output(audio_file.target_path)
            return str(exc)

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

    def _ensure_engine_ready(self) -> None:
        """
        Valida e configura o engine RVC na primeira chamada (inicialização lazy).

        Raises:
            RvcEngineError: Se o diretório do engine não existir.
        """
        if self._is_ready:
            return

        if not os.path.isdir(self._engine_dir):
            raise RvcEngineError(
                f"Diretório do engine RVC não encontrado: {self._engine_dir}. "
                "Execute scripts/setup_env.bat antes de rodar o pipeline."
            )

        if self._engine_dir not in sys.path:
            sys.path.insert(0, self._engine_dir)

        os.chdir(self._engine_dir)
        self._is_ready = True
        _log.debug(f"Engine RVC configurado: {self._engine_dir}")
