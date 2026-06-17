"""
Baixa amostras do dataset TAGARELA (Hugging Face) via streaming
e salva como WAVs 16kHz mono em data/real_tagarela/.

Uso:
    python scripts/download_tagarela.py
    python scripts/download_tagarela.py --limit 18750
    python scripts/download_tagarela.py --dry-run

Dependências:
    pip install datasets soundfile soxr
"""

import argparse
import logging
import sys
import wave
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.manifest import ManifestEntry, load as load_manifest, save as save_manifest

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

MANIFEST_PATH = ROOT / "data" / "manifest.csv"
OUT_DIR = ROOT / "data" / "real_tagarela"
TARGET_SR = 16000
DATASET_NAME = "freds0/TAGARELA"
ACCENT_FILTER = "pt-br"
DEFAULT_LIMIT = 18750
CHECKPOINT_INTERVAL = 500


def main():
    args = parse_args()

    existing = load_manifest(str(MANIFEST_PATH))
    done_filenames = {e.filename for e in existing if e.method == "tagarela"}
    log.info(f"{len(done_filenames)} entradas TAGARELA já no manifesto.")

    remaining = args.limit - len(done_filenames)
    if remaining <= 0:
        log.info("Limite já atingido. Nada a fazer.")
        return

    log.info(f"Meta: {args.limit} amostras. Pendentes: {remaining}.")

    if args.dry_run:
        log.info(f"[dry-run] Baixaria {remaining} amostras de {DATASET_NAME} (accent={ACCENT_FILTER}).")
        log.info(f"[dry-run] Saída em: data/real_tagarela/")
        return

    try:
        from datasets import load_dataset
    except ImportError:
        log.error("datasets não instalado. Execute: pip install datasets soundfile soxr")
        sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    log.info(f"Conectando ao {DATASET_NAME} via streaming...")
    dataset = load_dataset(DATASET_NAME, split="train", streaming=True)
    dataset = dataset.filter(lambda x: x.get("accent") == ACCENT_FILTER)

    new_entries = []
    errors = 0
    idx = _next_index(done_filenames)

    try:
        import tqdm
        bar = tqdm.tqdm(total=remaining, unit="arq", ncols=80)
    except ImportError:
        bar = None

    for sample in dataset:
        if len(new_entries) >= remaining:
            break

        filename = f"tagarela_{idx:06d}.wav"
        while filename in done_filenames:
            idx += 1
            filename = f"tagarela_{idx:06d}.wav"

        out_path = OUT_DIR / filename
        err = _save_sample(sample, out_path)

        if err:
            errors += 1
            log.error(f"{filename}: {err}")
        else:
            new_entries.append(ManifestEntry(
                filename=filename,
                label="real",
                method="tagarela",
                voice_model="",
                source_file=sample.get("path", ""),
                f0_method="",
                index_rate=None,
                protect=None,
                volume_envelope=None,
                hop_length=None,
                pitch=None,
                generated_at=_now(),
            ))
            idx += 1

        if bar:
            bar.update(1)

        if len(new_entries) % CHECKPOINT_INTERVAL == 0 and new_entries:
            existing = _flush(existing, new_entries)
            new_entries = []
            log.info(f"Checkpoint salvo.")

    if bar:
        bar.close()

    log.info(f"Gerados: {len(new_entries)}, erros: {errors}.")

    if new_entries:
        all_entries = _flush(existing, new_entries)
        reals = sum(1 for e in all_entries if e.label == "real")
        fakes = sum(1 for e in all_entries if e.label == "fake")
        log.info(f"Manifesto: {reals} reais, {fakes} fakes (+{len(new_entries)} novos).")


def _next_index(done_filenames: set) -> int:
    indices = []
    for f in done_filenames:
        if f.startswith("tagarela_") and f.endswith(".wav"):
            try:
                indices.append(int(f[9:15]))
            except ValueError:
                pass
    return max(indices) + 1 if indices else 0


def _save_sample(sample, out_path: Path) -> str | None:
    try:
        audio = sample["audio"]
        array = np.array(audio["array"], dtype=np.float32)
        sr = audio["sampling_rate"]

        if array.ndim > 1:
            array = array.mean(axis=0)

        if sr != TARGET_SR:
            try:
                import soxr
                array = soxr.resample(array, sr, TARGET_SR)
            except ImportError:
                import librosa
                array = librosa.resample(array, orig_sr=sr, target_sr=TARGET_SR)

        array_int16 = (array * 32767).clip(-32768, 32767).astype(np.int16)

        with wave.open(str(out_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(TARGET_SR)
            wf.writeframes(array_int16.tobytes())

        return None
    except Exception as e:
        if out_path.exists():
            out_path.unlink()
        return str(e)


def _flush(existing, new_entries):
    all_entries = existing + new_entries
    save_manifest(str(MANIFEST_PATH), all_entries)
    return all_entries


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_args():
    p = argparse.ArgumentParser(description="Baixa amostras do TAGARELA para o golden dataset.")
    p.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                   help=f"Total de amostras TAGARELA desejadas (padrão: {DEFAULT_LIMIT}).")
    p.add_argument("--dry-run", action="store_true",
                   help="Simula sem baixar nem modificar o manifesto.")
    return p.parse_args()


if __name__ == "__main__":
    main()
