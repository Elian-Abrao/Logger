"""logger_lifecycle.py - Funções de início e término do logger."""

from logging import Logger
from pathlib import Path
from datetime import datetime
import os
import sys

from .progress import format_block, combine_blocks

__all__ = ["logger_log_start", "logger_log_end", "_setup_lifecycle"]


def logger_log_start(self: Logger, verbose: int = 1) -> None:
    """Exibe informações de início de execução."""
    folder = Path(os.getcwd()).name
    script = Path(sys.argv[0]).name
    now = datetime.now()
    data = now.strftime("%d/%m/%Y")
    hora = now.strftime("%H:%M:%S")

    lines = [
        "🚀 PROCESSO INICIADO",
        f"Data: {data} • Hora: {hora}",
        f"Script: {script} • Pasta: {folder}",
    ]
    banner = format_block("🚦INÍCIO", lines)
    blocks = [banner]

    if verbose >= 1:
        self.reset_metrics()
        status = self.log_system_status(return_block=True)
        env = self.log_environment(return_block=True)
        blocks.extend([status, env])

    if verbose >= 2:
        self.debug("Registrando snapshot inicial de memória...")
        self.memory_snapshot()

    banner_final = combine_blocks(blocks)
    self.success(f"\n{banner_final}", extra={"plain": True})


def logger_log_end(self: Logger, verbose: int = 1) -> None:
    """Exibe informações de encerramento de execução."""
    folder = Path(os.getcwd()).name
    script = Path(sys.argv[0]).name
    now = datetime.now()
    data = now.strftime("%d/%m/%Y")
    hora = now.strftime("%H:%M:%S")

    if verbose >= 2:
        self.report_metrics()
        self.debug("Verificando possíveis vazamentos de memória...")
        self.check_memory_leak()

    blocks: list[str] = []
    if verbose >= 1:
        blocks.append(self.log_system_status(return_block=True))

    lines = [
        "🏁 PROCESSO FINALIZADO",
        f"Data: {data} • Hora: {hora}",
        f"Script: {script} • Pasta: {folder}",
    ]
    banner = format_block("🏁 FIM", lines)
    blocks.insert(0, banner)
    banner_final = combine_blocks(blocks)
    self.success(f"\n{banner_final}", extra={"plain": True})


def _setup_lifecycle(logger: Logger) -> None:
    """Acopla funções de ciclo de vida ao ``Logger``."""
    setattr(Logger, "start", logger_log_start)
    setattr(Logger, "end", logger_log_end)
