"""
Módulo raiz da aplicação — carrega configuração, configura logging e orquestra dependências.

Exporta:
    - AppModule (class): Ponto central de inicialização; único consumidor de main.py.

Dependências:
    - config.yaml: arquivo de configuração do pipeline (caminhos e parâmetros de backend).
    - PipelineFactory: conecta os componentes da infraestrutura no caso de uso.
    - PipelineController: recebe e interpreta os argumentos da CLI.

Utilizado por:
    - main.py (único consumidor)

Falhas de Domínio:
    - Levanta ConfigNotFoundError se config.yaml não for encontrado.
    - Levanta SystemExit se a configuração estiver malformada.
"""

import logging
import os
import sys
from typing import List

import yaml

from app.core.entities.elevenlabs_params import ElevenLabsParams
from app.core.entities.pipeline_config import PipelineConfig
from app.core.entities.rvc_params import RvcParams
from app.core.enums.f0_method import F0Method
from app.core.exceptions.pipeline_exceptions import ConfigNotFoundError
from app.infrastructure.factory import PipelineFactory
from app.presentation.controllers.pipeline_controller import PipelineController


# Diretório raiz do projeto (um nível acima de app/).
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Caminho padrão do arquivo de configuração.
_DEFAULT_CONFIG = os.path.join(_ROOT, "config.yaml")

# Caminho do log estruturado de erros de conversão por arquivo.
_ERROR_LOG = os.path.join(_ROOT, "conversion_errors.log")


