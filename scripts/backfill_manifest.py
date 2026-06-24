"""
Backfill de campos ausentes no manifesto legado.

Corrige entradas do Common Voice que foram criadas antes do schema completo:
  - method="" → "common_voice"
  - generated_at="" → "unknown"

Uso:
    python scripts/backfill_manifest.py
    python scripts/backfill_manifest.py --dry-run
"""

import argparse
import logging
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.manifest import load as load_manifest, save as save_manifest

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

MANIFEST_PATH = ROOT / "data" / "manifest.csv"


def main():
    args = parse_args()
    entries = load_manifest(str(MANIFEST_PATH))
    log.info(f"{len(entries)} entradas carregadas.")

    fixed = 0
    updated = []
    for e in entries:
        changes = {}
        if not e.method and e.label == "real":
            changes["method"] = "common_voice"
        if not e.generated_at:
            changes["generated_at"] = "unknown"
        if changes:
            e = replace(e, **changes)
            fixed += 1
        updated.append(e)

    log.info(f"{fixed} entradas a corrigir.")

    if args.dry_run:
        log.info("[dry-run] Nenhuma alteração salva.")
        return

    save_manifest(str(MANIFEST_PATH), updated)
    log.info("Manifesto salvo.")


def parse_args():
    p = argparse.ArgumentParser(description="Backfill de campos ausentes no manifesto.")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    main()
