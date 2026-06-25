"""
Flatten do golden dataset para inferência.

Move todos os arquivos para data/real/ e data/fake/ (diretórios planos)
e preenche a coluna filepath no manifesto com o caminho relativo.

Estrutura resultante:
    data/real/        → todos os reais (Common Voice + TAGARELA)
    data/fake/        → todos os fakes (flat, sem subpastas)
    data/manifest.csv → coluna filepath preenchida

O método e voice_model continuam no manifesto — não se perde rastreabilidade.

Uso:
    python scripts/flatten_dataset.py
    python scripts/flatten_dataset.py --dry-run
"""

import argparse
import logging
import shutil
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.manifest import load as load_manifest, save as save_manifest

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

DATA_DIR = ROOT / "data"
REAL_DIRS = ["real", "real_tagarela"]
FAKE_DIR = DATA_DIR / "fake"


def main():
    args = parse_args()
    entries = load_manifest(str(DATA_DIR / "manifest.csv"))

    # índice: filename → entrada
    by_filename = {e.filename: e for e in entries}

    # descobre onde cada arquivo está no disco
    log.info("Indexando arquivos no disco...")
    disk_index = _build_disk_index()
    log.info(f"{len(disk_index)} arquivos encontrados no disco.")

    real_out = DATA_DIR / "real"
    fake_out = DATA_DIR / "fake"

    moves = []
    missing = []
    conflicts = []

    for entry in entries:
        current_path = disk_index.get(entry.filename)
        if not current_path:
            missing.append(entry.filename)
            continue

        if entry.label == "real":
            dest = real_out / entry.filename
            new_filepath = f"real/{entry.filename}"
        else:
            dest = fake_out / entry.filename
            new_filepath = f"fake/{entry.filename}"

        if dest.exists() and dest != current_path:
            conflicts.append((entry.filename, current_path, dest))
            continue

        moves.append((current_path, dest, new_filepath, entry))

    log.info(f"Movimentos planejados: {len(moves)}")
    log.info(f"Arquivos não encontrados no disco: {len(missing)}")
    if conflicts:
        log.warning(f"Conflitos de nome (serão pulados): {len(conflicts)}")
        for fname, src, dst in conflicts[:5]:
            log.warning(f"  {fname}: {src} vs {dst}")

    if args.dry_run:
        log.info("[dry-run] Nenhum arquivo movido.")
        reals = sum(1 for _, _, fp, _ in moves if fp.startswith("real/"))
        fakes = sum(1 for _, _, fp, _ in moves if fp.startswith("fake/"))
        log.info(f"[dry-run] Moveria: {reals} reais, {fakes} fakes.")
        return

    real_out.mkdir(parents=True, exist_ok=True)

    updated = []
    moved = 0
    skipped = 0

    for src, dest, new_filepath, entry in moves:
        if src == dest:
            updated.append(replace(entry, filepath=new_filepath))
            skipped += 1
            continue
        try:
            shutil.move(str(src), str(dest))
            updated.append(replace(entry, filepath=new_filepath))
            moved += 1
        except Exception as e:
            log.error(f"Erro ao mover {src.name}: {e}")
            updated.append(entry)

    # entradas sem arquivo no disco mantêm filepath atual
    moved_filenames = {e.filename for e in updated}
    for entry in entries:
        if entry.filename not in moved_filenames:
            updated.append(entry)

    log.info(f"Movidos: {moved} | Já no lugar: {skipped} | Erros: {len(entries) - len(updated)}")

    save_manifest(str(DATA_DIR / "manifest.csv"), updated)

    # remove subpastas vazias de fake/
    _cleanup_empty_dirs(fake_out)
    log.info("Subpastas vazias removidas.")
    log.info("Flatten concluído.")


def _build_disk_index() -> dict:
    """Retorna {filename: Path} para todos os WAVs sob data/."""
    index = {}
    for wav in DATA_DIR.rglob("*.wav"):
        if wav.name in index:
            # guarda o mais específico (evita contar o destino já movido)
            pass
        index[wav.name] = wav
    return index


def _cleanup_empty_dirs(path: Path):
    for d in sorted(path.rglob("*"), reverse=True):
        if d.is_dir():
            try:
                d.rmdir()
            except OSError:
                pass


def parse_args():
    p = argparse.ArgumentParser(description="Flatten do dataset para inferência.")
    p.add_argument("--dry-run", action="store_true", help="Simula sem mover arquivos.")
    return p.parse_args()


if __name__ == "__main__":
    main()
