"""
Golden Dataset — Pipeline de Geração de Deepfakes de Voz por Conversão RVC.

Ponto de entrada da aplicação. Delega toda a inicialização ao AppModule.

Uso (via Python portátil):
    .\\py\\python.exe main.py                         # Modo teste (5 por voz, stratified)
    .\\py\\python.exe main.py --full                   # Lote completo, stratified
    .\\py\\python.exe main.py --strategy cross --full  # Lote completo, todos × todos
    .\\py\\python.exe main.py --voice ronaldo          # Apenas um modelo de voz
    .\\py\\python.exe main.py --limit 20               # Máximo 20 arquivos por voz
    .\\py\\python.exe main.py --list-models            # Lista modelos disponíveis
    .\\py\\python.exe main.py --config outro.yaml      # Config alternativo
"""

import sys

from app.app_module import AppModule


def main() -> None:
    """Inicializa o AppModule e executa o pipeline via controlador CLI."""
    AppModule().start(sys.argv[1:])


if __name__ == "__main__":
    main()
