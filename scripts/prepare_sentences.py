"""
Extrai as transcrições dos WAVs reais do corpus Common Voice PT.

Gera data/sentences.csv com (wav_filename, sentence) para uso pelo
script generate_tts_elevenlabs.py.

Uso:
    py/python.exe scripts/prepare_sentences.py
"""

import csv
import io
import logging
import os
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

CORPUS_TAR = ROOT / "cv-corpus-24.0-2025-12-05-pt.tar.gz"
VALIDATED_TSV = "cv-corpus-24.0-2025-12-05/pt/validated.tsv"
REAL_DIR = ROOT / "data" / "real"
OUT_CSV = ROOT / "data" / "sentences.csv"

csv.field_size_limit(10 ** 7)


def main():
    if not CORPUS_TAR.exists():
        log.error(f"Corpus não encontrado: {CORPUS_TAR}")
        sys.exit(1)

    real_wavs = set(os.listdir(REAL_DIR))
    log.info(f"{len(real_wavs)} WAVs reais em data/real/")

    matched = {}
    log.info("Lendo transcrições do corpus…")
    with tarfile.open(CORPUS_TAR, "r:gz") as tf:
        f = tf.extractfile(VALIDATED_TSV)
        reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8"), delimiter="\t")
        for row in reader:
            wav_name = row["path"].replace(".mp3", ".wav")
            if wav_name in real_wavs:
                sentence = row["sentence"].strip()
                if sentence:
                    matched[wav_name] = sentence

    log.info(f"{len(matched)} transcrições encontradas de {len(real_wavs)} WAVs.")
    missing = len(real_wavs) - len(matched)
    if missing:
        log.warning(f"{missing} WAVs sem transcrição (serão ignorados pelo TTS).")

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["wav_filename", "sentence", "char_count"])
        for wav, sentence in sorted(matched.items()):
            w.writerow([wav, sentence, len(sentence)])

    total_chars = sum(len(s) for s in matched.values())
    avg = total_chars / len(matched)
    log.info(f"Salvo em {OUT_CSV}")
    log.info(f"Total de chars: {total_chars:,}  |  Média por frase: {avg:.0f}")
    log.info(f"Por conta ElevenLabs (10k chars/mês): ~{10_000 // int(avg)} frases")


if __name__ == "__main__":
    main()
