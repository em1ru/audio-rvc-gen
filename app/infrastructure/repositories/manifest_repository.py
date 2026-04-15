"""
Repositório de manifesto — lê e escreve o CSV de ground truth do golden dataset.

Exporta:
    - ManifestRepository (class): Implementação de IManifestRepository via CSV.

Dependências externas:
    - Sistema de arquivos: data/manifest.csv (criado automaticamente na primeira escrita).

Utilizado por:
    - app.infrastructure.factory.PipelineFactory
    - app.core.use_cases.run_pipeline_use_case.RunPipelineUseCase (via interface)

Falhas de Domínio:
    - Erros de leitura de linhas malformadas são logados e ignorados (não interrompem o pipeline).
"""

import csv
import logging
import os
from typing import List

from app.core.entities.manifest_entry import ManifestEntry, ManifestLabel, ManifestMethod
from app.core.interfaces.manifest_repository_interface import IManifestRepository


_log = logging.getLogger(__name__)

# Cabeçalho canônico do CSV do manifesto.
# Impacto: Alterar a ordem ou nomes quebra a compatibilidade com manifestos existentes.
_CSV_FIELDS = [
    "filename",
    "label",
    "method",
    "voice_model",
    "source_file",
    "f0_method",
    "index_rate",
    "protect",
    "volume_envelope",
    "hop_length",
    "pitch",
    "generated_at",
]


class ManifestRepository(IManifestRepository):
    """
    Lê e escreve o manifesto CSV do golden dataset de forma incremental.

    O arquivo é persistido em `data/manifest.csv`. Cada execução do pipeline
    acumula novas entradas sem duplicar as já existentes (deduplicação por filename).

    Atributos:
        _manifest_path (str): Caminho absoluto do arquivo CSV do manifesto.

    Métodos Públicos:
        load: Carrega entradas existentes do CSV.
        save: Persiste a lista completa de entradas, sobrescrevendo o arquivo.

    Utilizado por:
        - app.infrastructure.factory.PipelineFactory (instanciação)
        - app.core.use_cases.run_pipeline_use_case.RunPipelineUseCase (via injeção)
    """

    def __init__(self, manifest_path: str) -> None:
        self._manifest_path = manifest_path

    def load(self) -> List[ManifestEntry]:
        """
        Carrega as entradas existentes do manifesto CSV.

        Returns:
            List[ManifestEntry]: Entradas previamente salvas;
                lista vazia se o arquivo não existir.
        """
        if not os.path.isfile(self._manifest_path):
            return []

        entries: List[ManifestEntry] = []
        with open(self._manifest_path, "r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                try:
                    entries.append(self._deserialize(row))
                except (KeyError, ValueError) as exc:
                    _log.warning(f"Linha malformada ignorada no manifesto: {exc}")

        _log.info(f"{len(entries)} entrada(s) carregada(s) de {self._manifest_path}")
        return entries

    def save(self, entries: List[ManifestEntry]) -> None:
        """
        Persiste a lista completa de entradas no manifesto CSV.

        Args:
            entries (List[ManifestEntry]): Lista completa de entradas a gravar.
        """
        os.makedirs(os.path.dirname(self._manifest_path), exist_ok=True)

        with open(self._manifest_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=_CSV_FIELDS)
            writer.writeheader()
            for entry in entries:
                writer.writerow(self._serialize(entry))

        _log.info(
            f"Manifesto salvo: {len(entries)} entrada(s) em {self._manifest_path}"
        )

    def _serialize(self, entry: ManifestEntry) -> dict:
        """
        Converte uma ManifestEntry para dicionário compatível com csv.DictWriter.

        Args:
            entry (ManifestEntry): Entrada a serializar.

        Returns:
            dict: Representação em strings para escrita CSV.
        """
        return {
            "filename": entry.filename,
            "label": entry.label.value,
            "method": entry.method.value,
            "voice_model": entry.voice_model,
            "source_file": entry.source_file,
            "f0_method": entry.f0_method,
            "index_rate": "" if entry.index_rate is None else str(entry.index_rate),
            "protect": "" if entry.protect is None else str(entry.protect),
            "volume_envelope": "" if entry.volume_envelope is None else str(entry.volume_envelope),
            "hop_length": "" if entry.hop_length is None else str(entry.hop_length),
            "pitch": "" if entry.pitch is None else str(entry.pitch),
            "generated_at": entry.generated_at,
        }

    def _deserialize(self, row: dict) -> ManifestEntry:
        """
        Converte uma linha do CSV para ManifestEntry.

        Args:
            row (dict): Linha do CSV como dicionário.

        Returns:
            ManifestEntry: Entidade reconstruída.

        Raises:
            ValueError: Se campos obrigatórios estiverem ausentes ou inválidos.
        """
        return ManifestEntry(
            filename=row["filename"],
            label=ManifestLabel(row["label"]),
            method=ManifestMethod(row["method"]),
            voice_model=row.get("voice_model", ""),
            source_file=row.get("source_file", ""),
            f0_method=row.get("f0_method", ""),
            index_rate=float(row["index_rate"]) if row.get("index_rate") else None,
            protect=float(row["protect"]) if row.get("protect") else None,
            volume_envelope=float(row["volume_envelope"]) if row.get("volume_envelope") else None,
            hop_length=int(row["hop_length"]) if row.get("hop_length") else None,
            pitch=int(row["pitch"]) if row.get("pitch") else None,
            generated_at=row.get("generated_at", ""),
        )
