"""logger_core.py - Configuração principal do logger.

Este módulo orquestra a criação do logger estruturado, delegando
funcionalidades específicas para módulos em ``logger.extras``.
"""

from __future__ import annotations

import logging
from logging import Logger, FileHandler
from pathlib import Path
from typing import Iterable

from logger.formatters.custom import (
    CustomFormatter,
    AutomaticTracebackLogger,
    _define_custom_levels,
)
from logger.handlers import ProgressStreamHandler, FileOnlyFilter
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

# ----- Função principal -----------------------------------------------------
def start_logger(
    name: str | None = None,
    log_dir: str = "Logs",
    console_level: str = "INFO",
    file_level: str = "DEBUG",
    capture_prints: bool = True,
    verbose: int = 0,
    *,
    show_profiling: bool = False,
    show_all_leaks: bool = False,
    watch_objects: Iterable[str] | None = None,
) -> Logger:
    """
    Cria e devolve um Logger configurado.

    verbose:
        0 → sem detalhes extras no log INFO;
        1 → só call_chain;
        2 → + pathname:lineno;
        3+ → pathname:lineno + thread_disp (máx).

    show_all_leaks:
        Se ``True`` exibe todas as diferenças de objetos na verificação de
        memória. Caso ``False`` (padrão) apenas diferenças relevantes são
        mostradas.

    watch_objects:
        Lista de tipos de objetos para acompanhar sempre na verificação de
        vazamento de memória.

    show_profiling:
        Define se o resumo de profiling será exibido ao final da execução.
    """
    logger = _configure_base_logger(
        name, log_dir, console_level, file_level, verbose
    )
    _setup_metrics(logger)
    _setup_monitoring(logger)
    _setup_context_and_profiling(logger)
    _setup_dependencies_and_network(logger)
    _setup_lifecycle(logger)
    setattr(logger, "_show_profiling", show_profiling)
    setattr(logger, "_leak_show_all", show_all_leaks)
    setattr(logger, "_leak_watch", set(watch_objects or []))
    setattr(logger, "_leak_threshold_mb", 5.0)
    if capture_prints:
        logger.capture_prints(True)  # type: ignore[attr-defined]
    logger.memory_snapshot()  # type: ignore[attr-defined]
    logger.start(show_profiling=show_profiling)  # type: ignore[attr-defined]
    return logger


# ----------------------- _configure_base_logger -----------------------------
def _configure_base_logger(
    name: str | None,
    log_dir: str,
    console_level: str = "INFO",
    file_level: str = "DEBUG",
    verbose: int = 0,
) -> Logger:
    """
    Monta toda a estrutura de logging (cores, arquivos, níveis).

    Retorna:
        Logger já configurado com handlers de console e arquivo.
    """
    # 🎨 Cores & níveis customizados
    _init_colorama()
    _define_custom_levels()

    console_level_value = getattr(logging, console_level)
    file_level_value    = getattr(logging, file_level)

    # 📂 Diretórios
    base = Path(log_dir)
    screen_dir, debug_dir = _setup_directories(base)

    filename = _get_log_filename(name)

    # 🪄 Subclasse que adiciona traceback automático
    logging.setLoggerClass(AutomaticTracebackLogger)
    logger = logging.getLogger(name)
    logger.setLevel(min(console_level_value, file_level_value))
    logger.handlers.clear()

    # --------------------- FORMATAÇÃO ---------------------------------------
    datefmt = "%Y-%m-%d %H:%M:%S"
    console_fmt = (
        "{asctime} {emoji} {levelname_color}{levelpad}- {message} {thread_disp}"
    )

    # Função helper que devolve o formato conforme verbose
    def _select_file_fmt(level: int) -> str:
        base_fmt   = "{asctime} {emoji} {levelname}{levelpad}- {message}"
        chain      = " [Cadeia de Funcoes: {call_chain}📍]"
        path_line  = " [{pathname}:{lineno}] -"
        thread     = " {thread_disp}"
        if level <= 0:
            return base_fmt
        elif level == 1:
            return f"{base_fmt} <>{chain}"
        elif level == 2:
            return f"{base_fmt} <>{path_line}{chain}"
        else:  # 3 ou mais
            return f"{base_fmt} <>{path_line}{chain}{thread}"

    file_fmt_info  = _select_file_fmt(verbose)   # ← para handler INFO
    file_fmt_debug = _select_file_fmt(3)         # ← verbosidade máxima

    # --------------------- HANDLERS -----------------------------------------
    # Console
    ch = ProgressStreamHandler()
    ch.setLevel(console_level_value)
    ch.setFormatter(CustomFormatter(fmt=console_fmt, datefmt=datefmt, style="{"))
    ch.addFilter(FileOnlyFilter())
    logger.addHandler(ch)

    # Arquivo DEBUG – sempre no formato máximo
    formatter_dbg = CustomFormatter(
        fmt=file_fmt_debug, datefmt=datefmt, style="{", use_color=False
    )
    fh_dbg = FileHandler(debug_dir / filename, encoding="utf-8")
    fh_dbg.setLevel(logging.DEBUG)
    fh_dbg.setFormatter(formatter_dbg)
    logger.addHandler(fh_dbg)

    # Arquivo INFO – formato depende de verbose
    formatter_info = CustomFormatter(
        fmt=file_fmt_info, datefmt=datefmt, style="{", use_color=False
    )
    fh_info = FileHandler(base / filename, encoding="utf-8")
    fh_info.setLevel(logging.INFO)
    fh_info.setFormatter(formatter_info)
    logger.addHandler(fh_info)

    # --------------------- METADADOS & AZÚCAR -------------------------------
    setattr(logger, "_screen_dir", screen_dir)
    setattr(logger, "_screen_name", name or "log")
    setattr(logger, "log_path",   str(base / filename))
    setattr(logger, "debug_log_path", str(debug_dir / filename))

    # Métodos utilitários
    setattr(Logger, "screen",          screen)
    setattr(Logger, "cleanup",         cleanup)
    setattr(Logger, "path",            path)
    setattr(Logger, "debug_path",      debug_path)
    setattr(Logger, "pause",           pause)
    setattr(Logger, "sleep",           logger_sleep)
    setattr(Logger, "timer",           logger_timer)
    setattr(Logger, "progress",        logger_progress)
    setattr(Logger, "capture_prints",  logger_capture_prints)

    return logger
