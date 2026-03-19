# RVC Deepfake Dataset Generator

Este projeto implementa um pipeline completo para a criação de um dataset de alta fidelidade voltado ao treinamento e validação de detectores de deepfake de áudio. O sistema utiliza a arquitetura **RVC v2** (via Applio Engine) para converter áudios reais do [Mozilla Common Voice](https://commonvoice.mozilla.org/) (Português) para a voz do **Ronaldo Fenômeno**.

## Estrutura do Projeto

O diretório está organizado da seguinte forma:

```text
golden_dataset/
├── setup_env.bat          # Script de bootstrap do ambiente portátil
├── extract_corpus.py      # Extração e conversão de MP3 para WAV (16kHz)
├── run_ronaldo_batch.py   # Script principal de inferência em lote
├── Ronaldo/               # Pesos (.pth) e Index (.index) do modelo RVC
├── rvc_engine/            # Núcleo do processador Applio RVC (RVC-CLI)
├── py/                    # Python 3.10 portátil (gerado automaticamente no setup)
├── raw_cv_corpus/         # Diretório de áudios reais (Target: 8.000 arquivos)
└── output_rvc/            # Diretório de áudios sintéticos (Voz do Ronaldo)
```

## Guia de Execução

### Pré-requisitos
- **Sistema Operacional:** Windows 10/11 (64-bit)
- **Espaço em Disco:** Mínimo de 15 GB (incluindo o arquivo `.tar.gz`)
- **Hardware:** O pipeline foi otimizado para **CPU**. Não é necessária GPU NVIDIA.

### 1. Configuração do Ambiente
Execute o script de bootstrap para baixar o Python portátil e as dependências (PyTorch CPU, Applio Engine e modelos de base RMVPE/ContentVec).

```powershell
.\setup_env.bat
```

### 2. Extração do Corpus
Este script extrai os clipes do arquivo `cv-corpus-24.0-2025-12-05-pt.tar.gz` original e os converte para WAV (16kHz mono). O processo suporta retomada automática (resume).

```powershell
.\py\python.exe extract_corpus.py
```
*Dica: Use `--limit 100` para extrair apenas uma amostra inicial.*

### 3. Conversão em Lote (Inference)
Inicia o processo de conversão de voz utilizando o modelo do Ronaldo. O script verifica arquivos já processados para evitar retrabalho.

**Modo Teste (processa apenas 5 arquivos):**
```powershell
.\py\python.exe run_ronaldo_batch.py
```

**Processamento Completo (todos os arquivos extraídos):**
```powershell
.\py\python.exe run_ronaldo_batch.py --full
```

## Detalhes técnicos

A inferência utiliza as seguintes configurações para garantir qualidade e estabilidade:

- **Método F0:** `rmvpe` (Equilíbrio ideal entre carga de CPU e precisão de pitch)
- **Index Rate:** `0.75`
- **Filtro de Proteção:** `0.33`
- **Audio Output:** 16kHz, WAV Mono

### Performance (CPU Only)
O tempo de processamento varia entre 5 a 20 segundos por áudio, dependendo da duração do clipe. Para o dataset completo de 8.000 arquivos, a estimativa total é de aproximadamente 18 a 20 horas de execução contínua.

## Licença e Uso

Este projeto é destinado exclusivamente para fins de **pesquisa em segurança cibernética** e detecção de mídias sintéticas. O objetivo é fortalecer as defesas contra ataques de engenharia social baseados em voz.