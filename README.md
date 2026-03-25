# RVC Multi-Voice Deepfake Dataset Generator

Pipeline para gerar um **golden dataset** de áudios deepfake a partir de vozes reais. Converte clipes do [Mozilla Common Voice](https://commonvoice.mozilla.org/) usando múltiplos modelos **RVC v2** (via Applio Engine) para criar pares real/fake para treino de detectores.

## Estrutura do Projeto

```text
golden_dataset/
├── run_pipeline.py          # Script principal — multi-voice batch conversion
├── config.yaml              # Configuração central (parâmetros RVC, caminhos)
│
├── models/                  # Modelos de voz RVC (um por subpasta)
│   ├── ronaldo/             #   └── .pth + .index
│   └── <outra_voz>/         #   └── .pth + .index
│
├── data/
│   ├── real/                # Áudios reais (Common Voice, 16kHz WAV)
│   └── fake/                # Áudios gerados, organizados por voz
│       ├── ronaldo/
│       └── <outra_voz>/
│
├── scripts/
│   ├── setup_env.bat        # Bootstrap do ambiente portátil
│   └── extract_corpus.py    # Extração do Common Voice → data/real/
│
├── rvc_engine/              # Applio RVC engine (gerado no setup)
└── py/                      # Python 3.10 portátil (gerado no setup)
```

## Como Usar

### 1. Setup do Ambiente

```powershell
scripts\setup_env.bat
```

### 2. Adicionar Modelos de Voz

Coloque os arquivos `.pth` e `.index` de cada modelo dentro de `models/<nome_da_voz>/`:

```text
models/
├── ronaldo/
│   ├── Ronaldo.pth
│   └── added_IVF370_Flat_nprobe_1_Ronaldo_v2.index
├── lula/
│   ├── Lula.pth
│   └── Lula.index
└── trump/
    ├── Trump.pth
    └── Trump.index
```

### 3. Extrair Corpus de Áudios Reais

```powershell
.\py\python.exe scripts\extract_corpus.py            # 8000 clipes
.\py\python.exe scripts\extract_corpus.py --limit 100 # Amostra menor
```

### 4. Gerar Deepfakes

```powershell
# Listar modelos detectados
.\py\python.exe run_pipeline.py --list-models

# Teste rápido (5 arquivos por voz)
.\py\python.exe run_pipeline.py

# Apenas uma voz específica
.\py\python.exe run_pipeline.py --voice ronaldo --limit 20

# Processamento completo (todas as vozes, todos os áudios)
.\py\python.exe run_pipeline.py --full
```

## Parâmetros RVC

Configuráveis via `config.yaml`:

| Parâmetro | Padrão | Descrição |
|-----------|--------|-----------|
| `f0_method` | `rmvpe` | Método de extração de pitch |
| `index_rate` | `0.75` | Taxa de influência do index |
| `protect` | `0.33` | Proteção de consoantes |
| `hop_length` | `128` | Hop length |
| `pitch` | `0` | Ajuste de pitch (semitons) |

## Performance (CPU Only)

~5-20 segundos por áudio, dependendo da duração. Para 8.000 arquivos × N vozes, estimar ~20h × N.

## Licença e Uso

Projeto exclusivo para **pesquisa em segurança cibernética** e detecção de mídias sintéticas.