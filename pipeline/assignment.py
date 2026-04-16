from typing import Dict, List


def assign(source_paths: List[str], voice_names: List[str], strategy: str) -> Dict[str, List[str]]:
    """Distribui source_paths entre voice_names conforme a estratégia escolhida.

    - stratified: round-robin interleaved — cada voz recebe ~1/N dos arquivos sem overlap.
    - cross: todas as vozes recebem todos os arquivos (N×M conversões no total).
    """
    if strategy == "cross":
        return {name: source_paths for name in voice_names}

    n = len(voice_names)
    return {name: source_paths[i::n] for i, name in enumerate(voice_names)}
