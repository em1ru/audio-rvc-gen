"""
Repositório de arquivos de áudio — lê áudios reais e gerencia saídas por modelo.

Exporta:
    - AudioRepository (class): Implementação de IAudioRepository via sistema de arquivos.

Dependências externas:
    - Sistema de arquivos: data/real/ (entrada) e data/fake/<modelo>/ (saída).

Utilizado por:
    - app.infrastructure.factory.PipelineFactory
    - app.core.use_cases.run_pipeline_use_case.RunPipelineUseCase (via interface)

Falhas de Domínio:
    - Levanta AudioInputError se o diretório real estiver ausente ou vazio.
"""

import glob
import logging
import os
from typing import List, Optional

from app.core.entities.audio_file import AudioFile
from app.core.exceptions.pipeline_exceptions import AudioInputError
from app.core.interfaces.audio_repository_interface import IAudioRepository


_log = logging.getLogger(__name__)


class AudioRepository(IAudioRepository):
    """
    Gerencia o acesso aos WAVs de entrada (reais) e controla os de saída (deepfake).

    Atributos:
        _real_dir (str): Diretório dos áudios reais de entrada.
        _fake_dir (str): Diretório raiz onde os deepfakes são salvos, um subdiretório por modelo.

    Métodos Públicos:
        find_all_real: Lista todos os WAVs no diretório real.
        find_pending: Filtra arquivos ainda não convertidos para um modelo.

    Utilizado por:
        - app.infrastructure.factory.PipelineFactory (instanciação)
        - app.core.use_cases.run_pipeline_use_case.RunPipelineUseCase (via injeção)

    Falhas de Domínio:
        - Levanta AudioInputError se o diretório real estiver vazio ou ausente.
    """

    def __init__(self, real_dir: str, fake_dir: str) -> None:
        self._real_dir = real_dir
        self._fake_dir = fake_dir

    def find_all_real(self) -> List[str]:
        """
        Retorna caminhos absolutos ordenados de todos os WAVs no diretório real.

        Returns:
            List[str]: Caminhos dos arquivos de entrada, ordenados alfabeticamente.

        Raises:
            AudioInputError: Se o diretório não existir ou não contiver arquivos WAV.
        """
        if not os.path.isdir(self._real_dir):
            raise AudioInputError(
                f"Diretório de áudios reais não encontrado: {self._real_dir}. "
                "Execute: .\\py\\python.exe scripts\\extract_corpus.py"
            )

        files = sorted(glob.glob(os.path.join(self._real_dir, "*.wav")))

        if not files:
            raise AudioInputError(
                f"Nenhum arquivo .wav encontrado em: {self._real_dir}. "
                "Execute: .\\py\\python.exe scripts\\extract_corpus.py"
            )

        return files

    def find_pending(
        self,
        source_paths: List[str],
        model_name: str,
        limit: Optional[int] = None,
    ) -> List[AudioFile]:
        """
        Filtra os arquivos ainda não convertidos para o modelo indicado.

        Args:
            source_paths (List[str]): Caminhos dos candidatos à conversão.
            model_name (str): Nome do modelo (define o subdiretório em fake_dir/).
            limit (Optional[int]): Máximo de arquivos a retornar;
                None retorna todos os pendentes.

        Returns:
            List[AudioFile]: Arquivos pendentes com caminhos de entrada e saída resolvidos.
        """
        output_dir = os.path.join(self._fake_dir, model_name)
        os.makedirs(output_dir, exist_ok=True)

        existing = set(os.listdir(output_dir))
        pending: List[AudioFile] = []
        skipped = 0

        for path in source_paths:
            filename = os.path.basename(path)
            if filename in existing:
                skipped += 1
                continue
            pending.append(AudioFile(
                source_path=path,
                target_path=os.path.join(output_dir, filename),
                filename=filename,
            ))

        _log.info(
            f"'{model_name}': {len(source_paths)} atribuído(s), "
            f"{skipped} já convertido(s), {len(pending)} pendente(s)."
        )

        if limit is not None and limit < len(pending):
            pending = pending[:limit]
            _log.info(f"'{model_name}': limitado a {limit} arquivo(s).")

        return pending
