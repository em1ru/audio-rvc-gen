import logging
import os
from typing import List, Optional

from pipeline import assignment, audio, elevenlabs, manifest, rvc
from pipeline.audio import ConversionResult
from pipeline.config import Config


log = logging.getLogger(__name__)


def run(
    config: Config,
    method: str = "rvc",
    strategy: str = "stratified",
    voice_filter: Optional[List[str]] = None,
    limit: Optional[int] = None,
) -> List[ConversionResult]:
    source_paths = audio.find_real(config.real_audio_dir)
    log.info(f"{len(source_paths)} áudio(s) real(is) encontrado(s).")

    if method == "elevenlabs":
        voices = [(v["name"], v["voice_id"]) for v in config.elevenlabs.voices]
        if not voices:
            raise ValueError("Nenhuma voz ElevenLabs configurada em config.yaml (elevenlabs.voices).")
        if voice_filter:
            voices = [(n, vid) for n, vid in voices if n in voice_filter]
        if not voices:
            raise ValueError(f"Nenhuma voz encontrada para o filtro: {voice_filter}")
        voice_names = [n for n, _ in voices]
    else:
        models = rvc.find_models(config.models_dir, voice_filter or config.active_models or None)
        voice_names = [m[0] for m in models]

    assignments = assignment.assign(source_paths, voice_names, strategy)
    total = sum(len(v) for v in assignments.values())
    log.info(f"Estratégia '{strategy}': {total} conversões planejadas entre {len(voice_names)} voz(es).")

    results: List[ConversionResult] = []

    if method == "elevenlabs":
        api_key = os.environ.get("ELEVENLABS_API_KEY", "")
        for voice_name, voice_id in voices:
            pending = audio.find_pending(assignments[voice_name], voice_name, config.fake_audio_dir, limit)
            if not pending:
                log.info(f"'{voice_name}': nenhum arquivo pendente — pulado.")
                continue
            result = elevenlabs.convert_batch(voice_name, voice_id, pending, config.elevenlabs, api_key)
            results.append(result)
            log.info(f"'{voice_name}': {result.success_count} ok, {result.error_count} erro(s), {result.elapsed_seconds:.1f}s.")
    else:
        for model_name, pth, index in models:
            pending = audio.find_pending(assignments[model_name], model_name, config.fake_audio_dir, limit)
            if not pending:
                log.info(f"'{model_name}': nenhum arquivo pendente — pulado.")
                continue
            result = rvc.convert_batch(model_name, pth, index, pending, config.rvc, config.rvc_engine_dir)
            results.append(result)
            log.info(f"'{model_name}': {result.success_count} ok, {result.error_count} erro(s), {result.elapsed_seconds:.1f}s.")

    manifest.update(
        config.manifest_path,
        source_paths,
        results,
        method,
        rvc_cfg=config.rvc if method == "rvc" else None,
    )
    return results
