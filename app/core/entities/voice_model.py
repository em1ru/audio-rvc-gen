"""
Entidade que representa um modelo de voz disponível para conversão.

Exporta:
    - VoiceModel (dataclass): Modelo de voz identificado por nome e arquivos ou voice_id.

Utilizado por:
    - app.core.use_cases.run_pipeline_use_case
    - app.core.interfaces.model_repository_interface
    - app.infrastructure.repositories.model_repository
    - app.infrastructure.repositories.elevenlabs_model_repository
    - app.infrastructure.providers.rvc_provider
    - app.infrastructure.providers.elevenlabs_provider
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class VoiceModel:
    """
    Modelo de voz compatível com RVC e ElevenLabs.

    Para modelos RVC, pth_path e index_path são obrigatórios; voice_id fica vazio.
    Para modelos ElevenLabs, voice_id é obrigatório; pth_path e index_path ficam vazios.

    Atributos:
        name (str): Nome do modelo (pasta em models/ para RVC; label configurável para ElevenLabs).
        pth_path (str): Caminho absoluto para o arquivo de pesos RVC (.pth); vazio para ElevenLabs.
        index_path (str): Caminho absoluto para o índice FAISS (.index); vazio para ElevenLabs.
        voice_id (str): Identificador da voz na API ElevenLabs; vazio para modelos RVC.

    Utilizado por:
        - app.core.use_cases.run_pipeline_use_case.RunPipelineUseCase
        - app.infrastructure.providers.rvc_provider.RvcProvider
        - app.infrastructure.providers.elevenlabs_provider.ElevenLabsProvider
    """

    name: str
    pth_path: str
    index_path: str
    voice_id: str = field(default="")
