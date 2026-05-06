"""
Golden Dataset — Pipeline de Geração de Deepfakes de Voz.

Uso:
    py/python.exe main.py                                # modo teste (5 por voz, rvc)
    py/python.exe main.py --full                         # todos os arquivos, rvc
    py/python.exe main.py --method elevenlabs --full     # todos os arquivos, elevenlabs
    py/python.exe main.py --voice pt_voice_1 --limit 20
    py/python.exe main.py --strategy cross --full
    py/python.exe main.py --list-models
    py/python.exe main.py --list-models --method elevenlabs
"""

import argparse
import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

import pipeline.config as cfg_module
from pipeline import rvc, runner

ROOT = os.path.dirname(os.path.abspath(__file__))

# Arquivos por voz no modo teste (sem --full ou --limit).
TEST_LIMIT = 5


def main():
    load_dotenv()
    args = parse_args()
    setup_logging()

    config = cfg_module.load(args.config or os.path.join(ROOT, "config.yaml"))

    if args.list_models:
        list_models(config, args.method)
        return

    strategy = "cross" if args.voice else args.strategy
    voice_filter = [args.voice] if args.voice else None

    if args.limit is not None:
        limit = args.limit
    elif args.full:
        limit = None
    else:
        limit = TEST_LIMIT
        logging.warning(f"Modo teste: {TEST_LIMIT} arquivo(s) por voz. Use --full para processar todos.")

    t0 = time.time()
    try:
        results = runner.run(config, method=args.method, strategy=strategy, voice_filter=voice_filter, limit=limit)
    except (FileNotFoundError, ValueError) as e:
        logging.error(str(e))
        sys.exit(1)

    elapsed = time.time() - t0
    total_ok = sum(r.success_count for r in results)
    total_err = sum(r.error_count for r in results)
    elapsed_str = f"{elapsed / 3600:.1f}h" if elapsed >= 3600 else f"{elapsed / 60:.1f}min"

    logging.info(f"Concluído — {total_ok} ok, {total_err} erro(s), {elapsed_str}.")
    if total_err:
        logging.warning("Verifique conversion_errors.log para detalhes.")


def list_models(config, method: str):
    if method == "elevenlabs":
        voices = config.elevenlabs.voices
        if not voices:
            logging.warning("Nenhuma voz ElevenLabs configurada em config.yaml.")
            return
        logging.info(f"{len(voices)} voz(es) configurada(s):")
        for v in voices:
            logging.info(f"  {v['name']:<25}  voice_id: {v['voice_id']}")
    else:
        try:
            models = rvc.find_models(config.models_dir)
        except FileNotFoundError as e:
            logging.error(str(e))
            return
        logging.info(f"{len(models)} modelo(s) RVC encontrado(s):")
        for name, pth, _ in models:
            pth_mb = os.path.getsize(pth) / 1024 / 1024
            logging.info(f"  {name:<25}  {os.path.basename(pth)} ({pth_mb:.1f} MB)")


def parse_args():
    p = argparse.ArgumentParser(description="Golden Dataset — Pipeline de Conversão de Voz")
    p.add_argument("--method", choices=["rvc", "elevenlabs"], default="rvc",
                   help="Backend de conversão (padrão: rvc).")
    p.add_argument("--full", action="store_true",
                   help="Processa todos os arquivos (padrão: modo teste, 5 por voz).")
    p.add_argument("--limit", type=int,
                   help="Máximo de arquivos por voz.")
    p.add_argument("--voice",
                   help="Processa apenas esta voz.")
    p.add_argument("--strategy", choices=["stratified", "cross"], default="stratified",
                   help="Estratégia de atribuição (padrão: stratified).")
    p.add_argument("--list-models", action="store_true",
                   help="Lista os modelos/vozes disponíveis e encerra.")
    p.add_argument("--config",
                   help="Caminho alternativo para o config.yaml.")
    return p.parse_args()


def setup_logging():
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    root.addHandler(console)

    fh = logging.FileHandler(os.path.join(ROOT, "conversion_errors.log"), encoding="utf-8")
    fh.setLevel(logging.ERROR)
    fh.setFormatter(logging.Formatter("%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    err = logging.getLogger("conversion_errors")
    err.addHandler(fh)
    err.propagate = False


if __name__ == "__main__":
    main()
