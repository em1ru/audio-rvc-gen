import glob
import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional


log = logging.getLogger(__name__)


@dataclass(frozen=True)
class AudioFile:
    source_path: str
    target_path: str
    filename: str


@dataclass
class ConversionResult:
    voice_name: str
    success_count: int
    error_count: int
    elapsed_seconds: float
    converted_files: List[AudioFile] = field(default_factory=list)


def find_real(real_dir: str) -> List[str]:
    if not os.path.isdir(real_dir):
        raise FileNotFoundError(
            f"Diretório de áudios reais não encontrado: {real_dir}\n"
            "Execute: py/python.exe scripts/extract_corpus.py"
        )
    files = sorted(glob.glob(os.path.join(real_dir, "*.wav")))
    if not files:
        raise FileNotFoundError(f"Nenhum .wav encontrado em {real_dir}")
    return files


def find_pending(
    source_paths: List[str],
    voice_name: str,
    fake_dir: str,
    limit: Optional[int] = None,
) -> List[AudioFile]:
    out_dir = os.path.join(fake_dir, voice_name)
    os.makedirs(out_dir, exist_ok=True)

    existing = set(os.listdir(out_dir))
    pending = [
        AudioFile(
            source_path=p,
            target_path=os.path.join(out_dir, os.path.basename(p)),
            filename=os.path.basename(p),
        )
        for p in source_paths
        if os.path.basename(p) not in existing
    ]

    skipped = len(source_paths) - len(pending)
    log.info(f"'{voice_name}': {len(source_paths)} atribuídos, {skipped} já prontos, {len(pending)} pendentes.")

    if limit is not None and limit < len(pending):
        pending = pending[:limit]
        log.info(f"'{voice_name}': limitado a {limit}.")

    return pending
