"""
Utilitário de extração do corpus Mozilla Common Voice.

Extrai clipes MP3 do arquivo tar.gz do Common Voice e os converte para
WAV (16 kHz, mono) prontos para uso como entrada do pipeline RVC.

Exporta:
    - extract_and_convert (func): Extração e conversão em stream do corpus.
    - convert_mp3_to_wav (func): Conversão de um único MP3 para WAV.

Dependências:
    - pydub: conversão de MP3 para WAV.
    - ffmpeg ou libav: backend de decodificação de áudio (requerido pelo pydub).

Utilizado por:
    - Executado diretamente via CLI antes do pipeline principal.

Falhas de Domínio:
    - Levanta SystemExit(1) se o arquivo tar.gz não for encontrado.
    - Levanta SystemExit(1) se o arquivo não puder ser aberto.
"""

import argparse
import logging
import os
import sys
import tarfile
import time


_log = logging.getLogger(__name__)

# Diretório do script e raiz do projeto.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_SCRIPT_DIR)

# Caminho padrão do arquivo tar.gz do Common Voice (Portuguese 24.0).
_DEFAULT_ARCHIVE = os.path.join(_ROOT, "cv-corpus-24.0-2025-12-05-pt.tar.gz")

# Diretório de saída padrão dos arquivos WAV convertidos.
_DEFAULT_OUTPUT = os.path.join(_ROOT, "data", "real")


def convert_mp3_to_wav(mp3_path: str, wav_path: str) -> bool:
    """
    Converte um único arquivo MP3 para WAV a 16 kHz mono via pydub.

    Args:
        mp3_path (str): Caminho absoluto do arquivo MP3 de entrada.
        wav_path (str): Caminho absoluto do arquivo WAV de saída.

    Returns:
        bool: True se a conversão foi bem-sucedida; False em caso de erro.
    """
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_mp3(mp3_path)
        audio = audio.set_frame_rate(16000).set_channels(1)
        audio.export(wav_path, format="wav")
        return True
    except Exception as exc:
        _log.warning(f"Falha na conversão de {os.path.basename(mp3_path)}: {exc}")
        return False


def extract_and_convert(archive_path: str, output_dir: str, limit: int) -> None:
    """
    Extrai clipes MP3 em stream do tar.gz e converte para WAV (16 kHz mono).

    Args:
        archive_path (str): Caminho absoluto do arquivo tar.gz do Common Voice.
        output_dir (str): Diretório de saída para os arquivos WAV convertidos.
        limit (int): Número máximo de clipes a extrair e converter.

    Raises:
        SystemExit: Com código 1 se o arquivo tar.gz não for encontrado ou
            não puder ser aberto.
    """
    if not os.path.isfile(archive_path):
        _log.critical(f"Arquivo não encontrado: {archive_path}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    existing = set(os.listdir(output_dir))
    _log.info(f"{len(existing)} arquivo(s) já existente(s) em {output_dir}")
    _log.info(f"Abrindo arquivo: {archive_path}")
    _log.info(f"Extraindo até {limit} clipes para: {output_dir}")

    extracted = 0
    skipped = 0
    errors = 0
    t_start = time.time()

    tmp_dir = os.path.join(_ROOT, "_tmp_extract")
    os.makedirs(tmp_dir, exist_ok=True)

    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            for member in tar:
                if extracted >= limit:
                    break
                if not member.isfile():
                    continue
                if not member.name.endswith(".mp3"):
                    continue
                if "/clips/" not in member.name and "\\clips\\" not in member.name:
                    continue

                base_name = os.path.basename(member.name)
                wav_name = os.path.splitext(base_name)[0] + ".wav"

                if wav_name in existing:
                    skipped += 1
                    continue

                try:
                    member_obj = tar.extractfile(member)
                    if member_obj is None:
                        continue

                    tmp_mp3 = os.path.join(tmp_dir, base_name)
                    with open(tmp_mp3, "wb") as f:
                        f.write(member_obj.read())

                    wav_path = os.path.join(output_dir, wav_name)
                    if convert_mp3_to_wav(tmp_mp3, wav_path):
                        extracted += 1
                        if extracted % 100 == 0 or extracted <= 5:
                            elapsed = time.time() - t_start
                            rate = extracted / elapsed if elapsed > 0 else 0
                            _log.info(
                                f"[{extracted}/{limit}] {wav_name} ({rate:.1f} arq/s)"
                            )
                    else:
                        errors += 1

                    os.remove(tmp_mp3)

                except Exception as exc:
                    _log.warning(f"Erro ao processar {member.name}: {exc}")
                    errors += 1

    except Exception as exc:
        _log.critical(f"Falha ao abrir o arquivo: {exc}")
        sys.exit(1)

    finally:
        try:
            os.rmdir(tmp_dir)
        except OSError:
            pass

    elapsed = time.time() - t_start
    _log.info(
        f"Concluído em {elapsed:.1f}s — "
        f"extraídos: {extracted}, "
        f"ignorados: {skipped}, "
        f"erros: {errors}, "
        f"total em {output_dir}: {len(os.listdir(output_dir))}"
    )


def main() -> None:
    """Configura logging, analisa argumentos e executa a extração do corpus."""
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format="[%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Extrai clipes do Common Voice e converte para WAV (16 kHz mono)"
    )
    parser.add_argument(
        "--limit", type=int, default=8000,
        help="Número máximo de clipes a extrair (padrão: 8000)",
    )
    parser.add_argument(
        "--archive", type=str, default=_DEFAULT_ARCHIVE,
        help=f"Caminho do arquivo tar.gz (padrão: {_DEFAULT_ARCHIVE})",
    )
    parser.add_argument(
        "--output", type=str, default=_DEFAULT_OUTPUT,
        help=f"Diretório de saída dos WAVs (padrão: {_DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    extract_and_convert(args.archive, args.output, args.limit)


if __name__ == "__main__":
    main()
