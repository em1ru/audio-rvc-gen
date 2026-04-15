"""
Caso de Uso: Execução do pipeline completo de geração de deepfakes de voz.

Exporta:
    - RunPipelineUseCase (class): Orquestra descoberta de modelos, atribuição de
      arquivos, conversão em lote e geração do manifesto do golden dataset.

Dependências:
    - IModelRepository: acesso aos modelos de voz disponíveis no sistema de arquivos.
    - IAudioRepository: leitura de áudios reais e controle de arquivos pendentes.
    - IFileAssignmentService: distribuição dos arquivos entre os modelos.
    - IVoiceConverter: execução da conversão de voz via engine RVC.
    - IManifestRepository: persistência incremental do manifesto CSV.

Utilizado por:
    - app.presentation.controllers.pipeline_controller

Falhas de Domínio:
    - Levanta ModelNotFoundError se nenhum modelo válido for descoberto.
    - Levanta AudioInputError se o diretório de áudios reais estiver vazio.
"""

import logging
import os
from datetime import datetime, timezone
from typing import List, Optional

from app.core.entities.conversion_result import ConversionResult
from app.core.entities.manifest_entry import ManifestEntry, ManifestLabel, ManifestMethod
from app.core.entities.rvc_params import RvcParams
from app.core.enums.assignment_strategy import AssignmentStrategy
from app.core.exceptions.pipeline_exceptions import ModelNotFoundError
from app.core.interfaces.audio_repository_interface import IAudioRepository
from app.core.interfaces.file_assignment_service_interface import IFileAssignmentService
from app.core.interfaces.manifest_repository_interface import IManifestRepository
from app.core.interfaces.model_repository_interface import IModelRepository
from app.core.interfaces.voice_converter_interface import IVoiceConverter


_log = logging.getLogger(__name__)


