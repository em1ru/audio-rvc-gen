#!/usr/bin/env python3
"""
Golden Dataset — Multi-Voice RVC Pipeline
==========================================
Converts real audio clips into deepfake versions using multiple RVC voice
models.  Models are auto-discovered from the models/ directory.

Usage (via portable Python):
    .\\py\\python.exe run_pipeline.py                   # Test mode (5 files per voice)
    .\\py\\python.exe run_pipeline.py --full             # Full batch, all voices
    .\\py\\python.exe run_pipeline.py --voice ronaldo    # Single voice only
    .\\py\\python.exe run_pipeline.py --limit 20         # 20 files per voice
    .\\py\\python.exe run_pipeline.py --list-models      # List available models

Options:
    --full          Process all files (default: test mode, 5 files)
    --limit N       Override file limit per voice
    --voice NAME    Process only the specified voice model
    --list-models   List detected models and exit
    --input DIR     Override input directory
    --config FILE   Path to config.yaml (default: config.yaml)
"""

import argparse
import glob
import logging
import os
import sys
import time

try:
    import yaml
except ImportError:
    # Minimal YAML parser fallback for environments without PyYAML
    yaml = None

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG = os.path.join(ROOT, "config.yaml")
ERROR_LOG = os.path.join(ROOT, "conversion_errors.log")

TEST_LIMIT = 5
BAR_WIDTH = 30


# ---------------------------------------------------------------------------
# Config Loader
# ---------------------------------------------------------------------------
def load_config(config_path: str) -> dict:
    """Load config.yaml and return as dict with resolved absolute paths."""
    if yaml is not None:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
    else:
        cfg = _parse_yaml_fallback(config_path)

    paths = cfg.get("paths", {})
    # Resolve relative paths against ROOT
    for key in ("models_dir", "real_audio_dir", "fake_audio_dir", "rvc_engine"):
        val = paths.get(key, "")
        if val and not os.path.isabs(val):
            paths[key] = os.path.join(ROOT, val)

    cfg["paths"] = paths
    return cfg


def _parse_yaml_fallback(path: str) -> dict:
    """Bare-bones YAML key: value parser (no nested structures beyond 1 level)."""
    cfg = {}
    current_section = None
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if not line.startswith(" ") and stripped.endswith(":"):
                current_section = stripped[:-1]
                cfg[current_section] = {}
            elif current_section is not None:
                if ":" in stripped:
                    k, v = stripped.split(":", 1)
                    k = k.strip()
                    v = v.strip()
                    # Parse simple types
                    if v == "[]":
                        v = []
                    elif v.replace(".", "", 1).lstrip("-").isdigit():
                        v = float(v) if "." in v else int(v)
                    cfg[current_section][k] = v
    return cfg


# ---------------------------------------------------------------------------
# Model Discovery
# ---------------------------------------------------------------------------
def discover_models(models_dir: str, active_filter: list = None) -> list:
    """
    Scan models_dir for subdirectories containing a .pth and .index file.
    Returns list of dicts: {name, pth_path, index_path}.
    """
    models = []

    if not os.path.isdir(models_dir):
        print(f"[ERROR] Models directory not found: {models_dir}")
        sys.exit(1)

    for entry in sorted(os.listdir(models_dir)):
        model_dir = os.path.join(models_dir, entry)
        if not os.path.isdir(model_dir):
            continue

        # Apply active_models filter
        if active_filter and entry not in active_filter:
            continue

        # Find .pth and .index files
        pth_files = glob.glob(os.path.join(model_dir, "*.pth"))
        index_files = glob.glob(os.path.join(model_dir, "*.index"))

        if not pth_files:
            print(f"[WARN] Skipping '{entry}': no .pth file found")
            continue
        if not index_files:
            print(f"[WARN] Skipping '{entry}': no .index file found")
            continue

        models.append({
            "name": entry,
            "pth_path": pth_files[0],
            "index_path": index_files[0],
        })

    return models


def print_models(models: list):
    """Pretty-print discovered models."""
    if not models:
        print("\n  No voice models found.")
        print("  Place .pth + .index files inside models/<voice_name>/\n")
        return

    print(f"\n{'='*60}")
    print(f"  Discovered Voice Models ({len(models)})")
    print(f"{'='*60}")
    for m in models:
        pth_size = os.path.getsize(m["pth_path"]) / (1024 * 1024)
        idx_size = os.path.getsize(m["index_path"]) / (1024 * 1024)
        print(f"\n  📢 {m['name']}")
        print(f"     PTH:   {os.path.basename(m['pth_path'])} ({pth_size:.1f} MB)")
        print(f"     Index: {os.path.basename(m['index_path'])} ({idx_size:.1f} MB)")
    print(f"\n{'='*60}\n")


