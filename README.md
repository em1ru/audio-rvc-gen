# Golden Dataset — Deepfake Voice Generator

Pipeline para gerar um **golden dataset** de áudios deepfake a partir de vozes reais. Converte clipes do [Mozilla Common Voice](https://commonvoice.mozilla.org/) usando **RVC v2** (Applio Engine) e/ou **ElevenLabs speech-to-speech** para criar pares real/fake destinados à validação de detectores de áudio sintético.

## Estrutura

```
golden_dataset/
│
├── main.py                  # Ponto de entrada — CLI
├── config.yaml              # Configuração central
├── requirements.txt
├── .env                     # Chaves de API (não commitado)
│
├── pipeline/
│   ├── config.py            # Carrega config.yaml
│   ├── audio.py             # Lê WAVs reais, encontra pendentes
│   ├── assignment.py        # Distribui arquivos entre vozes
│   ├── manifest.py          # Lê e escreve o CSV ground truth
│   ├── rvc.py               # Conversão via Applio RVC v2
│   ├── elevenlabs.py        # Conversão via API ElevenLabs STS
│   └── runner.py            # Orquestra o pipeline completo
│
├── models/                  # Modelos RVC (um por subpasta)
│   └── <voz>/               # <modelo>.pth + <modelo>.index
│
├── data/
│   ├── real/                # Áudios reais (WAV 16 kHz mono)
│   ├── fake/                # Deepfakes gerados, por voz
│   └── manifest.csv         # Ground truth do dataset
│
├── scripts/
│   ├── setup_env.bat        # Instala Python portátil + dependências RVC
│   └── extract_corpus.py    # Extrai Common Voice → data/real/
│
├── rvc_engine/              # Submódulo Applio RVC v2
└── py/                      # Python 3.10 portátil (gerado pelo setup)
```

## Setup

```powershell
# 1. Instala o ambiente (Python portátil + RVC)
scripts\setup_env.bat

# 2. Instala dependências do pipeline
.\py\python.exe -m pip install -r requirements.txt

# 3. Extrai os áudios reais do Common Voice
.\py\python.exe scripts\extract_corpus.py
```

## Uso

```powershell
# Modo teste — 5 arquivos por voz (padrão)
.\py\python.exe main.py

# Lote completo
.\py\python.exe main.py --full

# ElevenLabs (requer ELEVENLABS_API_KEY no .env e plano pago)
.\py\python.exe main.py --method elevenlabs --full

# Apenas uma voz específica
.\py\python.exe main.py --voice ronaldo --limit 20

# Cross: cada áudio convertido por todas as vozes
.\py\python.exe main.py --strategy cross --full

# Listar modelos/vozes disponíveis
.\py\python.exe main.py --list-models
.\py\python.exe main.py --list-models --method elevenlabs
```

## Estratégias de Atribuição

| Estratégia | Comportamento | Total de conversões |
|---|---|---|
| `stratified` (padrão) | Round-robin — cada voz recebe ~1/N dos áudios | `total_real` |
| `cross` | Todos os áudios em todas as vozes | `total_real × N_vozes` |

## Configuração — RVC (`config.yaml`)

```yaml
rvc_defaults:
  f0_method: rmvpe        # rmvpe | fcpe | crepe | harvest
  index_rate: 0.75        # peso do índice FAISS (0.0–1.0)
  protect: 0.33           # proteção de consoantes (0.0–0.5)
  volume_envelope: 0.25
  hop_length: 128
  pitch: 0
```

## Configuração — ElevenLabs (`config.yaml` + `.env`)

```yaml
# config.yaml
elevenlabs:
  model_id: eleven_multilingual_sts_v2
  output_format: pcm_16000
  voices:
    - name: pt_voice_1
      voice_id: SEU_VOICE_ID
```

```env
# .env
ELEVENLABS_API_KEY=sua_chave_aqui
```

## Manifesto

Após cada execução, `data/manifest.csv` é atualizado com todas as entradas do dataset:

| Campo | Descrição |
|---|---|
| `filename` | Nome do arquivo WAV |
| `label` | `real` ou `fake` |
| `method` | `rvc`, `elevenlabs` ou vazio (reais) |
| `voice_model` | Nome da voz usada na conversão |
| `source_file` | Áudio real de origem |
| `generated_at` | Timestamp ISO 8601 |

## Logs

- **Console**: `INFO` / `WARNING` / `ERROR` em tempo real.
- **`conversion_errors.log`**: falhas por arquivo no formato `timestamp | voz | arquivo | erro`.

---

Projeto destinado a **pesquisa acadêmica** em detecção de deepfakes de voz — ExACTa-PUC.
