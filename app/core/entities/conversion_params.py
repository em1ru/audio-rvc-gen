"""
Classe base para parâmetros de conversão de voz.

Exporta:
    - ConversionParams (dataclass): Tipo base para todos os parâmetros de conversão.

Dependências:
    Nenhuma.

Utilizado por:
    - app.core.entities.rvc_params.RvcParams (estende)
    - app.core.entities.elevenlabs_params.ElevenLabsParams (estende)
    - app.core.interfaces.voice_converter_interface.IVoiceConverter
    - app.core.use_cases.run_pipeline_use_case.RunPipelineUseCase
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ConversionParams:
    """
    Classe base para parâmetros de conversão de voz.

    Serve como contrato de tipo para o IVoiceConverter e o RunPipelineUseCase,
    permitindo que ambos aceitem qualquer conjunto de parâmetros de conversão
    sem depender de uma implementação concreta (RVC, ElevenLabs, etc.).

    Utilizado por:
        - app.core.entities.rvc_params.RvcParams
        - app.core.entities.elevenlabs_params.ElevenLabsParams
        - app.core.interfaces.voice_converter_interface.IVoiceConverter
    """
