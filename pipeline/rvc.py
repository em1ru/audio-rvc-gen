import glob
import logging
import os
import sys
import time
from typing import List, Optional, Tuple

import tqdm

from pipeline.audio import AudioFile, ConversionResult
from pipeline.config import RvcConfig


log = logging.getLogger(__name__)
error_log = logging.getLogger("conversion_errors")

_engine_ready = False


def find_models(
    models_dir: str, name_filter: Optional[List[str]] = None
) -> List[Tuple[str, str, str]]:
    """Retorna lista de (nome, pth_path, index_path) ordenada por nome."""
    if not os.path.isdir(models_dir):
        raise FileNotFoundError(f"Diretório de modelos não encontrado: {models_dir}")

    models = []
    for entry in sorted(os.scandir(models_dir), key=lambda e: e.name):
        if not entry.is_dir():
            continue
        pth = glob.glob(os.path.join(entry.path, "*.pth"))
        idx = glob.glob(os.path.join(entry.path, "*.index"))
        if pth and idx:
            models.append((entry.name, pth[0], idx[0]))

    if name_filter:
        models = [m for m in models if m[0] in name_filter]

    if not models:
        raise FileNotFoundError(
            "Nenhum modelo RVC encontrado. "
            "Adicione pastas com .pth e .index em models/."
        )
    return models


def convert_batch(
    model_name: str,
    pth_path: str,
    index_path: str,
    files: List[AudioFile],
    cfg: RvcConfig,
    engine_dir: str,
) -> ConversionResult:
    _ensure_ready(engine_dir)
    from rvc.infer.infer import VoiceConverter

    log.info(f"RVC '{model_name}': {len(files)} arquivo(s) — F0={cfg.f0_method}, index_rate={cfg.index_rate}")
    vc = VoiceConverter()
    converted = []
    errors = 0
    t0 = time.time()

    with tqdm.tqdm(total=len(files), desc=f"  {model_name}", unit="arq", ncols=80) as bar:
        for af in files:
            err = _convert_one(vc, pth_path, index_path, af, cfg)
            if err:
                errors += 1
                error_log.error(f"{model_name}|{af.filename}|{err}")
            else:
                converted.append(af)
            bar.update(1)

    return ConversionResult(
        voice_name=model_name,
        success_count=len(converted),
        error_count=errors,
        elapsed_seconds=time.time() - t0,
        converted_files=converted,
    )


def _convert_one(vc, pth_path, index_path, af: AudioFile, cfg: RvcConfig) -> Optional[str]:
    try:
        vc.convert_audio(
            audio_input_path=af.source_path,
            audio_output_path=af.target_path,
            model_path=pth_path,
            index_path=index_path,
            pitch=cfg.pitch,
            f0_method=cfg.f0_method,
            index_rate=cfg.index_rate,
            volume_envelope=cfg.volume_envelope,
            protect=cfg.protect,
            hop_length=cfg.hop_length,
            split_audio=False,
            f0_autotune=False,
            clean_audio=False,
            export_format=cfg.export_format,
            resample_sr=0,
            sid=0,
        )
        if not os.path.isfile(af.target_path):
            return "Arquivo de saída não criado."
        return None
    except Exception as e:
        _cleanup(af.target_path)
        return str(e)


def _ensure_ready(engine_dir: str) -> None:
    global _engine_ready
    if _engine_ready:
        return
    if not os.path.isdir(engine_dir):
        raise FileNotFoundError(
            f"Engine RVC não encontrado: {engine_dir}\n"
            "Execute scripts/setup_env.bat"
        )
    if engine_dir not in sys.path:
        sys.path.insert(0, engine_dir)
    os.chdir(engine_dir)
    _engine_ready = True


def _cleanup(path: str) -> None:
    if os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass
