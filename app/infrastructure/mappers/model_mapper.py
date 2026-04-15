"""
Mapeador de diretório do sistema de arquivos para a entidade VoiceModel.

Exporta:
    - ModelMapper (class): Traduz dados brutos de diretório para entidade VoiceModel.

Utilizado por:
    - app.infrastructure.repositories.model_repository.ModelRepository

Falhas de Domínio:
    - Retorna None (sem levantar exceção) se arquivos obrigatórios estiverem ausentes,
      delegando ao repositório a decisão de logar ou ignorar.
"""

import glob
import os
from typing import Optional

from app.core.entities.voice_model import VoiceModel


class ModelMapper:
    """
    Traduz dados brutos do sistema de arquivos para a entidade VoiceModel.

    Métodos Públicos:
        from_directory: Constrói um VoiceModel a partir de um diretório de modelo.

    Utilizado por:
        - app.infrastructure.repositories.model_repository.ModelRepository
    """

    @staticmethod
    def from_directory(model_dir: str, model_name: str) -> Optional[VoiceModel]:
        """
        Constrói um VoiceModel a partir do diretório de um modelo RVC.

        Args:
            model_dir (str): Caminho absoluto do diretório do modelo.
            model_name (str): Nome do modelo (nome da pasta em models/).

        Returns:
            VoiceModel: Entidade construída com os caminhos resolvidos.
            None: Se o diretório não contiver .pth ou .index válidos.
        """
        pth_files = glob.glob(os.path.join(model_dir, "*.pth"))
        index_files = glob.glob(os.path.join(model_dir, "*.index"))

        if not pth_files or not index_files:
            return None

        return VoiceModel(
            name=model_name,
            pth_path=pth_files[0],
            index_path=index_files[0],
        )
