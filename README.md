RVC Deepfake Dataset Generator
Pipeline para geração de dataset voltado ao treinamento e validação de detectores de deepfake de áudio. O sistema converte áudios reais do Mozilla Common Voice (Português) para a voz do Ronaldo Fenômeno utilizando a arquitetura RVC v2.

Estrutura do Projeto
Plaintext
golden_dataset/
├── setup_env.bat        # Configuração do ambiente portátil
├── extract_corpus.py    # Extração e conversão de MP3 para WAV
├── run_ronaldo_batch.py # Script de inferência em lote
├── Ronaldo/             # Pesos (.pth) e Index (.index) do modelo
├── py/                  # Python 3.10 portátil (criado no setup)
├── rvc_engine/          # Núcleo do Applio RVC
├── raw_cv_corpus/       # Base de áudios reais (WAV 16kHz)
└── output_rvc/          # Base de áudios sintéticos (Voz do Ronaldo)
Guia de Execução
Pré-requisitos
Windows 10/11 (64-bit)

Espaço em disco: ~15 GB

Nota: O pipeline foi otimizado para CPU. Não é necessária GPU NVIDIA.

1. Configuração do Ambiente
Execute o script de bootstrap para baixar o Python portátil e as dependências (PyTorch CPU, Applio Engine e modelos base RMVPE/ContentVec).

Code snippet
setup_env.bat
2. Extração do Corpus
Converte os clipes do arquivo .tar.gz original para WAV (16kHz mono). O script suporta retomada automática (resume).

Code snippet
.\py\python.exe extract_corpus.py
Para um teste rápido: .\py\python.exe extract_corpus.py --limit 100

3. Conversão em Lote (Inference)
Inicia o processo de conversão de voz.

Code snippet
# Modo teste (processa apenas 5 arquivos)
.\py\python.exe run_ronaldo_batch.py 

# Processamento completo (8.000 arquivos)
.\py\python.exe run_ronaldo_batch.py --full
Detalhes Técnicos
Configurações de Inferência
Método F0: RMVPE (Equilíbrio entre carga de CPU e qualidade de pitch)

Index Rate: 0.75

Filtro de Proteção: 0.33

Device: CPU (Inferência estável via PyTorch)

Performance Estimada (CPU)
Tempo por áudio: 5 a 20 segundos (variando conforme duração do clipe)

Estimativa total: ~18 horas para 8.000 arquivos.

Retomada: O script verifica a existência do arquivo em output_rvc/ antes de processar, permitindo interromper e continuar o processo a qualquer momento.

Dataset Gerado
Ao final do processamento, o dataset terá duas pastas pareadas com os mesmos nomes de arquivos:

raw_cv_corpus/: Vozes originais (Ground Truth / Real)

output_rvc/: Vozes convertidas (Deepfake / Fake)

Licença e Uso
Projeto destinado exclusivamente para fins de pesquisa em segurança cibernética e detecção de mídias sintéticas.

O que fazer agora?
Para atualizar o seu GitHub com esse README novo e limpo:

Salve o arquivo.

No terminal:

PowerShell
git add README.md
git commit -m "docs: cleanup readme and remove emojis"
git push origin main