class RunPipelineUseCase:
    """
    Orquestra o pipeline completo de geração de áudios deepfake e manifesto do golden dataset.

    Após cada execução, atualiza incrementalmente o manifesto CSV com entradas
    para todos os áudios reais disponíveis e para os fakes gerados na sessão,
    deduplicando por filename para evitar entradas repetidas entre execuções.

    Atributos:
        _model_repo (IModelRepository): Repositório de descoberta de modelos de voz.
        _audio_repo (IAudioRepository): Repositório de acesso aos arquivos de áudio.
        _assignment_service (IFileAssignmentService): Serviço de distribuição de arquivos.
        _voice_converter (IVoiceConverter): Provedor de conversão de voz via RVC.
        _manifest_repo (IManifestRepository): Repositório de persistência do manifesto.

    Métodos Públicos:
        execute: Executa o pipeline completo e retorna os resultados por modelo.
        list_available_models: Retorna os modelos descobertos sem executar conversões.

    Utilizado por:
        - app.presentation.controllers.pipeline_controller.PipelineController

    Falhas de Domínio:
        - Levanta ModelNotFoundError se nenhum modelo válido for encontrado.
        - Levanta AudioInputError se não houver áudios reais disponíveis.
    """

    def __init__(
        self,
        model_repo: IModelRepository,
        audio_repo: IAudioRepository,
        assignment_service: IFileAssignmentService,
        voice_converter: IVoiceConverter,
        manifest_repo: IManifestRepository,
    ) -> None:
        self._model_repo = model_repo
        self._audio_repo = audio_repo
        self._assignment_service = assignment_service
        self._voice_converter = voice_converter
        self._manifest_repo = manifest_repo

    def execute(
        self,
        strategy: AssignmentStrategy,
        rvc_params: RvcParams,
        active_filter: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> List[ConversionResult]:
        """
        Executa o pipeline completo de conversão e atualiza o manifesto do golden dataset.

        Args:
            strategy (AssignmentStrategy): Como distribuir os áudios reais entre os modelos.
                STRATIFIED divide por round-robin; CROSS usa todos os arquivos em cada modelo.
            rvc_params (RvcParams): Parâmetros de inferência aplicados a todos os modelos.
            active_filter (Optional[List[str]]): Nomes de modelos a processar;
                None processa todos os modelos descobertos.
            limit (Optional[int]): Número máximo de arquivos por modelo;
                None processa todos os pendentes.

        Returns:
            List[ConversionResult]: Um resultado por modelo com contagens de sucesso,
                erro, tempo e lista dos arquivos convertidos.

        Raises:
            ModelNotFoundError: Se nenhum modelo válido for encontrado no diretório.
            AudioInputError: Se não houver arquivos WAV no diretório de áudios reais.
        """
        models = self._model_repo.find_all(active_filter)
        if not models:
            raise ModelNotFoundError(
                "Nenhum modelo de voz válido encontrado. "
                "Verifique se os diretórios em models/ contêm arquivos .pth e .index."
            )

        _log.info(f"{len(models)} modelo(s) descoberto(s): {[m.name for m in models]}")

        source_paths = self._audio_repo.find_all_real()
        _log.info(f"{len(source_paths)} áudio(s) real(is) disponível(is).")

        assignment = self._assignment_service.assign(source_paths, models, strategy)
        total_assigned = sum(len(v) for v in assignment.values())
        _log.info(
            f"Estratégia '{strategy.value}': {total_assigned} conversão(ões) planejada(s)."
        )

        results: List[ConversionResult] = []
        for index, model in enumerate(models, 1):
            _log.info(f"[{index}/{len(models)}] Iniciando modelo: {model.name}")

            assigned = assignment[model.name]
            pending = self._audio_repo.find_pending(assigned, model.name, limit)

            if not pending:
                _log.info(f"Modelo '{model.name}': nenhum arquivo pendente — ignorado.")
                results.append(ConversionResult(
                    model_name=model.name,
                    success_count=0,
                    error_count=0,
                    elapsed_seconds=0.0,
                ))
                continue

            result = self._voice_converter.convert_batch(model, pending, rvc_params)
            results.append(result)

            _log.info(
                f"Modelo '{model.name}' concluído: "
                f"{result.success_count} ok, {result.error_count} erro(s), "
                f"{result.elapsed_seconds:.1f}s."
            )

        self._update_manifest(source_paths, results, rvc_params)
        return results

    def list_available_models(
        self, active_filter: Optional[List[str]] = None
    ) -> list:
        """
        Retorna os modelos de voz disponíveis sem iniciar conversões.

        Args:
            active_filter (Optional[List[str]]): Nomes de modelos a incluir;
                None retorna todos os descobertos.

        Returns:
            List[VoiceModel]: Modelos válidos encontrados no diretório.

        Raises:
            ModelNotFoundError: Se o diretório de modelos não existir.
        """
        return self._model_repo.find_all(active_filter)

    def _update_manifest(
        self,
        source_paths: List[str],
        results: List[ConversionResult],
        rvc_params: RvcParams,
    ) -> None:
        """
        Atualiza o manifesto CSV com entradas reais e fakes da sessão atual.

        Carrega o manifesto existente, adiciona novas entradas (reais e fakes),
        deduplica por filename e persiste. Entradas reais já existentes não são
        duplicadas; fakes são adicionados apenas os novos desta sessão.

        Args:
            source_paths (List[str]): Caminhos de todos os áudios reais disponíveis.
            results (List[ConversionResult]): Resultados da sessão de conversão.
            rvc_params (RvcParams): Parâmetros RVC usados nas conversões.
        """
        existing = self._manifest_repo.load()
        existing_filenames = {e.filename for e in existing}

        new_entries: List[ManifestEntry] = []

        # Entradas para todos os áudios reais ainda não registrados no manifesto
        for path in source_paths:
            filename = os.path.basename(path)
            if filename not in existing_filenames:
                new_entries.append(ManifestEntry(
                    filename=filename,
                    label=ManifestLabel.REAL,
                    method=ManifestMethod.NONE,
                    voice_model="",
                    source_file="",
                    f0_method="",
                    index_rate=None,
                    protect=None,
                    volume_envelope=None,
                    hop_length=None,
                    pitch=None,
                    generated_at="",
                ))

        # Entradas para os fakes gerados nesta sessão
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for result in results:
            for audio_file in result.converted_files:
                fake_key = f"{result.model_name}/{audio_file.filename}"
                if fake_key not in existing_filenames:
                    new_entries.append(ManifestEntry(
                        filename=audio_file.filename,
                        label=ManifestLabel.FAKE,
                        method=ManifestMethod.RVC,
                        voice_model=result.model_name,
                        source_file=os.path.basename(audio_file.source_path),
                        f0_method=rvc_params.f0_method.value,
                        index_rate=rvc_params.index_rate,
                        protect=rvc_params.protect,
                        volume_envelope=rvc_params.volume_envelope,
                        hop_length=rvc_params.hop_length,
                        pitch=rvc_params.pitch,
                        generated_at=generated_at,
                    ))

        if not new_entries:
            _log.info("Manifesto: nenhuma nova entrada a adicionar.")
            return

        all_entries = existing + new_entries
        self._manifest_repo.save(all_entries)

        real_count = sum(1 for e in all_entries if e.label == ManifestLabel.REAL)
        fake_count = sum(1 for e in all_entries if e.label == ManifestLabel.FAKE)
        _log.info(
            f"Manifesto atualizado: {real_count} real(is), {fake_count} fake(s) "
            f"({len(new_entries)} nova(s) entrada(s) nesta sessão)."
        )
