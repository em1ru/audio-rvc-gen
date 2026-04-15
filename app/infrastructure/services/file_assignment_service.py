"""
Serviço de atribuição de arquivos de áudio aos modelos de voz.

Exporta:
    - FileAssignmentService (class): Implementação de IFileAssignmentService com
      suporte às estratégias STRATIFIED e CROSS.

Utilizado por:
    - app.infrastructure.factory.PipelineFactory
    - app.core.use_cases.run_pipeline_use_case.RunPipelineUseCase (via interface)

Falhas de Domínio:
    - Levanta ValueError se a estratégia fornecida não for reconhecida.
"""

import logging
from typing import Dict, List

from app.core.entities.voice_model import VoiceModel
from app.core.enums.assignment_strategy import AssignmentStrategy
from app.core.interfaces.file_assignment_service_interface import IFileAssignmentService


_log = logging.getLogger(__name__)


class FileAssignmentService(IFileAssignmentService):
    """
    Distribui os arquivos de áudio entre os modelos de voz conforme a estratégia.

    Métodos Públicos:
        assign: Mapeia cada modelo para a lista de arquivos que deve converter.

    Utilizado por:
        - app.infrastructure.factory.PipelineFactory (instanciação)
        - app.core.use_cases.run_pipeline_use_case.RunPipelineUseCase (via injeção)
    """

    def assign(
        self,
        source_paths: List[str],
        models: List[VoiceModel],
        strategy: AssignmentStrategy,
    ) -> Dict[str, List[str]]:
        """
        Distribui os arquivos entre os modelos conforme a estratégia escolhida.

        Args:
            source_paths (List[str]): Lista de caminhos absolutos dos áudios reais.
            models (List[VoiceModel]): Modelos de voz disponíveis para conversão.
            strategy (AssignmentStrategy): Estratégia de distribuição (STRATIFIED ou CROSS).

        Returns:
            Dict[str, List[str]]: Mapeamento nome_do_modelo → lista de caminhos de entrada.

        Raises:
            ValueError: Se a estratégia não for reconhecida.
        """
        if strategy == AssignmentStrategy.STRATIFIED:
            return self._assign_stratified(source_paths, models)
        if strategy == AssignmentStrategy.CROSS:
            return self._assign_cross(source_paths, models)
        raise ValueError(f"Estratégia de atribuição desconhecida: '{strategy}'")

    def _assign_stratified(
        self,
        source_paths: List[str],
        models: List[VoiceModel],
    ) -> Dict[str, List[str]]:
        """
        Distribui por round-robin intercalado, garantindo diversidade de locutores.

        Cada modelo recebe os índices i, i+N, i+2N… da lista ordenada de arquivos,
        onde N é o número de modelos e i é o índice do modelo. Isso garante que
        locutores de diferentes regiões ou sessões de gravação sejam distribuídos
        uniformemente entre os modelos, evitando o viés de blocos contíguos.

        Args:
            source_paths (List[str]): Caminhos dos áudios reais.
            models (List[VoiceModel]): Modelos de voz.

        Returns:
            Dict[str, List[str]]: Atribuição round-robin intercalada por modelo.
        """
        n = len(models)
        assignment: Dict[str, List[str]] = {
            model.name: source_paths[i::n]
            for i, model in enumerate(models)
        }

        for name, files in assignment.items():
            _log.debug(f"STRATIFIED — '{name}': {len(files)} arquivo(s).")

        total = sum(len(v) for v in assignment.values())
        _log.info(
            f"STRATIFIED: {len(source_paths)} áudios distribuídos entre "
            f"{n} modelo(s) → {total} conversão(ões) planejada(s)."
        )
        return assignment

    def _assign_cross(
        self,
        source_paths: List[str],
        models: List[VoiceModel],
    ) -> Dict[str, List[str]]:
        """
        Atribui todos os arquivos a todos os modelos (N × M conversões).

        Args:
            source_paths (List[str]): Caminhos dos áudios reais.
            models (List[VoiceModel]): Modelos de voz.

        Returns:
            Dict[str, List[str]]: Todos os arquivos atribuídos a cada modelo.
        """
        assignment: Dict[str, List[str]] = {
            model.name: source_paths for model in models
        }
        total = len(source_paths) * len(models)
        _log.info(
            f"CROSS: {len(source_paths)} áudios × {len(models)} modelo(s) "
            f"= {total} conversão(ões) planejada(s)."
        )
        return assignment
