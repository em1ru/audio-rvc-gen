"""
Gera áudios TTS via ElevenLabs a partir das transcrições do Common Voice PT.

Cada conta gratuita tem 10.000 chars/mês (~250 frases). Para maximizar
a cobertura, use uma conta diferente por execução.

Uso:
    py/python.exe scripts/generate_tts_elevenlabs.py --api-key SUA_KEY --voice-id VOICE_ID
    py/python.exe scripts/generate_tts_elevenlabs.py --api-key SUA_KEY --voice-id VOICE_ID --limit 250
    py/python.exe scripts/generate_tts_elevenlabs.py --api-key SUA_KEY --voice-id VOICE_ID --dry-run

Vozes premade disponíveis no free tier (eleven_multilingual_v2):
    Rachel   21m00Tio8rEdSBb7vNzE
    Sarah    EXAVITQu4vr4xnSDxMaL
    Laura    FGY2WhTYpPnrIDTdsKH5
    Charlie  IKne3meq5aSn9XLyUdCD
    George   JBFqnCBsd6RMkjVDRZzb
    River    SAz9YHcvj6GT2YYXdXww
    Roger    CwhRBWXzGAHq8TQ4Fs17
"""

import argparse
import csv
import logging
import os
import sys
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.manifest import ManifestEntry, load as load_manifest, save as save_manifest

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

SENTENCES_CSV = ROOT / "data" / "sentences.csv"
FAKE_DIR = ROOT / "data" / "fake"
MANIFEST_PATH = ROOT / "data" / "manifest.csv"

MODEL_ID = "eleven_multilingual_v2"
OUTPUT_FORMAT = "pcm_16000"
_PCM_RATE = 16000
_PCM_WIDTH = 2
_PCM_CHANNELS = 1

RETRY_DELAY = 5
MAX_RETRIES = 3


def main():
    args = parse_args()

    if not SENTENCES_CSV.exists():
        log.error(f"Arquivo de frases não encontrado: {SENTENCES_CSV}")
        log.error("Execute primeiro: py/python.exe scripts/prepare_sentences.py")
        sys.exit(1)

    sentences = load_sentences(SENTENCES_CSV)
    log.info(f"{len(sentences)} frases disponíveis em sentences.csv")

    existing = load_manifest(str(MANIFEST_PATH))
    done_keys = {(e.filename, e.voice_model) for e in existing if e.method == "tts"}

    voice_label = f"elevenlabs_{args.voice_id[:8]}"
    out_dir = FAKE_DIR / voice_label

    pending = []
    for wav_filename, sentence in sentences:
        out_filename = wav_filename.replace(".wav", f"_{voice_label}.wav")
        if (out_filename, voice_label) not in done_keys:
            pending.append((wav_filename, sentence, out_filename))

    if args.limit:
        pending = pending[: args.limit]

    total_chars = sum(len(s) for _, s, _ in pending)
    log.info(f"Pendentes: {len(pending)} frases ({total_chars:,} chars)")

    if args.dry_run:
        log.info(f"[dry-run] Usaria {total_chars:,} chars da cota ({len(pending)} arquivos).")
        log.info(f"[dry-run] Saída em: data/fake/{voice_label}/")
        return

    from elevenlabs import ElevenLabs
    client = ElevenLabs(api_key=args.api_key)
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
        err = _convert_one(client, args.voice_id, sentence, out_path)
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


def load_sentences(path: Path):
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            rows.append((row["wav_filename"], row["sentence"]))
    return rows


def _convert_one(client, voice_id: str, text: str, out_path: Path):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            stream = client.text_to_speech.convert(
                voice_id=voice_id,
                text=text,
                model_id=MODEL_ID,
                output_format=OUTPUT_FORMAT,
            )
            pcm = b"".join(stream)
            if not pcm:
                return "Resposta vazia da API."
            _save_wav(pcm, out_path)
            return None
        except Exception as e:
            msg = str(e)
            if "429" in msg or "rate" in msg.lower():
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)
                    continue
            if out_path.exists():
                out_path.unlink()
            return msg
    return "Máximo de tentativas atingido."


def _save_wav(pcm: bytes, path: Path) -> None:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(_PCM_CHANNELS)
        wf.setsampwidth(_PCM_WIDTH)
        wf.setframerate(_PCM_RATE)
        wf.writeframes(pcm)


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_args():
    p = argparse.ArgumentParser(description="Gera TTS via ElevenLabs para o golden dataset.")
    p.add_argument("--api-key", required=True, help="ElevenLabs API key.")
    p.add_argument("--voice-id", required=True, help="ID da voz ElevenLabs a usar.")
    p.add_argument("--limit", type=int,
                   help="Máximo de frases a gerar (padrão: todas as pendentes).")
    p.add_argument("--dry-run", action="store_true",
                   help="Simula sem gerar nem modificar o manifesto.")
    return p.parse_args()


if __name__ == "__main__":
    main()
