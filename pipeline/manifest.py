import csv
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from pipeline.audio import AudioFile, ConversionResult
from pipeline.config import RvcConfig


log = logging.getLogger(__name__)

_FIELDS = [
    "filename", "label", "method", "voice_model", "source_file",
    "f0_method", "index_rate", "protect", "volume_envelope",
    "hop_length", "pitch", "generated_at",
]


@dataclass(frozen=True)
class ManifestEntry:
    filename: str
    label: str            # "real" | "fake"
    method: str           # "" | "rvc" | "elevenlabs"
    voice_model: str
    source_file: str
    f0_method: str
    index_rate: Optional[float]
    protect: Optional[float]
    volume_envelope: Optional[float]
    hop_length: Optional[int]
    pitch: Optional[int]
    generated_at: str


def load(path: str) -> List[ManifestEntry]:
    if not os.path.isfile(path):
        return []
    entries = []
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            try:
                entries.append(ManifestEntry(
                    filename=row["filename"],
                    label=row["label"],
                    method=row["method"],
                    voice_model=row.get("voice_model", ""),
                    source_file=row.get("source_file", ""),
                    f0_method=row.get("f0_method", ""),
                    index_rate=float(row["index_rate"]) if row.get("index_rate") else None,
                    protect=float(row["protect"]) if row.get("protect") else None,
                    volume_envelope=float(row["volume_envelope"]) if row.get("volume_envelope") else None,
                    hop_length=int(row["hop_length"]) if row.get("hop_length") else None,
                    pitch=int(row["pitch"]) if row.get("pitch") else None,
                    generated_at=row.get("generated_at", ""),
                ))
            except (KeyError, ValueError) as e:
                log.warning(f"Linha ignorada no manifesto: {e}")
    log.info(f"{len(entries)} entradas carregadas de {path}")
    return entries


def save(path: str, entries: List[ManifestEntry]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_FIELDS)
        w.writeheader()
        for e in entries:
            w.writerow({
                "filename": e.filename,
                "label": e.label,
                "method": e.method,
                "voice_model": e.voice_model,
                "source_file": e.source_file,
                "f0_method": e.f0_method,
                "index_rate": "" if e.index_rate is None else e.index_rate,
                "protect": "" if e.protect is None else e.protect,
                "volume_envelope": "" if e.volume_envelope is None else e.volume_envelope,
                "hop_length": "" if e.hop_length is None else e.hop_length,
                "pitch": "" if e.pitch is None else e.pitch,
                "generated_at": e.generated_at,
            })
    log.info(f"Manifesto salvo: {len(entries)} entradas em {path}")


def update(
    path: str,
    source_paths: List[str],
    results: List[ConversionResult],
    method: str,
    rvc_cfg: Optional[RvcConfig] = None,
) -> None:
    existing = load(path)
    keys = {(e.filename, e.voice_model) for e in existing}
    new_entries: List[ManifestEntry] = []

    for p in source_paths:
        filename = os.path.basename(p)
        if (filename, "") not in keys:
            new_entries.append(ManifestEntry(
                filename=filename, label="real", method="",
                voice_model="", source_file="", f0_method="",
                index_rate=None, protect=None, volume_envelope=None,
                hop_length=None, pitch=None, generated_at="",
            ))

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for result in results:
        for af in result.converted_files:
            if (af.filename, result.voice_name) in keys:
                continue
            if method == "rvc" and rvc_cfg:
                new_entries.append(ManifestEntry(
                    filename=af.filename, label="fake", method="rvc",
                    voice_model=result.voice_name,
                    source_file=os.path.basename(af.source_path),
                    f0_method=rvc_cfg.f0_method,
                    index_rate=rvc_cfg.index_rate, protect=rvc_cfg.protect,
                    volume_envelope=rvc_cfg.volume_envelope,
                    hop_length=rvc_cfg.hop_length, pitch=rvc_cfg.pitch,
                    generated_at=now,
                ))
            else:
                new_entries.append(ManifestEntry(
                    filename=af.filename, label="fake", method=method,
                    voice_model=result.voice_name,
                    source_file=os.path.basename(af.source_path),
                    f0_method="", index_rate=None, protect=None,
                    volume_envelope=None, hop_length=None, pitch=None,
                    generated_at=now,
                ))

    if not new_entries:
        log.info("Manifesto: nenhuma nova entrada.")
        return

    all_entries = existing + new_entries
    save(path, all_entries)
    reals = sum(1 for e in all_entries if e.label == "real")
    fakes = sum(1 for e in all_entries if e.label == "fake")
    log.info(f"Manifesto: {reals} reais, {fakes} fakes (+{len(new_entries)} novos).")
