"""
Tokens de identificação de dependências da camada de infraestrutura.

Tokens são strings que desacoplam o consumidor de uma dependência da sua
implementação concreta, permitindo substituição sem alterar o consumidor.

Exporta:
    Constantes string para cada dependência injetável do pipeline.

Utilizado por:
    - app.infrastructure.factory.PipelineFactory
"""

# Identificador do repositório de modelos de voz.
# Impacto: Alterar o token exige atualizar tanto o Factory quanto os consumidores.
MODEL_REPOSITORY: str = "MODEL_REPOSITORY"

# Identificador do repositório de arquivos de áudio.
AUDIO_REPOSITORY: str = "AUDIO_REPOSITORY"

# Identificador do provedor de conversão de voz via engine RVC.
VOICE_CONVERTER: str = "VOICE_CONVERTER"

# Identificador do serviço de atribuição de arquivos a modelos.
FILE_ASSIGNMENT_SERVICE: str = "FILE_ASSIGNMENT_SERVICE"

# Identificador do caso de uso principal do pipeline.
RUN_PIPELINE: str = "RUN_PIPELINE"

# Identificador do repositório de manifesto do golden dataset.
MANIFEST_REPOSITORY: str = "MANIFEST_REPOSITORY"
