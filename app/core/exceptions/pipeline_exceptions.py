"""
Exceções de domínio do pipeline de geração de deepfakes de voz.

Exporta:
    - PipelineError: base de todas as exceções do domínio.
    - ModelNotFoundError: diretório de modelos ausente ou vazio.
    - AudioInputError: diretório de áudio real ausente ou vazio.
    - ConfigNotFoundError: arquivo config.yaml não encontrado.
    - RvcEngineError: engine RVC não disponível ou não inicializável.
    - ConversionError: falha na conversão de um arquivo de áudio específico.

Utilizado por:
    - app.core.use_cases.run_pipeline_use_case
    - app.infrastructure.repositories.model_repository
    - app.infrastructure.repositories.audio_repository
    - app.infrastructure.providers.rvc_provider
    - app.app_module
"""


class PipelineError(Exception):
    """Erro base do pipeline — todas as exceções de domínio herdam desta."""


class ModelNotFoundError(PipelineError):
    """Levantada quando nenhum modelo de voz válido é encontrado no diretório configurado."""


class AudioInputError(PipelineError):
    """Levantada quando o diretório de áudio real está ausente ou não contém arquivos WAV."""


class ConfigNotFoundError(PipelineError):
    """Levantada quando o arquivo config.yaml não é encontrado no caminho esperado."""


class RvcEngineError(PipelineError):
    """Levantada quando o engine RVC não pode ser localizado ou inicializado."""


class ConversionError(PipelineError):
    """
    Levantada quando a conversão de um arquivo de áudio falha de forma irrecuperável.

    Atributos:
        model_name (str): Nome do modelo de voz que falhou.
        filename (str): Nome do arquivo de áudio que causou a falha.
        cause (Exception): Exceção original do engine RVC.
    """

    def __init__(self, model_name: str, filename: str, cause: Exception) -> None:
        super().__init__(
            f"Falha na conversão de '{filename}' pelo modelo '{model_name}': {cause}"
        )
        self.model_name = model_name
        self.filename = filename
        self.cause = cause
