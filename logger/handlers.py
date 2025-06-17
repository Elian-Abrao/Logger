"""handlers.py
--------------
Nome: Handlers
Descricao: Modulo que cria manipuladores de log para console e arquivo.
Funcionalidades: fornece funcoes para gerar handlers com formatadores definidos.
Uso:
    handler = create_console_handler(formatter)
"""

import logging
from pathlib import Path
from .formatters import ColoredFormatter


def create_console_handler(level: int = logging.INFO) -> logging.Handler:
    """Retorna um handler para o console."""
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(ColoredFormatter("%(levelname)s: %(message)s"))
    return handler


def create_file_handler(path: Path, level: int = logging.INFO) -> logging.Handler:
    """Cria um handler que grava logs em arquivo."""
    handler = logging.FileHandler(path)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
    return handler
