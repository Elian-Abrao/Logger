"""cleanup.py - Função para limpar a tela do terminal."""

import os
from logging import Logger

__all__ = ["cleanup"]


def cleanup(self: Logger) -> None:
    """Limpa o terminal da plataforma atual."""
    cmd = "cls" if os.name == "nt" else "clear"
    os.system(cmd)