# ---------------------------------------------------------------------------
# File Selection (with checkpoint/resume)
# ---------------------------------------------------------------------------
def get_pending_files(input_dir: str, output_dir: str, limit: int = None):
    """
    Find WAV files in input_dir not yet present in output_dir.
    Returns list of (input_path, output_path) tuples.
    """
    os.makedirs(output_dir, exist_ok=True)

    input_files = sorted(glob.glob(os.path.join(input_dir, "*.wav")))
    if not input_files:
        print(f"[WARN] No .wav files in {input_dir}")
        return []

    existing = set(os.listdir(output_dir))

    pending = []
    skipped = 0
    for inp in input_files:
        basename = os.path.basename(inp)
        if basename in existing:
            skipped += 1
            continue
        pending.append((inp, os.path.join(output_dir, basename)))

    print(f"  Total input files:  {len(input_files)}")
    print(f"  Already processed:  {skipped}")
    print(f"  Pending:            {len(pending)}")

    if limit is not None and limit < len(pending):
        pending = pending[:limit]
        print(f"  Limited to:         {limit}")

    return pending


# ---------------------------------------------------------------------------
# Applio Setup
# ---------------------------------------------------------------------------
def setup_applio(rvc_engine_dir: str):
    """Add Applio RVC engine to PYTHONPATH and set working directory."""
    if rvc_engine_dir not in sys.path:
        sys.path.insert(0, rvc_engine_dir)
    os.chdir(rvc_engine_dir)


