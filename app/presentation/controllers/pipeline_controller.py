"""
Controlador CLI do pipeline de geração de deepfakes de voz.

Exporta:
    - PipelineController (class): Interpreta argumentos de linha de comando e
      delega a execução ao RunPipelineUseCase.

Dependências:
    - app.core.use_cases.run_pipeline_use_case.RunPipelineUseCase (via injeção).
    - app.core.entities.rvc_params.RvcParams (parâmetros do config.yaml, via injeção).

Utilizado por:
    - app.app_module.AppModule.start

Falhas de Domínio:
    - Levanta SystemExit(1) em caso de erro de domínio (modelo não encontrado, etc.).
    - Levanta SystemExit(2) se os argumentos da CLI forem inválidos (comportamento padrão do argparse).
"""

import argparse
import logging
import os
import sys
import time
from typing import List

from app.core.constants.pipeline_constants import TEST_LIMIT
from app.core.entities.rvc_params import RvcParams
from app.core.enums.assignment_strategy import AssignmentStrategy
from app.core.exceptions.pipeline_exceptions import AudioInputError, ModelNotFoundError
from app.core.use_cases.run_pipeline_use_case import RunPipelineUseCase
from app.presentation.dtos.pipeline_request_dto import PipelineRequestDTO
from app.presentation.dtos.pipeline_result_dto import PipelineResultDTO


_log = logging.getLogger(__name__)


