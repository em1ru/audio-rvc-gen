"""
Importa áudios TTS do arquivo RAR para o golden dataset.

Extrai os MP3, converte para WAV 16 kHz mono e registra no manifest.csv.

Uso:
    py/python.exe scripts/import_tts.py
    py/python.exe scripts/import_tts.py --rar caminho/para/golden_audio.rar
    py/python.exe scripts/import_tts.py --dry-run
"""

import argparse
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.manifest import ManifestEntry, load as load_manifest, save as save_manifest

log = logging.getLogger(__name__)

UNRAR = Path(r"C:\Program Files\WinRAR\UnRAR.exe")
DEFAULT_RAR = ROOT / "golden_audio (1).rar"
FAKE_DIR = ROOT / "data" / "fake"
MANIFEST_PATH = ROOT / "data" / "manifest.csv"

TTS_ENGINES = ["edge", "google", "gtts", "polly"]
GENERATED_AT = "2026-03-10T00:00:00Z"


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args()

    rar_path = Path(args.rar)
    if not rar_path.exists():
        log.error(f"RAR não encontrado: {rar_path}")
        sys.exit(1)

    if not _ffmpeg_available():
        log.error("ffmpeg não encontrado no PATH. Instale e adicione ao PATH.")
        sys.exit(1)

    if not UNRAR.exists():
        log.error(f"UnRAR não encontrado em {UNRAR}")
        sys.exit(1)

    log.info(f"Extraindo {rar_path.name} ({rar_path.stat().st_size // 1024 // 1024} MB)…")
    with tempfile.TemporaryDirectory(prefix="import_tts_") as tmpdir:
        _extract_rar(rar_path, Path(tmpdir))
        mp3_files = _collect_mp3s(Path(tmpdir))
        log.info(f"{len(mp3_files)} MP3(s) encontrado(s) em {len(TTS_ENGINES)} engine(s).")

        existing = load_manifest(str(MANIFEST_PATH))
        existing_keys = {(e.filename, e.voice_model) for e in existing}

        new_entries = []
        skipped = 0
        errors = 0

        try:
            import tqdm
            bar = tqdm.tqdm(total=len(mp3_files), unit="arq", ncols=80)
        except ImportError:
            bar = None

        for engine, mp3_path in mp3_files:
            wav_name = mp3_path.stem.replace("_raw", "") + ".wav"
            # 00000_edge_raw.mp3 → 00000_edge.wav

            if (wav_name, engine) in existing_keys:
                skipped += 1
                if bar:
                    bar.update(1)
                continue

            out_dir = FAKE_DIR / engine
            out_path = out_dir / wav_name

            if not args.dry_run:
                out_dir.mkdir(parents=True, exist_ok=True)
                if not _convert_mp3_to_wav(mp3_path, out_path):
                    errors += 1
                    if bar:
                        bar.update(1)
                    continue

            new_entries.append(ManifestEntry(
                filename=wav_name,
                label="fake",
                method="tts",
                voice_model=engine,
                source_file="",
                f0_method="",
                index_rate=None,
                protect=None,
                volume_envelope=None,
                hop_length=None,
                pitch=None,
                generated_at=GENERATED_AT,
            ))
            if bar:
                bar.update(1)

        if bar:
            bar.close()

        log.info(f"Novos: {len(new_entries)}, já existentes: {skipped}, erros: {errors}.")

        if new_entries and not args.dry_run:
            all_entries = existing + new_entries
            save_manifest(str(MANIFEST_PATH), all_entries)
            reals = sum(1 for e in all_entries if e.label == "real")
            fakes = sum(1 for e in all_entries if e.label == "fake")
            log.info(f"Manifesto: {reals} reais, {fakes} fakes (+{len(new_entries)} novos).")
        elif args.dry_run:
            engines_found = {}
            for e in new_entries:
                engines_found[e.voice_model] = engines_found.get(e.voice_model, 0) + 1
            for eng, cnt in sorted(engines_found.items()):
                log.info(f"  [dry-run] {eng}: {cnt} arquivo(s)")
            log.info("[dry-run] Nenhuma alteração feita.")


def _extract_rar(rar_path: Path, dest: Path) -> None:
    result = subprocess.run(
        [str(UNRAR), "x", str(rar_path), str(dest) + os.sep, "-y"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"UnRAR falhou (código {result.returncode}): {result.stderr[-300:]}")


def _collect_mp3s(extract_dir: Path):
    """Retorna lista de (engine, Path) para cada MP3 extraído."""
    files = []
    base = extract_dir / "golden_audio"
    if not base.exists():
        base = extract_dir
    for engine in TTS_ENGINES:
        engine_dir = base / engine / "clean"
        if not engine_dir.exists():
            log.warning(f"Diretório ausente no RAR: {engine_dir.relative_to(extract_dir)}")
            continue
        mp3s = sorted(engine_dir.glob("*.mp3"))
        log.info(f"  {engine}: {len(mp3s)} arquivo(s)")
        for mp3 in mp3s:
            files.append((engine, mp3))
    return files


def _convert_mp3_to_wav(src: Path, dst: Path) -> bool:
    """Converte MP3 para WAV 16 kHz mono via ffmpeg. Retorna True se OK."""
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", str(src),
         "-ar", "16000", "-ac", "1", "-sample_fmt", "s16",
         str(dst)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        log.error(f"ffmpeg falhou em {src.name}: {result.stderr[-200:]}")
        return False
    return True


def _ffmpeg_available() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True)
        return True
    except FileNotFoundError:
        return False


def parse_args():
    p = argparse.ArgumentParser(description="Importa áudios TTS do RAR para o golden dataset.")
    p.add_argument("--rar", default=str(DEFAULT_RAR),
                   help=f"Caminho para o RAR (padrão: {DEFAULT_RAR.name})")
    p.add_argument("--dry-run", action="store_true",
                   help="Simula sem extrair nem modificar o manifesto.")
    return p.parse_args()


if __name__ == "__main__":
    main()
