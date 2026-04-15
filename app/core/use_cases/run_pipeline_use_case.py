"""
Caso de Uso: Execução do pipeline completo de geração de deepfakes de voz.

Exporta:
    - RunPipelineUseCase (class): Orquestra descoberta de modelos, atribuição de
      arquivos e conversão em lote por modelo de voz.

Dependências:
    - IModelRepository: acesso aos modelos de voz disponíveis no sistema de arquivos.
    - IAudioRepository: leitura de áudios reais e controle de arquivos pendentes.
    - IFileAssignmentService: distribuição dos arquivos entre os modelos.
    - IVoiceConverter: execução da conversão de voz via engine RVC.

Utilizado por:
    - app.presentation.controllers.pipeline_controller

Falhas de Domínio:
    - Levanta ModelNotFoundError se nenhum modelo válido for descoberto.
    - Levanta AudioInputError se o diretório de áudios reais estiver vazio.
"""

import logging
from typing import List, Optional

from app.core.entities.conversion_result import ConversionResult
from app.core.entities.rvc_params import RvcParams
from app.core.enums.assignment_strategy import AssignmentStrategy
from app.core.exceptions.pipeline_exceptions import ModelNotFoundError
from app.core.interfaces.audio_repository_interface import IAudioRepository
from app.core.interfaces.file_assignment_service_interface import IFileAssignmentService
from app.core.interfaces.model_repository_interface import IModelRepository
from app.core.interfaces.voice_converter_interface import IVoiceConverter


_log = logging.getLogger(__name__)


class RunPipelineUseCase:
    """
    Orquestra o pipeline completo de geração de áudios deepfake por conversão de voz.

    Atributos:
        _model_repo (IModelRepository): Repositório de descoberta de modelos de voz.
        _audio_repo (IAudioRepository): Repositório de acesso aos arquivos de áudio.
        _assignment_service (IFileAssignmentService): Serviço de distribuição de arquivos.
        _voice_converter (IVoiceConverter): Provedor de conversão de voz via RVC.

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
    ) -> None:
        self._model_repo = model_repo
        self._audio_repo = audio_repo
        self._assignment_service = assignment_service
        self._voice_converter = voice_converter

    def execute(
        self,
        strategy: AssignmentStrategy,
        rvc_params: RvcParams,
        active_filter: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> List[ConversionResult]:
        """
        Executa o pipeline completo de conversão de voz para todos os modelos ativos.

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
                erro e tempo de processamento.

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
