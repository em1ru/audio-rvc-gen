"""
Entidade que representa os parâmetros de inferência do engine RVC v2.

Exporta:
    - RvcParams (dataclass): Configuração completa de uma execução de conversão de voz.

Dependências:
    - app.core.enums.f0_method.F0Method

Utilizado por:
    - app.core.entities.pipeline_config
    - app.core.use_cases.run_pipeline_use_case
    - app.infrastructure.providers.rvc_provider
    - app.app_module (desserialização do config.yaml)
"""

from dataclasses import dataclass

from app.core.enums.f0_method import F0Method


@dataclass(frozen=True)
class RvcParams:
    """
    Parâmetros de configuração do algoritmo de conversão de voz RVC v2.

    Atributos:
        f0_method (F0Method): Algoritmo de extração de frequência fundamental.
            Impacto: RMVPE oferece melhor qualidade de pitch; FCPE é mais rápido.
        index_rate (float): Peso do índice FAISS na identidade vocal (0.0–1.0).
            Impacto: Valores altos aproximam mais a voz do modelo-alvo, podendo
            introduzir artefatos; valores baixos preservam características do locutor original.
        protect (float): Proteção de consoantes para reduzir artefatos (0.0–0.5).
            Impacto: Valores maiores protegem mais as consoantes, reduzindo
            distorções em sons não-vocálicos.
        volume_envelope (float): Mistura de envelope de volume origem/destino (0.0–1.0).
            Impacto: 0.0 preserva o volume original; 1.0 usa o envelope do modelo-alvo.
        hop_length (int): Tamanho do salto de quadro para extração de F0 (em amostras).
            Impacto: Valores menores aumentam a resolução temporal do pitch, com
            maior custo computacional.
        pitch (int): Deslocamento de pitch em semitons aplicado na saída.
            Impacto: 0 = sem alteração; positivo sobe, negativo desce o tom.
        export_format (str): Formato do arquivo de saída da conversão.

    Utilizado por:
        - app.infrastructure.providers.rvc_provider.RvcProvider
        - app.app_module.AppModule._load_config
    """

    f0_method: F0Method = F0Method.RMVPE
    index_rate: float = 0.75
    protect: float = 0.33
    volume_envelope: float = 0.25
    hop_length: int = 128
    pitch: int = 0
    export_format: str = "WAV"
