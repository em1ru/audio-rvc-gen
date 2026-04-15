# RVC Multi-Voice Deepfake Dataset Generator

Pipeline para gerar um **golden dataset** de áudios deepfake a partir de vozes reais. Converte clipes do [Mozilla Common Voice](https://commonvoice.mozilla.org/) usando múltiplos modelos **RVC v2** (via Applio Engine) para criar pares real/fake destinados ao treino de detectores de áudio sintético.

## Estrutura do Projeto

```text
golden_dataset/
├── main.py                  # Entry point da aplicação
├── config.yaml              # Configuração central (parâmetros RVC, caminhos)
├── requirements.txt         # Dependências diretas do projeto
│
├── app/                     # Código-fonte (Clean Architecture — ExACTa-PUC)
│   ├── app_module.py        # Módulo raiz: carrega config, injeta dependências
│   ├── core/                # Núcleo — sem dependências externas
│   │   ├── constants/       # Constantes configuráveis
│   │   ├── entities/        # VoiceModel, AudioFile, RvcParams, PipelineConfig...
│   │   ├── enums/           # AssignmentStrategy, F0Method
│   │   ├── exceptions/      # Exceções de domínio tipadas
│   │   ├── interfaces/      # Contratos (IModelRepository, IVoiceConverter...)
│   │   └── use_cases/       # RunPipelineUseCase
│   ├── presentation/        # Camada de interação com o usuário
│   │   ├── controllers/     # PipelineController (CLI → UseCase)
│   │   └── dtos/            # PipelineRequestDTO, PipelineResultDTO
│   └── infrastructure/      # Integrações externas
│       ├── factory.py       # Instancia e injeta dependências
│       ├── tokens.py        # Identificadores de dependências
│       ├── mappers/         # ModelMapper (filesystem → VoiceModel)
│       ├── providers/       # RvcProvider (wraps Applio VoiceConverter)
│       ├── repositories/    # ModelRepository, AudioRepository
│       └── services/        # FileAssignmentService (stratified / cross)
│
├── models/                  # Modelos de voz RVC (um por subpasta)
│   └── <nome_da_voz>/       # └── <modelo>.pth + <modelo>.index
│
├── data/
│   ├── real/                # Áudios reais (Common Voice, 16 kHz WAV mono)
│   └── fake/                # Deepfakes gerados, organizados por modelo
│       └── <nome_da_voz>/
│
├── scripts/
│   ├── setup_env.bat        # Bootstrap do ambiente Python portátil (Windows)
│   └── extract_corpus.py    # Extração do Common Voice → data/real/
│
├── rvc_engine/              # Submódulo Applio RVC v2 (engine de conversão)
└── py/                      # Python 3.10 portátil (gerado pelo setup_env.bat)
```

## Como Usar

### 1. Setup do Ambiente

```powershell
scripts\setup_env.bat
```

Instala um Python 3.10 portátil em `py/` com todas as dependências RVC. Não requer Python instalado no sistema.

### 2. Adicionar Modelos de Voz

Coloque os arquivos `.pth` e `.index` de cada modelo em `models/<nome_da_voz>/`:

```text
models/
├── ronaldo/
│   ├── Ronaldo.pth
│   └── added_IVF370_Flat_nprobe_1_Ronaldo_v2.index
└── lula/
    ├── Lula.pth
    └── Lula.index
```

### 3. Extrair Corpus de Áudios Reais

```powershell
.\py\python.exe scripts\extract_corpus.py             # 8.000 clipes (padrão)
.\py\python.exe scripts\extract_corpus.py --limit 100 # Amostra menor
```

### 4. Gerar Deepfakes

```powershell
# Listar modelos detectados
.\py\python.exe main.py --list-models

# Teste rápido (5 arquivos por voz, stratified)
.\py\python.exe main.py

# Apenas uma voz específica
.\py\python.exe main.py --voice ronaldo --limit 20

# Lote completo — stratified (total_fake ≈ total_real)
.\py\python.exe main.py --full

# Lote completo — cross (cada áudio convertido por todos os modelos)
.\py\python.exe main.py --strategy cross --full
```

## Estratégias de Atribuição

| Estratégia | Comportamento | Conversões totais |
|---|---|---|
| `stratified` (padrão) | Divide os áudios por round-robin entre os modelos | `total_real` |
| `cross` | Cada áudio é convertido por todos os modelos | `total_real × N_modelos` |

## Parâmetros RVC

Configuráveis via `config.yaml` na seção `rvc_defaults`:

| Parâmetro | Padrão | Descrição |
|---|---|---|
| `f0_method` | `rmvpe` | Algoritmo de extração de pitch (rmvpe, fcpe, crepe, harvest) |
| `index_rate` | `0.75` | Peso do índice FAISS na identidade vocal (0.0–1.0) |
| `protect` | `0.33` | Proteção de consoantes contra artefatos (0.0–0.5) |
| `volume_envelope` | `0.25` | Mistura de envelope de volume origem/destino (0.0–1.0) |
| `hop_length` | `128` | Tamanho do salto de quadro para extração de F0 |
| `pitch` | `0` | Deslocamento de pitch em semitons (0 = sem alteração) |

## Logs

- **Console**: mensagens `[INFO]` / `[WARNING]` / `[CRITICAL]` em tempo real.
- **`conversion_errors.log`**: registro estruturado de falhas por arquivo (`timestamp | modelo | arquivo | erro`).

## Performance (CPU Only)

~5–20 segundos por áudio. Para 8.000 arquivos com 6 modelos em estratégia `stratified` (~1.333 por modelo), estimar ~4–7 horas de CPU.

## Uso

Projeto destinado exclusivamente a **pesquisa em segurança cibernética** e detecção de mídias sintéticas.
