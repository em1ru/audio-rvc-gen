"""
Entidade que representa os parâmetros de síntese via ElevenLabs speech-to-speech.

Exporta:
    - ElevenLabsParams (dataclass): Configuração da chamada à API ElevenLabs STS.

Dependências:
    - app.core.entities.conversion_params.ConversionParams

Utilizado por:
    - app.infrastructure.providers.elevenlabs_provider.ElevenLabsProvider
    - app.app_module.AppModule._load_config
    - app.core.entities.pipeline_config.PipelineConfig
"""

from dataclasses import dataclass

from app.core.entities.conversion_params import ConversionParams


@dataclass(frozen=True)
class ElevenLabsParams(ConversionParams):
    """
    Parâmetros de configuração da API ElevenLabs speech-to-speech.

    Atributos:
        model_id (str): Identificador do modelo ElevenLabs a usar na conversão.
            Impacto: Define a qualidade e capacidades; modelos multilíngues suportam
            português diretamente sem degradação de naturalidade.
        output_format (str): Formato de áudio retornado pela API ElevenLabs.
            Impacto: 'pcm_16000' retorna PCM bruto 16-bit mono a 16 kHz, compatível
            com o golden dataset; é convertido para WAV antes de salvar no disco.

    Utilizado por:
        - app.infrastructure.providers.elevenlabs_provider.ElevenLabsProvider
        - app.app_module.AppModule
    """

    model_id: str = "eleven_multilingual_sts_v2"
    output_format: str = "pcm_16000"
