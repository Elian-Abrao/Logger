"""formatters.py
----------------
Nome: Formatters
Descricao: Modulo responsavel pelos formatadores de log.
Funcionalidades: adiciona cores as mensagens e define layout basico.
Uso:
    from logger.formatters import ColoredFormatter
"""

import logging
from colorama import Fore, Style

class ColoredFormatter(logging.Formatter):
    """Formata mensagens de log com cores por nivel."""

    COLORS = {
        "DEBUG": Fore.BLUE,
        "INFO": Fore.GREEN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.MAGENTA,
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        record.levelname = f"{color}{record.levelname}{Style.RESET_ALL}"
        return super().format(record)
