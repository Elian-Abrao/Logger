"""logger package
================
Nome: Logger
Descricao: Pacote que oferece utilitarios simples de log estruturado.
Funcionalidades: inicializacao de logger, handlers, formatadores e extras.
Uso basico:
    from logger import start_logger
    log = start_logger("app")
"""

from .core import start_logger, SimpleLogger

__all__ = ["start_logger", "SimpleLogger"]
