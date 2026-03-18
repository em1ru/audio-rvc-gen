#!/usr/bin/env python3
"""
Golden Dataset — RVC v2 Batch Voice Conversion (Applio Engine)
==============================================================
Converts raw Common Voice WAV clips to Ronaldo's voice using
Applio's VoiceConverter on CPU.

Usage (via portable Python):
    .\py\python.exe run_ronaldo_batch.py            # Test mode (5 files)
    .\py\python.exe run_ronaldo_batch.py --full      # Full batch (all files)
    .\py\python.exe run_ronaldo_batch.py --limit 20  # Custom limit

Options:
    --full          Process all files (default: test mode, 5 files only)
    --limit N       Override file limit (default: 5 in test, all in full)
    --input DIR     Input directory (default: .\raw_cv_corpus)
    --output DIR    Output directory (default: .\output_rvc)
"""

import argparse
import glob
import logging
import os
import sys
import time

# ---------------------------------------------------------------------------
# Paths — all absolute, based on this script's directory
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.abspath(__file__))
RVC_ENGINE = os.path.join(ROOT, "rvc_engine")
MODEL_PATH = os.path.join(ROOT, "Ronaldo", "Ronaldo.pth")
INDEX_PATH = os.path.join(
    ROOT, "Ronaldo",
    "added_IVF370_Flat_nprobe_1_Ronaldo_v2.index"
)
DEFAULT_INPUT_DIR = os.path.join(ROOT, "raw_cv_corpus")
DEFAULT_OUTPUT_DIR = os.path.join(ROOT, "output_rvc")
ERROR_LOG = os.path.join(ROOT, "conversion_errors.log")

# RVC Quality Parameters (CPU-optimized)
F0_METHOD = "rmvpe"
INDEX_RATE = 0.75
PROTECT = 0.33
VOLUME_ENVELOPE = 0.25
HOP_LENGTH = 128
PITCH = 0

TEST_LIMIT = 5  # Default limit for test mode
BAR_WIDTH = 30  # Width of the progress bar in characters


def setup_applio():
    """Add Applio's rvc_engine to PYTHONPATH and set working directory."""
    if RVC_ENGINE not in sys.path:
        sys.path.insert(0, RVC_ENGINE)
    # Applio loads config JSONs from relative paths (rvc/configs/),
    # so we must set CWD to the engine root
    os.chdir(RVC_ENGINE)


