"""logger_core.py - Configuração principal do logger.

Este módulo orquestra a criação do logger estruturado, delegando
funcionalidades específicas para módulos em ``logger.extras``.
"""

from __future__ import annotations

import logging
from logging import Logger, FileHandler
from pathlib import Path

from logger.formatters.custom import (
    CustomFormatter,
    AutomaticTracebackLogger,
    _define_custom_levels,
)
from logger.handlers import ProgressStreamHandler
from logger.core.context import _setup_context_and_profiling
from logger.extras import (
    _init_colorama,
    _setup_directories,
    _get_log_filename,
    logger_sleep,
    logger_timer,
    logger_progress,
    logger_capture_prints,
    _setup_metrics,
    _setup_monitoring,
    _setup_dependencies_and_network,
    _setup_lifecycle,
    screen,
    cleanup,
    path,
    debug_path,
    pause,
)


# ---------------------------------------------------------------------------
# Logger configuration
# ---------------------------------------------------------------------------

def _configure_base_logger(
    name: str | None,
    log_dir: str,
    console_level: str = "INFO",
    file_level: str = "DEBUG",
) -> Logger:
    """Cria e configura a instância base do ``Logger``."""

    _init_colorama()
    _define_custom_levels()

    console_level_value = getattr(logging, console_level)

    base = Path(log_dir)
    screen_dir, debug_dir = _setup_directories(base)
    filename = _get_log_filename(name)

    logging.setLoggerClass(AutomaticTracebackLogger)
    logger = logging.getLogger(name)
    logger.setLevel(console_level_value)
    logger.handlers.clear()

    datefmt = "%Y-%m-%d %H:%M:%S"
    console_fmt = "{asctime} {emoji} {levelname_color}{levelpad}- {message} {thread_disp}"
    file_fmt = (
        "{asctime} {emoji} {levelname}{levelpad}- {message} <> "
        "     [{pathname}:{lineno}] - [Cadeia de Funcoes: {call_chain}📍] {thread_disp}"
    )

    ch = ProgressStreamHandler()
    ch.setFormatter(CustomFormatter(fmt=console_fmt, datefmt=datefmt, style="{"))
    logger.addHandler(ch)

    formatter = CustomFormatter(fmt=file_fmt, datefmt=datefmt, style="{", use_color=False)
    fh_dbg = FileHandler(debug_dir / filename, encoding="utf-8")
    fh_dbg.setLevel(logging.DEBUG)
    fh_dbg.setFormatter(formatter)
    logger.addHandler(fh_dbg)

    fh_info = FileHandler(base / filename, encoding="utf-8")
    fh_info.setLevel(logging.INFO)
    fh_info.setFormatter(formatter)
    logger.addHandler(fh_info)

    # Atributos utilizados pelas funções auxiliares
    setattr(logger, "_screen_dir", screen_dir)
    setattr(logger, "_screen_name", name or "log")

    file_path = base / filename
    debug_log_path = debug_dir / filename
    setattr(logger, "log_path", str(file_path))
    setattr(logger, "debug_log_path", str(debug_log_path))

    # Conecta funções utilitárias
    setattr(Logger, "screen", screen)
    setattr(Logger, "cleanup", cleanup)
    setattr(Logger, "path", path)
    setattr(Logger, "debug_path", debug_path)
    setattr(Logger, "pause", pause)
    setattr(Logger, "sleep", logger_sleep)
    setattr(Logger, "timer", logger_timer)
    setattr(Logger, "progress", logger_progress)
    setattr(Logger, "capture_prints", logger_capture_prints)

    return logger


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def start_logger(
    name: str | None = None,
    log_dir: str = "Logs",
    console_level: str = "INFO",
    file_level: str = "DEBUG",
    capture_prints: bool = True,
) -> Logger:
    """Cria e configura uma nova instância de ``Logger``."""

    logger = _configure_base_logger(name, log_dir, console_level, file_level)
    _setup_metrics(logger)
    _setup_monitoring(logger)
    _setup_context_and_profiling(logger)
    _setup_dependencies_and_network(logger)
    _setup_lifecycle(logger)
    if capture_prints:
        logger.capture_prints(True)
    return logger
