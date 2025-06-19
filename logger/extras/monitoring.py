"""monitoring.py - Monitoramento de recursos do sistema.

Fornece a classe ``SystemMonitor`` para checagem de CPU e memória e funções
associadas ao ``Logger`` para registro dessas informações e detecção de
vazamento de memória.
"""

from logging import Logger
from collections import defaultdict
from typing import Dict, Tuple
import psutil
import gc

from .progress import format_block


class SystemMonitor:
    """Realiza leitura de uso de CPU e memória do processo atual."""

    def __init__(self) -> None:
        self._process = psutil.Process()
        self._baseline_memory: float | None = None
        self._object_counts: Dict[str, int] | None = None

    def get_memory_usage(self) -> Tuple[float, float]:
        """Retorna memória do processo em MB e uso total do sistema em %."""
        mem = self._process.memory_info().rss / (1024 * 1024)
        sys_mem = psutil.virtual_memory().percent
        return mem, sys_mem

    def get_cpu_usage(self) -> Tuple[float, float]:
        """Retorna CPU do processo e do sistema em porcentagem."""
        proc_cpu = self._process.cpu_percent(interval=None)
        sys_cpu = psutil.cpu_percent()
        return proc_cpu, sys_cpu

    def _count_objects(self) -> Dict[str, int]:
        counts: Dict[str, int] = defaultdict(int)
        for obj in gc.get_objects():
            counts[type(obj).__name__] += 1
        return counts

    def take_memory_snapshot(self) -> None:
        """Registra estado atual de uso de memória e contagem de objetos."""
        self._baseline_memory = self.get_memory_usage()[0]
        self._object_counts = self._count_objects()

    def get_memory_diff(self) -> Tuple[float, Dict[str, int]]:
        """Compara o estado atual com o snapshot anterior."""
        if self._baseline_memory is None:
            return 0.0, {}
        current_memory = self.get_memory_usage()[0]
        memory_diff = current_memory - self._baseline_memory
        current_counts = self._count_objects()
        diff = {
            name: current_counts.get(name, 0) - self._object_counts.get(name, 0)
            for name in set(current_counts) | set(self._object_counts or {})
            if current_counts.get(name, 0) != self._object_counts.get(name, 0)
        }
        return memory_diff, diff


def logger_log_system_status(self: Logger, level: str = "INFO", return_block: bool = False) -> str | None:
    """Loga o status atual de CPU e memória."""
    proc_mem, sys_mem = self._monitor.get_memory_usage()
    proc_cpu, sys_cpu = self._monitor.get_cpu_usage()
    lines = [
        f"CPU: Processo {proc_cpu:.1f}% • Sistema: {sys_cpu:.1f}%",
        f"Memória: {proc_mem:.1f}MB • Sistema: {sys_mem:.1f}%",
    ]
    block = format_block("STATUS DO SISTEMA", lines)
    if return_block:
        return block
    getattr(self, level.lower())(f"\n{block}")


def logger_memory_snapshot(self: Logger) -> None:
    """Armazena um snapshot de memória para comparação futura."""
    self._monitor.take_memory_snapshot()
    self.debug("Snapshot de memória registrado")


def logger_check_memory_leak(self: Logger, level: str = "WARNING") -> None:
    """Verifica diferenças de uso de memória indicando possível vazamento."""
    memory_diff, obj_diff = self._monitor.get_memory_diff()
    if not memory_diff and not obj_diff:
        return
    lines = [f"Diferença de memória: {memory_diff:.1f}MB"]
    for name, diff in obj_diff.items():
        lines.append(f"{name}: {diff:+d}")
    block = format_block("VAZAMENTO DE MEMÓRIA", lines)
    getattr(self, level.lower())(f"\n{block}")


def _setup_monitoring(logger: Logger) -> None:
    """Conecta o ``SystemMonitor`` à instância do logger."""
    monitor = SystemMonitor()
    setattr(logger, "_monitor", monitor)
    setattr(Logger, "log_system_status", logger_log_system_status)
    setattr(Logger, "memory_snapshot", logger_memory_snapshot)
    setattr(Logger, "check_memory_leak", logger_check_memory_leak)
