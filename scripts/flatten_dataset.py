"""
Flatten do golden dataset para inferência.

Move todos os arquivos para data/real/ e data/fake/ (diretórios planos)
e preenche a coluna filepath no manifesto com o caminho relativo.

Arquivos RVC que têm o mesmo nome do real de origem são renomeados para
incluir o voice_model: common_voice_pt_19273358_Lula.wav

Estrutura resultante:
    data/real/        → todos os reais (Common Voice + TAGARELA)
    data/fake/        → todos os fakes (flat, sem subpastas)
    data/manifest.csv → coluna filepath preenchida

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
FAKE_DIR = DATA_DIR / "fake"


def main():
    args = parse_args()
    entries = load_manifest(str(DATA_DIR / "manifest.csv"))

    log.info("Indexando arquivos no disco...")
    # índice: (filename, subdir_name) → Path  — preserva duplicatas por subpasta
    disk_index = _build_disk_index()
    log.info(f"{len(disk_index)} arquivos encontrados no disco.")

    real_out = DATA_DIR / "real"
    fake_out = DATA_DIR / "fake"

    # nomes que já vão existir no destino (para detectar conflitos)
    dest_names: set = set()
    moves = []
    missing = []

    for entry in entries:
        # tenta localizar o arquivo no disco
        current_path = _find_on_disk(entry, disk_index)

        if not current_path:
            missing.append(entry.filename)
            continue

        if entry.label == "real":
            new_filename = entry.filename
            dest = real_out / new_filename
            new_filepath = f"real/{new_filename}"
        else:
            # fakes RVC têm mesmo basename do real — renomeia com voice_model
            new_filename = _resolve_fake_filename(entry, dest_names)
            dest = fake_out / new_filename
            new_filepath = f"fake/{new_filename}"

        dest_names.add(new_filename)
        moves.append((current_path, dest, new_filepath, new_filename, entry))

    log.info(f"Movimentos planejados: {len(moves)}")
    log.info(f"Arquivos não encontrados no disco: {len(missing)}")
    if missing[:5]:
        for f in missing[:5]:
            log.warning(f"  não encontrado: {f}")

    if args.dry_run:
        reals = sum(1 for _, _, fp, _, _ in moves if fp.startswith("real/"))
        fakes = sum(1 for _, _, fp, _, _ in moves if fp.startswith("fake/"))
        renamed = sum(1 for _, _, _, fn, e in moves if fn != e.filename)
        log.info(f"[dry-run] Moveria: {reals} reais, {fakes} fakes ({renamed} fakes renomeados).")
        return

    real_out.mkdir(parents=True, exist_ok=True)

    updated = []
    moved = 0
    already = 0
    errors = 0

    for src, dest, new_filepath, new_filename, entry in moves:
        if src == dest:
            updated.append(replace(entry, filename=new_filename, filepath=new_filepath))
            already += 1
            continue
        try:
            shutil.move(str(src), str(dest))
            updated.append(replace(entry, filename=new_filename, filepath=new_filepath))
            moved += 1
        except Exception as e:
            log.error(f"Erro ao mover {src.name}: {e}")
            updated.append(entry)
            errors += 1

    # entradas sem arquivo no disco mantêm como estão
    moved_keys = {(e.filename, e.voice_model) for e in updated}
    for entry in entries:
        if (entry.filename, entry.voice_model) not in moved_keys:
            updated.append(entry)

    log.info(f"Movidos: {moved} | Já no lugar: {already} | Erros: {errors} | Sem arquivo: {len(missing)}")
    save_manifest(str(DATA_DIR / "manifest.csv"), updated)

    _cleanup_empty_dirs(fake_out)
    log.info("Subpastas vazias removidas.")
    log.info("Flatten concluído.")


def _build_disk_index() -> dict:
    """Retorna {(filename, parent_dir): Path} para todos os WAVs sob data/."""
    index = {}
    for wav in DATA_DIR.rglob("*.wav"):
        index[(wav.name, wav.parent.name)] = wav
        # também indexa só pelo nome (para arquivos sem ambiguidade)
        if wav.name not in index:
            index[wav.name] = wav
    return index


def _find_on_disk(entry, disk_index: dict) -> Path | None:
    """Localiza o arquivo no disco usando subpasta como dica."""
    if entry.label == "real":
        # tenta real/ e real_tagarela/
        for subdir in ("real", "real_tagarela"):
            p = disk_index.get((entry.filename, subdir))
            if p:
                return p
    else:
        # tenta a subpasta do voice_model
        subdir_hint = entry.voice_model.replace("elevenlabs_sts_", "elevenlabs_sts_")
        p = disk_index.get((entry.filename, subdir_hint))
        if p:
            return p
        # fallback: qualquer subpasta de fake/
        for key, path in disk_index.items():
            if isinstance(key, tuple) and key[0] == entry.filename:
                if "fake" in str(path):
                    return path
    # último recurso: só pelo nome
    return disk_index.get(entry.filename)


def _resolve_fake_filename(entry, dest_names: set) -> str:
    """
    Se o filename já está em dest_names (conflito com real ou outro fake),
    adiciona o voice_model ao stem.
    """
    if entry.filename not in dest_names:
        return entry.filename
    p = Path(entry.filename)
    voice_slug = entry.voice_model.replace(" ", "_")
    new_name = f"{p.stem}_{voice_slug}{p.suffix}"
    # garante unicidade em caso de colisão dupla
    i = 2
    base = new_name
    while new_name in dest_names:
        new_name = f"{Path(base).stem}_{i}{p.suffix}"
        i += 1
    return new_name


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
