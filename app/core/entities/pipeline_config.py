"""
Entidade de configuração central do pipeline, carregada do config.yaml.

Exporta:
    - PipelineConfig (dataclass): Configuração completa com caminhos e parâmetros RVC.

Dependências:
    - app.core.entities.rvc_params.RvcParams

Utilizado por:
    - app.app_module.AppModule._load_config
    - app.infrastructure.factory.PipelineFactory
    - app.presentation.controllers.pipeline_controller (via injeção de rvc_params)
"""

from dataclasses import dataclass, field
from typing import List

from app.core.entities.rvc_params import RvcParams


@dataclass(frozen=True)
class PipelineConfig:
    """
    Configuração completa do pipeline, derivada do config.yaml.

    Atributos:
        models_dir (str): Diretório raiz dos modelos de voz (cada subpasta é um modelo).
        real_audio_dir (str): Diretório com os áudios reais de entrada (WAV 16 kHz mono).
        fake_audio_dir (str): Diretório raiz de saída dos áudios deepfake por modelo.
        rvc_engine_dir (str): Caminho absoluto para o submódulo Applio RVC.
        rvc_params (RvcParams): Parâmetros padrão de inferência para o engine RVC.
        active_models (List[str]): Nomes dos modelos a processar; lista vazia = todos.

    Utilizado por:
        - app.app_module.AppModule (carregamento e injeção nas dependências)
        - app.infrastructure.factory.PipelineFactory
    """

    models_dir: str
    real_audio_dir: str
    fake_audio_dir: str
    rvc_engine_dir: str
    rvc_params: RvcParams
    active_models: List[str] = field(default_factory=list)