# ---------------------------------------------------------------------------
# Batch Conversion (per voice)
# ---------------------------------------------------------------------------
def convert_voice(model: dict, pending: list, rvc_params: dict,
                  rvc_engine_dir: str, is_test: bool):
    """Run RVC inference for a single voice model over all pending files."""
    setup_applio(rvc_engine_dir)

    from rvc.infer.infer import VoiceConverter

    total = len(pending)
    if total == 0:
        print(f"  ✓ Nothing to process — all files already converted.\n")
        return 0, 0

    print(f"\n  Loading VoiceConverter...")
    print(f"  Model:     {os.path.basename(model['pth_path'])}")
    print(f"  Index:     {os.path.basename(model['index_path'])}")
    print(f"  F0 method: {rvc_params.get('f0_method', 'rmvpe')}")
    print(f"  Files:     {total}\n")

    t_load = time.time()
    vc = VoiceConverter()
    print(f"  VoiceConverter ready ({time.time() - t_load:.1f}s)\n")

    success = 0
    errors = 0
    t_start = time.time()

    for i, (inp, out) in enumerate(pending, 1):
        basename = os.path.basename(inp)
        t_file = time.time()

        try:
            vc.convert_audio(
                audio_input_path=inp,
                audio_output_path=out,
                model_path=model["pth_path"],
                index_path=model["index_path"],
                pitch=rvc_params.get("pitch", 0),
                f0_method=rvc_params.get("f0_method", "rmvpe"),
                index_rate=rvc_params.get("index_rate", 0.75),
                volume_envelope=rvc_params.get("volume_envelope", 0.25),
                protect=rvc_params.get("protect", 0.33),
                hop_length=rvc_params.get("hop_length", 128),
                split_audio=False,
                f0_autotune=False,
                clean_audio=False,
                export_format=rvc_params.get("export_format", "WAV"),
                resample_sr=0,
                sid=0,
            )
            elapsed = time.time() - t_file
            if os.path.isfile(out):
                size_kb = os.path.getsize(out) / 1024
                print(f"  [{i}/{total}] ✓ {basename} ({elapsed:.1f}s, {size_kb:.0f} KB)")
                success += 1
            else:
                print(f"  [{i}/{total}] ✗ {basename} — output not created ({elapsed:.1f}s)")
                errors += 1

        except Exception as e:
            elapsed = time.time() - t_file
            print(f"  [{i}/{total}] ✗ {basename} — {e} ({elapsed:.1f}s)")
            logging.error(f"{model['name']}|{basename}|{e}")
            errors += 1
            if os.path.isfile(out):
                try:
                    os.remove(out)
                except OSError:
                    pass

        # Progress bar
        pct = i / total
        filled = int(BAR_WIDTH * pct)
        bar = "█" * filled + "░" * (BAR_WIDTH - filled)
        total_elapsed = time.time() - t_start
        rate = i / total_elapsed if total_elapsed > 0 else 0
        eta_sec = (total - i) / rate if rate > 0 else 0
        eta_min = eta_sec / 60
        eta_str = f"{eta_min / 60:.1f}h" if eta_min >= 60 else f"{eta_min:.0f}min"
        print(f"  [{bar}] {pct * 100:5.1f}%  {i}/{total}  "
              f"{rate:.2f} f/s  ETA: {eta_str}", flush=True)

    total_elapsed = time.time() - t_start
    print(f"\n  Voice '{model['name']}' done — "
          f"{success} ok, {errors} errors, {total_elapsed:.1f}s total")

    return success, errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Golden Dataset — Multi-Voice RVC Deepfake Pipeline"
    )
    parser.add_argument("--full", action="store_true",
                        help="Process ALL files (default: test mode, 5 files)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Max files per voice model")
    parser.add_argument("--voice", type=str, default=None,
                        help="Process only this voice model (folder name)")
    parser.add_argument("--list-models", action="store_true",
                        help="List discovered models and exit")
    parser.add_argument("--input", type=str, default=None,
                        help="Override input directory (real audio)")
    parser.add_argument("--config", type=str, default=DEFAULT_CONFIG,
                        help="Path to config.yaml")
    args = parser.parse_args()

    # --- Load config ---
    if not os.path.isfile(args.config):
        print(f"[ERROR] Config not found: {args.config}")
        sys.exit(1)
    cfg = load_config(args.config)

    paths = cfg["paths"]
    rvc_params = cfg.get("rvc_defaults", {})
    active_filter = cfg.get("active_models", []) or None

    # Override with --voice if given
    if args.voice:
        active_filter = [args.voice]

    # --- Discover models ---
    models = discover_models(paths["models_dir"], active_filter)

    if args.list_models:
        print_models(models)
        sys.exit(0)

    if not models:
        print("[ERROR] No voice models found.")
        print(f"  Place .pth + .index files inside: {paths['models_dir']}/<voice_name>/")
        sys.exit(1)

    # --- Input dir ---
    input_dir = args.input or paths["real_audio_dir"]
    if not os.path.isdir(input_dir):
        print(f"[ERROR] Input directory not found: {input_dir}")
        print("  Run: .\\py\\python.exe scripts\\extract_corpus.py")
        sys.exit(1)

    # --- Determine limit ---
    if args.limit is not None:
        limit = args.limit
    elif args.full:
        limit = None
    else:
        limit = TEST_LIMIT
        print()
        print("*" * 60)
        print(f"  TEST MODE — Processing only {TEST_LIMIT} files per voice.")
        print("  Use --full to process all files after validation.")
        print("*" * 60)
        print()

    # --- Setup ---
    logging.basicConfig(
        filename=ERROR_LOG,
        level=logging.ERROR,
        format="%(asctime)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    rvc_engine_dir = paths["rvc_engine"]
    if not os.path.isdir(rvc_engine_dir):
        print(f"[ERROR] RVC Engine not found: {rvc_engine_dir}")
        print("  Run scripts\\setup_env.bat first.")
        sys.exit(1)

    # --- Run pipeline for each voice ---
    print(f"\n{'='*60}")
    print(f"  GOLDEN DATASET — MULTI-VOICE PIPELINE")
    print(f"  Voices:  {', '.join(m['name'] for m in models)}")
    print(f"  Input:   {input_dir}")
    print(f"  Mode:    {'FULL' if args.full else f'TEST ({limit} per voice)'}")
    print(f"{'='*60}")

    grand_success = 0
    grand_errors = 0
    t_grand = time.time()

    for idx, model in enumerate(models, 1):
        output_dir = os.path.join(paths["fake_audio_dir"], model["name"])

        print(f"\n{'─'*60}")
        print(f"  Voice [{idx}/{len(models)}]: {model['name']}")
        print(f"  Output: {output_dir}")
        print(f"{'─'*60}")

        pending = get_pending_files(input_dir, output_dir, limit)
        if pending:
            s, e = convert_voice(model, pending, rvc_params, rvc_engine_dir,
                                 not args.full)
            grand_success += s
            grand_errors += e
        else:
            print("  ✓ Nothing to process.\n")

    # --- Grand summary ---
    grand_elapsed = time.time() - t_grand
    print(f"\n{'='*60}")
    print(f"  PIPELINE COMPLETE")
    print(f"  Voices processed: {len(models)}")
    print(f"  Total converted:  {grand_success}")
    print(f"  Total errors:     {grand_errors}")
    print(f"  Total time:       {grand_elapsed:.1f}s ({grand_elapsed / 60:.1f} min)")
    if grand_errors > 0:
        print(f"  Error log:        {ERROR_LOG}")
    print(f"{'='*60}\n")

    if not args.full and grand_success > 0:
        print("  *** TEST MODE COMPLETE ***")
        print(f"  Check output in: {paths['fake_audio_dir']}")
        print("  If quality is acceptable, run again with --full:\n")
        print("    .\\py\\python.exe run_pipeline.py --full\n")


if __name__ == "__main__":
    main()
