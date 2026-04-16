import os
from dataclasses import dataclass, field
from typing import List

import yaml


@dataclass
class RvcConfig:
    f0_method: str = "rmvpe"
    index_rate: float = 0.75
    protect: float = 0.33
    volume_envelope: float = 0.25
    hop_length: int = 128
    pitch: int = 0
    export_format: str = "WAV"


@dataclass
class ElevenLabsConfig:
    model_id: str = "eleven_multilingual_sts_v2"
    output_format: str = "pcm_16000"
    voices: List[dict] = field(default_factory=list)


@dataclass
class Config:
    models_dir: str
    real_audio_dir: str
    fake_audio_dir: str
    rvc_engine_dir: str
    rvc: RvcConfig
    elevenlabs: ElevenLabsConfig
    active_models: List[str] = field(default_factory=list)

    @property
    def manifest_path(self) -> str:
        return os.path.join(os.path.dirname(self.real_audio_dir), "manifest.csv")


def load(path: str) -> Config:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"config.yaml não encontrado: {path}")

    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    root = os.path.dirname(os.path.abspath(path))

    def resolve(rel):
        return os.path.join(root, rel) if rel and not os.path.isabs(rel) else rel

    p = raw.get("paths", {})
    r = raw.get("rvc_defaults", {})
    e = raw.get("elevenlabs", {})

    return Config(
        models_dir=resolve(p.get("models_dir", "models")),
        real_audio_dir=resolve(p.get("real_audio_dir", "data/real")),
        fake_audio_dir=resolve(p.get("fake_audio_dir", "data/fake")),
        rvc_engine_dir=resolve(p.get("rvc_engine", "rvc_engine")),
        rvc=RvcConfig(
            f0_method=r.get("f0_method", "rmvpe"),
            index_rate=float(r.get("index_rate", 0.75)),
            protect=float(r.get("protect", 0.33)),
            volume_envelope=float(r.get("volume_envelope", 0.25)),
            hop_length=int(r.get("hop_length", 128)),
            pitch=int(r.get("pitch", 0)),
            export_format=r.get("export_format", "WAV"),
        ),
        elevenlabs=ElevenLabsConfig(
            model_id=e.get("model_id", "eleven_multilingual_sts_v2"),
            output_format=e.get("output_format", "pcm_16000"),
            voices=e.get("voices", []) or [],
        ),
        active_models=raw.get("active_models", []) or [],
    )
