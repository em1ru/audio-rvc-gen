"""
Entidade que representa um modelo de voz RVC disponível para conversão.

Exporta:
    - VoiceModel (dataclass): Par de arquivos .pth + .index que define um modelo.

Utilizado por:
    - app.core.use_cases.run_pipeline_use_case
    - app.core.interfaces.model_repository_interface
    - app.infrastructure.repositories.model_repository
    - app.infrastructure.providers.rvc_provider
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class VoiceModel:
    """
    Modelo de voz RVC v2 composto por pesos e índice FAISS.

    Atributos:
        name (str): Nome do modelo (correspondente ao nome da pasta em models/).
        pth_path (str): Caminho absoluto para o arquivo de pesos do modelo (.pth).
        index_path (str): Caminho absoluto para o índice FAISS de embeddings (.index).

    Utilizado por:
        - app.core.use_cases.run_pipeline_use_case.RunPipelineUseCase
        - app.infrastructure.providers.rvc_provider.RvcProvider
    """

    name: str
    pth_path: str
    index_path: str
