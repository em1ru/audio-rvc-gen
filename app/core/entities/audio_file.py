"""
Entidade que representa um par de arquivos de áudio (entrada real → saída deepfake).

Exporta:
    - AudioFile (dataclass): Caminhos de origem e destino de um arquivo de áudio pendente.

Utilizado por:
    - app.core.interfaces.audio_repository_interface
    - app.core.interfaces.voice_converter_interface
    - app.infrastructure.repositories.audio_repository
    - app.infrastructure.providers.rvc_provider
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AudioFile:
    """
    Par de caminhos que representa uma conversão de áudio pendente.

    Atributos:
        source_path (str): Caminho absoluto do áudio real de entrada (WAV, 16 kHz mono).
        target_path (str): Caminho absoluto onde o áudio convertido será salvo.
        filename (str): Nome do arquivo sem diretório (usado para verificar existência).

    Utilizado por:
        - app.infrastructure.repositories.audio_repository.AudioRepository
        - app.infrastructure.providers.rvc_provider.RvcProvider
    """

    source_path: str
    target_path: str
    filename: str
