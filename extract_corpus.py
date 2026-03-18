#!/usr/bin/env python3
"""
Golden Dataset — Mozilla Common Voice Corpus Extractor
=====================================================
Extracts MP3 clips from the Common Voice tar.gz archive and converts
them to WAV (16 kHz, mono) for RVC inference.

Usage (via portable Python):
    .\py\python.exe extract_corpus.py [--limit N]

Options:
    --limit N   Only extract the first N clips (default: 8000)
"""

import argparse
import os
import sys
import tarfile
import time

# ---------------------------------------------------------------------------
# Paths — all relative to this script's directory
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.abspath(__file__))
ARCHIVE = os.path.join(ROOT, "cv-corpus-24.0-2025-12-05-pt.tar.gz")
OUTPUT_DIR = os.path.join(ROOT, "raw_cv_corpus")


def convert_mp3_to_wav(mp3_path: str, wav_path: str) -> bool:
    """Convert a single MP3 file to 16 kHz mono WAV using pydub."""
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_mp3(mp3_path)
        audio = audio.set_frame_rate(16000).set_channels(1)
        audio.export(wav_path, format="wav")
        return True
    except Exception as e:
        print(f"  [WARN] Failed to convert {os.path.basename(mp3_path)}: {e}")
        return False


def extract_and_convert(archive_path: str, output_dir: str, limit: int):
    """Stream-extract MP3 clips from the tar.gz and convert to WAV."""
    if not os.path.isfile(archive_path):
        print(f"[ERROR] Archive not found: {archive_path}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    # Count existing files to support resume
    existing = set(os.listdir(output_dir))
    print(f"[INFO] Found {len(existing)} existing files in {output_dir}")

    extracted = 0
    skipped = 0
    errors = 0
    t0 = time.time()

    print(f"[INFO] Opening archive: {archive_path}")
    print(f"[INFO] Extracting up to {limit} clips to: {output_dir}")
    print()

    # Temporary directory for intermediate MP3 files
    tmp_dir = os.path.join(ROOT, "_tmp_extract")
    os.makedirs(tmp_dir, exist_ok=True)

    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            for member in tar:
                if extracted >= limit:
                    break

                # Only process .mp3 files inside a clips/ directory
                if not member.isfile():
                    continue
                if not member.name.endswith(".mp3"):
                    continue
                if "/clips/" not in member.name and "\\clips\\" not in member.name:
                    continue

                # Derive output filename
                base_name = os.path.basename(member.name)
                wav_name = os.path.splitext(base_name)[0] + ".wav"

                # Skip if already converted (resume support)
                if wav_name in existing:
                    skipped += 1
                    continue

                # Extract MP3 to temp location
                try:
                    member_obj = tar.extractfile(member)
                    if member_obj is None:
                        continue

                    tmp_mp3 = os.path.join(tmp_dir, base_name)
                    with open(tmp_mp3, "wb") as f:
                        f.write(member_obj.read())

                    # Convert to WAV
                    wav_path = os.path.join(output_dir, wav_name)
                    if convert_mp3_to_wav(tmp_mp3, wav_path):
                        extracted += 1
                        if extracted % 100 == 0 or extracted <= 5:
                            elapsed = time.time() - t0
                            rate = extracted / elapsed if elapsed > 0 else 0
                            print(f"  [{extracted}/{limit}] {wav_name}  "
                                  f"({rate:.1f} files/sec)")
                    else:
                        errors += 1

                    # Cleanup temp MP3
                    os.remove(tmp_mp3)

                except Exception as e:
                    print(f"  [WARN] Error processing {member.name}: {e}")
                    errors += 1

    except Exception as e:
        print(f"[ERROR] Failed to open archive: {e}")
        sys.exit(1)
    finally:
        # Cleanup temp directory
        try:
            os.rmdir(tmp_dir)
        except OSError:
            pass

    elapsed = time.time() - t0
    print()
    print("=" * 60)
    print(f"  DONE in {elapsed:.1f}s")
    print(f"  Extracted & converted: {extracted}")
    print(f"  Skipped (already exist): {skipped}")
    print(f"  Errors: {errors}")
    print(f"  Total in {output_dir}: {len(os.listdir(output_dir))}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Extract Common Voice clips and convert to WAV"
    )
    parser.add_argument(
        "--limit", type=int, default=8000,
        help="Maximum number of clips to extract (default: 8000)"
    )
    parser.add_argument(
        "--archive", type=str, default=ARCHIVE,
        help=f"Path to tar.gz archive (default: {ARCHIVE})"
    )
    parser.add_argument(
        "--output", type=str, default=OUTPUT_DIR,
        help=f"Output directory for WAV files (default: {OUTPUT_DIR})"
    )
    args = parser.parse_args()

    extract_and_convert(args.archive, args.output, args.limit)


if __name__ == "__main__":
    main()
