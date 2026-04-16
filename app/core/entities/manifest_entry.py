"""
Entidade que representa uma linha do manifesto do golden dataset.

Exporta:
    - ManifestEntry (dataclass): Registro rastreável de um áudio com label, método e proveniência.
    - ManifestLabel (enum): Valores possíveis para o campo label.
    - ManifestMethod (enum): Métodos de síntese suportados.

Utilizado por:
    - app.core.interfaces.manifest_repository_interface
    - app.core.use_cases.run_pipeline_use_case
    - app.infrastructure.repositories.manifest_repository
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ManifestLabel(str, Enum):
    """
    Classificação de autenticidade de um áudio no golden dataset.

    Atributos:
        REAL (str): Áudio original, sem modificação.
        FAKE (str): Áudio gerado sinteticamente por algum método de conversão ou síntese.
    """

    REAL = "real"
    FAKE = "fake"


class ManifestMethod(str, Enum):
    """
    Método de síntese utilizado para gerar um áudio fake.

    Atributos:
        RVC (str): Retrieval-Based Voice Conversion via engine Applio.
        ELEVENLABS (str): Speech-to-speech via API ElevenLabs.
        NONE (str): Sem método aplicável (áudios reais).
    """

    RVC = "rvc"
    ELEVENLABS = "elevenlabs"
    NONE = ""


@dataclass(frozen=True)
class ManifestEntry:
    """
    Registro rastreável de um áudio no golden dataset, real ou fake.

    Para áudios reais, os campos de síntese ficam vazios/None.
    Para áudios fake, todos os campos de proveniência são preenchidos,
    permitindo reproduzir ou auditar qualquer geração.

    Atributos:
        filename (str): Nome do arquivo WAV (sem caminho completo).
        label (ManifestLabel): Classificação do áudio (real ou fake).
        method (ManifestMethod): Método de síntese; NONE para áudios reais.
        voice_model (str): Nome do modelo de voz usado; vazio para reais.
        source_file (str): Nome do arquivo real de origem da conversão; vazio para reais.
        f0_method (str): Algoritmo de extração de F0 usado; vazio para reais.
        index_rate (Optional[float]): Taxa do índice FAISS aplicada; None para reais.
        protect (Optional[float]): Proteção de consoantes aplicada; None para reais.
        volume_envelope (Optional[float]): Mistura de envelope de volume; None para reais.
        hop_length (Optional[int]): Hop length de extração de F0; None para reais.
        pitch (Optional[int]): Deslocamento de pitch em semitons; None para reais.
        generated_at (str): Timestamp ISO 8601 da geração; vazio para reais.

    Utilizado por:
        - app.core.use_cases.run_pipeline_use_case.RunPipelineUseCase
        - app.infrastructure.repositories.manifest_repository.ManifestRepository
    """

    filename: str
    label: ManifestLabel
    method: ManifestMethod
    voice_model: str
    source_file: str
    f0_method: str
    index_rate: Optional[float]
    protect: Optional[float]
    volume_envelope: Optional[float]
    hop_length: Optional[int]
    pitch: Optional[int]
    generated_at: str
