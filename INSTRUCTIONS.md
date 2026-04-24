# Como Contribuir com Áudios TTS — ElevenLabs

Ajude a expandir o golden dataset gerando áudios sintéticos gratuitos.
Cada conta ElevenLabs gratuita gera ~250 frases (10.000 chars/mês).

---

## Pré-requisitos

- Python 3.10+ instalado (ou use o `py/` do projeto)
- Git com acesso ao repositório
- ~500 MB livres em disco

---

## Passo a Passo

### 1. Clone o repositório

```bash
git clone <URL_DO_REPO>
cd golden_dataset
```

### 2. Instale as dependências

```bash
py\python.exe -m pip install -r requirements.txt
```

### 3. Crie uma conta ElevenLabs gratuita

1. Acesse [elevenlabs.io](https://elevenlabs.io) e crie uma conta
2. Vá em **Profile → API Keys → Create API Key**
3. Copie a chave gerada (ex: `sk_abc123...`)

### 4. Escolha uma voz

No painel ElevenLabs, vá em **Voices** e copie o `Voice ID` de uma voz que queira usar.

Vozes recomendadas (multilingual, funcionam bem em PT-BR):

| Nome    | Voice ID                   |
|---------|---------------------------|
| Sarah   | EXAVITQu4vr4xnSDxMaL      |
| Laura   | FGY2WhTYpPnrIDTdsKH5      |
| Charlie | IKne3meq5aSn9XLyUdCD      |
| George  | JBFqnCBsd6RMkjVDRZzb      |
| Roger   | CwhRBWXzGAHq8TQ4Fs17      |

> Use uma voz diferente de quem já contribuiu para maximizar a diversidade.

### 5. Prepare as frases (apenas na primeira vez)

```bash
py\python.exe scripts\prepare_sentences.py
```

Isso gera `data/sentences.csv` com as transcrições dos áudios reais.

### 6. Simule antes de rodar (opcional)

```bash
py\python.exe scripts\generate_tts_elevenlabs.py ^
    --api-key SUA_KEY ^
    --voice-id VOICE_ID ^
    --dry-run
```

### 7. Gere os áudios

```bash
py\python.exe scripts\generate_tts_elevenlabs.py ^
    --api-key SUA_KEY ^
    --voice-id VOICE_ID ^
    --limit 250
```

O script gera os WAVs em `data/fake/elevenlabs_<primeiros 8 chars do voice_id>/`
e registra tudo no `data/manifest.csv` automaticamente.

### 8. Comprima e envie os dados

```bash
# Comprime apenas os novos WAVs gerados (substitua VOICE_ID pelos primeiros 8 chars)
7z a tts_elevenlabs_VOICE_ID.7z data\fake\elevenlabs_VOICE_ID\
```

Envie o arquivo `.7z` + o `data/manifest.csv` atualizado para o responsável do projeto.

---

## Dúvidas frequentes

**Posso usar qualquer voz?**
Sim, desde que seja uma voz premade do free tier. Vozes de biblioteca (clonadas) requerem plano pago.

**O que acontece se acabar a cota?**
O script para e registra o erro. Os arquivos já gerados ficam salvos. Você pode continuar no mês seguinte ou com outra conta.

**Posso rodar em partes?**
Sim. O script detecta o que já foi gerado e pula automaticamente. Basta rodar novamente.

**Por que usar as mesmas frases dos áudios reais?**
Para criar um dataset paralelo: mesma frase, voz real vs. voz sintética. Isso é muito mais útil para avaliar detectores de deepfake.
