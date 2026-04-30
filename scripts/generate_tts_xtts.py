"""
Gera áudios TTS via XTTS-v2 (Coqui TTS) para o golden dataset.

XTTS-v2 clona a voz de um áudio de referência e sintetiza fala PT-BR
de forma muito mais realista que engines baseados em API. Requer GPU.

Dependências (instalar no ambiente com GPU antes de rodar):
    pip install TTS torch torchaudio

Uso:
    python scripts/generate_tts_xtts.py
    python scripts/generate_tts_xtts.py --speaker-wav data/real/common_voice_pt_19273358.wav
    python scripts/generate_tts_xtts.py --speaker-wav data/real/common_voice_pt_19273358.wav --voice-name minha_voz --limit 100
    python scripts/generate_tts_xtts.py --dry-run

O modelo XTTS-v2 (~1.8 GB) é baixado automaticamente na primeira execução.
"""

import argparse
import csv
import logging
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.manifest import ManifestEntry, load as load_manifest, save as save_manifest

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

SENTENCES_CSV = ROOT / "data" / "sentences.csv"
FAKE_DIR = ROOT / "data" / "fake"
MANIFEST_PATH = ROOT / "data" / "manifest.csv"
REAL_DIR = ROOT / "data" / "real"

MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"
LANGUAGE = "pt"
TARGET_SR = 16000


def main():
    args = parse_args()

    if not SENTENCES_CSV.exists():
        log.error("data/sentences.csv não encontrado. Execute primeiro: python scripts/prepare_sentences.py")
        sys.exit(1)

    sentences = load_sentences(SENTENCES_CSV)
    log.info(f"{len(sentences)} frases disponíveis.")

    speaker_wav = resolve_speaker_wav(args.speaker_wav)
    log.info(f"Referência de voz: {speaker_wav.name}")

    voice_label = args.voice_name or f"xtts_v2_{speaker_wav.stem[:20]}"
    out_dir = FAKE_DIR / voice_label

    existing = load_manifest(str(MANIFEST_PATH))
    done_keys = {(e.filename, e.voice_model) for e in existing}

    pending = []
    for wav_filename, sentence in sentences:
        out_filename = wav_filename.replace(".wav", f"_{voice_label}.wav")
        if (out_filename, voice_label) not in done_keys:
            pending.append((wav_filename, sentence, out_filename))

    if args.limit:
        pending = pending[:args.limit]

    log.info(f"Pendentes: {len(pending)} frases.")

    if args.dry_run:
        log.info(f"[dry-run] Saída em: data/fake/{voice_label}/")
        log.info(f"[dry-run] Modelo: {MODEL_NAME}")
        log.info("[dry-run] Nenhuma alteração feita.")
        return

    _check_gpu()
    tts = _load_model()

    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        import tqdm
        bar = tqdm.tqdm(total=len(pending), unit="arq", ncols=80)
    except ImportError:
        bar = None

    new_entries = []
    errors = 0

    for wav_filename, sentence, out_filename in pending:
        out_path = out_dir / out_filename
        err = _convert_one(tts, sentence, speaker_wav, out_path)
        if err:
            errors += 1
            log.error(f"{out_filename}: {err}")
        else:
            new_entries.append(ManifestEntry(
                filename=out_filename,
                label="fake",
                method="tts",
                voice_model=voice_label,
                source_file=wav_filename,
                f0_method="",
                index_rate=None,
                protect=None,
                volume_envelope=None,
                hop_length=None,
                pitch=None,
                generated_at=_now(),
            ))
        if bar:
            bar.update(1)

    if bar:
        bar.close()

    log.info(f"Gerados: {len(new_entries)}, erros: {errors}.")

    if new_entries:
        all_entries = existing + new_entries
        save_manifest(str(MANIFEST_PATH), all_entries)
        reals = sum(1 for e in all_entries if e.label == "real")
        fakes = sum(1 for e in all_entries if e.label == "fake")
        log.info(f"Manifesto: {reals} reais, {fakes} fakes (+{len(new_entries)} novos).")


def resolve_speaker_wav(path: str | None) -> Path:
    if path:
        p = Path(path)
        if not p.exists():
            log.error(f"Speaker WAV não encontrado: {p}")
            sys.exit(1)
        return p
    wavs = sorted(REAL_DIR.glob("*.wav"))
    if not wavs:
        log.error(f"Nenhum WAV real encontrado em {REAL_DIR}")
        sys.exit(1)
    return wavs[0]


def load_sentences(path: Path):
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            rows.append((row["wav_filename"], row["sentence"]))
    return rows


def _load_model():
    try:
        from TTS.api import TTS
    except ImportError:
        log.error("TTS não instalado. Execute: pip install TTS torch torchaudio")
        sys.exit(1)

    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    log.info(f"Carregando XTTS-v2 em {device.upper()}… (primeira vez baixa ~1.8 GB)")
    return TTS(MODEL_NAME).to(device)


def _check_gpu():
    try:
        import torch
        if not torch.cuda.is_available():
            log.warning("GPU não detectada — rodando em CPU. Vai ser muito lento.")
        else:
            log.info(f"GPU: {torch.cuda.get_device_name(0)}")
    except ImportError:
        log.warning("torch não instalado — instale com: pip install torch torchaudio")


def _convert_one(tts, text: str, speaker_wav: Path, out_path: Path) -> str | None:
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        tts.tts_to_file(
            text=text,
            speaker_wav=str(speaker_wav),
            language=LANGUAGE,
            file_path=tmp_path,
        )

        # Resample para 16kHz mono (XTTS-v2 gera 24kHz)
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", tmp_path,
             "-ar", str(TARGET_SR), "-ac", "1", "-sample_fmt", "s16",
             str(out_path)],
            capture_output=True,
        )
        os.unlink(tmp_path)

        if result.returncode != 0:
            return f"ffmpeg falhou: {result.stderr[-200:]}"
        if not out_path.exists():
            return "Arquivo não criado."
        return None
    except Exception as e:
        if out_path.exists():
            out_path.unlink()
        return str(e)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_args():
    p = argparse.ArgumentParser(description="Gera TTS com XTTS-v2 para o golden dataset.")
    p.add_argument("--speaker-wav",
                   help="WAV de referência para clonar a voz (padrão: primeiro real disponível).")
    p.add_argument("--voice-name",
                   help="Nome da voz no manifest (padrão: xtts_v2_<nome_do_arquivo>).")
    p.add_argument("--limit", type=int,
                   help="Máximo de frases a gerar.")
    p.add_argument("--dry-run", action="store_true",
                   help="Simula sem gerar nem modificar o manifesto.")
    return p.parse_args()


if __name__ == "__main__":
    main()
