# Contexto do Projeto — Para Claude

## O que é este projeto

Golden dataset de áudios para **avaliar detectores de deepfake de voz em PT-BR** (ExACTa-PUC). O objetivo é ter pares real/fake com diversidade de engines de síntese, para testar se um detector consegue distinguir voz humana de voz sintética.

## Estrutura do repo

```
pipeline/          # módulos do pipeline (config, audio, manifest, rvc, elevenlabs, runner, assignment)
scripts/           # scripts standalone de geração e importação
main.py            # CLI principal (--method rvc|elevenlabs, --strategy, --limit, etc.)
config.yaml        # configuração central (RVC defaults, ElevenLabs voices)
data/manifest.csv  # ground truth do dataset (commitado)
data/sentences.csv # transcrições dos WAVs reais do Common Voice PT (commitado)
```

## O que está no .gitignore (só na máquina local / drive do time)

| Path | Conteúdo | Tamanho |
|---|---|---|
| `data/real/` | 8.010 WAVs reais do Common Voice PT (16kHz mono) | ~grande |
| `data/fake/` | 9.503 WAVs sintéticos gerados | ~grande |
| `cv-corpus-24.0-2025-12-05-pt.tar.gz` | Corpus Common Voice PT completo | ~grande |
| `golden_audio (1).rar` | TTS gerado anteriormente (edge/google/gtts/polly) | 297 MB |
| `models/` | Modelos RVC v2: Lula, bolsonaro, ronaldo, rafaelbastos, silviosantos, defantecantando | ~grande |
| `rvc_engine/` | Applio RVC v2 (submódulo) | ~grande |
| `py/` | Python 3.10 portátil | ~grande |
| `.env` | API keys ElevenLabs (6 contas) | - |

## Estado atual do dataset (data/manifest.csv)

| Engine | Tipo | Arquivos |
|---|---|---|
| Common Voice PT | real | 8.010 |
| gTTS (Google Python) | tts | 2.000 |
| Amazon Polly | tts | 2.000 |
| Microsoft Edge TTS | tts | 1.999 |
| Google Cloud TTS | tts | 1.999 |
| ElevenLabs — 6 vozes (Sarah, Laura, Charlie, George, River, Callum) | tts | 1.505 |
| **Total** | | **17.513** |

VC (voice conversion) = 0 ainda.

## O que falta implementar (próximos passos)

### 1. XTTS-v2 (prioritário)
TTS neural local, zero-shot PT-BR, roda na GPU. Muito mais realista que os engines atuais. Implementar como `--method xtts` no pipeline ou script standalone em `scripts/generate_tts_xtts.py`. Instalar via `pip install TTS`.

### 2. Piper
TTS local, rápido, roda em CPU, múltiplas vozes PT-BR. Binário standalone, não precisa de GPU. Script standalone `scripts/generate_tts_piper.py`. Baixar em github.com/rhasspy/piper.

### 3. RVC (Voice Conversion)
Modelos já existem em `models/` (Lula, bolsonaro, ronaldo, rafaelbastos, silviosantos, defantecantando) e o engine está em `rvc_engine/`. O pipeline já suporta (`--method rvc`). Problema histórico: qualidade ruim nos modelos disponíveis. Testar com `.\py\python.exe main.py --method rvc --limit 5`.

### 4. ElevenLabs STS (Speech-to-Speech)
Pipeline já implementado em `pipeline/elevenlabs.py`. Bloqueado por `402 Payment Required` — requer plano pago (~$5/mês). Quando pago, rodar com `.\py\python.exe main.py --method elevenlabs`.

### 5. Channel degradation (simples, baixa prioridade)
Pegar WAVs gerados e aplicar degradação de codec (ffmpeg: encode opus/mp3 → decode de volta). Simula áudio transmitido por WhatsApp/telefone. Script ~30 linhas.

### 6. ElevenLabs — mais frases (mensal)
As 6 contas têm cota de 10k chars/mês cada. No início de cada mês rodar:
```bash
# ver scripts/generate_tts_elevenlabs.py e .env para as chaves e voice IDs
.\py\python.exe scripts\generate_tts_elevenlabs.py --api-key CHAVE --voice-id VOICE_ID --limit 250
```

## Como rodar o pipeline RVC

```bash
.\py\python.exe main.py --method rvc --limit 5          # teste
.\py\python.exe main.py --method rvc --full              # todos
.\py\python.exe main.py --list-models                    # ver modelos disponíveis
```

## Como gerar TTS ElevenLabs

```bash
.\py\python.exe scripts\prepare_sentences.py             # gera data/sentences.csv (só na 1ª vez)
.\py\python.exe scripts\generate_tts_elevenlabs.py --api-key CHAVE --voice-id VOICE_ID --limit 250
```

## Como importar o RAR de TTS antigo (se necessário reprocessar)

```bash
.\py\python.exe scripts\import_tts.py                    # extrai RAR, converte MP3→WAV, atualiza manifest
.\py\python.exe scripts\import_tts.py --dry-run          # simula sem alterar nada
```
