"""
Gera fakes via ElevenLabs Speech-to-Speech (Voice Changer)
usando arquivos do TAGARELA como fonte de áudio.

Uso:
    python scripts/generate_sts_elevenlabs.py \
        --voices "pirula:VOICE_ID_1,nathalia:VOICE_ID_2,sarah:EXAVITQu4vr4xnSDxMaL" \
        --files-per-voice 770

    python scripts/generate_sts_elevenlabs.py \
        --voices "pirula:VOICE_ID_1,sarah:EXAVITQu4vr4xnSDxMaL" --dry-run

Vozes default disponíveis (já usadas no TTS — prefira vozes customizadas):
    Matilda  XrExE9yKIg1WjnnlVkGX   female
    Brian    nPczCjzI2devNBz1zQrb   male
    Alice    Xb7hH8MSUJpSbSDYk0k2   female
    Daniel   onwK4e9ZLuTAKqWW03F9   male
"""

import argparse
import logging
import os
import sys
import time
import wave
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.manifest import ManifestEntry, load as load_manifest, save as save_manifest

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

MANIFEST_PATH = ROOT / "data" / "manifest.csv"
SOURCE_DIR = ROOT / "data" / "real_tagarela"
FAKE_DIR = ROOT / "data" / "fake"
MODEL_ID = "eleven_multilingual_sts_v2"
OUTPUT_FORMAT = "pcm_16000"
CHECKPOINT_INTERVAL = 100
RETRY_DELAY = 5
MAX_RETRIES = 3
DEFAULT_FILES_PER_VOICE = 770

_PCM_RATE = 16000
_PCM_WIDTH = 2
_PCM_CHANNELS = 1


def main():
    args = parse_args()
    voices = parse_voices(args.voices)

    api_key = args.api_key or os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        try:
            from dotenv import load_dotenv
            load_dotenv(ROOT / ".env")
            api_key = os.getenv("ELEVENLABS_API_KEY")
        except ImportError:
            pass
    if not api_key:
        log.error("ELEVENLABS_API_KEY não encontrada. Use --api-key ou defina no .env")
        sys.exit(1)

    source_files = sorted(SOURCE_DIR.glob("tagarela_*.wav"))
    if not source_files:
        log.error(f"Nenhum arquivo encontrado em {SOURCE_DIR}")
        sys.exit(1)
    log.info(f"{len(source_files)} arquivos TAGARELA disponíveis como fonte.")

    existing = load_manifest(str(MANIFEST_PATH))

    total_done = sum(1 for e in existing if e.method == "elevenlabs_sts")
    log.info(f"{total_done} entradas elevenlabs_sts já no manifesto.")

    if args.dry_run:
        for name, voice_id in voices:
            done = sum(1 for e in existing if e.voice_model == f"elevenlabs_sts_{name}")
            remaining = args.files_per_voice - done
            log.info(f"[dry-run] '{name}' ({voice_id}): {done} feitos, {remaining} pendentes")
        total = len(voices) * args.files_per_voice
        log.info(f"[dry-run] Total planejado: {total} arquivos ({total * 10.7 / 60:.0f} min estimados)")
        return

    from elevenlabs import ElevenLabs
    client = ElevenLabs(api_key=api_key)

    for name, voice_id in voices:
        existing = _process_voice(client, name, voice_id, source_files, existing, args.files_per_voice)

    reals = sum(1 for e in existing if e.label == "real")
    fakes = sum(1 for e in existing if e.label == "fake")
    log.info(f"\nFinalizado. Manifesto: {reals} reais, {fakes} fakes.")


def _process_voice(client, voice_name, voice_id, source_files, existing, files_per_voice):
    voice_model = f"elevenlabs_sts_{voice_name}"
    out_dir = FAKE_DIR / voice_model
    out_dir.mkdir(parents=True, exist_ok=True)

    done_for_voice = sum(1 for e in existing if e.voice_model == voice_model)
    log.info(f"\nVoz '{voice_name}': {done_for_voice} já gerados, meta={files_per_voice}")

    remaining = files_per_voice - done_for_voice
    if remaining <= 0:
        log.info(f"Voz '{voice_name}' já completa.")
        return existing

    used_sources = {e.source_file for e in existing if e.voice_model == voice_model}
    pending = [f for f in source_files if f.name not in used_sources][:remaining]

    if not pending:
        log.info(f"Sem arquivos fonte novos para '{voice_name}'.")
        return existing

    try:
        import tqdm
        bar = tqdm.tqdm(total=len(pending), desc=f"  {voice_name}", unit="arq", ncols=80)
    except ImportError:
        bar = None

    new_entries = []
    errors = 0
    total_saved = 0

    for src_path in pending:
        out_filename = f"sts_{voice_name}_{src_path.stem}.wav"
        out_path = out_dir / out_filename

        err = _convert_one(client, voice_id, src_path, out_path)

        if err:
            errors += 1
            log.error(f"{out_filename}: {err}")
        else:
            new_entries.append(ManifestEntry(
                filename=out_filename,
                label="fake",
                method="elevenlabs_sts",
                voice_model=voice_model,
                source_file=src_path.name,
                f0_method="",
                index_rate=None,
                protect=None,
                volume_envelope=None,
                hop_length=None,
                pitch=None,
                generated_at=_now(),
            ))
            total_saved += 1

        if bar:
            bar.update(1)

        if len(new_entries) % CHECKPOINT_INTERVAL == 0 and new_entries:
            existing = existing + new_entries
            save_manifest(str(MANIFEST_PATH), existing)
            new_entries = []
            log.info(f"Checkpoint salvo ({total_saved}/{remaining}).")

    if bar:
        bar.close()

    log.info(f"Voz '{voice_name}': {total_saved} gerados, {errors} erros.")

    if new_entries:
        existing = existing + new_entries
        save_manifest(str(MANIFEST_PATH), existing)

    return existing


def _convert_one(client, voice_id, src_path, out_path):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with open(src_path, "rb") as f:
                stream = client.speech_to_speech.convert(
                    voice_id=voice_id,
                    audio=f,
                    model_id=MODEL_ID,
                    output_format=OUTPUT_FORMAT,
                )
                pcm = b"".join(stream)

            if not pcm:
                return "Resposta vazia da API."

            with wave.open(str(out_path), "wb") as wf:
                wf.setnchannels(_PCM_CHANNELS)
                wf.setsampwidth(_PCM_WIDTH)
                wf.setframerate(_PCM_RATE)
                wf.writeframes(pcm)

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


def parse_voices(voices_str):
    voices = []
    for pair in voices_str.split(","):
        pair = pair.strip()
        if ":" not in pair:
            log.error(f"Formato inválido: '{pair}'. Use 'nome:voice_id'")
            sys.exit(1)
        name, voice_id = pair.split(":", 1)
        voices.append((name.strip(), voice_id.strip()))
    return voices


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_args():
    p = argparse.ArgumentParser(description="Gera fakes STS via ElevenLabs a partir do TAGARELA.")
    p.add_argument(
        "--voices", required=True,
        help="Vozes no formato 'nome:voice_id,nome2:voice_id2,...'"
    )
    p.add_argument(
        "--files-per-voice", type=int, default=DEFAULT_FILES_PER_VOICE,
        help=f"Arquivos a gerar por voz (padrão: {DEFAULT_FILES_PER_VOICE})"
    )
    p.add_argument("--api-key", help="ElevenLabs API key (ou use .env)")
    p.add_argument("--dry-run", action="store_true",
                   help="Simula sem gerar nem modificar o manifesto.")
    return p.parse_args()


if __name__ == "__main__":
    main()
