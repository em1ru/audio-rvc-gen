"""
Enumeração dos métodos de extração de frequência fundamental (F0) suportados pelo RVC.

Exporta:
    - F0Method (enum): Algoritmos de extração de pitch disponíveis no engine Applio.

Utilizado por:
    - app.core.entities.rvc_params
    - app.infrastructure.providers.rvc_provider
"""

from enum import Enum


class F0Method(str, Enum):
    """
    Algoritmos de extração de pitch (F0) disponíveis no engine RVC v2.

    Atributos:
        RMVPE (str): Robust Model for Vocal Pitch Estimation — mais preciso, padrão recomendado.
        FCPE (str): Fast Pitch Extractor — equilíbrio entre velocidade e qualidade.
        CREPE (str): Convolutional Representation for Pitch Estimation — alto custo, alta precisão.
        HARVEST (str): Estimação via método Harvest (WORLD vocoder) — rápido, menor qualidade.

    Utilizado por:
        - app.core.entities.rvc_params.RvcParams
        - app.infrastructure.providers.rvc_provider.RvcProvider
    """

    RMVPE = "rmvpe"
    FCPE = "fcpe"
    CREPE = "crepe"
    HARVEST = "harvest"
