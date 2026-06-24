"""
Prepara clips de áudio para upload no ElevenLabs Instant Voice Clone.

Para cada voz: baixa o YouTube, recorta 60s do meio, exporta MP3 128k (<10MB).

Uso:
    python scripts/prepare_clone_clips.py
    python scripts/prepare_clone_clips.py --out-dir /caminho/alternativo
    python scripts/prepare_clone_clips.py --dry-run

Dependências:
    pip install pydub yt-dlp
"""

import argparse
import logging
import shutil
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

VOICES = [
    {
        "name": "joutjout",
        "url": "https://www.youtube.com/watch?v=OljdATv51HA",
        "gender": "female",
    },
    {
        "name": "cienciatoddia",
        "url": "https://www.youtube.com/watch?v=o0LjwAohJO8",
        "gender": "male",
    },
    {
        "name": "leifert",
        "url": "https://www.youtube.com/watch?v=zPfb05B7jAg",
        "gender": "male",
    },
    {
        "name": "fatima",
        "url": "https://youtu.be/ex77o4FgWok",
        "gender": "female",
    },
]

CLIP_DURATION_MS = 60_000
BITRATE = "128k"


def main():
    args = parse_args()
    out_dir = Path(args.out_dir)

    _clean(out_dir)

    if args.dry_run:
        log.info("[dry-run] Limparia os arquivos existentes e recriaria:")
        for v in VOICES:
            log.info(f"  upload_{v['name']}.mp3  ← {v['url']}")
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        from pydub import AudioSegment
    except ImportError:
        log.error("pydub não instalado. Execute: pip install pydub")
        sys.exit(1)

    if not shutil.which("yt-dlp"):
        log.error("yt-dlp não encontrado. Execute: pip install yt-dlp")
        sys.exit(1)

    for voice in VOICES:
        name = voice["name"]
        url = voice["url"]
        raw_wav = out_dir / f"raw_{name}.wav"
        out_mp3 = out_dir / f"upload_{name}.mp3"

        log.info(f"\n[{name}] Baixando {url}")
        _download(url, raw_wav)

        if not raw_wav.exists():
            log.error(f"[{name}] Download falhou, pulando.")
            continue

        log.info(f"[{name}] Recortando {CLIP_DURATION_MS // 1000}s e convertendo para MP3...")
        audio = AudioSegment.from_file(str(raw_wav))

        start = max(0, len(audio) // 2 - CLIP_DURATION_MS // 2)
        clip = audio[start : start + CLIP_DURATION_MS]

        clip = clip.set_channels(1).set_frame_rate(16000)
        clip.export(str(out_mp3), format="mp3", bitrate=BITRATE)

        size_mb = out_mp3.stat().st_size / 1024 / 1024
        log.info(f"[{name}] {out_mp3.name}: {size_mb:.1f}MB")

        raw_wav.unlink()

    log.info("\nPronto. Arquivos para upload no ElevenLabs:")
    for v in VOICES:
        p = out_dir / f"upload_{v['name']}.mp3"
        if p.exists():
            log.info(f"  {p}")


def _clean(out_dir: Path):
    patterns = ["raw_*.wav", "clip_clone_*.wav", "upload_clone_*.mp3", "upload_*.mp3"]
    removed = 0
    for pattern in patterns:
        for f in out_dir.glob(pattern):
            f.unlink()
            removed += 1
    if removed:
        log.info(f"Limpeza: {removed} arquivo(s) removido(s) de {out_dir}")


def _download(url: str, out_wav: Path):
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "-x",
        "--audio-format", "wav",
        "--audio-quality", "0",
        "-o", str(out_wav.with_suffix("")) + ".%(ext)s",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log.error(f"yt-dlp stderr: {result.stderr[-500:]}")


def parse_args():
    p = argparse.ArgumentParser(description="Prepara clips MP3 para ElevenLabs Voice Clone.")
    p.add_argument(
        "--out-dir",
        default=str(Path(__file__).resolve().parent.parent / "data" / "clone_clips"),
        help="Pasta de saída (padrão: data/clone_clips/)",
    )
    p.add_argument("--dry-run", action="store_true", help="Simula sem baixar nem converter.")
    return p.parse_args()


if __name__ == "__main__":
    main()
