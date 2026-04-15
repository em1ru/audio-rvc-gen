"""
Factory do pipeline — instancia e conecta todos os componentes de infraestrutura.

Exporta:
    - PipelineFactory (class): Constrói o RunPipelineUseCase com dependências injetadas.

Dependências:
    - PipelineConfig: configuração carregada pelo AppModule a partir do config.yaml.

Utilizado por:
    - app.app_module.AppModule.start
"""

import os

from app.core.entities.pipeline_config import PipelineConfig
from app.core.use_cases.run_pipeline_use_case import RunPipelineUseCase
from app.infrastructure.providers.rvc_provider import RvcProvider
from app.infrastructure.repositories.audio_repository import AudioRepository
from app.infrastructure.repositories.manifest_repository import ManifestRepository
from app.infrastructure.repositories.model_repository import ModelRepository
from app.infrastructure.services.file_assignment_service import FileAssignmentService


class PipelineFactory:
    """
    Constrói o RunPipelineUseCase com todas as dependências de infraestrutura.

    Métodos Públicos:
        create_run_pipeline: Instancia e conecta os componentes do pipeline.

    Utilizado por:
        - app.app_module.AppModule.start
    """

    @staticmethod
    def create_run_pipeline(config: PipelineConfig) -> RunPipelineUseCase:
        """
        Constrói o caso de uso principal com as dependências derivadas da configuração.

        O manifesto é persistido em data/manifest.csv, derivado do diretório pai
        de real_audio_dir (data/), mantendo todos os artefatos do dataset agrupados.

        Args:
            config (PipelineConfig): Configuração carregada e validada do config.yaml.

        Returns:
            RunPipelineUseCase: Caso de uso pronto para execução via controlador.
        """
        data_dir = os.path.dirname(config.real_audio_dir)
        manifest_path = os.path.join(data_dir, "manifest.csv")

        model_repo = ModelRepository(config.models_dir)
        audio_repo = AudioRepository(config.real_audio_dir, config.fake_audio_dir)
        assignment_service = FileAssignmentService()
        rvc_provider = RvcProvider(config.rvc_engine_dir)
        manifest_repo = ManifestRepository(manifest_path)

        return RunPipelineUseCase(
            model_repo=model_repo,
            audio_repo=audio_repo,
            assignment_service=assignment_service,
            voice_converter=rvc_provider,
            manifest_repo=manifest_repo,
        )
