"""core.py
---------
Nome: Core
Descricao: Modulo principal que instancia o logger e fornece funcionalidades basicas.
Funcionalidades:
- Cria instancias de SimpleLogger
- Associa handlers de console e arquivo
- Expõe metodos utilitarios timer e progress
Uso:
    from logger.core import start_logger
    log = start_logger("app")
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from .handlers import create_console_handler, create_file_handler
from .extras import Timer, progress


class SimpleLogger(logging.Logger):
    """Logger extendido com utilitarios extras."""

    def timer(self, name: str):
        return Timer(self, name)

    def progress(self, iterable, desc: str = ""):
        return progress(iterable, desc)


def start_logger(name: str,
                 log_file: Optional[str | Path] = None,
                 level: int = logging.INFO) -> SimpleLogger:
    """Cria e configura uma instancia de ``SimpleLogger``."""
    logging.setLoggerClass(SimpleLogger)
    logger = logging.getLogger(name)  # type: SimpleLogger
    logger.setLevel(level)
    logger.handlers.clear()

    logger.addHandler(create_console_handler(level))
    if log_file:
        logger.addHandler(create_file_handler(Path(log_file), level))

    return logger