class AppModule:
    """
    Módulo raiz: carrega configuração, configura logging e conecta todas as dependências.

    Determina o backend de conversão a partir do argumento --method (rvc ou elevenlabs)
    e instancia o pipeline correspondente via PipelineFactory.

    Métodos Públicos:
        start: Inicializa a aplicação e executa o pipeline via controlador.

    Utilizado por:
        - main.py

    Falhas de Domínio:
        - Levanta ConfigNotFoundError se config.yaml não existir no caminho esperado.
    """

    def start(self, argv: List[str]) -> None:
        """
        Inicializa o pipeline: carrega config, configura logging e executa o controlador.

        Args:
            argv (List[str]): Argumentos de linha de comando (normalmente sys.argv[1:]).

        Raises:
            ConfigNotFoundError: Se o config.yaml não for encontrado.
        """
        config_path = self._resolve_config_path(argv)
        config = self._load_config(config_path)
        self._setup_logging()

        method = self._resolve_method(argv)

        if method == "elevenlabs":
            use_case = PipelineFactory.create_elevenlabs_pipeline(config)
            conversion_params = config.elevenlabs_params
        else:
            use_case = PipelineFactory.create_rvc_pipeline(config)
            conversion_params = config.rvc_params

        controller = PipelineController(use_case, conversion_params)
        controller.execute(argv)

    def _resolve_config_path(self, argv: List[str]) -> str:
        """
        Extrai o caminho do config.yaml dos argumentos ou usa o caminho padrão.

        Args:
            argv (List[str]): Argumentos brutos da CLI.

        Returns:
            str: Caminho absoluto do config.yaml a utilizar.
        """
        for i, arg in enumerate(argv):
            if arg == "--config" and i + 1 < len(argv):
                return argv[i + 1]
        return _DEFAULT_CONFIG

    def _resolve_method(self, argv: List[str]) -> str:
        """
        Extrai o método de conversão dos argumentos ou retorna o padrão ('rvc').

        Args:
            argv (List[str]): Argumentos brutos da CLI.

        Returns:
            str: 'rvc' ou 'elevenlabs'.
        """
        for i, arg in enumerate(argv):
            if arg == "--method" and i + 1 < len(argv):
                return argv[i + 1]
        return "rvc"

    def _load_config(self, config_path: str) -> PipelineConfig:
        """
        Carrega e deserializa o config.yaml, retornando a entidade PipelineConfig.

        Args:
            config_path (str): Caminho absoluto do arquivo de configuração.

        Returns:
            PipelineConfig: Configuração validada com caminhos absolutos resolvidos.

        Raises:
            ConfigNotFoundError: Se o arquivo não existir.
        """
        if not os.path.isfile(config_path):
            raise ConfigNotFoundError(
                f"Arquivo de configuração não encontrado: {config_path}"
            )

        with open(config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        paths = raw.get("paths", {})
        rvc_raw = raw.get("rvc_defaults", {})
        elevenlabs_raw = raw.get("elevenlabs", {})

        def resolve(key: str, default: str = "") -> str:
            """Resolve caminho relativo em relação à raiz do projeto."""
            val = paths.get(key, default)
            if val and not os.path.isabs(val):
                return os.path.join(_ROOT, val)
            return val

        rvc_params = RvcParams(
            f0_method=F0Method(rvc_raw.get("f0_method", F0Method.RMVPE.value)),
            index_rate=float(rvc_raw.get("index_rate", 0.75)),
            protect=float(rvc_raw.get("protect", 0.33)),
            volume_envelope=float(rvc_raw.get("volume_envelope", 0.25)),
            hop_length=int(rvc_raw.get("hop_length", 128)),
            pitch=int(rvc_raw.get("pitch", 0)),
            export_format=rvc_raw.get("export_format", "WAV"),
        )

        elevenlabs_params = ElevenLabsParams(
            model_id=elevenlabs_raw.get("model_id", "eleven_multilingual_sts_v2"),
            output_format=elevenlabs_raw.get("output_format", "pcm_16000"),
        )

        elevenlabs_voices = elevenlabs_raw.get("voices", []) or []

        return PipelineConfig(
            models_dir=resolve("models_dir", "models"),
            real_audio_dir=resolve("real_audio_dir", "data/real"),
            fake_audio_dir=resolve("fake_audio_dir", "data/fake"),
            rvc_engine_dir=resolve("rvc_engine", "rvc_engine"),
            rvc_params=rvc_params,
            active_models=raw.get("active_models", []) or [],
            elevenlabs_params=elevenlabs_params,
            elevenlabs_voices=elevenlabs_voices,
        )

    def _setup_logging(self) -> None:
        """
        Configura handlers de logging para stdout (INFO+) e arquivo (erros de conversão).

        Formato do console: [LEVEL] contexto: mensagem (padrão ExACTa-PUC).
        Formato do arquivo: timestamp | model|file|error (estruturado para análise).
        """
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)

        # Handler de console: exibe INFO e acima no stdout
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(_PipelineFormatter())
        root_logger.addHandler(console_handler)

        # Handler de arquivo: registra apenas erros de conversão por arquivo
        error_handler = logging.FileHandler(_ERROR_LOG, encoding="utf-8")
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        error_logger = logging.getLogger("conversion_errors")
        error_logger.addHandler(error_handler)
        error_logger.propagate = False


class _PipelineFormatter(logging.Formatter):
    """
    Formata mensagens de log no padrão ExACTa-PUC: [LEVEL] contexto: mensagem.

    Utilizado por:
        - AppModule._setup_logging (handler de console)
    """

    _LABELS = {
        logging.DEBUG: "DEBUG",
        logging.INFO: "INFO",
        logging.WARNING: "WARNING",
        logging.ERROR: "ERROR",
        logging.CRITICAL: "CRITICAL",
    }

    def format(self, record: logging.LogRecord) -> str:
        """
        Formata o registro de log no padrão [LEVEL] contexto: mensagem.

        Args:
            record (logging.LogRecord): Registro de log a formatar.

        Returns:
            str: Mensagem formatada no padrão ExACTa-PUC.
        """
        level = self._LABELS.get(record.levelno, record.levelname)
        context = record.name.split(".")[-1]
        return f"[{level}] {context}: {record.getMessage()}"