class PipelineController:
    """
    Controlador de linha de comando que interpreta o input do usuário e aciona o pipeline.

    Atributos:
        _use_case (RunPipelineUseCase): Caso de uso injetado para execução do pipeline.
        _rvc_params (RvcParams): Parâmetros RVC carregados do config.yaml via AppModule.

    Métodos Públicos:
        execute: Interpreta argv, constrói o DTO e delega ao caso de uso.

    Utilizado por:
        - app.app_module.AppModule.start

    Falhas de Domínio:
        - Encapsula ModelNotFoundError e AudioInputError como SystemExit(1).
    """

    def __init__(self, use_case: RunPipelineUseCase, rvc_params: RvcParams) -> None:
        self._use_case = use_case
        self._rvc_params = rvc_params

    def execute(self, argv: List[str]) -> None:
        """
        Interpreta os argumentos de linha de comando e executa o pipeline.

        Args:
            argv (List[str]): Argumentos de linha de comando (normalmente sys.argv[1:]).

        Raises:
            SystemExit: Com código 1 em caso de erro de domínio; 2 para args inválidos.
        """
        args = self._parse_args(argv)

        if args.list_models:
            self._handle_list_models()
            return

        request = self._build_request(args)
        self._log_plan(request)

        t_start = time.time()
        try:
            results = self._use_case.execute(
                strategy=request.strategy,
                rvc_params=request.rvc_params,
                active_filter=request.active_filter,
                limit=request.limit,
            )
        except (ModelNotFoundError, AudioInputError) as exc:
            _log.critical(str(exc))
            sys.exit(1)

        elapsed = time.time() - t_start
        result_dto = PipelineResultDTO(
            results=results,
            total_success=sum(r.success_count for r in results),
            total_errors=sum(r.error_count for r in results),
            total_elapsed_seconds=elapsed,
        )
        self._log_summary(result_dto, request)

    def _parse_args(self, argv: List[str]) -> argparse.Namespace:
        """
        Configura e analisa os argumentos aceitos pela CLI.

        Args:
            argv (List[str]): Lista de argumentos brutos.

        Returns:
            argparse.Namespace: Argumentos analisados.
        """
        parser = argparse.ArgumentParser(
            description="Golden Dataset — Pipeline de Conversão de Voz (RVC v2)"
        )
        parser.add_argument(
            "--full", action="store_true",
            help="Processa TODOS os arquivos (padrão: modo teste, 5 por voz).",
        )
        parser.add_argument(
            "--limit", type=int, default=None,
            help="Número máximo de arquivos por modelo de voz.",
        )
        parser.add_argument(
            "--voice", type=str, default=None,
            help="Processa apenas este modelo de voz (nome da pasta em models/).",
        )
        parser.add_argument(
            "--strategy", type=str, default=AssignmentStrategy.STRATIFIED.value,
            choices=[s.value for s in AssignmentStrategy],
            help=(
                "Como atribuir áudios reais aos modelos: "
                "'stratified' divide igualmente (padrão), "
                "'cross' usa todos os arquivos em cada modelo."
            ),
        )
        parser.add_argument(
            "--list-models", action="store_true",
            help="Lista os modelos de voz disponíveis e encerra.",
        )
        parser.add_argument(
            "--config", type=str, default=None,
            help="Caminho para o config.yaml (padrão: config.yaml na raiz do projeto).",
        )
        return parser.parse_args(argv)

    def _build_request(self, args: argparse.Namespace) -> PipelineRequestDTO:
        """
        Constrói o DTO de requisição a partir dos argumentos analisados da CLI.

        Args:
            args (argparse.Namespace): Argumentos analisados pelo argparse.

        Returns:
            PipelineRequestDTO: DTO pronto para ser consumido pelo caso de uso.
        """
        if args.voice:
            # Modo de voz única: usa estratégia cross para processar todos os arquivos
            strategy = AssignmentStrategy.CROSS
            active_filter = [args.voice]
        else:
            strategy = AssignmentStrategy(args.strategy)
            active_filter = None

        if args.limit is not None:
            limit = args.limit
            is_test_mode = False
        elif args.full:
            limit = None
            is_test_mode = False
        else:
            limit = TEST_LIMIT
            is_test_mode = True
            _log.warning(
                f"Modo teste ativo — processando apenas {TEST_LIMIT} arquivo(s) por voz. "
                "Use --full para processar todos."
            )

        return PipelineRequestDTO(
            strategy=strategy,
            rvc_params=self._rvc_params,
            active_filter=active_filter,
            limit=limit,
            is_test_mode=is_test_mode,
        )

    def _handle_list_models(self) -> None:
        """Lista os modelos de voz disponíveis via use case e registra no log."""
        try:
            models = self._use_case.list_available_models()
        except ModelNotFoundError as exc:
            _log.critical(str(exc))
            sys.exit(1)

        if not models:
            _log.warning("Nenhum modelo de voz encontrado.")
            _log.warning(
                "Adicione subpastas com arquivos .pth e .index em models/<nome_do_modelo>/."
            )
            return

        _log.info(f"{len(models)} modelo(s) disponível(is):")
        for model in models:
            pth_mb = os.path.getsize(model.pth_path) / (1024 * 1024)
            idx_mb = os.path.getsize(model.index_path) / (1024 * 1024)
            _log.info(
                f"  {model.name:<25} "
                f"PTH: {os.path.basename(model.pth_path)} ({pth_mb:.1f} MB)  "
                f"Index: {os.path.basename(model.index_path)} ({idx_mb:.1f} MB)"
            )

    def _log_plan(self, request: PipelineRequestDTO) -> None:
        """Registra o plano de execução antes de iniciar o pipeline."""
        _log.info(f"Estratégia:    {request.strategy.value.upper()}")
        _log.info(f"Modelos:       {request.active_filter or 'todos'}")
        _log.info(f"Limite:        {request.limit if request.limit else 'sem limite'}")
        _log.info(
            f"RVC params:    F0={request.rvc_params.f0_method.value}, "
            f"index_rate={request.rvc_params.index_rate}, "
            f"protect={request.rvc_params.protect}, "
            f"pitch={request.rvc_params.pitch}"
        )

    def _log_summary(
        self, result: PipelineResultDTO, request: PipelineRequestDTO
    ) -> None:
        """Registra o resumo final após a conclusão do pipeline."""
        elapsed_min = result.total_elapsed_seconds / 60
        elapsed_str = (
            f"{elapsed_min / 60:.1f}h" if elapsed_min >= 60 else f"{elapsed_min:.1f}min"
        )
        _log.info(
            f"Pipeline concluído — {result.total_success} conversão(ões) ok, "
            f"{result.total_errors} erro(s), {elapsed_str} total."
        )
        if result.total_errors > 0:
            _log.warning("Verifique conversion_errors.log para detalhes dos erros.")
        if request.is_test_mode and result.total_success > 0:
            _log.info(
                "Modo teste concluído com sucesso. "
                "Execute novamente com --full para processar todos os arquivos."
            )
