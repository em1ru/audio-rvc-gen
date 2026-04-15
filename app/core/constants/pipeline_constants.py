"""
Constantes de configuração do pipeline de geração do golden dataset.

Exporta:
    - TEST_LIMIT: número de arquivos processados no modo de teste.

Utilizado por:
    - app.presentation.controllers.pipeline_controller
"""

# Número máximo de arquivos processados por modelo de voz no modo de teste.
# Impacto: Reduzir acelera a validação; aumentar valida mais amostras antes do modo completo.
# Restrição: Deve ser pequeno o suficiente para completar em minutos (recomendado < 10).
TEST_LIMIT: int = 5