def setup_logging():
    """Configure error logging to file."""
    logging.basicConfig(
        filename=ERROR_LOG,
        level=logging.ERROR,
        format="%(asctime)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def validate_paths(input_dir):
    """Check that all required files and directories exist."""
    errors = []
    if not os.path.isfile(MODEL_PATH):
        errors.append(f"Model not found: {MODEL_PATH}")
    if not os.path.isfile(INDEX_PATH):
        errors.append(f"Index not found: {INDEX_PATH}")
    if not os.path.isdir(RVC_ENGINE):
        errors.append(
            f"RVC Engine not found: {RVC_ENGINE}\n"
            f"  → Run setup_env.bat first."
        )
    if not os.path.isdir(input_dir):
        errors.append(
            f"Input directory not found: {input_dir}\n"
            f"  → Run extract_corpus.py first to extract Common Voice clips."
        )
    if errors:
        for e in errors:
            print(f"[ERROR] {e}")
        sys.exit(1)


def get_pending_files(input_dir: str, output_dir: str, limit: int = None):
    """
    Scan input directory for .wav files and filter out already-processed ones.
    Returns list of (input_path, output_path) tuples.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Get all input WAV files, sorted for deterministic order
    input_files = sorted(glob.glob(os.path.join(input_dir, "*.wav")))

    if not input_files:
        print(f"[ERROR] No .wav files found in {input_dir}")
        print(f"  → Run extract_corpus.py first.")
        sys.exit(1)

    # Build set of already-processed files for fast lookup
    existing = set(os.listdir(output_dir))

    # Filter to pending files only (checkpoint/resume)
    pending = []
    skipped = 0
    for inp in input_files:
        basename = os.path.basename(inp)
        if basename in existing:
            skipped += 1
            continue
        out = os.path.join(output_dir, basename)
        pending.append((inp, out))

    print(f"[INFO] Total input files:  {len(input_files)}")
    print(f"[INFO] Already processed:  {skipped}")
    print(f"[INFO] Pending:            {len(pending)}")

    # Apply limit
    if limit is not None and limit < len(pending):
        pending = pending[:limit]
        print(f"[INFO] Limited to:         {limit} files")

    return pending


def run_batch(pending, args):
    """Run Applio VoiceConverter inference on all pending files."""
    setup_applio()

    from rvc.infer.infer import VoiceConverter

    total = len(pending)
    if total == 0:
        print("\n[OK] Nothing to process — all files already converted!")
        return

    # Initialize VoiceConverter (auto-detects CPU)
    print(f"\n{'='*60}")
    print(f"  Loading Applio VoiceConverter...")
    print(f"  Model: {MODEL_PATH}")
    print(f"  Index: {INDEX_PATH}")
    print(f"  Device: CPU (auto-detected)")
    print(f"  F0 method: {F0_METHOD}")
    print(f"  Index rate: {INDEX_RATE}")
    print(f"{'='*60}\n")

    t_load = time.time()
    vc = VoiceConverter()
    print(f"[OK] VoiceConverter initialized in {time.time() - t_load:.1f}s\n")

    # Process files one by one
    success = 0
    errors = 0
    t_start = time.time()

    for i, (inp, out) in enumerate(pending, 1):
        basename = os.path.basename(inp)
        t_file = time.time()

        try:
            print(f"[{i}/{total}] Converting {basename}...", flush=True)
            vc.convert_audio(
                audio_input_path=inp,
                audio_output_path=out,
                model_path=MODEL_PATH,
                index_path=INDEX_PATH,
                pitch=PITCH,
                f0_method=F0_METHOD,
                index_rate=INDEX_RATE,
                volume_envelope=VOLUME_ENVELOPE,
                protect=PROTECT,
                hop_length=HOP_LENGTH,
                split_audio=False,
                f0_autotune=False,
                clean_audio=False,
                export_format="WAV",
                resample_sr=0,
                sid=0,
            )
            elapsed = time.time() - t_file
            # Check output was actually created
            if os.path.isfile(out):
                size_kb = os.path.getsize(out) / 1024
                print(f"  ✓ {elapsed:.1f}s ({size_kb:.0f} KB)")
                success += 1
            else:
                print(f"  ✗ Output not created ({elapsed:.1f}s)")
                errors += 1

        except Exception as e:
            elapsed = time.time() - t_file
            print(f"  ✗ FAILED ({elapsed:.1f}s) — {e}")
            logging.error(f"{basename} | {e}")
            errors += 1

            # Remove partial output if it was created
            if os.path.isfile(out):
                try:
                    os.remove(out)
                except OSError:
                    pass

        # --- Progress Bar ---
        pct = i / total
        filled = int(BAR_WIDTH * pct)
        bar = "█" * filled + "░" * (BAR_WIDTH - filled)
        total_elapsed = time.time() - t_start
        rate = i / total_elapsed if total_elapsed > 0 else 0
        eta_sec = (total - i) / rate if rate > 0 else 0
        eta_min = eta_sec / 60
        if eta_min >= 60:
            eta_str = f"{eta_min/60:.1f}h"
        else:
            eta_str = f"{eta_min:.0f}min"
        print(f"  [{bar}] {pct*100:5.1f}%  "
              f"{i}/{total}  "
              f"{rate:.2f} files/s  "
              f"ETA: {eta_str}",
              flush=True)

    # Summary
    total_elapsed = time.time() - t_start
    output_dir = os.path.dirname(out) if pending else DEFAULT_OUTPUT_DIR
    print(f"\n{'='*60}")
    print(f"  BATCH COMPLETE")
    print(f"  Total time:    {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)")
    print(f"  Successful:    {success}")
    print(f"  Errors:        {errors}")
    print(f"  Output dir:    {output_dir}")
    if errors > 0:
        print(f"  Error log:     {ERROR_LOG}")
    print(f"{'='*60}")

    if not args.full and success > 0:
        print(f"\n  *** TEST MODE COMPLETE ***")
        print(f"  Please listen to the {success} files in:")
        print(f"    {output_dir}")
        print(f"\n  If quality is acceptable, run again with --full:")
        print(f'    .\\py\\python.exe run_ronaldo_batch.py --full')
        print()


def main():
    parser = argparse.ArgumentParser(
        description="RVC v2 batch voice conversion — Ronaldo Fenômeno (Applio engine)"
    )
    parser.add_argument(
        "--full", action="store_true",
        help="Process ALL files (default: test mode with 5 files)"
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Override number of files to process"
    )
    parser.add_argument(
        "--input", type=str, default=DEFAULT_INPUT_DIR,
        help=f"Input directory with WAV files"
    )
    parser.add_argument(
        "--output", type=str, default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for converted files"
    )
    args = parser.parse_args()

    setup_logging()
    validate_paths(args.input)

    # Determine limit
    if args.limit is not None:
        limit = args.limit
    elif args.full:
        limit = None  # No limit
    else:
        limit = TEST_LIMIT
        print()
        print("*" * 60)
        print("  TEST MODE — Processing only first 5 files.")
        print("  Use --full to process all files after validation.")
        print("*" * 60)
        print()

    pending = get_pending_files(args.input, args.output, limit)
    run_batch(pending, args)


if __name__ == "__main__":
    main()
