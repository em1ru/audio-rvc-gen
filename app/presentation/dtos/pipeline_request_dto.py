"""
DTO de entrada do controlador do pipeline.

Exporta:
    - PipelineRequestDTO (dataclass): Estrutura que transporta os parâmetros
      da requisição da CLI para o caso de uso.

Utilizado por:
    - app.presentation.controllers.pipeline_controller
    - app.core.use_cases.run_pipeline_use_case
"""

from dataclasses import dataclass, field
from typing import List, Optional

from app.core.entities.rvc_params import RvcParams
from app.core.enums.assignment_strategy import AssignmentStrategy


@dataclass
class PipelineRequestDTO:
    """
    Estrutura de dados que transporta os parâmetros da requisição do pipeline.

    Atributos:
        strategy (AssignmentStrategy): Estratégia de distribuição dos arquivos entre modelos.
        rvc_params (RvcParams): Parâmetros de inferência RVC carregados do config.yaml.
        active_filter (Optional[List[str]]): Nomes de modelos a processar; None = todos.
        limit (Optional[int]): Máximo de arquivos por modelo; None = todos os pendentes.
        is_test_mode (bool): Se True, indica que o limite foi aplicado pelo modo de teste.

    Utilizado por:
        - app.presentation.controllers.pipeline_controller.PipelineController
    """

    strategy: AssignmentStrategy
    rvc_params: RvcParams
    active_filter: Optional[List[str]] = None
    limit: Optional[int] = None
    is_test_mode: bool = False
