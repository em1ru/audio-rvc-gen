import logging
import os
import time
import wave
from typing import List, Optional

import tqdm

from pipeline.audio import AudioFile, ConversionResult
from pipeline.config import ElevenLabsConfig


log = logging.getLogger(__name__)
error_log = logging.getLogger("conversion_errors")

_PCM_SAMPLE_RATE = 16000
_PCM_SAMPLE_WIDTH = 2   # 16-bit
_PCM_CHANNELS = 1       # mono


def convert_batch(
    voice_name: str,
    voice_id: str,
    files: List[AudioFile],
    cfg: ElevenLabsConfig,
    api_key: str,
) -> ConversionResult:
    if not api_key:
        raise ValueError(
            "ELEVENLABS_API_KEY não definida. "
            "Adicione ao .env ou exporte no terminal."
        )

    from elevenlabs import ElevenLabs
    client = ElevenLabs(api_key=api_key)

    log.info(f"ElevenLabs '{voice_name}': {len(files)} arquivo(s) — model={cfg.model_id}")
    converted = []
    errors = 0
    t0 = time.time()

    with tqdm.tqdm(total=len(files), desc=f"  {voice_name}", unit="arq", ncols=80) as bar:
        for af in files:
            err = _convert_one(client, voice_id, af, cfg)
            if err:
                errors += 1
                error_log.error(f"{voice_name}|{af.filename}|{err}")
            else:
                converted.append(af)
            bar.update(1)

    return ConversionResult(
        voice_name=voice_name,
        success_count=len(converted),
        error_count=errors,
        elapsed_seconds=time.time() - t0,
        converted_files=converted,
    )


def _convert_one(client, voice_id: str, af: AudioFile, cfg: ElevenLabsConfig) -> Optional[str]:
    try:
        os.makedirs(os.path.dirname(af.target_path), exist_ok=True)
        with open(af.source_path, "rb") as f:
            stream = client.speech_to_speech.convert(
                voice_id=voice_id,
                audio=f,
                model_id=cfg.model_id,
                output_format=cfg.output_format,
            )
            pcm = b"".join(stream)

        if not pcm:
            return "Resposta vazia da API."

        _save_wav(pcm, af.target_path)

        if not os.path.isfile(af.target_path):
            return "Arquivo não criado após escrita."
        return None
    except Exception as e:
        _cleanup(af.target_path)
        return str(e)


def _save_wav(pcm: bytes, path: str) -> None:
    with wave.open(path, "wb") as wf:
        wf.setnchannels(_PCM_CHANNELS)
        wf.setsampwidth(_PCM_SAMPLE_WIDTH)
        wf.setframerate(_PCM_SAMPLE_RATE)
        wf.writeframes(pcm)


def _cleanup(path: str) -> None:
    if os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass
